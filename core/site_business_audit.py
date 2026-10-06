"""
Cradilot Core - 业务与安全深度机检 (Business & Security Deep Probes)

第②步的证据来源之二：core.site_audit 负责传输层/头部/CMS/漏洞情报那 25 项，本模块负责
把 data/audit_checklist.json 里剩下的可测条目补齐——SEO 与商业表达（网站有没有完成
它该做的活）、账号与数据面（有没有登录/账户/API 面）、以及固定清单的路径与 DNS 探测。

三条硬边界（写在这里以免日后被当成"漏做"）：
  · 只发 GET / HEAD，只请求老板本人提供且属于他自己企业的那个网址的源主机；
  · 不注入任何载荷、不尝试任何凭据、不制造负载、不扫端口段；
  · 不取回任何属于第三方客户的文件——猜 ID 的发票/订单链接一律不测，
    该风险留在顾问电话里问（清单里对应条目已改成 internal_access）；
  · 每一项要么给出观测值，要么如实标 unverified / not_applicable，绝不把"没测到"写成"没有"。

内容类判断全部基于已抓到的首页正文，零额外请求；路径类共用一个 client 并发跑，
单请求 3.5 秒上限，超时即标 unverified 而不是猜一个结论。
"""

import re
import socket
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.web_scraper import inspect_tls, is_ssrf_safe

PATH_TIMEOUT_SECONDS = 3.5
# 简报要求"5 分钟出结论"，第②步只是其中一步：深探必须有硬上限，到点就如实标未测。
DEEP_BUDGET_SECONDS = 18.0

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Cradilot-SiteAudit/3.0"
)


def _finding(check: str, title: str, status: str, observed: str, plain: str,
             severity: str = "INFO", skus: Optional[List[str]] = None,
             source: str = "machine_probe") -> Dict[str, Any]:
    """与 core.site_audit 同结构：下游（评分、界面、PDF）只按这一种形状消费结论。"""
    return {
        "check": check, "title": title, "status": status, "observed": observed,
        "plain": plain, "severity": severity, "vendor_skus": skus or [],
        "evidence_source": source, "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _unverified(check: str, title: str, why: str) -> Dict[str, Any]:
    return _finding(check, title, "unverified", why,
                    f"Not verified in this run ({why}). This is not used as a deduction or a sales point.",
                    "UNKNOWN", source="probe_failed")

# ─── 路径探测清单：每项 (清单条目 id, 说明, 路径, 命中判据) ───────────────────
# "命中"要么是内容特征（说明该文件真的可被公网取回），要么是 200 + 非 HTML。
_PATH_PROBES: List[Tuple[str, str, str, str]] = [
    ("git_exposed", "Version control metadata", "/.git/config", "repositoryformatversion"),
    ("directory_listing", "Directory listing enabled", "/icons/", "index of"),
    ("debug_endpoints", "Debug and profiler endpoints", "/_profiler/phpinfo", "phpinfo"),
    ("debug_api", "Debug API reachable", "/actuator/env", '"source"'),
    ("admin_panel", "Admin panel reachable", "/wp-login.php", "user_login"),
    ("admin_crm_reachable", "Admin or CRM panel internet-reachable", "/administrator/", "username"),
    ("management_interfaces", "Management interfaces reachable", "/phpmyadmin/", "phpmyadmin"),
    ("swagger_exposure", "API documentation public", "/swagger-ui.html", "swagger"),
    ("legacy_api", "Legacy endpoints still live", "/api/v1/", None),
    ("sitemap", "XML sitemap published", "/sitemap.xml", "<urlset"),
    ("robots_txt", "robots.txt present and sane", "/robots.txt", "user-agent"),
    ("llms_txt", "llms.txt published for machine readers", "/llms.txt", None),
    ("public_bucket", "Published bucket allows listing", None, None),
    ("backup_database", "Database dump downloadable", "/backup.sql", "insert into"),
]

# 常见 CMS/后台登录页线索，用于"后台是否暴露"这类只读观测
_ADMIN_HINTS = ("/wp-login.php", "/xmlrpc.php", "/administrator/", "/phpmyadmin/", "/actuator/")


# ─── 小工具 ──────────────────────────────────────────────────────────────────
def _ok(iid: str, label: str, observed: str, plain: str,
        skus: Optional[List[str]] = None, severity: str = "INFO") -> Dict[str, Any]:
    return _finding(iid, label, "pass", observed, plain, severity, skus or [])


def _bad(iid: str, label: str, observed: str, plain: str,
         skus: Optional[List[str]] = None, severity: str = "MEDIUM") -> Dict[str, Any]:
    return _finding(iid, label, "fail", observed, plain, severity, skus or [])


def _na(iid: str, label: str, reason: str) -> Dict[str, Any]:
    """结构性不适用（例如没有购物车却查结账面）：不是缺陷，也不是通过。"""
    f = _finding(iid, label, "unverified", reason,
                 f"This feature does not appear on the site, so the check does not apply ({reason}). "
                 "It is not scored and not written up as a gap.",
                 "UNKNOWN", source="not_applicable_structure")
    return f


def _head(client: httpx.Client, base: str, path: str,
          timeout: float = PATH_TIMEOUT_SECONDS) -> Tuple[Optional[int], str]:
    url = base.rstrip("/") + (path or "")
    try:
        resp = client.get(url, follow_redirects=False, timeout=timeout)
        body = (resp.text or "")[:2000] if resp.status_code == 200 else ""
        return resp.status_code, body
    except Exception as exc:
        return None, f"{type(exc).__name__}"


class _Deadline:
    """整段深度探测共用的时间预算。到点就停，未跑完的条目如实标 unverified。"""

    def __init__(self, seconds: float):
        self._end = time.monotonic() + max(0.0, seconds)

    def left(self) -> float:
        return max(0.0, self._end - time.monotonic())

    def expired(self) -> bool:
        return self.left() <= 0.2

    def http_timeout(self, cap: float) -> float:
        return max(0.5, min(cap, self.left()))


def _same_origin(base_url: str, target: str) -> bool:
    """只允许探测目标主机自己的路径：绝不用客户的表单去打第三方的地址。"""
    a = urllib.parse.urlparse(base_url).netloc
    b = urllib.parse.urlparse(target).netloc
    if not b:
        return True
    return b == a or b.endswith("." + a.split(":")[0])


# ─── 内容类判据（全部基于已抓到的首页，零额外请求） ───────────────────────────
def _txt(html: str) -> str:
    return re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html or "")


def _meta(html: str, name: str) -> str:
    for m in re.finditer(r'<meta\b[^>]*>', html or "", re.I):
        tag = m.group(0)
        if re.search(rf'(?:name|property)\s*=\s*["\']?{re.escape(name)}["\']', tag, re.I):
            c = re.search(r'content\s*=\s*["\']([^"\']*)["\']', tag, re.I)
            if c:
                return c.group(1).strip()
    return ""


def _ld_json_types(html: str) -> List[str]:
    """页面上声明的结构化数据类型（只读解析，不求值）。"""
    types: List[str] = []
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>([\s\S]{0,8000}?)</script>',
                         html or "", re.I):
        types += re.findall(r'"@type"\s*:\s*"([A-Za-z]+)"', m.group(1))
    return types


def _content_checks(base_url: str, html: str, headers: Dict[str, str],
                    signals: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    text = _txt(html)
    low = (html or "").lower()
    words = len(text.split())

    def sig(name: str) -> bool:
        return bool(signals.get(name, {}).get("present"))

    def add(row: Dict[str, Any]) -> None:
        out.append(row)

    # 1. 商业表达：网站有没有完成它的活
    add(_ok("who_they_are", "Company identity stated", f"{words:,} words of readable text"
            if words > 120 else f"only {words} words of readable text",
            "The homepage makes clear who this is.") if words > 120 else
        _bad("who_they_are", "Company identity stated", f"only {words} words of readable text",
             "The homepage has almost no readable text, so neither customers nor search engines can tell who you are.",
             ["DEMO-IWB-STARTER"], "HIGH"))

    add(_ok("what_they_sell", "Products or services clearly listed",
            "the page lists products, services or price cues", "Visitors can see what you sell.") if sig("what_they_sell") else
        _bad("what_they_sell", "Products or services clearly listed", "no product, service or price wording on the page",
             "If nobody can see what you sell, you have no shopfront sign.", ["DEMO-WP17-BUSINESS"], "HIGH"))

    add(_ok("who_for", "Target customer identifiable", "the homepage names the customers it serves",
            "Business buyers can see themselves in it.") if sig("who_for") else
        _bad("who_for", "Target customer identifiable", "no description of who you serve",
             "If it looks like anyone can buy, nobody feels it is meant for them.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    add(_ok("problem_solved", "Problem and outcome explained", "the text states an outcome or solution",
            "The page talks about results, not just model numbers.") if re.search(r"(?i)\b(solution|help[s]? you|save|reduce|faster|"
                                                       r"since 19\d\d|we supply|we install)\b", text) else
        _bad("problem_solved", "Problem and outcome explained", "no outcome or solution wording",
             "Model numbers without value do not bring enquiries.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    add(_ok("why_this_company", "Reason to choose you over others", "differentiation or experience stated",
            "It gives a reason to choose you.") if re.search(r"(?i)\b(why us|since 19|experience|in-house|stocking|"
                                              r"authorised|certified|24/7|next day|same day)\b", text) else
        _bad("why_this_company", "Reason to choose you over others", "no differentiation stated",
             "Without a reason, all that is left is price negotiation.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    add(_ok("product_tiers", "Product or service tiers legible", "a product/service listing structure is present",
            "A quote-ready list can be read in full.") if re.search(r"(?i)<(ul|table)[^>]*>[\s\S]{0,4000}?"
                                                     r"(package|tier|plan|price|rm\s)", low) else
        _bad("product_tiers", "Product or service tiers legible", "no package or tier list found",
             "Buyers cannot shortlist themselves, so every question lands in a phone call.", [], "MEDIUM"))

    # 2. 转化通道
    cta = re.search(r'(?i)(contact|whatsapp|quote|enquir|inquir|call|book|request|get a price)', text)
    add(_ok("primary_cta", "Primary call to action", cta.group(0) if cta else "none",
            "The first screen offers a clickable next step.") if cta else
        _bad("primary_cta", "Primary call to action", "no call-to-action wording on the page",
             "Traffic with no exit is like turning customers away at the door.", ["DEMO-IWB-STARTER"], "HIGH"))

    add(_ok("contact_channel", "Direct contact channel visible", "a phone, email or address is present",
            "Customers can find a way to reach you straight away.") if sig("contact_channel") else
        _bad("contact_channel", "Direct contact channel visible", "no tel:/mailto:/WhatsApp link or address found",
             "With no direct channel, a hesitating visitor simply leaves.", ["DEMO-MAIL-PRO-10U"], "HIGH"))

    add(_ok("lead_form", "Enquiry or lead form present", "an enquiry form is present",
            "Enquiries come in in a structured way.") if sig("lead_form") else
        _bad("lead_form", "Enquiry or lead form present", "no enquiry form on the page",
             "No form means no trackable leads, only phone-call memory.", ["DEMO-WP17-BUSINESS"], "HIGH"))

    add(_ok("quote_request", "Request-a-quote path exists", "a request-a-quote entry is present",
            "Trade buyers can start an enquiry directly.") if sig("quote_request") else
        _bad("quote_request", "Request-a-quote path exists", "no request-a-quote entry found",
             "The standard B2B move has nowhere to land on your site.", ["DEMO-ECOM-STANDARD"], "MEDIUM"))

    add(_ok("whatsapp_cta", "WhatsApp click-to-chat offered", "a wa.me / API link is present",
            "Malaysian buyers like to ask a question first.") if sig("whatsapp_cta") else
        _bad("whatsapp_cta", "WhatsApp click-to-chat offered", "no WhatsApp click-to-chat found",
             "The channel local buyers prefer is missing, so the question goes to a competitor.", [], "MEDIUM"))

    viewport = bool(re.search(r'(?i)<meta[^>]+name=["\']?viewport', (html or "")))
    add(_ok("mobile_flow", "Mobile journey usable end to end", "viewport plus tappable channels present",
            "A phone visitor can finish the journey.") if viewport and cta else
        _bad("mobile_flow", "Mobile journey usable end to end",
             f"viewport {'present' if viewport else 'missing'}, call to action {'present' if cta else 'missing'}",
             "Most SME traffic comes from phones only; one broken step loses one order.", ["DEMO-WP17-BUSINESS"], "HIGH"))

    # 3. 信任证据
    for iid, label, sname, sev, note in (
        ("customer_logos", "Client or brand logos shown", "customer_logos", "LOW",
         "Recognisable client brands do the trusting for you."),
        ("case_studies", "Case studies or project examples", "case_studies", "MEDIUM",
         "Without examples, your promises are only words."),
        ("testimonials", "Customer testimonials", "testimonials", "LOW", "Named reviews beat adjectives."),
        ("awards", "Awards or recognition", "awards", "LOW", "Third-party recognition costs nothing and is often forgotten."),
        ("certifications", "Certifications listed", "certifications", "MEDIUM",
         "Tender evaluators shortlist on licences and certifications first."),
        ("partners", "Partners or distributors listed", "customer_logos", "LOW",
         "Partner brands back up your supply capability."),
        ("deployment_examples", "Real deployments shown", "case_studies", "MEDIUM",
         "Real installation photos convince more than stock photos."),
        ("quantified_results", "Numbers backing the claims", "quantified_results", "MEDIUM",
         "Statements with numbers can be checked."),
    ):
        add(_ok(iid, label, "shown on the page", note) if sig(sname) else
            _bad(iid, label, "this evidence is not on the page", f"{label}: not found on the page. {note}",
                 ["DEMO-SEO-STANDARD"], sev))

    # 4. 可衡量性
    add(_ok("ga4", "Google Analytics 4 installed", "gtag/G- measurement loaded",
            "You know who shows up.") if sig("ga4") else
        _bad("ga4", "Google Analytics 4 installed", "no GA4 / gtag found",
             "Without measurement, every optimisation is guesswork.", [], "MEDIUM"))
    add(_ok("gtm", "Google Tag Manager installed", "a GTM container is present", "Adding tags needs no code change.")
        if sig("gtm") else
        _bad("gtm", "Google Tag Manager installed", "no GTM container found",
             "Every tracking change has to be queued for a developer.", [], "LOW"))
    tracking = sig("ga4") or sig("gtm") or sig("meta_pixel")
    add(_ok("conversion_tracking", "Conversion events configured", "a measurement or pixel base is present",
            "The attribution base exists; events can be added as needed.") if tracking else
        _bad("conversion_tracking", "Conversion events configured", "no measurement or pixel found",
             "You cannot say what you spent or which order it brought.", [], "MEDIUM"))
    for iid, label, note in (
        ("form_tracking", "Form submissions tracked", "form events can count a lead as a conversion"),
        ("cta_tracking", "CTA clicks tracked", "button clicks show which offer is working"),
        ("funnel_tracking", "Funnel or goal steps defined", "step goals show where buyers drop off"),
    ):
        add(_ok(iid, label, "can be configured on the existing measurement base" if tracking else "none",
                note + " (the event itself has to be confirmed as set up in your account)") if tracking else
            _na(iid, label, "the site has no usable measurement base"))

    # 5. SEO 技术面
    title = re.search(r"<title[^>]*>([\s\S]{0,400}?)</title>", (html or ""), re.I)
    t = (title.group(1).strip() if title else "")
    add(_ok("title_tag", "Title tag present and sized", f"{len(t)} characters: {t[:60]}",
            "The line shown in search results is one you wrote.") if 15 <= len(t) <= 70 else
        _bad("title_tag", "Title tag present and sized", f"title length {len(t)} characters ({t[:50] or 'missing'})",
             "Too short, too long or empty and the search engine writes that line for you.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    desc = _meta(html, "description")
    add(_ok("meta_description", "Meta description present", f"{len(desc)} characters",
            "You have copy space that lifts click-through.") if 50 <= len(desc) <= 200 else
        _bad("meta_description", "Meta description present", f"description length {len(desc)} characters",
             "With no description the system grabs body text instead, and click-through suffers.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    h1 = re.findall(r"<h1\b[^>]*>([\s\S]{0,200}?)</h1>", (html or ""), re.I)
    add(_ok("h1_single", "One clear H1", f"{len(h1)} H1", "The page topic is clear to machines as well.")
        if len(h1) == 1 else
        _bad("h1_single", "One clear H1", f"{len(h1)} H1 tags found",
             "With no single H1, or several, topic weight is spread flat.", [], "MEDIUM"))

    h2 = len(re.findall(r"<h2\b", (html or ""), re.I))
    add(_ok("heading_structure", "Heading hierarchy (H2 and below)", f"{h2} H2 headings",
            "The content has layers a crawler can split.") if h2 >= 2 else
        _bad("heading_structure", "Heading hierarchy (H2 and below)", f"only {h2} H2 headings",
             "No hierarchy anywhere on the page, so a long page reads like a wall of text.", [], "LOW"))

    canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*>', (html or ""), re.I)
    add(_ok("canonical", "Canonical tag set", canonical.group(0)[:80] if canonical else "",
            "Duplicate pages stop competing with each other.") if canonical else
        _bad("canonical", "Canonical tag set", "no canonical link found",
             "www / non-www and parameter pages each become their own copy of the content.", [], "MEDIUM"))

    internal = {h for h in re.findall(r'href=["\']([^"\'#][^"\']*)["\']', (html or ""))
                if _same_origin(base_url, urllib.parse.urljoin(base_url, h))}
    add(_ok("internal_links", "Internal linking to key pages", f"{len(internal)} same-site links",
            "Your key pages are not islands.") if len(internal) >= 3 else
        _bad("internal_links", "Internal linking to key pages", f"only {len(internal)} same-site links",
             "Orphan pages bring no visitors and get no indexing.", [], "MEDIUM"))

    noindex = (_meta(html, "robots") or "").lower()
    robots_hdr = (headers.get("x-robots-tag") or "").lower()
    blocked = "noindex" in noindex or "noindex" in robots_hdr
    add(_bad("indexability", "Indexability (no accidental noindex)",
             f"meta robots={noindex or '-'}, header={robots_hdr or '-'}",
             "The page tells search engines not to index it, so no traffic arrives however good it looks.", [], "CRITICAL") if blocked else
        _ok("indexability", "Indexability (no accidental noindex)",
            "no noindex directive found", "The site is open and can be found."))

    types = _ld_json_types(html)
    add(_ok("structured_data", "Structured data present (JSON-LD)", ", ".join(sorted(set(types))[:6]) or "-",
            "Machines can read you field by field instead of guessing.") if types else
        _bad("structured_data", "Structured data present (JSON-LD)", "no JSON-LD structured data found",
             "Without structured data, AI and rich results cannot pick you up.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    tl = {t.lower() for t in types}
    for iid, key, label, sev in (("org_schema", "organization", "Organization schema", "MEDIUM"),
                                 ("product_schema", "product", "Product schema", "LOW"),
                                 ("faq_schema", "faq", "FAQ schema", "LOW")):
        hit = any(key in t for t in tl) or (key == "organization" and bool(
            re.search(r'(?i)"@type"\s*:\s*"(corporation|localbusiness|ngo|educationalorganization'
                      r'|professional-service)"', (html or "")[:20000])))
        add(_ok(iid, label, "declared", "Your entity identity is checkable by machines.") if hit else
            _bad(iid, label, "that type not found", f"{label} missing: answer engines cannot cite you reliably.",
                 ["DEMO-SEO-STANDARD"], sev))

    imgs = re.findall(r'<img\b[^>]*>', (html or ""), re.I)
    no_alt = [i for i in imgs if not re.search(r'alt\s*=\s*["\'][^"\']+["\']', i, re.I)]
    if imgs:
        add(_ok("image_alt", "Image alt coverage", f"{len(imgs) - len(no_alt)}/{len(imgs)} images carry alt text",
                "Images are searchable and accessibility is covered.") if len(no_alt) * 2 < len(imgs) else
            _bad("image_alt", "Image alt coverage", f"{len(no_alt)}/{len(imgs)} images have no alt text",
                 "Images are blank to both search engines and screen readers.", [], "LOW"))
    else:
        add(_na("image_alt", "Image alt coverage", "the homepage references no img images"))

    # 6. 账号 / API / 数据面（只描述观测，不做任何访问尝试）
    add(_ok("login_page", "Login entry point present", "a login entry is present",
            "The account-related checks below apply to this site.") if sig("login_form") else
        _na("login_page", "Login entry point present", "the site has no login entry"))
    add(_ok("registration_open", "Open self-service registration", "a self-service sign-up entry is present",
            "Registration creates customer data, and with it the isolation requirement.") if sig("register_form") else
        _na("registration_open", "Open self-service registration", "no self-service registration found"))
    add(_ok("customer_registration", "Customer self-registration enabled", "an account sign-up entry is present",
            "Customer records start here.") if sig("register_form") else
        _na("customer_registration", "Customer self-registration enabled", "no sign-up entry found"))
    add(_ok("customer_login", "Customer portal login found", "a member/customer login is present",
            "This is the boundary for the access-rights checks.") if sig("account_portal") else
        _na("customer_login", "Customer portal login found", "no customer area found"))
    add(_ok("profile_edit", "Profile edit flow", "a profile edit path appears on the page",
            "Profile endpoints are a common IDOR point (needs an authorised window to verify).") if re.search(r"(?i)/(profile|account)/?(edit)?\b",
                                                                     low) else
        _na("profile_edit", "Profile edit flow", "no profile edit path found"))
    add(_ok("account_recovery", "Account recovery path", "password recovery / account restore is present",
            "Recovery flows are usually the weakest link in authentication.") if re.search(r"(?i)(forgot|reset).{0,12}(password|account)"
                                                            r"|找回(密码|账户)", low) else
        _na("account_recovery", "Account recovery path", "no account recovery entry found"))
    add(_unverified("mfa_offered", "MFA or 2-step offered",
                    "the site does have a login entry; whether two-factor is enabled has to be confirmed in your own account area, the homepage text does not show it")
        if sig("login_form") else
        _na("mfa_offered", "MFA or 2-step offered", "the site has no login entry"))
    add(_ok("password_reset", "Password reset link handling", "a reset page is present",
            "The reset entry is visible; token strength needs confirming in your account area.") if re.search(r"(?i)reset.{0,10}password|forgot.{0,10}password",
                                                             low) else
        _na("password_reset", "Password reset link handling", "no reset page found"))
    add(_ok("jwt_usage", "JWT held client-side", "a JWT appears on the front end",
            "Token exposure sits on the browser side.") if re.search(r"(?i)\beyJ[A-Za-z0-9_\-]{10,}|jwt[_-]?(token)?\b",
                                                  (html or "")) else
        _na("jwt_usage", "JWT held client-side", "no sign of JWT use found"))

    api_paths = sorted({m[:28] for m in re.findall(r'["\'](/api/[a-z0-9\-_/\.]{2,40})', (html or ""))})
    add(_ok("rest_surface", "Public REST endpoints detected",
            ", ".join(api_paths[:6]) or str(signals.get("api_surface", {}).get("evidence") or "endpoints seen"),
            "An API surface exists, so the access-rights checks apply to this site.") if sig("api_surface") else
        _na("rest_surface", "Public REST endpoints detected", "the front end references no API endpoint"))
    add(_ok("websocket", "WebSocket endpoints used", "the page declares a wss channel",
            "Real-time channels need authentication too.") if sig("websocket") else
        _na("websocket", "WebSocket endpoints used", "no WebSocket channel found"))
    add(_ok("api_versioning", "API versioning in use", "endpoints carry a version number",
            "Versioning is what lets you retire things safely.") if re.search(r'/api/v\d|/v\d+/', (html or "")) else
        _bad("api_versioning", "API versioning in use", "no version number on the endpoints",
             "An unversioned API can only stay compatible forever; old flaws never get retired.", [], "LOW") if sig("api_surface") else
        _na("api_versioning", "API versioning in use", "the site has no API surface"))
    ext_hosts = sorted({urllib.parse.urlparse(u).netloc
                        for u in re.findall(r'["\']https?://[^"\']{6,120}["\']', (html or ""))
                        if not _same_origin(base_url, u) and urllib.parse.urlparse(u).netloc})
    add(_ok("third_party_apis", "Third-party integrations identified",
            ", ".join(ext_hosts[:6]),
            "Every embedded service is part of your attack surface.") if ext_hosts else
        _na("third_party_apis", "Third-party integrations identified", "the page references no off-site service address"))
    leaked_fields = re.search(r'(?i)"(password|passwd|secret|api_?key|ic_?no)"\s*:\s*'
                              r'"[^"\']{8,}"', (html or ""))
    if leaked_fields:
        add(_bad("excessive_data_exposure", "Responses returning more than needed",
                 f"JSON embedded in the page carries a sensitive field with a value ({leaked_fields.group(1)})",
                 "The response sends out fields it should not include.", [], "HIGH"))
    else:
        add(_unverified("excessive_data_exposure", "Responses returning more than needed",
                        "which fields the API returns can only be confirmed by logging into your own account, it is not visible from the homepage"))
    err_trace = bool(re.search(r"(?i)(traceback \(most recent|wp-content/themes/[^\"']*\.php"
                               r"|sqlstate\[|ora-[0-9]{5})", (html or "")))
    add(_ok("api_error_leakage", "API errors leaking internals", "no error template leak found",
            "Errors do not give away paths or versions.") if not err_trace else
        _bad("api_error_leakage", "API errors leaking internals", "the page contains framework error signatures",
             "A single error page is enough to piece together internal paths and component versions.", [], "MEDIUM"))

    # 7. 凭据与隐私（命中即"已经发布出去"）
    from core.site_signals import find_secrets
    secrets = find_secrets(html)
    if secrets:
        kinds = ", ".join(s["kind"] for s in secrets[:4])
        add(_bad("api_keys_in_page", "API keys published in page or scripts", f"{len(secrets)} found: {kinds}",
                 "A key the browser can see is a public key; once seen, rotate it immediately.", [], "CRITICAL"))
    else:
        add(_ok("api_keys_in_page", "API keys published in page or scripts",
                "no key patterns in the homepage or inline scripts", "You already do this right; it costs you nothing."))
    add(_ok("ai_key_leakage", "Model API keys published client-side", "no model keys found",
            "Nobody is running models on your quota.") if not secrets else
        _bad("ai_key_leakage", "Model API keys published client-side",
             "credential patterns present on the page", "A model key on the front end means paying someone else's bill.", [], "CRITICAL"))
    add(_ok("cloud_credentials", "Cloud credentials in client assets",
            "no cloud provider credentials found", "The cloud account is not published with the page.") if not re.search(r'AKIA[0-9A-Z]{16}|'
                                                                        r'BEGIN (RSA |EC |)PRIVATE KEY',
                                                                        (html or "")) else
        _bad("cloud_credentials", "Cloud credentials in client assets", "the page contains a cloud credential or private key block",
             "One access key bypasses every other control.", [], "CRITICAL"))
    add(_ok("database_credentials", "Database credentials reachable", "no connection string found",
            "The database password is not published with the static assets.") if not re.search(r'(?i)(mongodb|mysql|postgres(?:ql)?|mssql)://'
                                                            r'[^\s"\']+:[^\s"\']+@', (html or "")) else
        _bad("database_credentials", "Database credentials reachable", "the page contains a connection string with a password",
             "A published connection string is a published database.", [], "CRITICAL"))
    add(_ok("password_in_html", "Password or secret fields hardcoded in HTML", "no hardcoded password found",
            "No password is written into the file being served.") if not re.search(r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{6,}["\']',
                                                            (html or "")) else
        _bad("password_in_html", "Password or secret fields hardcoded in HTML", "a password assignment appears in the HTML",
             "A password written into the page is already public information.", [], "HIGH"))
    hrefs = " ".join(re.findall(r'href\s*=\s*["\']([^"\']+)["\']', (html or ""), re.I))
    pii = re.findall(r'(?<!\d)\d{6}-\d{2}-\d{4}(?!\d)', text)  # 大马 IC 形态
    # 邮箱与电话多以 tel:/mailto:/wa.me 链接发布，只看正文会漏掉——界面就会说"没留联系方式"
    both = text + " " + hrefs
    emails = set(re.findall(r'[\w\.\-+]+@[\w\.\-]+\.[a-z]{2,}', both))
    emails |= {m.rstrip(".") for m in re.findall(r'mailto:([^"\'\s?>]+)', both, re.I)}
    phones = set(re.findall(r'(?:\+?60|01)\s?-?\s?[2-9]\d{1,2}[-\s]?\d{3}[-\s]?\d{4}', both))
    phones |= set(re.findall(r'tel:([^"\'\s?>]+)', both, re.I))
    phones |= set(re.findall(r'(?:wa\.me|api\.whatsapp\.com)/(?:44/)?(\d{9,13})', both, re.I))
    emails, phones = sorted(emails), sorted(phones)
    if pii:
        add(_bad("pii_exposure", "Personally identifiable data on public pages",
                 f"{len(pii)} suspected IC (identity card) numbers", "Identity card numbers appear on a public page and will be taken in bulk by crawlers.",
                 [], "HIGH"))
    elif len(emails) > 6 or len(phones) > 6:
        add(_bad("pii_exposure", "Personally identifiable data on public pages",
                 f"{len(emails)} emails / {len(phones)} phone numbers clustered on the page",
                 "A contact list published in the open is filing it for the data brokers.", [], "MEDIUM"))
    else:
        add(_ok("pii_exposure", "Personally identifiable data on public pages",
                f"{len(emails)} emails, {len(phones)} phone numbers, no IC-number patterns",
                "No bulk personal identity data on public pages."))
    add(_ok("customer_pii_public", "Customer PII on public pages", "no customer list found published",
            "Customer records are not sitting where the public internet can fetch them.") if not pii else
        _bad("customer_pii_public", "Customer PII on public pages", f"{len(pii)} identity-number patterns found",
             "Once a customer list is scraped, the leak is not your incident, it is your liability.", [], "HIGH"))
    add(_ok("error_verbosity", "Verbose errors or stack traces served", "no error signatures on the homepage",
            "The page does not document your stack for an attacker.") if not re.search(r"(?i)(fatal error|warning:.*?on line|"
                                                             r"stack trace|traceback)", text[:6000]) else
        _bad("error_verbosity", "Verbose errors or stack traces served", "error text appears on the page",
             "Error text leaks paths, versions and how queries are written.", [], "MEDIUM"))

    # 8. 云与商店形态
    storage = re.findall(r'(s3[.-][a-z0-9-]+\.amazonaws\.com|[a-z0-9.-]+\.blob\.core\.windows\.net|'
                         r'storage\.googleapis\.com|[a-z0-9.-]+\.digitaloceanspaces\.com)', (html or ""), re.I)
    add(_ok("cloud_storage", "Object storage in use", ", ".join(sorted(set(storage))[:3]),
            "The page references object storage directly, so bucket permissions need a separate confirmation.") if storage else
        _na("cloud_storage", "Object storage in use", "the page references no object storage address"))
    add(_ok("store_platform", "Storefront platform detected",
            ", ".join(sorted({p for p in ("woocommerce", "shopify", "magento", "opencart") if p in low})) or "-",
            "The platform decides who owns the patching.") if sig("store_platform") else
        _na("store_platform", "Storefront platform detected", "no store platform found"))
    add(_ok("checkout_present", "Checkout flow found", "a cart or checkout path is present",
            "The payment-logic checks apply to this site.") if sig("checkout_present") else
        _na("checkout_present", "Checkout flow found", "the site has no cart or checkout flow"))
    pay = sorted({p for p in ("paypal", "stripe", "molpay", "ipp", "razorpay", "billplz",
                              "econsolidated")
                  if re.search(rf"(?i)(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", (html or ""))})
    add(_ok("payment_provider", "Payment provider integration identified",
            ", ".join(pay), "A hosted checkout is far safer than storing card data yourself.") if pay else
        _na("payment_provider", "Payment provider integration identified", "no payment channel component found"))
    add(_ok("support_channel", "Support or ticketing channel present", "a ticketing or help centre is present",
            "Support requests have somewhere to go.") if re.search(r"(?i)(help.?desk|tickets?|/support|knowledge base|faq)",
                                            (html or "")) else
        _bad("support_channel", "Support or ticketing channel present", "no ticketing or help centre found",
             "After-sales runs on a personal WhatsApp, and the history is not something the company can get back.", ["DEMO-MAIL-PRO-10U"], "MEDIUM"))
    add(_ok("customer_search", "Customer search API", "a search/query endpoint appears on the page",
            "Search endpoints are where unauthorised data access shows up most often.") if sig("search_or_query") and sig("api_surface") else
        _na("customer_search", "Customer search API", "no outward-facing customer query API found"))

    # 9. AI 采纳面
    add(_ok("ai_chatbot", "Live chat or AI assistant on site", "a chat or auto-reply component is detected",
            "Someone, or something, is picking up enquiries.") if sig("chat_widget") else
        _bad("ai_chatbot", "Live chat or AI assistant on site", "no chat or auto-reply component appears on the page",
             "Enquiries sent after hours go unanswered, and by the time you reply the next day the buyer has asked someone else.", ["DEMO-AI-AGENT"], "HIGH"))
    for iid, label, pat, sev in (
        ("ai_search", "AI or semantic site search", r"(?i)(semantic search|ai search|natural language search)", "LOW"),
        ("ai_support", "AI support deflection offered", r"(?i)(ai assist|smart reply|automated answer)", "LOW"),
        ("ai_recommendation", "Product recommendations in use", r"(?i)(you may also like|recommended for you|related products)", "LOW"),
        ("ai_personalisation", "Personalised content or pricing", r"(?i)(personalis|personaliz|for you|pricing based on)", "LOW"),
    ):
        add(_ok(iid, label, "this capability appears on the page", "This AI capability is already on the site.")
            if re.search(pat, (html or "")) else
            _bad(iid, label, "this capability not found", f"{label}: not visible on the site, a gain worth evaluating.",
                 ["DEMO-AI-AGENT"], sev))
    add(_ok("ai_lead_qualification", "Automated enquiry qualification",
            "a form exists and a chat component is present, so requirements can be pre-asked automatically" if sig("lead_form") and sig("chat_widget") else "-",
            "The enquiry can be qualified before a person ever sees it.") if sig("lead_form") and sig("chat_widget") else
        _na("ai_lead_qualification", "Automated enquiry qualification", "the site has neither a form nor a chat component"))
    add(_ok("entity_clarity", "Company entity unambiguous to machines",
            f"registration number {'yes' if sig('company_registration') else 'no'}, address "
            f"{'yes' if sig('physical_address') else 'no'}, brand name consistent",
            "Name, address and registration number back each other up, which is how machines recognise you.") if sig("company_registration") or sig("physical_address") else
        _bad("entity_clarity", "Company entity unambiguous to machines", "neither the registration number nor the address appears",
             "With an unclear entity, neither search nor AI will vouch for you.", ["DEMO-SEO-STANDARD"], "MEDIUM"))
    add(_ok("product_entity_clarity", "Products named consistently",
            "product names match the catalogue structure" if sig("what_they_sell") else "-",
            "Internal part numbers mean nothing outside; the product wording has to be findable by search.") if sig("what_they_sell") else
        _bad("product_entity_clarity", "Products named consistently", "the page shows no consistent product naming",
             "With only internal part numbers, neither buyers nor AI can find you.", ["DEMO-SEO-STANDARD"], "MEDIUM"))
    add(_ok("llm_readable_content", "Machine-readable product information",
            "body text and structured data can be read directly" if types and words > 200 else "-",
            "Only content that can be read can be cited.") if types and words > 200 else
        _bad("llm_readable_content", "Machine-readable product information",
             f"{words} words of body text, structured data {'present' if types else 'absent'}",
             "A catalogue kept only in PDFs or images cannot be read by search engines or AI.", ["DEMO-SEO-STANDARD"], "MEDIUM"))
    add(_ok("structured_product_data", "Structured product listings",
            ", ".join(sorted(t for t in tl if t in ("product", "offers", "aggregatearray"))) or "-",
            "Only with structured product data can answer engines recommend you.") if any(
        t in tl for t in ("product", "offers", "itemlist", "aggregatearray")) else
        _bad("structured_product_data", "Structured product listings", "no product structured data found",
             "If products are invisible to machines, the AI recommendation slots go to someone else.", ["DEMO-SEO-STANDARD"], "LOW"))

    # 10. 内容与法务面
    newest = max({int(m) for m in re.findall(r"\b(20\d{2})\b", text)} or {0})
    now_year = time.localtime().tm_year
    add(_ok("outdated_content", "Content maintained (dates, copyright year)",
            f"newest year on the page {newest or 'not found'}", "There are signs of maintenance.") if newest >= now_year - 1 else
        _bad("outdated_content", "Content maintained (dates, copyright year)",
             f"newest year on the page is {newest or 'not found'} (this year {now_year})",
             "A year that stopped several years ago hurts more than no year at all: customers start by wondering whether you are still trading.", ["DEMO-WP17-BUSINESS"], "HIGH"))
    dead_cta = re.findall(r'href\s*=\s*["\'](#[^"\']*|javascript:void\(0\)|)["\']', (html or ""))
    add(_ok("broken_cta", "Buttons wired to a real destination", f"{len(dead_cta)} anchor or placeholder links",
            "The buttons go somewhere.") if len(dead_cta) <= 4 else
        _bad("broken_cta", "Buttons wired to a real destination", f"{len(dead_cta)} links are empty anchors or placeholders",
             "A button that does nothing is an order lost.", ["DEMO-WP17-BUSINESS"], "MEDIUM"))
    add(_ok("contact_details", "Address, phone and email published",
            f"{len(emails)} emails, {len(phones)} phone numbers, address "
            f"{'yes' if sig('physical_address') else 'no'}", "The business can be verified on the ground.")
        if sig("physical_address") and (emails or phones) else
        _bad("contact_details", "Address, phone and email published", "address, phone or email not all present",
             "Trade buyers check that you have a real physical address before they send an enquiry.", ["DEMO-MAIL-PRO-10U"], "HIGH"))
    add(_ok("social_links", "Social or marketplace links present", "third-party platform links present",
            "A third-party presence corroborates that the entity is real.") if re.search(r"(?i)(facebook\.com/|instagram\.com/|linkedin\.com/"
                                                      r"|tiktok\.com/@|shopee\.com\.my|lazada\.com\.my)",
                                                      (html or "")) else
        _bad("social_links", "Social or marketplace links present", "no third-party platform links found",
             "With only your own site as an island, one pillar of trust is missing.", [], "LOW"))
    for iid, label, sname, sev in (("privacy_policy", "Privacy policy published", "privacy_policy", "HIGH"),
                                   ("terms_published", "Terms of service published", "terms_published", "MEDIUM"),
                                   ("cookie_notice", "Cookie or consent notice", "cookie_notice", "LOW"),
                                   ("company_registration", "Registration number displayed",
                                    "company_registration", "MEDIUM")):
        add(_ok(iid, label, "shown on the page", "It saves a round of back-and-forth when buyers and partners verify who you are.") if sig(sname) else
            _bad(iid, label, "not present on the page", f"{label}: once you collect customer data, its absence gets questioned in due diligence.",
                 ["DEMO-MAIL-PRO-10U"], sev))
    title_txt = re.sub(r"<[^>]+>", " ", t or "")
    h1_txt = re.sub(r"<[^>]+>", " ", (h1[0] if h1 else ""))
    stop = {"the", "and", "for", "with", "our", "you", "are", "www", "com", "my", "sdn", "bhd"}
    title_words = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9&'\-]{2,}",
                                         re.sub(r"<[^>]+>", " ", title_txt).lower())} - stop
    h1_words = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9&'\-]{2,}",
                                      re.sub(r"<[^>]+>", " ", h1_txt).lower())} - stop
    if not (title_words and h1_words):
        add(_na("brand_consistency", "Brand name consistent across pages",
                "the title or the H1 is missing, so there is no brand wording to compare"))
    elif title_words & h1_words:
        add(_ok("brand_consistency", "Brand name consistent across pages",
                ", ".join(sorted(title_words & h1_words)[:3]),
                "Title and main heading point to the same name, so neither machines nor people get it wrong."))
    else:
        add(_bad("brand_consistency", "Brand name consistent across pages",
                 f"title wording {sorted(title_words)[:3]} and main heading {sorted(h1_words)[:3]} share no terms",
                 "When one company uses two or three names on its own homepage, search and AI treat them as different entities.",
                 ["DEMO-SEO-STANDARD"], "LOW"))
    superlative = re.findall(r"(?i)\b(best|no\.?\s?1|leading|largest|cheapest|award[- ]winning|"
                             r"number\s?one)\b", text)
    add(_ok("unverifiable_claims", "Claims without evidence", "no unsupported superlatives used",
            "Only supported claims can be checked.") if not superlative else
        _bad("unverifiable_claims", "Claims without evidence",
             f"{len(superlative)} superlatives used with no numbers behind them",
             "A number-one claim with no numbers behind it is just advertising copy to a trade buyer.", ["DEMO-SEO-STANDARD"], "MEDIUM"))

    # 11. 资源与参数面（只读首页即可判定，零额外请求）
    img_tags = re.findall(r'<img\b[^>]*>', (html or ""), re.I)
    sized = [i for i in img_tags if re.search(r'(?i)(srcset=|\.webp|loading=["\']lazy)', i)]
    if img_tags:
        ratio = len(sized) / len(img_tags)
        add(_ok("image_optimisation", "Images sized and compressed",
                f"{len(sized)}/{len(img_tags)} images use srcset/webp/lazy loading",
                "Images are served at screen size, so phone visitors do not download the originals.") if ratio >= 0.5 else
            _bad("image_optimisation", "Images sized and compressed",
                 f"only {len(sized)} of {len(img_tags)} images are sized or format-optimised",
                 "Most homepage images are uncropped originals, so phone visitors pay for data while they wait.",
                 ["DEMO-CF-BOOSTER-PERSONAL"], "MEDIUM"))
    else:
        add(_na("image_optimisation", "Images sized and compressed", "the homepage references no img images"))

    scripts = re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', (html or ""), re.I)
    styles = re.findall(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', (html or ""), re.I)
    heavy = [s for s in scripts if not re.search(r'(?i)(\.min\.|bundle|app\.[a-f0-9]{6,})', s)]
    total_assets = len(scripts) + len(styles)
    add(_ok("asset_bloat", "JavaScript and CSS weight",
            f"{len(scripts)} scripts + {len(styles)} stylesheets, {len(heavy)} with no sign of compression",
            "The number of front-end assets is within an acceptable range.") if total_assets <= 24 and len(heavy) <= 8 else
        _bad("asset_bloat", "JavaScript and CSS weight",
             f"{total_assets} front-end asset files ({len(heavy)} uncompressed)",
             "Dozens of large files load one after another, and the first screen time goes entirely on things that are not content.",
             ["DEMO-CF-BOOSTER-PERSONAL"], "LOW"))

    if sig("url_param_present"):
        add(_unverified("open_redirect", "Open redirect on login or outbound links",
                        "the page has parameters that can affect the redirect target; whether they can be pointed off-site has to be confirmed inside your own account."))
    else:
        add(_na("open_redirect", "Open redirect on login or outbound links",
                "no parameters affecting the redirect target appear on the homepage"))
    return out


# ─── 路径与 DNS 类判据 ───────────────────────────────────────────────────────
def _probe_paths(base_url: str, html: str,
                 dl: Optional["_Deadline"] = None) -> Dict[str, Dict[str, Any]]:
    """
    固定清单的路径探测：共用一个 client，只发 GET，只打目标主机自己。

    404 是有效结论（该项不存在）；连接失败/超时是 unverified，绝不折算成"没暴露"。
    超出第②步时间预算的条目同样标 unverified——"没来得及测"与"测了没有"是两回事。
    """
    results: Dict[str, Dict[str, Any]] = {}
    origin = urllib.parse.urlparse(base_url)
    base = f"{origin.scheme}://{origin.netloc}"
    todo = [row for row in _PATH_PROBES if row[2] is not None and row[0] != "public_bucket"]

    def _probe(row: Tuple[str, str, str, str]):
        iid, label, path, expect = row
        timeout = dl.http_timeout(PATH_TIMEOUT_SECONDS) if dl else PATH_TIMEOUT_SECONDS
        return row + _head(client, base, path, timeout)

    try:
        client = httpx.Client(timeout=PATH_TIMEOUT_SECONDS, headers={"user-agent": BROWSER_UA},
                              verify=True, follow_redirects=False)
    except Exception as exc:      # client 建不起来：全部如实标未测
        for iid, label, _p, _e in todo:
            results[iid] = _unverified(iid, label, f"client initialisation failed: {type(exc).__name__}")
        return results

    with client:
        pool = ThreadPoolExecutor(max_workers=min(6, max(1, len(todo))))
        try:
            futs = {pool.submit(_probe, row): row for row in todo}
            done, _pending = wait(list(futs), timeout=(dl.left() if dl else None))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        for fut, (iid, label, path, expect) in futs.items():
            if fut not in done:
                results[iid] = _unverified(iid, label, "this step's time budget ran out, request not completed")
                continue
            try:
                _i, _l, _p, _e, code, body = fut.result()
            except Exception as exc:
                results[iid] = _unverified(iid, label, f"{type(exc).__name__}")
                continue
            if code is None:
                results[iid] = _unverified(iid, label, f"{path} request did not complete ({body})")
                continue
            if iid in _SHOULD_EXIST:
                results[iid] = _published_file_result(iid, label, path, code, body)
                continue
            lowered = body.lower()
            exposed = code == 200 and (expect in lowered if expect else
                                       "<!doctype html>" not in lowered[:120] and len(body) > 0)
            if exposed:
                results[iid] = _bad(iid, label, f"{path} returns 200 and the content is readable",
                                     f"{label}: it can be fetched straight from the public internet. This is not about whether you buy anything, "
                                     "so please have your current provider close it or move it out of the web root.",
                                     ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"], "CRITICAL")
            elif code == 200:
                results[iid] = _bad(iid, label, f"{path} returns 200 (HTML page)",
                                    f"{label}: the path responds and it is not a 404. We did not try any credentials, "
                                    "so whether access is authorised is for you to confirm.",
                                    ["DEMO-WP17-BUSINESS"], "HIGH")
            else:
                guarded = "returns {c} (present but not publicly readable, which is the correct configuration)" if code in (401, 403) \
                    else "returns {c}"
                results[iid] = _ok(iid, label, f"{path} " + guarded.format(c=code),
                                   f"{label}: nothing can be fetched from it publicly, so you have this one right already and it costs you nothing.")
    return results


# 这几项反过来：存在是好事（引导爬虫与答案引擎），404 才是缺口。
_SHOULD_EXIST = {
    "sitemap": ("XML sitemap not published: search engines can only discover pages by following links.", "LOW", ["DEMO-SEO-STANDARD"]),
    "robots_txt": ("robots.txt not published: nothing guides the crawl budget or the admin paths.", "LOW", ["DEMO-SEO-STANDARD"]),
    "llms_txt": ("llms.txt not published: AI search and assistants have to guess when they read your catalogue.", "LOW", ["DEMO-SEO-STANDARD"]),
}


def _published_file_result(iid: str, label: str, path: str, code: int, body: str) -> Dict[str, Any]:
    missing_note, sev, skus = _SHOULD_EXIST[iid]
    if code == 200:
        first = next((ln.strip() for ln in (body or "").splitlines() if ln.strip()), "")
        return _ok(iid, label, f"{path} returns 200, first line reads: {first[:48]}",
                   f"{label}: the file is published and publicly readable, so keep it as it is.")
    if 300 <= code < 400:
        return _ok(iid, label, f"{path} returns {code} (published; crawlers pick it up by following the redirect)",
                   f"{label}: the entry exists but redirects, which does not stop it being discovered.")
    if code in (403, 401):
        return _unverified(iid, label, f"{path} returns {code} (present but not publicly readable)")
    return _bad(iid, label, f"{path} returns {code}", missing_note, skus, sev)


def _probe_dns(domain: str, html: str, headers: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    resolver_ok = True

    def lookup(name: str, port: int = 443):
        try:
            return sorted({i[4][0] for i in socket.getaddrinfo(name, port)})
        except Exception:
            return []

    # IPv6
    try:
        v6 = [a for a in lookup(domain) if ":" in a]
        out["ipv6"] = _ok("ipv6", "IPv6 and AAAA alignment", f"AAAA {len(v6)} records",
                          "Dual stack is available, so mail and access do not break on v6-only networks.") if v6 else \
            _bad("ipv6", "IPv6 and AAAA alignment", "no AAAA records found",
                 "Some networks are v6-only, and when the mail-from and the actual entry point differ, deliverability suffers.", [], "LOW")
    except Exception as exc:
        resolver_ok = False
        out["ipv6"] = _unverified("ipv6", "IPv6 and AAAA alignment", str(exc))

    # DNS 记录卫生
    try:
        addrs = lookup(domain)
        out["dns_records"] = _ok("dns_records", "DNS records and TTL hygiene",
                                 f"resolves to {len(addrs)} addresses",
                                 "The records exist and can be queried, so any later fix can actually take effect.") if addrs else \
            _bad("dns_records", "DNS records and TTL hygiene", "the domain resolves to no address",
                 "When resolution fails, no fix can land.", ["DEMO-DOM-COM"], "HIGH")
    except Exception as exc:
        out["dns_records"] = _unverified("dns_records", "DNS records and TTL hygiene", str(exc))

    # 公网 IP 与机房
    try:
        addrs = [a for a in lookup(domain) if is_ssrf_safe(a)]
        out["public_ip"] = _ok("public_ip", "Public IP and server geolocation",
                               ", ".join(addrs[:3]) or "-",
                               "The public address actually serving the site is identified; see the hosting_location item for where it is hosted.") if addrs else \
            _bad("public_ip", "Public IP and server geolocation", "no verifiable public address",
                 "Odd resolution results leave both customers and search engines outside.", ["DEMO-WP17-BUSINESS"], "HIGH")
    except Exception as exc:
        out["public_ip"] = _unverified("public_ip", "Public IP and server geolocation", str(exc))

    # staging / test 站点是否公网可达（只探 3 个约定前缀，不做枚举）
    # 先排掉泛解析：*.domain 整体解析时，任何前缀都会"命中"，结论没有意义
    def _nonce_lookup() -> bool:
        return bool(lookup(f"cradilot-nohost-{int(time.time()) % 100000}.{domain}", 80))

    staging_hits = []
    if _nonce_lookup():
        out["staging_public"] = _unverified(
            "staging_public", "Staging or test environment public",
            "this domain uses wildcard resolution (any subdomain resolves), so this cannot tell whether a test site exists")
    else:
        for prefix in ("stage", "staging", "dev"):
            name = f"{prefix}.{domain}"
            if lookup(name, 80) or lookup(name, 443):
                staging_hits.append(name)
        out["staging_public"] = (
            _bad("staging_public", "Staging or test environment public",
                 ", ".join(staging_hits) + " resolve on the public internet",
                 "By naming convention these subdomains are usually build or preview environments. We did not access their content, "
                 "but being publicly resolvable is itself worth checking: what runs there and whether indexing is blocked.",
                 ["DEMO-CF-BOOSTER-PERSONAL"], "LOW") if staging_hits else
            _ok("staging_public", "Staging or test environment public",
                "none of the stage/dev/test conventional prefixes resolve",
                "Internal build environments are not hanging on the public internet, so you have this one right."))

    # 页面引用的云主机名（资产发现的诚实子集：只看客户自己发出来的）
    cloud_pat = (r'([a-z0-9.-]+\.(?:amazonaws\.com|blob\.core\.windows\.net|'
                 r'storage\.googleapis\.com|cloudfront\.net|azureedge\.net|vercel\.app|netlify\.app))')
    hosts = sorted({urllib.parse.urlparse("https://" + h).netloc
                    for h in re.findall(cloud_pat, (html or ""), re.I)})
    out["cloud_assets"] = (_ok("cloud_assets", "Public cloud assets discovered",
                               ", ".join(hosts[:4]),
                               "These third-party addresses come from your own pages, so they belong in the same asset inventory.") if hosts else
                           _na("cloud_assets", "Public cloud assets discovered", "the page references no recognisable cloud asset host"))

    # DDoS / 边缘防护：从解析与响应头判断，不打任何流量
    edge = bool(re.search(r"(?i)cloudflare|cf-ray", str(headers.get("server", "")) +
                          str(headers.get("cf-ray", "")) + str(headers.get("via", "")))) or \
        bool(signals_via(headers))
    out["ddos_protection"] = (_ok("ddos_protection", "DDoS absorption in front of origin",
                                   "the response headers place the site behind a CDN or edge service",
                                   "Ordinary attack traffic is absorbed at the edge, so the origin does not take it alone.") if edge else
                               _bad("ddos_protection", "DDoS absorption in front of origin",
                                    "no CDN or edge protection signatures found",
                                    "A few hundred malicious requests overnight can stop an origin responding, and SMEs usually hear about it from their customers first.",
                                    ["DEMO-CF-BOOSTER-PERSONAL"], "MEDIUM"))
    if not resolver_ok:
        out["dns_records"]["status"] = "unverified"
    return out


def signals_via(headers: Dict[str, str]) -> bool:
    via = str(headers.get("via") or "").lower()
    return any(t in via for t in ("akamai", "fastly", "cloudflare", "varnish"))


def _extra_http_checks(base_url: str, headers: Dict[str, str], html: str,
                       dl: Optional["_Deadline"] = None) -> Dict[str, Dict[str, Any]]:
    """单请求即可判定的头部/重定向类结论（不发载荷、不试凭据）。"""
    out: Dict[str, Dict[str, Any]] = {}
    origin = urllib.parse.urlparse(base_url)
    base = f"{origin.scheme}://{origin.netloc}"

    def to(cap: float = PATH_TIMEOUT_SECONDS) -> float:
        return dl.http_timeout(cap) if dl else cap

    def hdr(name: str) -> str:
        return str(headers.get(name) or "")

    hsts = hdr("strict-transport-security")
    out["hsts"] = (_ok("hsts", "HSTS policy", hsts[:70],
                       "From now on the browser only uses https, so the downgrade window is closed.") if "max-age=" in hsts else
                   _bad("hsts", "HSTS policy", "the response header has no max-age",
                        "With no enforced HTTPS, a hand-typed http:// or a downgrade can expose sessions and form data.",
                        ["DEMO-CF-BOOSTER-PERSONAL", "DEMO-SSL-BUSINESS"], "MEDIUM"))
    csp = hdr("content-security-policy")
    out["csp"] = (_ok("csp", "Content-Security-Policy", f"{len(csp)} characters of directives",
                      "The page is restricted in whose scripts it can load.") if csp else
                  _bad("csp", "Content-Security-Policy", "this response header is not returned",
                       "If a third-party component is ever poisoned, visitors' browsers run the attacker's code directly.",
                       ["DEMO-CF-BOOSTER-PERSONAL"], "MEDIUM"))

    # CORS：带一个无害的 Origin 观察回显，不做任何注入
    try:
        with httpx.Client(timeout=PATH_TIMEOUT_SECONDS, headers={"user-agent": BROWSER_UA,
                                                                "origin": "https://example-invalid.test"},
                          verify=True, follow_redirects=False) as client:
            resp = client.get(base, timeout=to())
            acao = str(resp.headers.get("access-control-allow-origin") or "")
            if acao == "*":
                out["cors_policy"] = _bad("cors_policy", "CORS policy reflection", "ACAO: *",
                                         "Any website can read your API data.", [], "HIGH")
            elif "example-invalid.test" in acao:
                out["cors_policy"] = _bad("cors_policy", "CORS policy reflection",
                                          f"ACAO reflected an arbitrary origin: {acao[:60]}",
                                          "The allow list effectively does not exist, so sessions can be read by third-party sites.", [], "HIGH")
            else:
                out["cors_policy"] = _ok("cors_policy", "CORS policy reflection",
                                         acao or "no ACAO returned (browsers refuse cross-origin reads by default)",
                                         "Cross-origin reads are blocked by the default policy.")
    except Exception as exc:
        out["cors_policy"] = _unverified("cors_policy", "CORS policy reflection", str(exc))

    # www 与 apex 是否统一到一处
    apex_host = re.sub(r"^www\.", "", origin.netloc)
    try:
        with httpx.Client(timeout=PATH_TIMEOUT_SECONDS, headers={"user-agent": BROWSER_UA},
                          verify=True, follow_redirects=True) as client:
            other = f"{origin.scheme}://{apex_host}" if origin.netloc.lower().startswith("www.") \
                else f"{origin.scheme}://www.{apex_host}"
            resp = client.get(other)
            landed = urllib.parse.urlparse(str(resp.url)).netloc.lower()
            same = landed == origin.netloc.lower()
            out["www_apex_redirect"] = (
                _ok("www_apex_redirect", "Canonical host redirect (www vs apex)",
                    f"{other} → {landed or resp.status_code}",
                    "Link weight is no longer split in two.") if same else
                _bad("www_apex_redirect", "Canonical host redirect (www vs apex)",
                     f"{other} stopped at {landed or resp.status_code}",
                     "Two hosts are live at the same time, the SEO gets split, and the certificate may cover only one of them.", [], "LOW"))
    except Exception as exc:
        out["www_apex_redirect"] = _unverified("www_apex_redirect", "Canonical host redirect (www vs apex)",
                                               str(exc))

    # 缓存与边缘
    cache = (hdr("cache-control") + " " + hdr("age") + " " + hdr("x-cache")).strip()
    out["cache_headers"] = (_ok("cache_headers", "Cache-control and expiry headers", cache[:80] or "-",
                                "Static content has cache directives, so repeat visits do not rebuild the whole page.")
                            if re.search(r"(?i)(max-age|s-maxage|x-cache:\s*hit|age:)", cache) else
                            _bad("cache_headers", "Cache-control and expiry headers", "no cache directives found",
                                 "Every visitor pushes a full render onto the origin, so slow and costly arrive together.",
                                 ["DEMO-CF-BOOSTER-PERSONAL"], "MEDIUM"))
    edge_sig = " ".join([hdr("server"), hdr("cf-ray"), hdr("cf-cache-status"), hdr("x-cache"),
                         hdr("via"), hdr("x-amz-cf-id"), hdr("x-akamai-transformed")])
    has_edge = bool(re.search(r"(?i)cloudflare|akamai|fastly|varnish|sucuri|cdn-cache|x-site-cache",
                              edge_sig))
    out["cdn"] = (_ok("cdn", "CDN edge serving the site", edge_sig[:70].strip() or "edge signatures confirmed in the response headers",
                      "Static content sits closer to the buyer.") if has_edge else
                  _bad("cdn", "CDN edge serving the site", "the response headers show no CDN or edge node signatures",
                       "Visitors nationwide and even from other states all hit the same machine, and mobile first screens suffer most.",
                       ["DEMO-CF-BOOSTER-PERSONAL"], "MEDIUM"))
    out["load_balancer"] = _na("load_balancer", "Load balancer in front of origin",
                                "whether several instances sit behind it cannot be told from the public internet; this is an architecture confirmation item")
    out["waf_present"] = (_ok("waf_present", "Web application firewall in front of the site",
                              "the response headers carry protection signatures", "Common attack patterns get blocked before the patch lands.")
                          if re.search(r"(?i)(sucuri|cloudflare|akamai|mod_security|x-waf)",
                                       hdr("server") + hdr("via") + hdr("x-powered-by-360waf")) else
                          _bad("waf_present", "Web application firewall in front of the site",
                               "no WAF signatures found",
                               "Without a WAF, every flaw in the application itself is exposed straight to the internet.",
                               ["DEMO-CF-BOOSTER-PRO"], "MEDIUM"))
    out["serverless"] = (_ok("serverless", "Serverless or edge functions detected",
                             hdr("x-vercel-id") or hdr("x-nf-account") or hdr("server")[:30],
                             "Function-based deployment moves the patching responsibility to the platform.")
                         if re.search(r"(?i)vercel|netlify|x-vercel|awslambda",
                                      hdr("server") + hdr("x-powered-by")) else
                         _na("serverless", "Serverless or edge functions detected", "no serverless signatures found"))
    out["container_platform"] = (_ok("container_platform", "Container platform detected",
                                     hdr("x-powered-by")[:40],
                                     "An orchestrated environment needs its own hardening baseline.")
                                 if re.search(r"(?i)kube|docker|container", hdr("x-powered-by") + hdr("server"))
                                 else _na("container_platform", "Container platform detected", "no container platform signatures found"))
    out["sourcemap_leak"] = _na("sourcemap_leak", "Source maps served to the browser",
                                "this has to be confirmed bundle by bundle; this homepage references no .js.map files") \
        if ".js.map" not in (html or "") else \
        _bad("sourcemap_leak", "Source maps served to the browser", "the page references .js.map files",
             "A source map hands readable source code to the browser.", [], "MEDIUM")

    # 404 处理：一次请求，只看是否泄露栈信息
    try:
        with httpx.Client(timeout=PATH_TIMEOUT_SECONDS, headers={"user-agent": BROWSER_UA},
                          verify=True, follow_redirects=True) as client:
            resp = client.get(base.rstrip("/") + "/cradilot-no-such-page-404")
            leaky = bool(re.search(r"(?i)(traceback \(most recent|sqlstate|ora-\d{5}|stack trace|"
                                   r"fatal error|on line \d+)", resp.text or ""))
            out["error_handling"] = (_bad("error_handling", "Graceful error pages",
                                          f"the 404 page shows framework error signatures (HTTP {resp.status_code})",
                                          "A bare error page loses the buyer and hands over the internal paths at the same time.",
                                          [], "MEDIUM") if leaky else
                                      _ok("error_handling", "Graceful error pages",
                                          f"HTTP {resp.status_code}, no stack details leaked",
                                          "The error page does not explain anything to an attacker."))
    except Exception as exc:
        out["error_handling"] = _unverified("error_handling", "Graceful error pages", str(exc))

    # GraphQL：只在页面自己引用了 graphql 时，发一次无操作的 GET 观察是否有端点
    if re.search(r"(?i)/graphql\b", (html or "")):
        try:
            with httpx.Client(timeout=PATH_TIMEOUT_SECONDS, headers={"user-agent": BROWSER_UA},
                              verify=True, follow_redirects=False) as client:
                resp = client.get(base.rstrip("/") + "/graphql")
                introspect = resp.status_code == 200 and "data" in (resp.text or "")[:400].lower()
                out["graphql"] = (_bad("graphql", "GraphQL endpoint exposed",
                                       f"/graphql returns {resp.status_code}"
                                       + (", and introspection looks open" if introspect else ""),
                                       "With introspection enabled you hand the whole API map to the outside.",
                                       [], "HIGH" if introspect else "MEDIUM"))
        except Exception as exc:
            out["graphql"] = _unverified("graphql", "GraphQL endpoint exposed", str(exc))
    else:
        out["graphql"] = _na("graphql", "GraphQL endpoint exposed", "the page references no GraphQL endpoint")

    # 对象列表：只查客户页面自己发出来的桶地址，绝不猜桶名
    m = re.search(r'https?://[a-z0-9.-]*(?:amazonaws\.com|storage\.googleapis\.com|'
                  r'blob\.core\.windows\.net|digitaloceanspaces\.com)[^"\'\s<>]*', (html or ""), re.I)
    if m:
        try:
            with httpx.Client(timeout=PATH_TIMEOUT_SECONDS, headers={"user-agent": BROWSER_UA},
                              verify=True, follow_redirects=False) as client:
                resp = client.get(m.group(0))
                listing = bool(re.search(r"(?i)(<listbucketresult|<key>|x-amz-meta|<enumeration)",
                                         resp.text or ""))
                out["public_bucket"] = (_bad("public_bucket", "Published bucket allows listing",
                                             f"{resp.status_code}, returns an object listing",
                                             "The bucket your pages reference can be listed object by object, so customer files and backups could be taken in bulk.",
                                             [], "CRITICAL") if listing else
                                         _ok("public_bucket", "Published bucket allows listing",
                                             f"{resp.status_code}, no listing returned",
                                             "The published storage address cannot be listed, so keep this one as it is."))
        except Exception as exc:
            out["public_bucket"] = _unverified("public_bucket", "Published bucket allows listing", str(exc))
        out["public_storage_bucket"] = out["public_bucket"]
    else:
        out["public_bucket"] = _na("public_bucket", "Published bucket allows listing",
                                   "the page references no object storage address")
        out["public_storage_bucket"] = out["public_bucket"]

    # 失效链接抽样：只取同站前 8 条（绝对或相对写法都算），逐条 HEAD，超时即未测
    raw_hrefs = re.findall(r'href=["\']([^"\'#]{2,160})["\']', (html or ""))
    links: List[str] = []
    for h in raw_hrefs:
        u = urllib.parse.urljoin(base + "/", h)
        if _same_origin(base, u) and u not in links:
            links.append(u)
        if len(links) >= 8:
            break
    broken: List[str] = []
    checked = 0
    if links:
        try:
            with httpx.Client(timeout=3.0, headers={"user-agent": BROWSER_UA},
                              verify=True, follow_redirects=True) as client:
                for u in links:
                    if dl and dl.expired():
                        break
                    if not _same_origin(base, u):
                        continue
                    try:
                        r = client.head(u, timeout=to(3.0))
                        checked += 1
                        if r.status_code in (404, 410, 500, 502, 503):
                            broken.append(f"{u} ({r.status_code})")
                    except Exception:
                        continue
        except Exception as exc:
            out["broken_links"] = _unverified("broken_links", "Broken internal links sampled", str(exc))
        else:
            out["broken_links"] = (_bad("broken_links", "Broken internal links sampled",
                                        ", ".join(broken[:5]),
                                        "A clicked link lands on a 404; buyers do not report it to you, they just close the page.",
                                        ["DEMO-WP17-BUSINESS"], "MEDIUM") if broken else
                                   _ok("broken_links", "Broken internal links sampled",
                                       f"sampling {checked}/{len(links)} same-site links, all fine",
                                       "Links within the sampled range are usable.") if checked else
                                   _unverified("broken_links", "Broken internal links sampled",
                                               "none of the sampled links completed a request"))
    else:
        out["broken_links"] = _na("broken_links", "Broken internal links sampled", "the homepage has no same-site links to sample")
    out["broken_pages"] = out.get("broken_links") or _na("broken_pages", "Key pages return 200",
                                                        "the same sampling batch did not complete")
    return out


def _tls_checks(host: str) -> Dict[str, Dict[str, Any]]:
    try:
        info = inspect_tls(host) or {}
    except Exception as exc:
        return {"tls_config": _unverified("tls_config", "TLS version and certificate chain", str(exc))}
    if not info.get("cert_checked"):
        return {"tls_config": _unverified("tls_config", "TLS version and certificate chain",
                                          info.get("ssl_error") or "the handshake returned no certificate information")}
    observed = f"issued by {info.get('cert_issuer') or 'not disclosed'}; expires {info.get('cert_not_after') or 'unknown'}"
    trusted = bool(info.get("ssl_valid"))
    return {"tls_config": (
        _ok("tls_config", "TLS version and certificate chain", observed,
            "The certificate chain and domain match pass the default trust store, so the transport layer needs no extra spend.") if trusted else
        _bad("tls_config", "TLS version and certificate chain",
             observed + f"; validation did not pass: {info.get('ssl_error') or ''}",
             "When the certificate chain is not trusted, the browser warns the visitor before any content is read.",
             ["DEMO-SSL-BUSINESS"], "HIGH"))}


def _perf_checks(page: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    ms = page.get("elapsed_ms")
    size = page.get("bytes") or 0
    if isinstance(ms, int):
        out["page_speed"] = (_ok("page_speed", "Homepage load time", f"{ms} ms / {size/1024:.0f} KB",
                                 "The first screen is within an acceptable range on mobile networks.") if ms <= 2500 else
                             _bad("page_speed", "Homepage load time", f"{ms} ms / {size/1024:.0f} KB",
                                  "Past 2.5 seconds, mobile visitors leave before the page finishes rendering; that is a net loss of traffic and budget.",
                                  ["DEMO-CF-BOOSTER-PERSONAL", "DEMO-WP17-BUSINESS"],
                                  "HIGH" if ms > 4000 else "MEDIUM"))
        out["mobile_performance"] = (_ok("mobile_performance", "Mobile load experience",
                                         f"weight {size/1024/1024:.2f} MB",
                                         "Phone visitors do not have to pay for data while your page downloads.") if size <= 2_500_000 else
                                     _bad("mobile_performance", "Mobile load experience",
                                          f"homepage weight {size/1024/1024:.2f} MB",
                                          "Most SME traffic comes from phones, and a few megabytes of homepage means over ten seconds of blank screen on 4G.",
                                          ["DEMO-CF-BOOSTER-PERSONAL"], "MEDIUM"))
    else:
        out["page_speed"] = _unverified("page_speed", "Homepage load time", "the homepage request did not complete, so there is no timing sample")
        out["mobile_performance"] = _unverified("mobile_performance", "Mobile load experience",
                                                "the homepage request did not complete, so there is no size sample")
    return out


def deep_findings(base_url: str, html: str, headers: Dict[str, str], domain: str,
                  signals: Dict[str, Any], page: Dict[str, Any],
                  budget: float = DEEP_BUDGET_SECONDS) -> Tuple[List[Dict[str, Any]],
                                                                Dict[str, Any]]:
    """
    返回 (findings, extras)。findings 用清单条目 id 作为 check 名，
    extras 里带 stances（内容类判据的观测原文）供界面与 PDF 引用。
    """
    findings: List[Dict[str, Any]] = []
    started = time.monotonic()
    dl = _Deadline(budget)
    with ThreadPoolExecutor(max_workers=3) as pool:
        f1 = pool.submit(_probe_paths, base_url, html or "", dl)
        f2 = pool.submit(_extra_http_checks, base_url, headers or {}, html or "", dl)
        f3 = pool.submit(_probe_dns, domain, html or "", headers or {})
        groups = []
        for fut in (f1, f2, f3):
            try:
                groups.append(fut.result())
            except Exception:
                groups.append({})
    # 实测先行：下游按"每个条目取第一条结论"对号，实测结果必须盖过正文推断
    for group in groups:
        findings.extend(group.values())
    findings.extend(_content_checks(base_url, html or "", headers or {}, signals))
    findings.extend(_tls_checks(urllib.parse.urlparse(base_url).hostname or domain).values())
    findings.extend(_perf_checks(page or {}).values())

    # 内容类判据顺带产出的观测，供结论卡直接引用原文
    stances = {f["check"]: f.get("observed") for f in findings if f.get("observed")}
    spent = round(time.monotonic() - started, 2)
    return findings, {"signals": signals, "stances": stances,
                      "probe_seconds": spent, "probe_budget": budget,
                      "budget_exhausted": dl.expired()}
