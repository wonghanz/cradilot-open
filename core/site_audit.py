"""
Cradilot Core - 官网机检引擎 (Site Machine Audit)

输入老板自己的网址，输出一组**可查证、可复述、可对应到真实 本公司产品**的检查结论。
这是新流程第 ② 步的证据来源：结论不是问出来的，是测出来的。

设计约束
  · 全程零付费 API key；本机解析优先，公共 DoH / RDAP 兜底。
  · 每一项独立超时并返回三态：pass / fail / unverified。
    断网或对方无响应时必须如实标 unverified，绝不把"没测到"写成"没有"。
  · 每项自带白话说明(plain)与它真正导向的 SKU，供蓝图与评分卡直接引用。

复用而非重写：TLS 核验用 web_scraper.inspect_tls，邮件防伪用
dev_audit.DevLevelAuditEngine.inspect_dns_email_security（已改为真实 DNS 解析）。
"""

import json
import re
import socket
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core import audit_checklist, site_signals, vuln_intel
from core.site_business_audit import deep_findings
from core.web_scraper import inspect_tls, normalize_url, is_ssrf_safe
from core.dev_audit import DevLevelAuditEngine

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Cradilot-SiteAudit/3.0"
)

# 单项检查的墙钟上限。任何一项卡住都不能拖垮整份审计（官方 5 分钟硬指标）。
CHECK_TIMEOUT_SECONDS = float(6.0)

# 安全响应头：缺哪一项、后果是什么、由哪个产品补
SECURITY_HEADERS = [
    ("strict-transport-security", "HSTS",
     "HTTPS is not forced. When a visitor types http:// by hand, or a downgrade attack is used, "
     "login sessions and form entries can be read.",
     ["DEMO-CF-BOOSTER-PERSONAL", "DEMO-SSL-BUSINESS"]),
    ("content-security-policy", "CSP",
     "The page does not say whose scripts it may load. If any third-party component is poisoned, "
     "the visitor's browser runs the attacker's code directly.",
     ["DEMO-CF-BOOSTER-PERSONAL"]),
    ("x-frame-options", "X-Frame-Options",
     "Being embedded in a frame is not blocked, so a click-jacking page can cover your admin buttons with a decoy.",
     ["DEMO-CF-BOOSTER-PERSONAL"]),
    ("x-content-type-options", "X-Content-Type-Options",
     "MIME sniffing is not blocked, so an uploaded image file can be run by the browser as a script.",
     ["DEMO-CF-BOOSTER-PERSONAL"]),
    ("referrer-policy", "Referrer-Policy",
     "Outbound links do not control the address they carry, so internal paths and customer query "
     "parameters leak to third parties.",
     ["DEMO-CF-BOOSTER-PERSONAL"]),
]

TECH_FINGERPRINTS = [
    (r"/wp-content/|wp-includes|<meta name=\"generator\" content=\"WordPress",
     "WordPress", "A self-hosted WordPress site that goes long without updates is most often "
     "compromised through its plugins."),
    (r"__NEXT_DATA__|/_next/", "Next.js", "The front-end framework version needs to follow security advisories."),
    (r"data-reactroot|react", "React", "Build-chain dependencies need to be confirmed free of known vulnerabilities."),
    (r"wixstatic|wix.com", "Wix", "Domain and business email still have to be completed on your side."),
    (r"squarespace", "Squarespace", "Domain and business email still have to be completed on your side."),
    (r"shopify", "Shopify",
     "With Shopify already in place, the focus moves to domain, business email and the certificate."),
    (r"opencart|oc-content", "OpenCart",
     "Older OpenCart releases have many published vulnerabilities and need migration or managed hardening."),
    (r"laravel|livewire", "Laravel", "On a custom-built system, patching and backups are your own responsibility."),
    (r"jquery-1\.|jquery/1\.|jquery.min.js\?v=1", "jQuery 1.x (outdated)",
     "jQuery 1.x has publicly disclosed prototype pollution flaws that are still being exploited at volume."),
]

# Cloudflare 判定线索（本公司有转售 Cloudflare 驱动的托管服务）
CLOUDFLARE_SERVER_TOKENS = ("cloudflare",)
CF_COOKIE_TOKENS = ("__cf_bm", "cf_clearance")
CF_NS_PATTERN = re.compile(r"(?:^|\.)ns\d+\.cloudflare\.(?:com|by)$", re.IGNORECASE)


# ─── 结论构造 ────────────────────────────────────────────────────────────────
def _finding(check: str, title: str, status: str, observed: str,
             plain: str, severity: str = "INFO",
             skus: Optional[List[str]] = None,
             source: str = "machine_probe") -> Dict[str, Any]:
    """status 只允许 pass / fail / unverified。unverified 不得转译成 fail。"""
    return {
        "check": check,
        "title": title,
        "status": status,
        "observed": observed,
        "plain": plain,
        "severity": severity,
        "vendor_skus": skus or [],
        "evidence_source": source,
        "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _unverified(check: str, title: str, why: str) -> Dict[str, Any]:
    return _finding(check, title, "unverified", why,
                    f"This check could not be completed in this run ({why}). "
                    "It is not used for any deduction or sales point.",
                    severity="UNKNOWN", source="probe_failed")


# ─── 各项检查 ────────────────────────────────────────────────────────────────
def _fetch_homepage(url: str) -> Dict[str, Any]:
    """抓首页：拿响应头、状态码、HTML、跳转链路与耗时。跳转后再次校验内网地址。"""
    out: Dict[str, Any] = {"ok": False}
    headers = {"User-Agent": BROWSER_UA, "Accept": "text/html,*/*"}
    with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers, verify=True) as client:
        started = time.time()
        resp = client.get(url)
        out["elapsed_ms"] = int((time.time() - started) * 1000)
        # 重定向可能把请求带进内网，跳转落地主机必须再验一次（旧版只验入参主机）
        final_host = urllib.parse.urlparse(str(resp.url)).hostname or ""
        if final_host and final_host != urllib.parse.urlparse(url).hostname and not is_ssrf_safe(final_host):
            raise ValueError(f"Redirect reached an unauthorised internal address ({final_host}); request aborted")
        out.update({
            "ok": True,
            "final_url": str(resp.url),
            "status_code": resp.status_code,
            "http_version": resp.http_version,
            "headers": {k.lower(): v for k, v in resp.headers.items()},
            # 页面构建器（Elementor/Divi）会把几十万字节的 CSS 内联在 <head>，
            # 原样截断会让正文（图片、H1、链接、联系方式）整块掉在窗口之外。
            "html": _strip_css_bodies(resp.text or "")[:HTML_KEEP_CHARS],
            "bytes": len(resp.content or b""),
            "redirect_chain": [str(h.url) for h in getattr(resp, "history", [])],
        })
    return out


# 内容类判据要读的是标记，不是样式表。
HTML_KEEP_CHARS = 1_200_000


def _strip_css_bodies(html: str) -> str:
    return re.sub(r"<style\b[^>]*>[\s\S]*?</style>", "<!--css omitted-->", html or "", flags=re.I)


def _check_transport(final_url: str, hdrs: Dict[str, str], http_version: str) -> List[Dict[str, Any]]:
    """HTTPS 强制、证书有效期、HTTP 版本。"""
    findings: List[Dict[str, Any]] = []
    host = urllib.parse.urlparse(final_url).hostname or ""

    if not final_url.startswith("https://"):
        findings.append(_finding(
            "https_enforced", "Site-wide HTTPS", "fail", f"Final landing point: {final_url}",
            "Visitors get an unencrypted page. The browser shows a \"Not secure\" warning, and anything "
            "typed into a form can be read in transit.",
            "HIGH", ["DEMO-WP17-BUSINESS", "DEMO-SSL-BUSINESS"]))
        return findings

    findings.append(_finding("https_enforced", "Site-wide HTTPS", "pass", "https is in use",
                             "Visitors get an encrypted connection, so the browser shows no security warning.",
                             skus=[]))

    tls = inspect_tls(host)
    if not tls.get("cert_checked"):
        findings.append(_unverified("certificate", "Certificate validity",
                                    tls.get("ssl_error") or "TLS handshake did not complete"))
    else:
        days = tls.get("cert_days_left")
        issuer = tls.get("cert_issuer") or "unknown issuer"
        if days is None:
            findings.append(_finding("certificate", "Certificate validity", "unverified",
                                     f"A trusted certificate was confirmed, but the expiry date could not be "
                                     f"resolved ({tls.get('cert_detail_error', '')})",
                                     "The certificate chain is trusted. The expiry date was not read in this run, "
                                     "so no risk is claimed from it.", "UNKNOWN"))
        elif days < 0:
            findings.append(_finding("certificate", "Certificate validity", "fail",
                                     f"{issuer}, expired {abs(days)} days ago",
                                     "The certificate has expired. Browsers hold the whole site at a warning page, "
                                     "which is the same as the website being offline.",
                                     "CRITICAL", ["DEMO-SSL-BUSINESS", "DEMO-WP17-BUSINESS"]))
        elif days < 21:
            findings.append(_finding("certificate", "Certificate validity", "fail",
                                     f"{issuer}, {days} days left",
                                     "The certificate expires soon and has no auto-renewal. Every day renewal slips "
                                     "is another day the site stays blocked.",
                                     "HIGH", ["DEMO-WP17-BUSINESS"]))
        else:
            findings.append(_finding("certificate", "Certificate validity", "pass",
                                     f"{issuer}, {days} days left",
                                     "The certificate is within its validity period. Confirm whether the host handles "
                                     "auto-renewal, otherwise the site is still blocked once it lapses.",
                                     skus=[]))

    if str(http_version).upper() in ("HTTP/1.0", "HTTP/1.1"):
        findings.append(_finding("http_version", "Transport protocol version", "fail", http_version,
                                 "Still on HTTP/1.1: page assets are fetched one after another, so the first screen "
                                 "is clearly slower on a phone.",
                                 "LOW", ["DEMO-CF-BOOSTER-PERSONAL", "DEMO-WP17-BUSINESS"]))
    else:
        findings.append(_finding("http_version", "Transport protocol version", "pass", http_version or "unknown",
                                 "HTTP/2 or higher is in use, so static assets can be fetched in parallel.",
                                 skus=[]))
    return findings


def _check_headers(hdrs: Dict[str, str]) -> List[Dict[str, Any]]:
    """安全响应头逐条核验，按缺失数量给总评。"""
    findings: List[Dict[str, Any]] = []
    missing: List[str] = []
    for header, label, consequence, skus in SECURITY_HEADERS:
        value = hdrs.get(header, "")
        if value:
            findings.append(_finding(f"header_{header}", f"{label} response header", "pass",
                                     value[:70], f"{label} is configured.", skus=[]))
        else:
            missing.append(label)
            findings.append(_finding(f"header_{header}", f"{label} response header", "fail",
                                     "This response header was not returned",
                                     f"{label} is missing: {consequence}", "MEDIUM", skus))

    server = hdrs.get("server", "")
    if re.search(r"\d+\.\d+", server):
        findings.append(_finding("server_version_disclosure", "Server version disclosure", "fail",
                                 f"Server: {server}",
                                 "The response headers publish the server and component version numbers, so a scanner "
                                 "can match them straight to known vulnerabilities.",
                                 "MEDIUM", ["DEMO-CF-BOOSTER-PERSONAL"]))
    elif server:
        findings.append(_finding("server_version_disclosure", "Server version disclosure", "pass",
                                 f"Server: {server}", "The response headers do not publish a specific version number.",
                                 skus=[]))
    else:
        findings.append(_finding("server_version_disclosure", "Server version disclosure", "pass",
                                 "No Server header returned",
                                 "The response headers expose no back-end information.", skus=[]))

    # Cookie 属性：有 Set-Cookie 但缺 Secure/HttpOnly 才算问题，没有 Cookie 则无话可说
    cookies = hdrs.get("set-cookie", "")
    if cookies:
        weak = [n for n, pat in (("Secure", r"\bsecure\b"), ("HttpOnly", r"\bhttponly\b"),
                                 ("SameSite", r"samesite"))
                if not re.search(pat, cookies, re.IGNORECASE)]
        if weak:
            findings.append(_finding("cookie_flags", "Cookie security attributes", "fail",
                                     f"Missing {'/'.join(weak)}",
                                     f"Session cookies are missing the {'/'.join(weak)} attribute, "
                                     "so a stolen session is easier to replay directly in a cross-site or "
                                     "plain-text setting.",
                                     "MEDIUM", ["DEMO-CF-BOOSTER-PERSONAL"]))
        else:
            findings.append(_finding("cookie_flags", "Cookie security attributes", "pass",
                                     "Secure/HttpOnly/SameSite all present",
                                     "Session cookie attributes are fully configured.", skus=[]))
    else:
        findings.append(_finding("cookie_flags", "Cookie security attributes", "unverified",
                                 "The homepage set no cookies",
                                 "This request returned no cookies, so there is nothing to judge here.", "UNKNOWN"))

    if missing:
        findings.append(_finding(
            "header_score", "Security response headers overall", "fail" if len(missing) >= 3 else "pass",
            f"{len(SECURITY_HEADERS) - len(missing)}/{len(SECURITY_HEADERS)} configured, "
            f"missing {', '.join(missing)}",
            f"{'Most' if len(missing) >= 3 else 'Some'} of the basic protection headers are missing "
            f"({', '.join(missing)}). "
            "On an enterprise CDN/WAF this is a one-time set of checkboxes, with no change to your website code.",
            "HIGH" if len(missing) >= 3 else "MEDIUM",
            ["DEMO-CF-BOOSTER-PERSONAL"]))
    else:
        findings.append(_finding("header_score", "Security response headers overall", "pass",
                                 f"{len(SECURITY_HEADERS)}/{len(SECURITY_HEADERS)} all configured",
                                 "The basic protection response headers are complete, so no extra spend is needed "
                                 "here.", skus=[]))
    return findings


def _check_mixed_content(html: str, final_url: str) -> List[Dict[str, Any]]:
    """页面一边挂 https 一边拉 http 资源。"""
    if not html:
        return [_unverified("mixed_content", "Mixed content", "The page source could not be retrieved")]
    # 只统计浏览器真的会去取的资源。此前用宽松的 (?:src|href) 匹配，把
    # <link rel="profile" href="http://gmpg.org/xfn/11"> 这类纯元数据引用也算了进去，
    # 而那是 WordPress 每页都带、浏览器从不加载的指针 —— 正常站点因此被误报混合内容。
    loadable: List[str] = []
    for tag in ("script", "img", "iframe", "source", "embed", "video", "audio"):
        loadable += re.findall(
            r'<%s\b[^>]*?\ssrc\s*=\s*["\']http://([^"\'/>]+)' % tag, html, re.IGNORECASE)
    loadable += re.findall(
        r'<link\b[^>]*?rel\s*=\s*["\']stylesheet["\'][^>]*?href\s*=\s*["\']http://([^"\'/>]+)',
        html, re.IGNORECASE)
    loadable += re.findall(
        r'<form\b[^>]*?action\s*=\s*["\']http://([^"\'/>]+)', html, re.IGNORECASE)
    hits = loadable
    if hits:
        uniq = sorted(set(hits))[:3]
        return [_finding("mixed_content", "Mixed content", "fail",
                         f"The page loads {len(set(hits))} http:// resources (for example: {', '.join(uniq)})",
                         "An encrypted page also loads images or scripts in plain text. The browser blocks part of "
                         "them, so the page looks broken, and those resources can be swapped on the way in.",
                         "MEDIUM", ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"])]
    return [_finding("mixed_content", "Mixed content", "pass", "No http:// references found",
                     "Page resources load the same way throughout, so the page never looks half broken.", skus=[])]


def _check_mobile(html: str) -> List[Dict[str, Any]]:
    if not html:
        return [_unverified("mobile_viewport", "Mobile friendliness", "The page source could not be retrieved")]
    if re.search(r"""<meta[^>]+name=["']viewport["']""", html, re.IGNORECASE):
        return [_finding("mobile_viewport", "Mobile friendliness", "pass", "A viewport is declared",
                         "The page scales properly on a phone. In Malaysia over 60% of enquiries arrive by phone.",
                         skus=[])]
    return [_finding("mobile_viewport", "Mobile friendliness", "fail", "No viewport tag declared",
                     "On a phone it shows a shrunk desktop page. Customers have to zoom in to read anything, and "
                     "most of them simply leave.",
                     "HIGH", ["DEMO-WP17-BUSINESS", "DEMO-IWB-STARTER"])]


def _check_speed(elapsed_ms: Optional[int], total_bytes: Optional[int]) -> List[Dict[str, Any]]:
    if elapsed_ms is None:
        return [_unverified("response_time", "Homepage response time", "No timing was captured in this run")]
    if elapsed_ms > 2500:
        level, plain = "HIGH", (f"The full homepage took {elapsed_ms} ms. The widely used rule of thumb is that past "
                                "3 seconds a sizeable share of visitors close the tab before they see any content, "
                                "so the ad spend goes to waste.")
    elif elapsed_ms > 1200:
        level, plain = "MEDIUM", (f"The full homepage took {elapsed_ms} ms. It works but is slow, and the mobile "
                                  "experience drops noticeably.")
    else:
        level, plain = "INFO", f"The full homepage took {elapsed_ms} ms. The speed looks good."
    findings = [_finding("response_time", "Homepage response time",
                         "pass" if elapsed_ms <= 1200 else "fail",
                         f"{elapsed_ms} ms (homepage {total_bytes or 0:,} bytes)", plain,
                         level, ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"] if level != "INFO" else [])]
    if total_bytes and total_bytes > 2_500_000:
        findings.append(_finding("page_weight", "Homepage weight", "fail", f"{total_bytes/1024/1024:.1f} MB",
                                 "The homepage is too heavy. On mobile data it loads clearly slower, usually because "
                                 "of large uncompressed images.",
                                 "MEDIUM", ["DEMO-CF-BOOSTER-PERSONAL"]))
    return findings


def _check_technology(html: str, hdrs: Dict[str, str]) -> List[Dict[str, Any]]:
    detected: List[str] = []
    notes: List[str] = []
    blob = (html or "")[:200_000]
    for pattern, name, note in TECH_FINGERPRINTS:
        if re.search(pattern, blob, re.IGNORECASE):
            detected.append(name)
            notes.append(note)
    gen = re.search(r"""<meta[^>]+name=["']generator["'][^>]+content=["']([^"']+)""",
                    blob, re.IGNORECASE)
    if gen and gen.group(1) not in detected:
        detected.append(gen.group(1))
    powered = hdrs.get("x-powered-by", "")
    if powered:
        detected.append(f"X-Powered-By: {powered}")

    if detected:
        uniq = list(dict.fromkeys(detected))[:6]
        return [_finding("technology_stack", "Technology stack identified", "pass", ", ".join(uniq),
                         f"The underlying technology of your website was identified: {', '.join(uniq)}. "
                         + (notes[0] if notes else
                            "Hosting and update responsibilities need to be confirmed clearly with your "
                            "current supplier."),
                         "INFO", ["DEMO-WP17-BUSINESS"] if any("WordPress" in d for d in uniq) else [])]
    return [_finding("technology_stack", "Technology stack identified", "unverified",
                     "No known fingerprint matched",
                     "No common website builder was identified. It may be custom-built or a purely static page.",
                     "UNKNOWN")]


def detect_cloudflare(host: str, hdrs: Dict[str, str]) -> Dict[str, Any]:
    """判断站点是否已经过 Cloudflare。返回 {"behind": bool, "signals": [...]}。

    只认真正属于 Cloudflare 的证据：响应头特征、Cookie 名、NS 授权、
    或解析 IP 落在其公开前缀段内。解析到几个 IP 之类的通用信息不得计入，
    否则任何能解析的域名都会被判定为"已在用 Cloudflare"。
    """
    signals: List[str] = []

    server = hdrs.get("server", "")
    if any(t in server.lower() for t in CLOUDFLARE_SERVER_TOKENS):
        signals.append(f"Response header server: {server}")
    if hdrs.get("cf-ray"):
        signals.append("Response header cf-ray is present")
    cookie = hdrs.get("set-cookie", "").lower()
    if any(t in cookie for t in CF_COOKIE_TOKENS):
        signals.append("Cloudflare cookies are set")

    # 响应头已足以定论时，不再做 IP 段与 NS 两次外网查询
    if signals:
        return {"behind": True, "signals": signals}

    try:
        ips = sorted({info[4][0] for info in socket.getaddrinfo(host, None)})
    except Exception as exc:
        return {"behind": False, "inconclusive": True,
                "signals": [f"DNS resolution did not complete ({type(exc).__name__})"]}

    ranges_ok = True
    try:
        import ipaddress
        req = urllib.request.Request("https://api.cloudflare.com/client/v4/ips",
                                     headers={"user-agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SECONDS) as resp:
            cf = json.loads(resp.read().decode("utf-8")).get("result", {}) or {}

        def _cidrs(key: str) -> List[str]:
            # 该接口历史上返回过 {"cidr": ...} 与裸字符串两种形态
            out = []
            for entry in cf.get(key) or []:
                if isinstance(entry, str):
                    out.append(entry)
                elif isinstance(entry, dict) and entry.get("cidr"):
                    out.append(str(entry["cidr"]))
            return out

        try:
            nets4 = [ipaddress.ip_network(c) for c in _cidrs("ipv4_cidrs")]
            nets6 = [ipaddress.ip_network(c) for c in _cidrs("ipv6_cidrs")]
        except ValueError:
            nets4, nets6 = [], []

        for ip in ips:
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                continue
            pool = nets4 if addr.version == 4 else nets6
            if pool and any(addr in net for net in pool):
                signals.append(f"Resolved IP {ip} falls inside a Cloudflare published prefix range")
                break
    except Exception:
        ranges_ok = False

    if not signals:
        try:
            from core.dev_audit import _resolve_records
            ns_texts, ns_via, _ = _resolve_records(host, "NS")
            if ns_via != "unresolved" and any(CF_NS_PATTERN.search(t.rstrip(".")) for t in ns_texts):
                signals.append(f"Nameserver delegation points to Cloudflare ({', '.join(ns_texts[:2])})")
        except Exception:
            pass

    return {"behind": bool(signals), "inconclusive": bool(not signals and not ranges_ok),
            "signals": signals}


def _check_cloudflare(cf_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把 detect_cloudflare 的结论翻译成给老板看的一句话。"""
    observed = "; ".join(dict.fromkeys(cf_state.get("signals") or []))[:220]
    if cf_state.get("behind"):
        return [_finding("cloudflare", "Cloudflare usage", "pass", observed,
                         "Your website already goes through Cloudflare. To be clear about this first: what you need "
                         "is not buying a CDN again, but handing the WAF rules, the caching policy and certificate "
                         "renewal to someone to manage. In our Cloudflare-powered managed service these three "
                         "are configuration steps, not something your own team has to watch.",
                         "INFO", ["DEMO-CF-BOOSTER-PERSONAL"])]
    if cf_state.get("inconclusive"):
        return [_unverified("cloudflare", "Cloudflare usage",
                            observed or "the lookups needed to tell did not complete")]
    return [_finding("cloudflare", "Cloudflare usage", "fail",
                     observed or "No Cloudflare indicator was found",
                     "Your website does not go through Cloudflare today: no CDN caching and no edge WAF blocking, so "
                     "a DDoS has to be absorbed by the host itself.",
                     "MEDIUM", ["DEMO-CF-BOOSTER-PERSONAL"])]


def _check_domain_registration(domain: str) -> List[Dict[str, Any]]:
    """域名注册状态与到期日。.my 走 MYNIC whois，其余走 RDAP。"""
    def _query_rdap() -> Optional[Dict[str, Any]]:
        try:
            req = urllib.request.Request(f"https://rdap.org/domain/{domain}",
                                         headers={"user-agent": BROWSER_UA,
                                                  "accept": "application/rdap+json"})
            with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def _query_mynic() -> Optional[Dict[str, str]]:
        try:
            with socket.create_connection(("whois.mynic.my", 43), timeout=CHECK_TIMEOUT_SECONDS) as sk:
                sk.sendall(f"{domain}\r\n".encode("ascii", "ignore"))
                time.sleep(0.6)
                raw = b""
                sk.setblocking(False)
                import select
                while True:
                    r, _, _ = select.select([sk], [], [], 1.5)
                    if not r:
                        break
                    chunk = sk.recv(4096)
                    if not chunk:
                        break
                    raw += chunk
            text = raw.decode("utf-8", "ignore")
            fields = {}
            for key, label in (("Creation Date", "created"), ("Registry Expiry Date", "expires"),
                               ("Registrar", "registrar")):
                m = re.search(rf"^{key}\s*:\s*(.+)$", text, re.MULTILINE)
                if m:
                    fields[label] = m.group(1).strip()
            return fields or None
        except Exception:
            return None

    info = _query_rdap()
    path = "rdap"
    if info is None and domain.endswith(".my"):
        fields = _query_mynic()
        if fields:
            info, path = fields, "mynic_whois"
    if info is None:
        return [_unverified("domain_registrant", "Domain registration and registrant of record",
                            "Neither RDAP nor MYNIC whois returned data"),
                _unverified("domain_expiry", "Domain expiry runway",
                            "Neither RDAP nor MYNIC whois returned data")]

    expires_raw = ""
    registrar = ""
    if path == "rdap":
        for ev in info.get("events", []) or []:
            if str(ev.get("eventAction", "")).lower() in ("expiration", "expiry"):
                expires_raw = str(ev.get("eventDate", ""))
        for ent in info.get("entities", []) or []:
            if "registrar" in (ent.get("roles") or []):
                for a in ent.get("vcardArray", [None, []])[1] or []:
                    if a and a[0] == "fn":
                        registrar = str(a[3])
        status_tokens = [str(s).lower() for s in (info.get("status") or [])]
    else:
        expires_raw = info.get("expires", "")
        registrar = info.get("registrar", "")
        status_tokens = []

    days_left: Optional[int] = None
    if expires_raw:
        try:
            cleaned = expires_raw.replace("Z", "+00:00")[:19]
            from datetime import datetime, timezone
            exp_dt = datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)
            days_left = (exp_dt - datetime.now(timezone.utc)).days
        except Exception:
            days_left = None

    risky = {t for t in ("clienttransferprohibited", "redemptionperiod",
                         "pendingdelete", "serverhold", "clienthold")}
    flagged = sorted(risky.intersection(status_tokens))

    expiry_observed = ""
    if expires_raw:
        expiry_observed = f"Expires {expires_raw[:10]}"
        if days_left is not None:
            expiry_observed += f" ({days_left} days left)"
    if flagged:
        expiry_observed += f", status {', '.join(flagged)}"

    out: List[Dict[str, Any]] = []
    risky_days = days_left is not None and days_left < 45
    if flagged or risky_days:
        out.append(_finding(
            "domain_expiry", "Domain expiry runway", "fail", expiry_observed or "The expiry date could not be read",
            "The domain is in a risky state or close to expiry. Once a domain lapses, the website and "
            "**all business email** stop working at the same time and mail from customers bounces back. "
            "That is far more serious than how the website looks.",
            "CRITICAL", ["DEMO-DOM-COM", "DEMO-DOM-MY"], source=path))
    elif days_left is not None:
        out.append(_finding(
            "domain_expiry", "Domain expiry runway", "pass", expiry_observed,
            "There is enough runway before expiry. Check that renewal notices arrive at a shared company mailbox "
            "rather than a personal one.",
            "INFO", ["DEMO-DOM-COM"], source=path))
    else:
        out.append(_unverified("domain_expiry", "Domain expiry runway",
                               "The registry record does not publish an expiry date"))

    out.append(_finding(
        "domain_registrant", "Domain registration and registrant of record", "unverified",
        f"Registrar {registrar or 'not disclosed'}; the registrant's contact details are hidden in the public record",
        "Public RDAP/whois normally discloses only the registrar, and the registrant's name and email are hidden by "
        "a privacy service, so this run does not reach a conclusion for you on who the domain is registered to. "
        "That question belongs to the interview and a back-office check: many SME domains were first registered "
        "through a friend's or an agent's personal email, renewal notices went to a private mailbox, the domain "
        "lapsed and was re-registered by someone else, and the customers and orders moved with it.",
        "UNKNOWN", ["DEMO-DOM-MY"], source=path))
    return out


def _check_hosting_location(host: str, behind_cloudflare: bool) -> List[Dict[str, Any]]:
    """机房在哪：决定本地与大陆访问延迟。仅在源站 IP 可见时才有意义。"""
    if behind_cloudflare:
        return [_finding("hosting_location", "Server location", "unverified",
                         "The site is behind Cloudflare, so only edge node IPs are public and the origin server "
                         "location is not visible",
                         "Hiding the origin behind a CDN is a normal and correct configuration, not a defect, so this "
                         "item draws no conclusion and does not suggest moving hosts. If you really want more speed, "
                         "measure the edge cache hit rate first.",
                         "UNKNOWN", source="not_applicable_behind_cdn")]
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        return [_unverified("hosting_location", "Server location", "The domain did not resolve")]
    try:
        req = urllib.request.Request(f"https://get.geojs.io/v1/ip/geo/{ip}.json",
                                     headers={"user-agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SECONDS) as resp:
            geo = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return [_unverified("hosting_location", "Server location",
                            f"Geolocation data was not retrieved ({type(exc).__name__})")]

    country = geo.get("country") or "unknown"
    org = geo.get("org") or geo.get("asn") or "unknown provider"
    city = geo.get("city") or ""
    observed = f"{ip} | {city} {country} | {org}".strip(" |")
    mainland = country in ("Malaysia", "Singapore")
    plain = (
        f"Your website's server sits in {city or country} ({org}). "
        + ("A sensible nearby location." if mainland else
           "The server is outside this region, so latency for visitors in Malaysia and mainland China is clearly "
           "higher. We have data centres in South-East Asia, and moving the same setup usually improves local "
           "access speed in a way people notice.")
    )
    return [_finding("hosting_location", "Server location",
                     "pass" if mainland else "fail", observed, plain,
                     "MEDIUM" if not mainland else "INFO",
                     [] if mainland else ["DEMO-WP17-BUSINESS", "DEMO-EBIZ17-AIPRO"],
                     source="geojs_keyless")]


def _check_email_security(domain: str) -> List[Dict[str, Any]]:
    """真实解析 SPF / DMARC / DKIM / MX。这是"为什么需要企业邮箱"的硬证据。"""
    res = DevLevelAuditEngine.inspect_dns_email_security(domain)
    if not res.get("dns_verified"):
        return [_unverified("email_authentication", "Email spoofing protection records (SPF/DMARC/DKIM)",
                            res.get("spf_record") or "DNS resolution was unreachable")]

    findings: List[Dict[str, Any]] = []
    observed_bits = []
    if res.get("has_spf"):
        strength = res.get("spf_strength")
        label = {"hard_fail": "-all hard reject", "soft_fail": "~all soft reject",
                 "permissive": "+all (no protection at all)", "unterminated": "no terminator",
                 "absent": "none"}.get(strength, strength)
        observed_bits.append(f"SPF {label}")
    else:
        observed_bits.append("SPF missing")
    if res.get("has_dmarc"):
        observed_bits.append(f"DMARC p={res.get('dmarc_policy') or '?'}"
                             + ("/reporting address set" if res.get("dmarc_report_configured")
                                else "/no reporting address"))
    else:
        observed_bits.append("DMARC missing")
    if res.get("dkim_verified"):
        observed_bits.append(f"DKIM detected ({', '.join(res.get('dkim_selectors') or [])})")
    elif res.get("dkim_inconclusive"):
        observed_bits.append("DKIM inconclusive (this domain uses wildcard DNS)")
    else:
        observed_bits.append("DKIM not detected")
    if res.get("mx_hosts"):
        observed_bits.append(f"MX {', '.join(res['mx_hosts'][:2])}")

    ok = bool(res.get("email_auth_blocking"))
    findings.append(_finding(
        "email_authentication", "Email spoofing protection records (SPF/DMARC/DKIM)",
        "pass" if ok else "fail", "; ".join(observed_bits),
        res.get("risk_summary") or "",
        "HIGH" if not res.get("has_spf") and not res.get("has_dmarc") else "MEDIUM",
        [] if ok else ["DEMO-MAIL-PRO-10U"],
        source=res.get("via") or "dns"))
    return findings


def _check_exposure(base_url: str) -> List[Dict[str, Any]]:
    """
    敏感路径自查。前提：这是老板自己的网站、由本人提供并要求分析，
    属于配置自检，不是对外扫描。措辞上按"你的站有没有把 X 暴露出去"陈述。
    """
    paths = [
        ("/.env", "Environment variable file",
         "These usually hold database passwords and third-party keys in plain text, so if the file can be read you "
         "have handed over the whole back end."),
        ("/.git/HEAD", "Version control entry point",
         "A public .git folder means the source code and the full commit history, including passwords once committed, "
         "can be rebuilt."),
        ("/wp-config.php.bak", "Configuration file backup",
         "Backup files are commonly forgotten after a manual change to the site and contain the database password in "
         "plain text."),
    ]
    exposed: List[str] = []
    reasons: List[str] = []
    checked = 0
    for path, label, consequence in paths:
        try:
            with httpx.Client(timeout=4.0, follow_redirects=False,
                              headers={"User-Agent": BROWSER_UA}, verify=True) as client:
                resp = client.get(base_url.rstrip("/") + path)
                checked += 1
                # 只有真的返回 200 且内容不像伪静态 200（回首页）才算暴露
                if resp.status_code == 200 and len(resp.content or b"") > 0:
                    body = (resp.text or "")[:400]
                    if "not found" not in body.lower() and "<!DOCTYPE html>" not in body[:80].upper():
                        exposed.append(f"{path} ({label})")
                        reasons.append(consequence)
        except Exception:
            continue

    if checked == 0:
        return [_unverified("sensitive_paths", "Sensitive file exposure check", "No path request completed")]
    if exposed:
        return [_finding("sensitive_paths", "Sensitive file exposure check", "fail", ", ".join(exposed),
                         f"These addresses can be fetched directly over the public internet: {', '.join(exposed)}. "
                         + " ".join(dict.fromkeys(reasons)) +
                         " This is an act-today item and has nothing to do with buying anything. Ask your current "
                         "supplier to close it first.",
                         "CRITICAL", ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"])]
    return [_finding("sensitive_paths", "Sensitive file exposure check", "pass",
                     f"{checked} common exposure paths checked, none readable",
                     "None of these are exposed to the public. You have this one right and do not need to spend "
                     "anything more.", skus=[])]


def _check_parked_or_placeholder(html: str, status_code: Optional[int]) -> List[Dict[str, Any]]:
    """有域名但页面是空壳/停放页——比没官网更伤，因为它传递"这家公司不认真"。"""
    if not html:
        return [_unverified("site_content", "Real page content", "The page content could not be retrieved")]
    text_len = len(re.sub(r"<[^>]+>", " ", html))
    blob = html[:200_000].lower()
    parked = [k for k in ("buy this domain", "domain is for sale", "parked domain",
                          "under construction", "此域名出售", "域名停放") if k in blob]
    if parked:
        return [_finding("site_content", "Real page content", "fail",
                         f"Parked/placeholder page keywords matched: {', '.join(parked)}; "
                         f"body text about {text_len} characters",
                         "The domain is live, but it opens on a parked page or an \"under construction\" placeholder. "
                         "For out-of-state and overseas customers this costs more trust than having no website at "
                         "all, because they have already decided not to come to you.",
                         "HIGH", ["DEMO-WP17-BUSINESS", "DEMO-IWB-STARTER"])]
    if text_len < 400:
        return [_finding("site_content", "Real page content", "fail",
                         f"Only {text_len} characters of text after the tags are removed (HTTP {status_code})",
                         "The page carries almost nothing that can be checked: no products, no address, no contact "
                         "phone number. To a search engine and to a company doing procurement checks this is the same "
                         "as not existing.",
                         "HIGH", ["DEMO-WP17-BUSINESS", "DEMO-IWB-STARTER"])]
    return [_finding("site_content", "Real page content", "pass",
                     f"Body text about {text_len:,} characters (HTTP {status_code})",
                     "The page has real content, which is the basis for being found and being trusted.", skus=[])]


# ─── 网络专家视角：已知漏洞 / 配置暴露 / 攻击面 ──────────────────────────────
# 这一组检查的边界（本引擎刻意不做的事，写在这里以免日后被当成遗漏）：
#   · 不注入任何 XSS / SQLi 载荷——已知漏洞一律用官方公告比对得出，而不是打出来的
#   · 不尝试任何账号或口令，包括不测 admin/admin
#   · 不做 1-65535 全端口扫描，只探下面这张"绝不该公网可达"的固定端口清单
#   · 只请求老板本人提供、且属于他自己企业的那个网址
# 因此每一项结论都是"读配置 + 比对公开情报"，属于只读体检。
# 情报源与实测限制见 core/vuln_intel.py（OSV / CISA KEV / endoflife.date / WP 官方目录）。

_SEVERITY_ORDER = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")


def _worst(severities: List[str]) -> str:
    best = -1
    for s in severities:
        try:
            best = max(best, _SEVERITY_ORDER.index(s))
        except ValueError:
            continue
    return _SEVERITY_ORDER[best] if best >= 0 else "MEDIUM"


def _check_known_vulnerabilities(rep: Dict[str, Any]) -> List[Dict[str, Any]]:
    """已识别组件 × 公开安全公告。有 KEV 在利用条目时措辞必须升级一档。"""
    out: List[Dict[str, Any]] = []
    hits = rep.get("hits") or []
    queried = rep.get("osv_queried") or []
    exploited = [h for h in hits if h.get("known_exploited")]

    if hits:
        lines = []
        for h in sorted(hits, key=lambda x: (not x.get("known_exploited"),
                                             _SEVERITY_ORDER.index(x["severity"])
                                             if x.get("severity") in _SEVERITY_ORDER else 1))[:6]:
            tag = "[exploited in the wild] " if h.get("known_exploited") else ""
            lines.append(f"{tag}{h['component_label']} {h['installed_version']}: "
                         f"{h.get('cve') or h.get('id')} ({h.get('severity') or 'not rated'}, "
                         f"official fix in {h.get('fixed_in') or 'see advisory'})")
        sev = "CRITICAL" if exploited else ("HIGH" if any(
            h.get("severity") in ("HIGH", "CRITICAL") for h in hits) else "MEDIUM")
        plain = ("Matching your website's publicly referenced components against public advisories returned "
                 f"{len(hits)} disclosed security entries. "
                 + ("Some of them are on CISA's known-exploited list. For those an attacker needs no skill at all; "
                    "automated scripts sitting on the public internet find them and plant malware by themselves."
                    if exploited else
                    "All of these already have an official fixed version, so patching is doable; nobody is just "
                    "accountable for doing it."))
        if exploited:
            plain += ("Note: this is not a theoretical risk. These are entries already being exploited in the wild, "
                      "and handing the patches and virtual patching to your managed provider is the first priority.")
        out.append(_finding("known_vulnerabilities", "Known vulnerability match (CVE / GHSA)", "fail",
                           f"{len(queried)} components matched {len(hits)} advisories: " + "; ".join(lines),
                           plain, sev,
                           ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL",
                            "DEMO-ACRONIS-WKS"]))
    elif queried:
        out.append(_finding("known_vulnerabilities", "Known vulnerability match (CVE / GHSA)", "pass",
                            f"The {len(queried)} open-source components that carry a version number have no "
                            "matching entry in the public advisory databases",
                            "You are right on this one for now, so there is nothing to spend on it."
                            f" ({rep.get('coverage_note') or ''})",
                            "INFO", skus=[]))
    else:
        reason = (rep.get("osv_skipped") or "; ".join(rep.get("osv_errors") or [])
                  or "No fingerprinted component was queryable")
        out.append(_unverified("known_vulnerabilities", "Known vulnerability match (CVE / GHSA)", reason))

    dead = rep.get("eol_lines_dead") or []
    lines_seen = [c for c in rep.get("components") or [] if c.get("source") == "eol_line"]
    if dead:
        bits = [f"{d['label']} {d['installed']} (version line {d.get('cycle')} stopped security maintenance on "
                f"{d.get('eol_date') or 'an earlier date'})" for d in dead]
        out.append(_finding("software_lifecycle", "Software version lifecycle", "fail", "; ".join(bits),
                            f"The website still runs version lines that no longer receive security maintenance: "
                            f"{'; '.join(bits)}. "
                            "End of maintenance means no further patch will ever be issued for that version, so this "
                            "is not an \"upgrade it later\" matter but a must-migrate one.",
                            "HIGH", ["DEMO-WP17-BUSINESS", "DEMO-EBIZ17-AIPRO"]))
    elif lines_seen:
        out.append(_finding("software_lifecycle", "Software version lifecycle", "pass",
                            ", ".join(f"{c['label']} {c['version']}" for c in lines_seen),
                            "The server version lines identified are still inside official maintenance.",
                            "INFO", skus=[]))
    else:
        out.append(_unverified("software_lifecycle", "Software version lifecycle",
                               "No readable server version clue was retrieved (most hosts hide the version header, "
                               "which is not a defect in itself)"))
    return out


def _check_wordpress_plugins(wp_plugins: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """插件与主题：OSV 对 WP 生态 0 覆盖（实测），因此改用官方目录判"还在不在维护"。"""
    if not wp_plugins:
        return [_finding("wordpress_plugins", "Plugin maintenance status", "unverified",
                         "No plugin or theme was identified from the page",
                         "No plugin dependencies were identified, or the site is not on this technology stack. "
                         "This item is not scored.",
                         "UNKNOWN", source="not_applicable")]
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(
            lambda item: vuln_intel.wordpress_plugin_status(item["slug"], item["kind"]),
            wp_plugins[:10]))

    stale: List[str] = []
    private: List[str] = []
    checked = 0
    errors: List[str] = []
    for st in statuses:
        state = st.get("state")
        if state in ("stale", "current"):
            checked += 1
        elif state == "not_in_directory":
            checked += 1
            private.append(st["slug"])
        elif state == "unreachable":
            errors.append(f"{st['slug']}: {st.get('error')}")
    stale = [f"{s.get('name') or s['slug']} (last updated {s.get('last_updated')}, "
             f"{s.get('months_since_update')} months without a release; latest official {s.get('latest')})"
             for s in statuses if s.get("state") == "stale"]

    if checked == 0:
        return [_unverified("wordpress_plugins", "Plugin maintenance status",
                            "; ".join(errors[:2]) or "The official plugin directory could not be reached")]
    if stale:
        return [_finding("wordpress_plugins", "Plugin maintenance status", "fail", "; ".join(stale),
                         f"Your website runs plugins that nobody has updated for a long time: {'; '.join(stale)}. "
                         "The biggest entry point for malware on a WordPress site is not a badly written theme, it is "
                         "a plugin whose author stopped and whose holes nobody patches any more. Managed virtual "
                         "patching and automatic updates are exactly what closes this gap.",
                         "HIGH", ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"])]
    if private:
        return [_finding("wordpress_plugins", "Plugin maintenance status", "fail",
                         f"{len(private)} plugins/themes are not in the official directory: "
                         f"{', '.join(private[:6])}",
                         "These components are not in the official WordPress directory. They are usually paid "
                         "licensed builds or nulled copies of unclear origin. The difference is that plugins inside "
                         "the official directory can be patched by automatic updates, while those outside it can only "
                         "be upgraded by hand, and on an SME site nobody upgrades by hand.",
                         "MEDIUM", ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"])]
    return [_finding("wordpress_plugins", "Plugin maintenance status", "pass",
                     f"All {checked} identified plugins/themes are in the official directory and have recent "
                     f"maintenance records",
                     "Plugin maintenance status is normal, so no extra investment is needed here.", "INFO", skus=[])]


_WP_PROBES = (
    ("/readme.html", "Version readme file still online", "MEDIUM",
     lambda s, t: s == 200 and "wordpress" in t[:3000].lower() and "<h1" in t[:3000].lower()),
    ("/xmlrpc.php", "XML-RPC interface open to the public", "MEDIUM",
     lambda s, t: "xml-rpc" in t[:400].lower()),
    ("/?rest_route=/wp/v2/users", "REST interface can list admin account names", "HIGH",
     lambda s, t: s == 200 and '"slug"' in t[:4000] and '"name"' in t[:4000]),
    ("/wp-content/uploads/", "Upload directory has file listing open", "HIGH",
     lambda s, t: s == 200 and "index of /" in t[:400].lower()),
    ("/wp-login.php", "Admin login page is open to the public", "LOW",
     lambda s, t: s == 200 and 'name="log"' in t[:6000]),
)


def _check_wordpress_surface(base_url: str, html: str) -> List[Dict[str, Any]]:
    """WordPress 配置面只读探测。含"默认凭据"这一项的正确做法：只报登录面是否裸露，绝不信凭据。"""
    blob = (html or "").lower()
    if "wp-content" not in blob and "wp-includes" not in blob and "wordpress" not in blob:
        return [_finding("wordpress_surface", "CMS configuration surface", "unverified",
                         "No WordPress fingerprint was found",
                         "This site is not WordPress driven, so this group of checks does not apply and is not "
                         "scored.",
                         "UNKNOWN", source="not_applicable")]

    problems: List[str] = []
    advisories: List[str] = []
    done = 0
    severities: List[str] = []
    try:
        with httpx.Client(timeout=4.0, follow_redirects=False,
                          headers={"user-agent": BROWSER_UA}, verify=True) as client:
            for path, label, sev, judge in _WP_PROBES:
                try:
                    resp = client.get(base_url.rstrip("/") + path)
                    done += 1
                    if judge(resp.status_code, resp.text or ""):
                        item = f"{path}: {label}"
                        severities.append(sev)
                        if sev == "LOW":
                            advisories.append(item)
                        else:
                            problems.append(item)
                except Exception:
                    continue
    except Exception as exc:
        return [_unverified("wordpress_surface", "CMS configuration surface", f"{type(exc).__name__}")]

    if done == 0:
        return [_unverified("wordpress_surface", "CMS configuration surface", "No probe request completed")]
    if problems:
        return [_finding("wordpress_surface", "CMS configuration surface", "fail",
                         "; ".join(problems + advisories),
                         f"These settings can be read directly over the public internet: {'; '.join(problems)}. "
                         "The one that can list admin account names hands brute-force scripts a free username list. "
                         "Problems like this can be closed without buying anything, but someone has to own closing "
                         "them.",
                         _worst(severities),
                         ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"])]
    return [_finding("wordpress_surface", "CMS configuration surface", "pass",
                     f"None of the {done} common configuration exposures are open"
                     + (f"; note: {'; '.join(advisories)}" if advisories else ""),
                     "None of these are exposed to the public, which is right. "
                     "(An admin login page being open to the public is a normal setup. It is hardened with two-step "
                     "verification and source restrictions, not by taking the website down.)",
                     "INFO", skus=[])]


# "绝不该在公网可达"的端口。80/443/53 不在此列（本就该开放），22 只作提示。
_PORT_RISK = {
    445: ("CRITICAL", "SMB file sharing port",
          "The main entry point ransomware uses to move sideways and encrypt more machines. Telecom operators "
          "should already block this at their level"),
    1433: ("CRITICAL", "MSSQL database port",
           "The database is reachable straight from the public internet. One weak password and the whole database "
           "is pulled out"),
    3306: ("CRITICAL", "MySQL database port",
           "The database is reachable straight from the public internet. One weak password and the whole database "
           "is pulled out"),
    5432: ("CRITICAL", "PostgreSQL port",
           "The database is reachable straight from the public internet. One weak password and the whole database "
           "is pulled out"),
    6379: ("CRITICAL", "Redis port",
           "Redis is often built without authentication. Reachable from the public internet it can be read and "
           "written directly, including writing scheduled tasks"),
    9200: ("CRITICAL", "Elasticsearch port",
           "The search index is reachable from the public internet, so customer data can be exported in bulk"),
    27017: ("CRITICAL", "MongoDB port",
            "The database is reachable straight from the public internet. Many unprotected instances have "
            "historically had the full database downloaded"),
    11211: ("CRITICAL", "Memcached port",
            "A cache service reachable from the public internet can be used to amplify attacks and can also leak "
            "session data"),
    21: ("MEDIUM", "FTP port", "FTP transfers in plain text, so account passwords and file contents can be read "
                               "in transit"),
    25: ("LOW", "SMTP port", "If it is an unconfigured open relay, it can be used to send spam under your own domain"),
    110: ("LOW", "POP3 port", "A plain-text mail retrieval port is open to the public internet"),
    143: ("LOW", "IMAP port", "A plain-text mail retrieval port is open to the public internet"),
    8080: ("MEDIUM", "Secondary HTTP port",
           "Usually an unprotected admin panel or internal system that was left open to the public internet"),
    8443: ("MEDIUM", "Secondary HTTPS port",
           "Usually an unprotected admin panel that was left open to the public internet"),
    8888: ("MEDIUM", "Common control panel port",
           "The default port of server panels such as BT/aaPanel. Exposed, it hands over an admin entrance"),
    22: ("INFO", "SSH port",
         "Being open to the public internet is normal in itself, but the source IPs should be restricted and "
         "password login turned off in favour of keys"),
}


def _probe_port(ip: str, port: int, timeout: float = 1.2) -> Optional[Tuple[int, bytes]]:
    """只建立连接与读首包（或对 Redis/Memcached 发一条只读命令），不发送任何凭据。"""
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(1.0)
            banner = b""
            if port == 6379:
                sock.sendall(b"PING\r\n")
            elif port == 11211:
                sock.sendall(b"version\r\n")
            try:
                banner = sock.recv(512)
            except Exception:
                banner = b""
            return port, banner
    except Exception:
        return None


def _check_exposed_services(host: str, behind_cloudflare: bool) -> List[Dict[str, Any]]:
    """
    固定端口清单的可达性检查。

    前置判断决定这项是否有意义：站点在 Cloudflare 之后时，公网解析到的是边缘节点，
    探到的端口属于 Cloudflare 而不是贵司源站——此时必须标 unverified，
    否则会把 CDN 的正常端口说成客户的漏洞。
    """
    if behind_cloudflare:
        return [_finding("exposed_services", "Open ports on the public internet", "unverified",
                         "The site is behind Cloudflare, so public DNS resolves to edge nodes rather than the "
                         "origin server",
                         "Behind a CDN this check cannot see the origin's ports. That is a limit of the method, not a "
                         "weakness on your side, so no conclusion is drawn.",
                         "UNKNOWN", source="not_applicable_behind_cdn")]
    try:
        ips = sorted({info[4][0] for info in socket.getaddrinfo(host, None)})
    except Exception:
        return [_unverified("exposed_services", "Open ports on the public internet", "The domain did not resolve")]
    v4 = [ip for ip in ips if is_ssrf_safe(ip)]
    if not v4:
        return [_unverified("exposed_services", "Open ports on the public internet",
                            "All resolved addresses are private or reserved and were blocked by the safety boundary")]

    open_ports: List[Tuple[int, bytes]] = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        for ip in v4[:1]:
            for result in pool.map(lambda p: _probe_port(ip, p), sorted(_PORT_RISK)):
                if result:
                    open_ports.append(result)

    if not open_ports:
        return [_finding("exposed_services", "Open ports on the public internet", "pass",
                         f"None of the {len(_PORT_RISK)} high-risk or admin ports are reachable on {v4[0]}",
                         f"We probed {v4[0]} on {len(_PORT_RISK)} ports that should never be reachable from the "
                         "public internet, and not one of them answered. You have this one right.",
                         "INFO", skus=[])]

    bits: List[str] = []
    severities: List[str] = []
    for port, banner in open_ports:
        sev, label, why = _PORT_RISK[port]
        extra = ""
        if port == 6379 and banner.startswith(b"+PONG"):
            sev = "CRITICAL"
            extra = (" (measured: it answered +PONG with no authentication at all, so it is wide open to read "
                     "and write)")
        elif port == 6379 and b"NOAUTH" in banner:
            sev = "HIGH"
            extra = (" (authentication is required, so the risk is lower, but the port itself should not be open "
                     "to the public internet)")
        elif port == 11211 and banner.startswith(b"VERSION"):
            extra = f" (the reply states version {banner[8:30].decode('latin-1').strip()})"
        elif port == 3306 and len(banner) > 6:
            ver = banner[5:].split(b"\x00", 1)[0].decode("latin-1", "ignore")[:24]
            if re.match(r"^\d+\.\d+", ver):
                extra = f" (the handshake packet states the server version {ver} directly)"
        bits.append(f"{port}/tcp {label}: {why}{extra}")
        severities.append(sev)

    return [_finding("exposed_services", "Open ports on the public internet", "fail", "; ".join(bits),
                     "On your website's public IP address, anyone can connect directly to these ports: "
                     + "; ".join(bits) +
                     ". These are not a guess about what might be used one day; they are entrances open right now. "
                     "The first step is to have your current supplier use the firewall to limit access to the sources "
                     "that genuinely need it, and that has nothing to do with buying anything.",
                     _worst(severities),
                     ["DEMO-VPS-C1", "DEMO-CF-BOOSTER-PRO"])]


# 备份文件枚举：必须同时满足"体积可观 + 不是网页 + 魔数对得上"才算命中，
# 否则站点把任意未知路径 rewrite 回首页时会大面积误报。
_BACKUP_CANDIDATES = ("backup.zip", "backup.sql", "dump.sql", "database.sql",
                      "site.zip", "public/backups/db.sql.gz")
_MAGIC = ((b"PK\x03\x04", "ZIP"), (b"\x1f\x8b", "gzip"),
          (b"-- MySQL", "MySQL dump"), (b"SQLite format", "SQLite"))


def _identify_bytes(body: bytes) -> Optional[str]:
    for prefix, name in _MAGIC:
        if body.startswith(prefix):
            return name
    return None


def _check_backup_artifacts(base_url: str, domain: str) -> List[Dict[str, Any]]:
    """网站根目录是否还能直接下载备份。命中等于整库客户资料外泄。"""
    root = base_url.rstrip("/")
    candidates = list(_BACKUP_CANDIDATES) + [f"{domain}.zip", f"{domain}.sql",
                                             f"{domain}_backup.sql", "backup.sql.gz"]
    hits: List[str] = []
    done = 0
    try:
        with httpx.Client(timeout=4.0, follow_redirects=False,
                          headers={"user-agent": BROWSER_UA}, verify=True) as client:
            for path in candidates:
                try:
                    resp = client.get(f"{root}/{path}")
                    done += 1
                    if resp.status_code != 200:
                        continue
                    body = resp.content or b""
                    ctype = (resp.headers.get("content-type") or "").lower()
                    if "text/html" in ctype:
                        continue          # rewrite 回首页：不是备份文件
                    kind = _identify_bytes(body[:32])
                    if kind and len(body) > 8 * 1024:
                        hits.append(f"/{path} ({kind}, {len(body) // 1024} KB)")
                except Exception:
                    continue
    except Exception as exc:
        return [_unverified("backup_artifacts", "Backup files downloadable", f"{type(exc).__name__}")]

    if done == 0:
        return [_unverified("backup_artifacts", "Backup files downloadable", "No request completed")]
    if hits:
        return [_finding("backup_artifacts", "Backup files downloadable", "fail", "; ".join(hits),
                         f"These addresses can be downloaded by anyone over the public internet: {'; '.join(hits)}. "
                         "A backup file holds the complete customer list and the accounting books, so this is a "
                         "deal-with-it-today problem.",
                         "CRITICAL", ["DEMO-WP17-BUSINESS", "DEMO-CF-BOOSTER-PERSONAL"])]
    return [_finding("backup_artifacts", "Backup files downloadable", "pass",
                     f"None of the {done} common backup file names can be downloaded directly",
                     "There is no directly downloadable backup file in the web root, which is right.",
                     "INFO", skus=[])]


def _cloudflare_networks() -> List[Any]:
    """Cloudflare 公开前缀段（免 key），带进程内缓存。取不到时返回空表。"""
    cached = _CF_NET_CACHE.get("nets")
    if cached is not None and time.monotonic() - cached[1] < 86400:
        return cached[0]
    try:
        import ipaddress
        req = urllib.request.Request("https://api.cloudflare.com/client/v4/ips",
                                     headers={"user-agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SECONDS) as resp:
            cf = json.loads(resp.read().decode("utf-8")).get("result", {}) or {}
        nets = []
        for key in ("ipv4_cidrs", "ipv6_cidrs"):
            for entry in cf.get(key) or []:
                cidr = entry if isinstance(entry, str) else (entry or {}).get("cidr")
                if cidr:
                    try:
                        nets.append(ipaddress.ip_network(str(cidr)))
                    except ValueError:
                        continue
        nets = list({str(n): n for n in nets}.values())
        _CF_NET_CACHE["nets"] = (nets, time.monotonic())
        return nets
    except Exception:
        return []


_CF_NET_CACHE: Dict[str, Any] = {}


def _is_cloudflare_ip(ip: str) -> bool:
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    nets = _cloudflare_networks()
    return bool(nets) and any(addr.version == n.version and addr in n for n in nets)


def _check_origin_concealment(domain: str, behind_cloudflare: bool) -> List[Dict[str, Any]]:
    """
    已经挂了 CDN 的站，最常见的真实风险是源站 IP 泄露：
    证书透明度日志里 cpanel./mail./ftp. 这类子域常直接解析到源站，
    攻击者绕过 WAF 只需换 Host 头。只读公开证书日志，不碰源站。
    """
    if not behind_cloudflare:
        return [_finding("origin_concealment", "Origin server hidden (behind a CDN)", "unverified",
                         "The site has no CDN/WAF in front, so the origin IP is the public IP",
                         "This site runs without a fronting CDN, so this item does not apply and is not scored.",
                         "UNKNOWN", source="not_applicable")]
    # 只探"与本应保持同源代理"的子域。mail./smtp./webmail. 之类属于邮件基础设施，
    # 按设计就不能走 Web CDN 代理（实测 iotservices.my 的 MX 就在另一台马来西亚 VPS 上），
    # 把它们算进源站泄露是误报。
    names = {domain, f"www.{domain}", f"dev.{domain}", f"staging.{domain}",
             f"test.{domain}", f"admin.{domain}", f"cpanel.{domain}", f"ftp.{domain}"}
    leaked: List[str] = []
    resolved: List[str] = []
    for name in sorted(names):
        try:
            for info in socket.getaddrinfo(name, None):
                ip = info[4][0]
                if name not in resolved:
                    resolved.append(name)
                if is_ssrf_safe(ip) and not _is_cloudflare_ip(ip):
                    leaked.append(f"{name} → {ip}")
                    break
        except Exception:
            continue
    uniq = sorted(set(leaked))
    if uniq:
        return [_finding("origin_concealment", "Origin server hidden (behind a CDN)", "fail",
                         "; ".join(uniq[:6]),
                         f"Your site already uses a CDN, but {len(uniq)} website/admin subdomains do not go through "
                         f"the proxy and give the server address directly: "
                         f"{', '.join(u.split(' → ')[0] for u in uniq[:4])}. "
                         "If any one of those addresses serves this same website, the WAF can be bypassed. An "
                         "attacker does not have to get through the CDN at all, they just connect to that address. "
                         "The fix is to put the same-origin subdomains behind the proxy as well and to allow only the "
                         "CDN's origin-pull ranges on the server firewall.",
                         "HIGH", ["DEMO-CF-BOOSTER-PERSONAL", "DEMO-CF-BOOSTER-PRO"])]
    if not resolved:
        return [_unverified("origin_concealment", "Origin server hidden (behind a CDN)",
                            "No subdomain lookup completed")]
    return [_finding("origin_concealment", "Origin server hidden (behind a CDN)", "pass",
                     f"{len(resolved)} of the {len(names)} website/admin subdomains resolve, and every result falls "
                     f"inside the CDN ranges",
                     "The origin is hidden properly, so the CDN/WAF is not something that can be walked around. This "
                     "one is done right.",
                     "INFO", skus=[])]


# 每个并发分支的墙钟上限。路径枚举类分支要发十几个请求，比单项探测宽。
BRANCH_TIMEOUT_SECONDS = float(28.0)


def _fetch_feed(base_url: str) -> str:
    """站点的 RSS：WP 的 <generator> 在这里比在首页稳，属对方公开提供的同一份内容。"""
    try:
        with httpx.Client(timeout=4.0, follow_redirects=True,
                          headers={"user-agent": BROWSER_UA}) as client:
            resp = client.get(base_url.rstrip("/") + "/feed/")
            if resp.status_code == 200:
                return (resp.text or "")[:60_000]
    except Exception:
        pass
    return ""


def _vuln_branch(base_url: str, html: str,
                 headers: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    feed = _fetch_feed(base_url) if html else ""
    rep = vuln_intel.build_report(html, headers, extra_blobs=[feed] if feed else ())
    return _check_known_vulnerabilities(rep), rep


# ─── 编排 ────────────────────────────────────────────────────────────────────
def audit_website(raw_url: str) -> Dict[str, Any]:
    """
    对贵司自己的官网做一次完整机检。返回 findings 列表 + 汇总。

    单项异常只影响该项（标 unverified），不会让整份审计失败。
    """
    url = normalize_url(raw_url or "")
    host = urllib.parse.urlparse(url).hostname or ""
    domain = host[4:] if host.startswith("www.") else host

    started = time.time()
    if not url:
        return {"success": False, "error": "No URL was provided", "url": raw_url, "findings": [],
                "summary": _empty_summary("No URL was provided")}
    if not host:
        return {"success": False, "error": "The URL format could not be parsed", "url": raw_url,
                "findings": [], "summary": _empty_summary("The URL format could not be parsed")}
    if not is_ssrf_safe(host):
        return {"success": False, "error": f"The probe to a private or reserved address was blocked ({host})",
                "url": raw_url, "findings": [],
                "summary": _empty_summary("The target was blocked by the safety boundary")}

    try:
        page = _fetch_homepage(url)
    except Exception as exc:
        # 抓不到首页：机检项大面积无从执行，但邮件与域名检查仍独立可跑
        page = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    final_url_for_probes = page.get("final_url") or url
    html_for_probes = page.get("html") or ""
    headers_for_probes = {str(k).lower(): str(v) for k, v in (page.get("headers") or {}).items()}
    # 站型判定只读已抓到的内容，零额外请求；就算后面的探测分支超时，层级结论依然存在
    signals = site_signals.detect_signals(html_for_probes, headers_for_probes)
    level, level_label, level_evidence = site_signals.classify_level(signals)
    findings: List[Dict[str, Any]] = []
    # detect_cloudflare 依赖首页响应头；抓不到首页时按"未确认在用"处理，
    # 让机房定位这一项仍照常尝试，而不是整块跳过。
    cf_state: Dict[str, Any] = {"behind": False, "signals": []}
    if page.get("ok"):
        hdrs = page["headers"]
        final_url = page["final_url"]
        html = page["html"]
        findings.extend(_check_transport(final_url, hdrs, page.get("http_version", "")))
        findings.extend(_check_headers(hdrs))
        findings.extend(_check_mixed_content(html, final_url))
        findings.extend(_check_mobile(html))
        findings.extend(_check_speed(page.get("elapsed_ms"), page.get("bytes")))
        findings.extend(_check_technology(html, hdrs))
        findings.extend(_check_parked_or_placeholder(html, page.get("status_code")))
        cf_state = detect_cloudflare(host, hdrs)
        findings.extend(_check_cloudflare(cf_state))
    else:
        reason = page.get("error") or "The homepage request did not complete"
        findings.append(_finding(
            "reachability", "Website reachability", "unverified", reason,
            f"From this network, {final_host_hint(url)} could not be opened in this run. "
            "Note: this does **not mean** there is a problem with your website, only that it was not measured this "
            "time. If you are running on the venue network, switch network or try again later. Confirming that a site "
            "is genuinely unreachable needs several observation points.",
            "UNKNOWN", source="probe_failed"))

    # 与首页无关或可并行的分支：全部并发，任何一项卡住都不能拖垮整份审计
    behind = bool(cf_state.get("behind"))
    deep_extras: Dict[str, Any] = {}

    def _deep_branch() -> List[Dict[str, Any]]:
        deep, extras = deep_findings(final_url_for_probes, html_for_probes, headers_for_probes,
                                     domain, signals, page)
        deep_extras.update(extras)
        return deep

    branches = [
        ("page_probes", lambda: _check_exposure(final_url_for_probes)),
        ("wp_surface", lambda: _check_wordpress_surface(final_url_for_probes, html_for_probes)),
        ("backups", lambda: _check_backup_artifacts(final_url_for_probes, domain)),
        ("services", lambda: _check_exposed_services(host, behind)),
        ("origin", lambda: _check_origin_concealment(domain, behind)),
        ("email", lambda: _check_email_security(domain)),
        ("registration", lambda: _check_domain_registration(domain)),
        ("hosting", lambda: _check_hosting_location(host, behind)),
        ("deep", _deep_branch),
    ]
    with ThreadPoolExecutor(max_workers=len(branches) + 2) as pool:
        futures = {pool.submit(fn): name for name, fn in branches}
        vuln_future = pool.submit(_vuln_branch, final_url_for_probes, html_for_probes,
                                  page.get("headers") or {})
        plugin_future = pool.submit(
            _check_wordpress_plugins, vuln_intel.extract_wordpress_plugins(html_for_probes))
        pending = set(futures)
        try:
            for fut in as_completed(futures, timeout=BRANCH_TIMEOUT_SECONDS + 10):
                pending.discard(fut)
                try:
                    findings.extend(fut.result(timeout=BRANCH_TIMEOUT_SECONDS))
                except Exception as exc:
                    findings.append(_unverified(f"parallel_{futures[fut]}",
                                                f"{futures[fut]} branch", f"{type(exc).__name__}: {exc}"))
        except FuturesTimeout:
            pass
        for fut in sorted(pending, key=lambda f: futures[f]):
            fut.cancel()
            findings.append(_unverified(f"parallel_{futures[fut]}", f"{futures[fut]} branch",
                                        "ran past the step-2 time budget"))
        try:
            vuln_findings, vuln_report = vuln_future.result(timeout=BRANCH_TIMEOUT_SECONDS + 20)
            findings.extend(vuln_findings)
        except Exception as exc:
            vuln_report = {}
            findings.append(_unverified("known_vulnerabilities", "Known vulnerability match (CVE / GHSA)",
                                        f"{type(exc).__name__}: {exc}"))
        try:
            findings.extend(plugin_future.result(timeout=BRANCH_TIMEOUT_SECONDS + 10))
        except Exception as exc:
            findings.append(_unverified("wordpress_plugins", "Plugin maintenance status",
                                        f"{type(exc).__name__}: {exc}"))

    summary = _summarize(findings, started, domain, url, page.get("ok", False))
    # 明细对号入座：清单决定"该查什么"，探针决定"查到了什么"，两者只在最后一步合流
    checklist_rows = audit_checklist.rows_from_findings(findings, signals, level)
    return {"success": True, "url": url, "final_url": page.get("final_url", url),
            "domain": domain, "findings": findings, "summary": summary,
            "vulnerability_report": vuln_report,
            "site_level": f"L{level}", "site_level_label": level_label,
            "site_level_evidence": level_evidence,
            "signals_present": site_signals.present_signals(signals),
            "checklist": checklist_rows,
            "conclusions": audit_checklist.rollup(checklist_rows),
            "checklist_summary": audit_checklist.summary(checklist_rows, level, level_label,
                                                        level_evidence),
            "advisory_groups": audit_checklist.advisory_items(checklist_rows),
            "probe_meta": {k: v for k, v in deep_extras.items() if k != "signals"}}


def final_host_hint(url: str) -> str:
    return urllib.parse.urlparse(url).netloc or url


def _empty_summary(reason: str) -> Dict[str, Any]:
    return {"reason": reason, "pass": 0, "fail": 0, "unverified": 0,
            "not_applicable": 0,
            "critical": [], "audit_seconds": 0.0, "score": None,
            "score_note": "Checks were not completed, so no health score is given"}


def _summarize(findings: List[Dict[str, Any]], started: float,
               domain: str, url: str, page_ok: bool) -> Dict[str, Any]:
    passes = [f for f in findings if f["status"] == "pass"]
    fails = [f for f in findings if f["status"] == "fail"]
    not_applicable = [f for f in findings
                      if f["status"] == "unverified"
                      and str(f.get("evidence_source", "")).startswith("not_applicable")]
    na_ids = {id(f) for f in not_applicable}
    unknown = [f for f in findings if f["status"] == "unverified" and id(f) not in na_ids]
    critical = [f["title"] for f in fails if f["severity"] in ("CRITICAL", "HIGH")]

    # 健康分只在"确凿通过/失败"的集合上算，unverified 不进分母
    graded = len(passes) + len(fails)
    score = round(len(passes) / graded * 100, 1) if graded else None
    note = (f"{len(passes)} checks passed and {len(fails)} show a clear gap"
            + (f". {len(unknown)} items could not be verified in this run and are not counted in the score."
               if unknown else "."))
    if unknown:
        note += "Unverified items are labelled as they are and are never turned into a reason to deduct points."
    if not_applicable:
        note += (f"A further {len(not_applicable)} checks do not apply to this site's technology stack "
                 "(for example the admin panel checks on a non-WordPress site), so they are listed separately "
                 "rather than counted as failures.")

    skus: List[str] = []
    for f in fails:
        for s in f.get("vendor_skus") or []:
            if s not in skus:
                skus.append(s)

    return {
        "domain": domain,
        "url": url,
        "audited": page_ok,
        "pass": len(passes),
        "fail": len(fails),
        "unverified": len(unknown),
        "not_applicable": len(not_applicable),
        "graded_checks": graded,
        "score": score,
        "score_note": note,
        "critical": critical,
        "suggested_skus": skus,
        "audit_seconds": round(time.time() - started, 2),
    }
