"""
Cradilot Core - 审计主清单装载、门控与结论汇总

单一事实来源：data/audit_checklist.json 定义"要查什么、能不能从外面查、缺了多严重、
用哪个 本公司产品补"。本模块只做三件事：
  1. 按站型（L1-L5）与已识别功能（signals）决定哪些条目适用；
  2. 把探针给出的 finding 逐条对号入座，缺 verdict 的一律标 unverified，绝不猜；
  3. 汇总成客户看得懂的四条结论（界面），明细留给 PDF。

不可测的条目（internal_access / human_review / external_service / interview）不参与
评分、不参与通过率、不在界面冒充"检查过"——它们只是顾问上门时要当面确认的清单。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKLIST_PATH = BASE_DIR / "data" / "audit_checklist.json"
CATALOG_PATH = BASE_DIR / "data" / "product_catalog.json"

# 只有这六类会真的去测；其余类别只能如实说明"从外面测不到"。
MEASURED = ("passive_http", "passive_dns", "passive_tls", "passive_tcp_targeted",
            "content_parse", "perf_sample")

# 界面四问：客户只该看到这四处结论，其余全进 PDF。
CONCLUSIONS = (
    ("hosting", "Cloud hosting & resilience",
     "Where your site actually runs, how fast it answers, and whether it survives a bad day."),
    ("security", "Security & exposure",
     "What the public internet can already see, reach or download from your site."),
    ("conversion", "Appeal & conversion potential",
     "Whether a stranger landing on your page can tell what you sell and reach you."),
    ("ai", "AI coverage of enquiries",
     "Whether anyone — human or automated — responds when the buyer asks, any hour."),
)

_STATE_ORDER = ("fail", "unverified", "not_tested", "pass", "not_applicable")
_SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0, "UNKNOWN": 0}

_CACHE: Dict[str, Any] = {}


def load(path: Optional[Path] = None) -> Dict[str, Any]:
    """把清单读成按 id 索引的字典；同一份数据只读一次。"""
    key = str(path or CHECKLIST_PATH)
    if _CACHE.get("key") == key:
        return _CACHE["data"]
    raw = json.loads(Path(key).read_text(encoding="utf-8"))
    fields = raw["fields"]
    probe_ids = raw.get("probe_ids") or {}
    by_probe: Dict[str, str] = {}
    items: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for mid, mod in raw["modules"].items():
        for row in mod["items"]:
            item = dict(zip(fields, row))
            item["module"] = mid
            item["module_title"] = mod["title"]
            item["bucket"] = mod["bucket"]
            item["probe"] = probe_ids.get(item["id"], item["id"])
            items[item["id"]] = item
            order.append(item["id"])
            by_probe.setdefault(item["probe"], item["id"])
    data = {
        "version": raw.get("version"),
        "how": raw["how"],
        "levels": raw["levels"],
        "modules": {k: {"title": v["title"], "bucket": v["bucket"]} for k, v in raw["modules"].items()},
        "items": items,
        "order": order,
        "by_probe": by_probe,
    }
    _CACHE["key"] = key
    _CACHE["data"] = data
    return data


def product_index() -> Dict[str, Dict[str, Any]]:
    """SKU → 产品名与年费。界面与 PDF 对客户说产品名，不说内部编号。"""
    if "products" in _CACHE:
        return _CACHE["products"]
    idx: Dict[str, Dict[str, Any]] = {}
    try:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        for p in raw.get("products") or []:
            idx[str(p.get("sku"))] = {"name": p.get("name") or str(p.get("sku")),
                                      "billing": p.get("billing") or "",
                                      "monthly_myr": p.get("monthly_myr"),
                                      "annual_myr": p.get("annual_myr"),
                                      "category": p.get("category") or ""}
    except Exception:
        idx = {}
    _CACHE["products"] = idx
    return idx


def applicable(item: Dict[str, Any], signals: Dict[str, Any], level: int) -> Tuple[bool, str]:
    """条目是否适用于本站：先过功能门槛，再过层级门槛。"""
    gate = item.get("gate") or ""
    if gate and not signals.get(gate, {}).get("present"):
        note = signals.get(gate, {}).get("note") or gate
        return False, f"Not applicable — we saw no matching feature: {note}."
    if int(item["level"]) > level:
        return False, (f"Site classified as L{level}; this check only applies from "
                       f"L{item['level']} onwards.")
    return True, ""


def rows_from_findings(findings: List[Dict[str, Any]], signals: Dict[str, Any],
                       level: int) -> List[Dict[str, Any]]:
    """
    把探针结论对到清单条目上。

    三种来源状态要分清：not_applicable（门槛未过，压根不该查）、not_tested（该查但这类
    检查从公网看不到，留给顾问/客户后台）、以及真正的 pass/fail/unverified。
    任何"没有对应 finding"的适用条目都记 unverified，不记 fail。
    """
    data = load()
    by_id: Dict[str, Dict[str, Any]] = {}
    for f in findings or []:
        cid = str(f.get("check") or "")
        owner = data["items"].get(cid) and cid or data["by_probe"].get(cid)
        if owner and owner not in by_id:
            by_id[owner] = f

    rows: List[Dict[str, Any]] = []
    for iid in data["order"]:
        item = data["items"][iid]
        applies, why_na = applicable(item, signals, level)
        finding = by_id.get(iid)
        row = {
            "id": iid,
            "label": item["label"],
            "module": item["module"],
            "module_title": item["module_title"],
            "bucket": item["bucket"],
            "how": item["how"],
            "how_note": data["how"][item["how"]],
            "level": int(item["level"]),
            "severity": item["severity"],
            "remedy": item["remedy"],
            "why": item["why"],
            "gate": item.get("gate") or "",
            "state": "unverified",
            "observed": "",
            "detail": "",
            "skipped_reason": "",
            "measurable": item["how"] in MEASURED,
        }
        if not applies:
            row["state"] = "not_applicable"
            row["skipped_reason"] = why_na
        elif item["how"] not in MEASURED:
            row["state"] = "not_tested"
            row["skipped_reason"] = data["how"][item["how"]]
        elif finding is None:
            row["state"] = "unverified"
            row["skipped_reason"] = "Probe did not return a result on this run."
        else:
            row["state"] = finding.get("status") or "unverified"
            row["observed"] = finding.get("observed") or ""
            row["detail"] = finding.get("plain") or ""
            row["severity"] = finding.get("severity") or item["severity"]
            if finding.get("vendor_skus"):
                row["remedy"] = finding["vendor_skus"]
            if row["state"] == "unverified":
                row["skipped_reason"] = finding.get("plain") or "Not verified this run."
        rows.append(row)
    return rows


def _rate(rows: List[Dict[str, Any]]) -> str:
    """四条结论右上角的"Rate"：取已测失败项里最重的一档；没测到就 N/A。"""
    fails = [r for r in rows if r["state"] == "fail"]
    if not fails:
        measured_any = [r for r in rows if r["state"] in ("pass", "fail")]
        return "N/A" if not measured_any else "OK"
    return max(fails, key=lambda r: _SEVERITY_RANK.get(r["severity"], 0))["severity"]


def _headline(bucket: str, rows: List[Dict[str, Any]], rate: str) -> str:
    """一句话结论：只由实测缺口拼出来，缺口为空时说"没发现问题"而不是"没问题"。"""
    fails = [r for r in rows if r["state"] == "fail"]
    top = sorted(fails, key=lambda r: -_SEVERITY_RANK.get(r["severity"], 0))[:3]
    if not top:
        if any(r["state"] == "pass" for r in rows):
            return "Nothing measured here came back as a gap."
        return "Not enough was measured to give you a verdict."
    joined = " + ".join(r["label"].lower() for r in top)
    lead = {"hosting": "Your cloud placement and resilience let you down: ",
            "security": "Exposed to the public internet: ",
            "conversion": "Visitors cannot act on your site: ",
            "ai": "Nobody answers buyers automatically: "}[bucket]
    return lead + joined + "."


def _sentence(item: Dict[str, Any]) -> str:
    return f"{item['label']} — {item['why']}"


def rollup(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """四个概念结论：Title / Result / Rate + 对应方案一行。"""
    out: List[Dict[str, Any]] = []
    for bucket, title, blurb in CONCLUSIONS:
        mine = [r for r in rows if r["bucket"] == bucket]
        measured = [r for r in mine if r["measurable"] and r["state"] != "not_applicable"]
        fails = [r for r in measured if r["state"] == "fail"]
        passes = [r for r in measured if r["state"] == "pass"]
        unknown = [r for r in measured if r["state"] == "unverified"]
        rate = _rate(measured)
        remedies: List[str] = []
        for f in sorted(fails, key=lambda r: -_SEVERITY_RANK.get(r["severity"], 0)):
            for sku in f["remedy"]:
                if sku not in remedies:
                    remedies.append(sku)
        out.append({
            "bucket": bucket,
            "title": title,
            "question": blurb,
            "result": _headline(bucket, measured, rate),
            "rate": rate,
            "counts": {"pass": len(passes), "fail": len(fails), "unverified": len(unknown),
                       "not_applicable": len([r for r in mine if r["state"] == "not_applicable"]),
                       "not_tested": len([r for r in mine if r["state"] == "not_tested"]),
                       "measured": len(measured)},
            "gaps": [_sentence(f) for f in fails[:6]],
            "remedies": remedies,
            "remedy_products": [_product_line(sku) for sku in remedies[:4]],
        })
    return out


def _product_line(sku: str) -> Dict[str, Any]:
    p = product_index().get(sku) or {}
    monthly, annual = p.get("monthly_myr"), p.get("annual_myr")
    if str(p.get("billing") or "").lower() == "monthly" and monthly:
        price = f"RM {_money(monthly)} / month"
    elif annual:
        price = f"RM {_money(annual)} / year"
    elif monthly:
        price = f"RM {_money(monthly)} / month"
    else:
        price = "price on request"      # 目录标 not_priced：只能定性提及，不编金额
    return {"sku": sku, "name": p.get("name") or sku, "price_label": price,
            "annual_myr": annual, "billing": p.get("billing") or ""}


def _money(value: Any) -> str:
    num = float(value)
    return f"{num:,.0f}" if abs(num - round(num)) < 0.005 else f"{num:,.2f}"


def advisory_items(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按"从外面看不到"的原因分组，供 PDF 与顾问电话使用。"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        if r["state"] != "not_tested":
            continue
        groups.setdefault(r["how"], []).append(r)
    return groups


def summary(rows: List[Dict[str, Any]], level: int, level_label: str,
            fired: List[str]) -> Dict[str, Any]:
    measured = [r for r in rows if r["measurable"] and r["state"] != "not_applicable"]
    graded = [r for r in measured if r["state"] in ("pass", "fail")]
    return {
        "level": f"L{level}",
        "level_label": level_label,
        "level_evidence": fired,
        "items_total": len(rows),
        "items_measured": len(measured),
        "items_graded": len(graded),
        "pass": len([r for r in graded if r["state"] == "pass"]),
        "fail": len([r for r in graded if r["state"] == "fail"]),
        "unverified": len([r for r in measured if r["state"] == "unverified"]),
        "not_applicable": len([r for r in rows if r["state"] == "not_applicable"]),
        "not_tested": len([r for r in rows if r["state"] == "not_tested"]),
        "score": round(len([r for r in graded if r["state"] == "pass"]) / len(graded) * 100, 1)
        if graded else None,
        "score_note": (f"{len(graded)} of {len(measured)} applicable checks produced a definite "
                       "result. Unverified items are excluded from the score, not counted as gaps."),
    }
