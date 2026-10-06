"""第②步主清单 × 探针的契约测试。

清单（data/audit_checklist.json）与探针（core/site_business_audit.py）是两份分开维护的
东西：一漂移，界面就会把"根本没查"显示成"查过且没问题"，或让一条永远不会有结论的
条目占据报告。这里守的是结构与边界，不是文案。
"""

import json
import re
import time
from pathlib import Path

from core import audit_checklist as ac
from core import site_business_audit as sba
from core import site_signals as ss

ROOT = Path(__file__).parent.parent
RAW = json.loads((ROOT / "data" / "audit_checklist.json").read_text(encoding="utf-8"))
DATA = ac.load()
ITEMS = DATA["items"]
CORE_SRC = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "core").glob("*.py")}
CATALOG = json.loads((ROOT / "data" / "product_catalog.json").read_text(encoding="utf-8"))
CATALOG_SKUS = {p["sku"] for p in CATALOG["products"]}

# 一个 L2 形态的小站：有表单、有登录字段、有 GTM，没有购物车也没有 API
FIXTURE = """<!doctype html><html lang="en"><head>
<title>Acme Sdn Bhd - Steel Supply Selangor</title>
<meta name="description" content="Acme supplies and installs structural steel across Selangor since 1998.">
<link rel="canonical" href="https://acme.example/"><script src="/app.min.js"></script>
</head><body><h1>Acme Steel Supply</h1><h2>Products</h2><h2>Why us</h2>
<p>We supply steel for contractors. 25 years, 400 projects. Request a quote today.</p>
<ul><li>package RM 100</li><li>tier RM 200</li></ul>
<form action="/contact"><input name="email"><input type="password" name="pwd"></form>
<a href="tel:+60123456789">Call</a> <a href="https://wa.me/60123456789">WhatsApp</a>
<img src="/x.jpg" alt="steel"><img src="/y.webp" loading="lazy" srcset="a 1x">
<p>Lot 12, Jalan 5/1, 43000 Kajang, Selangor, Malaysia. SSM No. 200401234K</p>
<p>Privacy Policy · Terms of Use · 2026 Acme</p>
<script>(function(w,d,s,l){})(window,0,0,'dataLayer');
</script><script src="https://www.googletagmanager.com/gtm.js"></script>
<a href="/about">About</a><a href="/products">Products</a><a href="/contact">Contact</a>
</body></html>"""


def _signals(html=FIXTURE, headers=None):
    return ss.detect_signals(html, headers or {"server": "nginx"})


def _rows(html=FIXTURE, headers=None, level=None):
    sig = _signals(html, headers)
    found = sba._content_checks("https://acme.example", html, headers or {}, sig)
    lvl = level if level is not None else ss.classify_level(sig)[0]
    return ac.rows_from_findings(found, sig, lvl), sig, lvl


# ─── 清单自身的完整性 ─────────────────────────────────────────────────────────

def test_checklist_rows_are_well_formed():
    fields = RAW["fields"]
    ids = []
    for mid, mod in RAW["modules"].items():
        assert mod["bucket"] in {b for b, _, _ in ac.CONCLUSIONS}, f"{mid} 归到了不存在的结论桶"
        for row in mod["items"]:
            assert len(row) == len(fields), f"{mid} 有条目字段数不匹配"
            assert row[2] in RAW["how"], f"{row[0]} 的 how 不在类别表里"
            assert 1 <= int(row[3]) <= 5, f"{row[0]} 的 level 越界"
            assert row[5] in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"), f"{row[0]} 严重度非法"
            assert row[1] and row[7], f"{row[0]} 缺 label 或 why"
            assert isinstance(row[6], list), f"{row[0]} 的 remedy 必须是 SKU 列表（可以为空）"
            ids.append(row[0])
    assert len(ids) == len(set(ids)), "清单里有重复 id：同名条目会让对号入座只命中第一条"
    assert set(ids) == set(ITEMS)


def test_every_remedy_sku_is_a_real_vendor_product():
    unknown = sorted({s for it in ITEMS.values() for s in it["remedy"] if s not in CATALOG_SKUS})
    assert not unknown, f"清单推荐了目录里不存在的 SKU: {unknown}"


def test_gates_only_reference_signals_we_actually_detect():
    known = set(ss.SIGNAL_PATTERNS) | {"edge_cdn", "api_or_login"}
    missing = sorted({it["gate"] for it in ITEMS.values() if it["gate"] and it["gate"] not in known})
    assert not missing, f"条目依赖的信号没人产出，这些检查会被永久标为不适用: {missing}"


def test_probe_aliases_all_point_at_real_items():
    bad = [k for k, v in RAW["probe_ids"].items() if k not in ITEMS or not v]
    assert not bad, f"probe_ids 里有孤儿别名: {bad}"


def test_every_measurable_item_is_actually_probed():
    blob = "\n".join(CORE_SRC.values())
    alias = RAW["probe_ids"]
    emitted = set(re.findall(r'["\']([a-z0-9_]+)["\']', blob))
    unprobed = [i for i, it in ITEMS.items()
                if it["how"] in ac.MEASURED and i not in emitted and alias.get(i, i) not in emitted]
    assert not unprobed, f"这些条目声明成可从公网测，却没有任何探针产出结论: {unprobed}"


# ─── 探针结论必须落在清单里 ───────────────────────────────────────────────────

def test_content_checks_emit_only_known_checklist_items():
    rows, _, _ = _rows()
    emitted = [f["check"] for f in sba._content_checks(
        "https://acme.example", FIXTURE, {}, _signals())]
    unknown = sorted(set(emitted) - set(ITEMS))
    assert not unknown, f"探针输出了清单上没有的条目: {unknown}"
    assert len(emitted) == len(set(emitted)), "同一条目被判定两次，第一条会静默盖掉第二条"
    assert rows, "内容判据一条都没产出"


def test_states_come_from_the_six_value_vocabulary():
    rows, _, _ = _rows()
    allowed = {"pass", "fail", "unverified", "not_applicable", "not_tested"}
    assert {r["state"] for r in rows} <= allowed, "出现了状态机之外的状态"


def test_missing_probe_is_unverified_never_a_gap():
    rows, _, _ = _rows()
    graded_unmeasured = [r for r in rows
                         if r["state"] == "fail" and not r["measurable"]]
    assert not graded_unmeasured, "不可测条目被判成缺口"
    # 清单声明可测但探针没给结论 → unverified，且不得进分母
    row = {r["id"]: r for r in rows}["git_exposed"]
    assert row["state"] == "unverified" and row["observed"] == ""


def test_unverified_and_not_applicable_do_not_move_the_score():
    rows, _, _ = _rows()
    summary = ac.summary(rows, 2, "L2", [])
    graded = [r for r in rows if r["state"] in ("pass", "fail") and r["measurable"]]
    assert summary["items_graded"] == len(graded)
    assert summary["pass"] + summary["fail"] == len(graded)
    assert summary["not_applicable"] + summary["not_tested"] + summary["unverified"] > 0
    if summary["score"] is not None:
        assert summary["score"] == round(summary["pass"] / len(graded) * 100, 1)


def test_level_gating_switches_modules_off_with_a_readable_reason():
    rows, _, _ = _rows(level=1)
    high = [r for r in rows if r["level"] > 1]
    assert high, "L1 门槛下应至少有条目被关掉"
    assert all(r["state"] == "not_applicable" and r["skipped_reason"] for r in high)
    # 关掉条目不得改变"确凿结论"的集合：不适用既不是通过也不是缺口
    summary = ac.summary(rows, 1, "L1 Basic website", [])
    graded = {r["id"] for r in rows if r["state"] in ("pass", "fail")}
    assert graded.isdisjoint({r["id"] for r in high}), "被层级关掉的条目仍被判了通过/缺口"
    assert summary["items_graded"] == len(graded)


def test_gate_and_level_each_give_their_own_reason():
    sig = _signals()
    # 功能门槛优先：没看到购物车就不该去查结账面，理由要说出缺了哪个功能
    ok, why = ac.applicable({"level": 1, "gate": "checkout_present"}, sig, 5)
    assert ok is False and "cart or checkout" in why
    # 门槛过了但站型不够：理由要报出本站被判成哪一层
    ok, why = ac.applicable({"level": 4, "gate": ""}, sig, 2)
    assert ok is False and "L2" in why and "L4" in why
    # 站型够、门槛也过 —— 才是"该查"
    ok, why = ac.applicable({"level": 2, "gate": "login_form"}, sig, 2)
    assert ok is True and why == ""


def test_every_closed_row_reason_matches_why_it_closed():
    rows, sig, lvl = _rows()
    closed = [r for r in rows if r["state"] == "not_applicable"]
    assert closed, "fixture 是个小站，不可能所有条目都适用"
    for r in closed:
        reason = r["skipped_reason"]
        assert reason, f"{r['id']} 关掉了却没写原因"
        gate_missing = bool(r["gate"]) and not sig.get(r["gate"], {}).get("present")
        if gate_missing:
            assert "no matching feature" in reason, f"{r['id']} 因缺功能关闭: {reason}"
        else:
            assert f"L{lvl}" in reason, f"{r['id']} 因站型关闭，理由没报出站型: {reason}"


def test_customer_facing_checklist_text_is_english_only():
    """清单文案与关闭理由会直接进界面和 PDF 附录，混进中文就像报告坏了。"""
    cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff01-\uff5e]")
    bad = [i for i, it in ITEMS.items()
           if cjk.search(it["label"]) or cjk.search(it["why"])]
    assert not bad, f"checklist items mix in Chinese: {bad[:5]}"
    rows, _, _ = _rows()
    mixed = sorted({r["skipped_reason"] for r in rows if cjk.search(r["skipped_reason"] or "")})
    assert not mixed, f"closure reasons still carry Chinese: {mixed[:3]}"
    prose = sorted({f"{r['id']}.{f}={r.get(f)}" for r in rows
                    for f in ("observed", "detail") if cjk.search(str(r.get(f) or ""))})
    assert not prose, f"row wording still carries Chinese: {prose[:3]}"
    for _, title, blurb in ac.CONCLUSIONS:
        assert not cjk.search(title + blurb)


def test_catalog_copy_printed_into_the_quote_is_english_only():
    """产品名与说明原样印进蓝图和 PDF 报价表：读不到中文，也读不到术语。"""
    cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff01-\uff5e]")
    bad = [(p.get("sku"), k, p[k]) for p in CATALOG["products"]
           for k in ("name", "product_name", "category", "description", "billing")
           if cjk.search(str(p.get(k) or ""))]
    assert not bad, f"catalog fields still Chinese: {bad[:3]}"


def test_four_conclusions_cover_every_bucket_and_rate_vocabulary():
    rows, _, lvl = _rows()
    cons = ac.rollup(rows)
    assert [c["bucket"] for c in cons] == [b for b, _, _ in ac.CONCLUSIONS]
    for c in cons:
        assert c["title"] and c["result"] and c["rate"]
        assert c["rate"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "OK", "N/A")
        assert set(c["counts"]) == {"pass", "fail", "unverified", "not_applicable",
                                    "not_tested", "measured"}
        assert c["counts"]["fail"] == 0 or c["rate"] not in ("OK", "N/A"), "有缺口却说 N/A"
        assert all(p["sku"] in CATALOG_SKUS and p["price_label"] for p in c["remedy_products"])


def test_product_prices_quote_the_billing_cycle_vendor_advertises():
    idx = ac.product_index()
    assert idx
    monthly = ac._product_line("DEMO-WP17-BUSINESS")
    assert "month" in monthly["price_label"], "月付产品被折算成年费报给客户"
    annual = ac._product_line("DEMO-CF-BOOSTER-PERSONAL")
    assert annual["price_label"].endswith("year")
    unpriced = ac._product_line("DEMO-AI-AGENT")
    assert unpriced["price_label"] == "price on request", "目录无公开单价时不得编一个金额"


# ─── 硬边界：只读、不打凭据、不扫端口、不注入载荷 ─────────────────────────────

def test_probes_stay_read_only_and_passive():
    src = CORE_SRC["site_business_audit.py"] + CORE_SRC["site_audit.py"]
    for verb in (".post(", ".put(", ".patch(", ".delete(", "Request(method="):
        assert verb not in src, f"探针里出现了写请求 {verb}"
    assert "smtplib" not in src and "paramiko" not in src
    assert not re.search(r"range\(\s*1\s*,\s*(6553[0-9]|65536)", src), "出现了端口段扫描"


def test_no_credential_or_payload_guessing_anywhere_in_the_probes():
    src = CORE_SRC["site_business_audit.py"]
    assert not re.search(r"(user_?login|admin)\s*[:=]\s*\w", src), "出现了尝试凭据的痕迹"
    for payload in ("<script>alert", "' OR 1=1", "../../etc/passwd", "union select"):
        assert payload not in src.lower(), f"探针里出现了注入载荷 {payload}"
    # 路径清单只能是固定条目，不能由页面内容拼出任意 URL 再去打
    for row in sba._PATH_PROBES:
        path = row[2]
        assert path is None or (path.startswith("/") and "?" not in path), \
            f"{row[0]} 的探测路径不是固定清单项"


def test_deep_probe_stops_at_its_deadline_and_says_so():
    """到点没测完的条目必须标 unverified，不能悄悄当成"没暴露"。"""
    sig = _signals()
    started = time.monotonic()
    findings, extras = sba.deep_findings(
        "http://cradilot-nope.invalid", FIXTURE, {}, "cradilot-nope.invalid", sig, {}, budget=1.0)
    spent = time.monotonic() - started
    assert spent < 6.0, f"深探超出时间预算：{spent:.1f}s"
    assert extras["probe_budget"] == 1.0
    rows = ac.rows_from_findings(findings, sig, 1)
    by_id = {r["id"]: r for r in rows}
    for probe, _, path, _e in sba._PATH_PROBES:
        if path is None:
            continue
        row = by_id.get(probe)
        if row and row["measurable"]:
            assert row["state"] in ("unverified", "not_applicable"), \
                f"{probe} 在打不通的主机上被判成 {row['state']}"


def test_a_403_on_a_sensitive_path_is_correct_configuration_not_a_finding():
    ok = sba._published_file_result("sitemap", "XML sitemap published", "/sitemap.xml", 404, "")
    assert ok["status"] == "fail", "缺 sitemap 是该告诉客户的缺口"
    moved = sba._published_file_result("sitemap", "XML sitemap published", "/sitemap.xml", 301, "")
    assert moved["status"] == "pass", "跳转后的 sitemap 一样能被爬虫取到"


def test_the_pdf_appendix_keeps_severity_on_confirmed_gaps_only():
    """附录 A 的严重度只属于实测缺口；内部哨兵 UNKNOWN 不许进客户的文件。

    UNKNOWN 在 core/audit_checklist.py 里与 INFO 同秩，意思是"这一项压根没测"。
    给一条 Not measured 标上 UNKNOWN 严重度，等于宣称我们知道一个并不存在的风险等级；
    而它印在顾问亲手递出去的文件里，看起来就是程序漏了原始枚举。
    """
    from typst_generator.compiler import _audit_appendix_blocks

    rows = [
        {"module_title": "Website & infrastructure", "label": "Software past end of support",
         "state": "fail", "severity": "HIGH", "observed": "PHP 7.4 reached end of support."},
        {"module_title": "Website & infrastructure", "label": "Domain and registrant ownership",
         "state": "unverified", "severity": "UNKNOWN", "observed": "Whois privacy is switched on."},
        {"module_title": "Authentication", "label": "Admin console exposure",
         "state": "not_tested", "severity": "UNKNOWN", "skipped_reason": "Needs inside access."},
    ]
    page = "\n".join(_audit_appendix_blocks({"site_audit": {
        "url": "https://example.my", "site_level": "L2", "level_label": "Brochure site",
        "rows": rows, "summary": {}}}))

    assert "UNKNOWN" not in page, "内部哨兵 UNKNOWN 漏进了客户附录"
    assert "Not measured" in page
    assert "Needs inside access" in page
    assert "Gap · HIGH" in page, "实测缺口要把严重度一并印出来"
