"""
官网机检引擎契约测试。

刻意全部离线：用构造好的响应头与 HTML 片段断言判定规则，不打真实网络。
这些用例锁的是三类容易回退的行为：
  1. unverified 不得被折算成 fail（测不到 ≠ 没有）
  2. 已知的误报模式不得复发（WordPress rel=profile、Cloudflare 边缘 IP 判机房）
  3. 每条 fail 必须带真实存在的 SKU，蓝图与采购车才不会引用查无此物的产品
"""

import pytest

from core import vuln_intel
from core.vuln_intel import fingerprint_components
from core.site_audit import (
    _check_headers, _check_known_vulnerabilities, _check_mixed_content, _check_mobile,
    _check_origin_concealment, _check_exposed_services, _check_parked_or_placeholder,
    _check_speed, _check_technology, _check_wordpress_plugins, _identify_bytes,
    _PORT_RISK, _summarize, _worst, _finding, detect_cloudflare, audit_website,
)
from core.product_catalog import catalog, parse_headcount


# ─── 状态三态契约 ─────────────────────────────────────────────────────────────
def test_finding_only_allows_three_states():
    for status in ("pass", "fail", "unverified"):
        assert _finding("c", "t", status, "o", "p")["status"] == status


def test_unverified_never_counts_toward_score_denominator():
    """未核验项不进分母，否则"这次没测到"会伪装成"贵司缺失该项"。"""
    findings = [
        _finding("a", "A", "pass", "o", "p"),
        _finding("b", "B", "fail", "o", "p", "HIGH"),
        _finding("c", "C", "unverified", "本次网络不可达", "p"),
        _finding("d", "D", "unverified", "本次网络不可达", "p"),
    ]
    summary = _summarize(findings, 0.0, "example.my", "https://example.my", True)
    assert summary["pass"] == 1
    assert summary["fail"] == 1
    assert summary["unverified"] == 2
    assert summary["graded_checks"] == 2
    assert summary["score"] == pytest.approx(50.0)
    assert "not counted in the score" in summary["score_note"]


def test_empty_audit_yields_no_invented_score():
    summary = _summarize([], 0.0, "x.my", "https://x.my", False)
    assert summary["score"] is None
    assert summary["graded_checks"] == 0


# ─── 已知误报的回归 ───────────────────────────────────────────────────────────
def test_wordpress_profile_link_is_not_mixed_content():
    """<link rel="profile" href="http://gmpg.org/..."> 浏览器从不加载，不得算混合内容。"""
    html = ('<html><head><link rel="profile" href="http://gmpg.org/xfn/11"></head>'
            '<body><script src="https://cdn.example/a.js"></script></body></html>')
    out = _check_mixed_content(html, "https://example.my")[0]
    assert out["status"] == "pass"


def test_real_insecure_script_is_mixed_content():
    html = '<html><body><script src="http://evil.example/x.js"></script></body></html>'
    out = _check_mixed_content(html, "https://example.my")[0]
    assert out["status"] == "fail"
    assert "evil.example" in out["observed"]


def test_insecure_form_action_is_caught():
    html = '<html><body><form action="http://api.example/lead"></form></body></html>'
    out = _check_mixed_content(html, "https://example.my")[0]
    assert out["status"] == "fail"


def test_cloudflare_edge_ip_does_not_trigger_offshore_verdict():
    """站点经 Cloudflare 时源站被遮住，不得据此说"服务器在外国"并劝人搬主机。"""
    hdrs = {"server": "cloudflare", "cf-ray": "8f3a:LHR"}
    state = detect_cloudflare("anything.example", hdrs)
    assert state["behind"] is True
    assert any("cloudflare" in s.lower() for s in state["signals"])


def test_resolve_count_alone_is_not_cloudflare_evidence():
    """通用解析信息不得被当成 Cloudflare 痕迹，否则所有能解析的域名都"已在用 CF"。"""
    state = detect_cloudflare("no-such-host.invalid", {})
    assert state["behind"] is False
    assert not any("Resolved" in s for s in state["signals"])


# ─── 响应头与移动端 ───────────────────────────────────────────────────────────
def test_all_headers_present_scores_pass_and_sells_nothing():
    """全项通过时必须明确"不需要额外花钱"，不能为了成单硬凑缺口。"""
    hdrs = {
        "strict-transport-security": "max-age=31536000; includeSubDomains",
        "content-security-policy": "default-src 'self'",
        "x-frame-options": "DENY",
        "x-content-type-options": "nosniff",
        "referrer-policy": "strict-origin-when-cross-origin",
        "server": "LiteSpeed",
    }
    findings = _check_headers(hdrs)
    overall = [f for f in findings if f["check"] == "header_score"][0]
    assert overall["status"] == "pass"
    assert "no extra spend is needed here" in overall["plain"]
    assert overall["vendor_skus"] == []


def test_missing_three_headers_is_high_and_maps_to_cdn():
    findings = _check_headers({"server": "Apache/2.4.52"})
    overall = [f for f in findings if f["check"] == "header_score"][0]
    assert overall["status"] == "fail"
    assert overall["severity"] == "HIGH"
    assert "DEMO-CF-BOOSTER-PERSONAL" in overall["vendor_skus"]


def test_server_version_disclosure_flagged():
    findings = _check_headers({"server": "Microsoft-IIS/10.0"})
    hit = [f for f in findings if f["check"] == "server_version_disclosure"][0]
    assert hit["status"] == "fail"


def test_cookie_flags_checked_only_when_cookies_are_set():
    weak = [f for f in _check_headers({"set-cookie": "session=abc; path=/"})
            if f["check"] == "cookie_flags"][0]
    assert weak["status"] == "fail"
    assert "Secure" in weak["observed"]

    good = [f for f in _check_headers(
        {"set-cookie": "session=abc; Secure; HttpOnly; SameSite=Lax; path=/"}
    ) if f["check"] == "cookie_flags"][0]
    assert good["status"] == "pass"
    assert good["vendor_skus"] == []

    # 首页不下发 Cookie 时该项无从评判，报 unverified 而不是"通过"或"缺陷"
    none = [f for f in _check_headers({}) if f["check"] == "cookie_flags"][0]
    assert none["status"] == "unverified"


def test_missing_viewport_is_high_and_points_at_builder():
    out = _check_mobile("<html><head><title>x</title></head></html>")[0]
    assert out["status"] == "fail"
    assert out["severity"] == "HIGH"
    assert "DEMO-WP17-BUSINESS" in out["vendor_skus"]


# ─── 空壳与性能 ───────────────────────────────────────────────────────────────
def test_parked_domain_page_is_treated_as_worse_than_none():
    html = "<html><body>This domain is for sale. Buy this domain today.</body></html>"
    out = _check_parked_or_placeholder(html, 200)[0]
    assert out["status"] == "fail"
    assert "parked" in out["plain"] or "placeholder" in out["plain"]


def test_thin_placeholder_page_fails():
    out = _check_parked_or_placeholder("<html><body>Coming soon</body></html>", 200)[0]
    assert out["status"] == "fail"


def test_substantive_page_passes_without_selling():
    html = "<html><body>" + ("关于我们 产品目录 霹雳州怡保 报价电话 05-540 1234 " * 30) + "</body></html>"
    out = _check_parked_or_placeholder(html, 200)[0]
    assert out["status"] == "pass"
    assert out["vendor_skus"] == []


def test_speed_thresholds_and_missing_timing_is_unverified():
    assert _check_speed(600, 40_000)[0]["status"] == "pass"
    assert _check_speed(3000, 40_000)[0]["severity"] == "HIGH"
    assert _check_speed(None, None)[0]["status"] == "unverified"


def test_oversized_homepage_reported():
    out = _check_speed(900, 4_000_000)
    assert any(f["check"] == "page_weight" and f["status"] == "fail" for f in out)


def test_legacy_jquery_is_surfaced():
    html = '<html><head><script src="/js/jquery-1.12.4.min.js"></script></head></html>'
    out = _check_technology(html, {})[0]
    assert "jQuery 1.x" in out["observed"]


# ─── 产品目录契约 ─────────────────────────────────────────────────────────────
def test_every_fail_finding_references_a_real_sku():
    """蓝图与采购车不得引用查无此物的产品：所有 SKU 必须能在目录里取到。"""
    hdrs = {"server": "Apache/2.4.49"}
    samples = (_check_headers(hdrs) + _check_mobile("<html></html>")
               + _check_mixed_content('<script src="http://a/b.js"></script>', "https://x")
               + _check_parked_or_placeholder("<html><body>short</body></html>", 200)
               + _check_speed(9000, 10))
    for f in samples:
        for sku in f["vendor_skus"]:
            assert catalog.get(sku) is not None, f"虚构 SKU {sku}"


def test_headcount_uses_lower_bound_of_band():
    """取下界：宁可少算席位低估总价，也不要给老板报一个虚高数字。"""
    assert parse_headcount("6-15 人") == 6
    assert parse_headcount("1-10 人") == 1
    assert parse_headcount(None) == 10
    assert parse_headcount("21 人以上") == 21


def test_mail_pro_is_priced_in_ten_user_blocks():
    assert catalog.annual_for("DEMO-MAIL-PRO-10U", seats=6) == pytest.approx(831.60)
    assert catalog.annual_for("DEMO-MAIL-PRO-10U", seats=21) == pytest.approx(2494.80)


def test_unpriced_product_returns_none_not_zero():
    """AI Agent 无公开价：必须返回 None，让上层显示"待报价"，而不是算成 0 元。"""
    assert catalog.annual_for("DEMO-AI-AGENT", seats=10) is None


def test_fabricated_legacy_skus_are_gone():
    for bogus in ("DEMO-BMAIL-PRO-5U", "DEMO-ACRONIS-500G", "DEMO-VPS-LINUX-2C4G",
                  "DEMO-STARTER-COMBO", "DEMO-WP-AI-EBIZ17"):
        assert catalog.get(bogus) is None, f"{bogus} 系旧版虚构 SKU，应已移除"


# ─── 入口守卫 ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("bad", ["", "   "])
def test_blank_url_short_circuits(bad):
    res = audit_website(bad)
    assert res["success"] is False
    assert res["findings"] == []


# ─── 网络专家层：漏洞情报 / 配置面 / 攻击面 ──────────────────────────────────
WP_ASSET_MARKUP = """
<link rel='stylesheet' id='dash-css'  href='/wp-includes/css/dashicons.min.css?ver=7.2-alpha-63675'>
<script src='/wp-includes/js/jquery/jquery.min.js?ver=7.2-alpha-63675'></script>
<script src='/wp-includes/js/jquery/jquery-migrate.min.js?ver=3.4.1'></script>
"""

CDN_MARKUP = """
<script src='https://cdn.jsdelivr.net/npm/jquery@1.12.4/dist/jquery.min.js'></script>
<script src='/static/js/bootstrap-4.3.1.min.js'></script>
<link href='/wp-content/plugins/wa/js/moment.min.js?ver=5.2' rel='stylesheet'>
<link href='/cdn/fontawesome/4.7.0/css/font-awesome.min.css' rel='stylesheet'>
"""


def test_query_string_version_is_never_read_as_a_library_version():
    """实测：wordpress.org 自身输出 jquery.min.js?ver=7.2-alpha-63675。
    把那个值当 jQuery 版本去查公告，就会把完全不相干的 CVE 算到客户头上。"""
    comps = fingerprint_components(WP_ASSET_MARKUP, {})
    assert [c["package"] for c in comps if c["ecosystem"]] == []     # 没有任何库版本被读出
    assert [c["package"] for c in comps if not c["ecosystem"]] == ["wordpress"]


def test_wordpress_core_version_is_still_detected_from_generator():
    comps = fingerprint_components('<meta name="generator" content="WordPress 5.8.1">', {})
    assert [c["label"] for c in comps] == ["WordPress"]
    assert comps[0]["version"] == "5.8.1" and comps[0]["ecosystem"] is None


def test_fontawesome_pre5_maps_to_its_old_package_name():
    """5.0 改了包名。查错名字会得到 0 条公告，然后被当成"该组件无漏洞"。"""
    comps = {c["package"]: c["version"] for c in fingerprint_components(CDN_MARKUP, {})}
    assert comps.get("font-awesome") == "4.7.0"
    assert "@fortawesome/fontawesome-free" not in comps


def test_only_path_versions_are_accepted_from_cdn_urls():
    comps = {c["package"]: c["version"] for c in fingerprint_components(CDN_MARKUP, {})}
    assert comps["jquery"] == "1.12.4"
    assert comps["bootstrap"] == "4.3.1"
    assert "moment" not in comps              # moment.min.js?ver=5.2 是站点版本，不算


def test_migrate_and_jquery_do_not_cross_contaminate():
    comps = fingerprint_components("<script src='/libs/jquery-migrate-3.4.1.min.js'></script>", {})
    assert [c["package"] for c in comps] == ["jquery-migrate"]


def test_actively_exploited_advisory_escalates_to_critical():
    rep = {"hits": [{"component_label": "jQuery", "installed_version": "1.12.4",
                     "id": "GHSA-jpcq-cgw6-v4j6", "cve": "CVE-2020-11023",
                     "severity": "MODERATE", "fixed_in": "3.5.0",
                     "known_exploited": True}],
           "osv_queried": ["jquery@1.12.4"], "eol_lines_dead": [], "components": [],
           "coverage_note": "x"}
    finding = _check_known_vulnerabilities(rep)[0]
    assert finding["status"] == "fail"
    assert finding["severity"] == "CRITICAL"      # 公告本身只标到 Moderate
    assert "CVE-2020-11023" in finding["observed"]
    assert "3.5.0" in finding["observed"]         # 必须给出可执行的修复版本
    assert "being exploited in the wild" in finding["plain"]


def test_clean_cve_sweep_states_its_own_coverage_limit_and_sells_nothing():
    rep = {"hits": [], "osv_queried": ["jquery@3.7.1", "bootstrap@5.3.2"],
           "eol_lines_dead": [], "components": [],
           "coverage_note": "公告库对 WordPress 核心与插件无覆盖"}
    finding = _check_known_vulnerabilities(rep)[0]
    assert finding["status"] == "pass"
    assert finding["vendor_skus"] == []
    assert "WordPress 核心与插件无覆盖" in finding["plain"]


def test_unqueried_cve_branch_stays_unverified():
    finding = _check_known_vulnerabilities(
        {"hits": [], "osv_queried": [], "osv_skipped": "未指纹到可查询组件",
         "osv_errors": [], "eol_lines_dead": [], "components": []})[0]
    assert finding["status"] == "unverified"
    assert "not used for any deduction" in finding["plain"]


def test_dead_version_line_carries_the_real_eol_date():
    rep = {"hits": [], "osv_queried": ["jquery@3.7.1"], "coverage_note": "x",
           "components": [{"label": "PHP", "version": "7.4.33", "source": "eol_line",
                           "ecosystem": None, "package": "php"}],
           "eol_lines_dead": [{"label": "PHP", "installed": "7.4.33", "cycle": "7.4",
                               "eol_date": "2022-11-28", "state": "eol"}]}
    lifecycle = [f for f in _check_known_vulnerabilities(rep)
                 if f["check"] == "software_lifecycle"][0]
    assert lifecycle["status"] == "fail"
    assert "2022-11-28" in lifecycle["observed"]      # 真实日期，不是"很久以前"
    assert "no further patch will ever be issued" in lifecycle["plain"]


def _fake_status(mapping):
    def _inner(slug, kind="plugin"):
        return mapping.get(slug, {"state": "unreachable", "slug": slug, "error": "boom"})
    return _inner


def test_plugin_outside_official_directory_is_not_reported_as_unreachable(monkeypatch):
    """不在官方目录 = 没有上游补丁通道，这本身是结论；旧写法把它写成"目录没访问到"。"""
    monkeypatch.setattr(vuln_intel, "wordpress_plugin_status",
                        _fake_status({"secret": {"state": "not_in_directory",
                                                 "slug": "secret"}}))
    finding = _check_wordpress_plugins([{"kind": "plugin", "slug": "secret"}])[0]
    assert finding["status"] == "fail"
    assert "not in the official directory" in finding["observed"]


def test_all_directory_failures_report_the_real_reason(monkeypatch):
    monkeypatch.setattr(vuln_intel, "wordpress_plugin_status", _fake_status({}))
    finding = _check_wordpress_plugins([{"kind": "plugin", "slug": "x"}])[0]
    assert finding["status"] == "unverified"
    assert "boom" in finding["observed"]


def test_not_applicable_checks_are_bucketed_apart_from_unverified():
    """非 WP 站的 WP 后台检查不适用，不能算成"本次没测到"，否则报告显得不可靠。"""
    findings = [
        _finding("a", "A", "pass", "o", "p"),
        _finding("b", "B", "fail", "o", "p", "HIGH"),
        _finding("w", "W", "unverified", "未识别出 WordPress", "p", "UNKNOWN",
                 source="not_applicable"),
        _finding("c", "C", "unverified", "网络不可达", "p"),
    ]
    summary = _summarize(findings, 0.0, "x.my", "https://x.my", True)
    assert summary["not_applicable"] == 1
    assert summary["unverified"] == 1
    assert "do not apply to this site" in summary["score_note"]
    assert summary["graded_checks"] == 2


class _FakeSocket:
    def __init__(self, table):
        self.table = table
        self.queries: list = []

    def getaddrinfo(self, host, port):
        self.queries.append(host)
        addrs = self.table.get(host)
        if not addrs:
            raise OSError("NXDOMAIN")
        return [(2, 1, 6, "", (a, 0)) for a in addrs]


def test_mail_subdomains_are_never_called_an_origin_leak(monkeypatch):
    """mail./webmail. 按设计指向邮件服务器，不能算源站泄露（实测 iotservices.my 即误报过）。"""
    fake = _FakeSocket({"vendor.example": ["104.16.0.1"], "www.vendor.example": ["104.16.0.2"],
                        "mail.vendor.example": ["203.0.0.9"]})
    monkeypatch.setattr("core.site_audit.socket", fake)
    monkeypatch.setattr("core.site_audit._is_cloudflare_ip", lambda ip: ip.startswith("104.16."))
    finding = _check_origin_concealment("vendor.example", True)[0]
    assert "mail.vendor.example" not in fake.queries
    assert finding["status"] == "pass"


def test_unproxied_admin_subdomain_is_a_bypassable_waf(monkeypatch):
    fake = _FakeSocket({"vendor.example": ["104.16.0.1"],
                        "cpanel.vendor.example": ["110.4.45.101"]})
    monkeypatch.setattr("core.site_audit.socket", fake)
    monkeypatch.setattr("core.site_audit._is_cloudflare_ip", lambda ip: ip.startswith("104.16."))
    finding = _check_origin_concealment("vendor.example", True)[0]
    assert finding["status"] == "fail"
    assert finding["severity"] == "HIGH"
    assert "110.4.45.101" in finding["observed"]


def test_port_check_is_silent_behind_a_cdn():
    """CDN 之后探到的是边缘节点端口，说成客户漏洞是错的。"""
    finding = _check_exposed_services("example.my", True)[0]
    assert finding["status"] == "unverified"
    assert "a limit of the method" in finding["plain"]


def test_never_public_ports_are_the_critical_set():
    for port in (445, 3306, 1433, 5432, 6379, 9200, 27017, 11211):
        assert _PORT_RISK[port][0] == "CRITICAL", port
    for expected_open in (80, 443, 53):
        assert expected_open not in _PORT_RISK, "本就该开放的端口不得进入告警清单"


def test_worst_severity_picks_the_highest():
    assert _worst(["INFO", "HIGH", "MEDIUM"]) == "HIGH"
    assert _worst(["LOW", "CRITICAL"]) == "CRITICAL"
    assert _worst([]) == "MEDIUM"


def test_backup_detection_requires_a_real_magic_byte():
    assert _identify_bytes(b"PK\x03\x04rest") == "ZIP"
    assert _identify_bytes(b"-- MySQL dump 10.13") == "MySQL dump"
    assert _identify_bytes(b"<!DOCTYPE html><html>") is None   # rewrite 回首页


def test_new_expert_findings_all_reference_real_skus():
    rep = {"hits": [{"component_label": "jQuery", "installed_version": "1.12.4",
                     "id": "G", "cve": "CVE-2020-11022", "severity": "HIGH",
                     "fixed_in": "3.5.0", "known_exploited": False}],
           "osv_queried": ["jquery@1.12.4"], "coverage_note": "x",
           "components": [{"label": "PHP", "version": "7.4", "source": "eol_line",
                           "ecosystem": None, "package": "php"}],
           "eol_lines_dead": [{"label": "PHP", "installed": "7.4", "cycle": "7.4",
                               "eol_date": "2022-11-28", "state": "eol"}]}
    samples = _check_known_vulnerabilities(rep)
    assert len(samples) == 2
    for f in samples:
        for sku in f["vendor_skus"]:
            assert catalog.get(sku) is not None, f"虚构 SKU {sku}"
