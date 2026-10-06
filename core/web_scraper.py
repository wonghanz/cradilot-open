"""
Cradilot Core - Real-Time Website Scraper & Technical Stack Auditor
Performs live website crawling, SSL certificate verification, mobile responsiveness check,
security header audit, and CMS stack detection.
Enforces NodiGuard SSRF defense (blocks internal/private IPs) and strict zero emoji policy.
"""

import re
import ssl
import time
import socket
import ipaddress
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx


def inspect_tls(hostname: str, port: int = 443, timeout: float = 4.0) -> Dict[str, Any]:
    """
    真实 TLS 证书核验。此前 ssl_valid 被无条件写死为 True，等于把未做的检查冒充成扫描结果。
    返回证书链是否受信任、颁发机构、到期时间与剩余天数；任何异常都如实降级并带原因。
    """
    result = {
        "ssl_valid": False, "cert_issuer": "", "cert_not_after": "",
        "cert_days_left": None, "ssl_error": "", "cert_checked": False,
    }
    if not hostname:
        result["ssl_error"] = "The target host name could not be resolved"
        return result
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                # 走到这里说明证书链与域名匹配均已通过默认信任库校验
                result["cert_checked"] = True
                result["ssl_valid"] = True
                cert = tls_sock.getpeercert() or {}
    except Exception as exc:
        result["ssl_error"] = f"{type(exc).__name__}: {exc}"
        return result

    # 明细解析与信任核验分离：解析失败要如实标注，不得静默留空
    try:
        issuer_map: Dict[str, str] = {}
        for rdn in cert.get("issuer", ()) or ():
            for attr, value in rdn or ():
                issuer_map[attr] = value
        result["cert_issuer"] = (issuer_map.get("organizationName")
                                 or issuer_map.get("commonName")
                                 or "Unknown issuing authority")
        not_after = str(cert.get("notAfter", "")).replace(" GMT", "").strip()
        result["cert_not_after"] = not_after
        if not_after:
            try:
                exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
                result["cert_days_left"] = (exp - datetime.now(timezone.utc)).days
            except ValueError:
                result["cert_detail_error"] = f"Expiry date format could not be parsed: {not_after}"
    except Exception as exc:
        result["cert_detail_error"] = f"{type(exc).__name__}: {exc}"
    return result

# Disallowed private and loopback networks for SSRF defense
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_ssrf_safe(hostname: str) -> bool:
    """Validate that hostname does not resolve to private or loopback IP ranges."""
    try:
        # Check if hostname is an IP string
        ip = ipaddress.ip_address(hostname)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                return False
        return True
    except ValueError:
        pass

    try:
        # Resolve hostname via DNS
        addr_info = socket.getaddrinfo(hostname, None)
        for item in addr_info:
            ip_str = item[4][0]
            ip = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip in net:
                    return False
        return True
    except Exception:
        # DNS resolution failure or network error
        return False


def normalize_url(raw_url: str) -> str:
    """Ensure URL has a valid http/https scheme."""
    raw = raw_url.strip()
    if not raw:
        return ""
    if not raw.startswith("http://") and not raw.startswith("https://"):
        return f"https://{raw}"
    return raw


def inspect_company_website(raw_url: str) -> Dict[str, Any]:
    """
    Perform deep technical audit and live scraping of a company's website:
    - SSL certificate and HTTPS enforcement
    - Response latency (ms)
    - Mobile viewport meta tag
    - Page Title and Meta Description
    - Technology and CMS detection (WordPress, Shopify, Wix, etc.)
    - Security headers (HSTS, CSP, X-Frame-Options)
    """
    url = normalize_url(raw_url)
    if not url:
        return {
            "success": False,
            "error": "The URL cannot be empty.",
            "url": raw_url,
            "has_website": False
        }

    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""

    if not hostname:
        return {
            "success": False,
            "error": "Invalid URL format.",
            "url": raw_url,
            "has_website": False
        }

    # SSRF Protection Gate
    if not is_ssrf_safe(hostname):
        return {
            "success": False,
            "error": f"Blocked by the security defense: probing internal private addresses or invalid domain names is not allowed ({hostname}).",
            "url": raw_url,
            "has_website": False
        }

    start_time = time.time()
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Cradilot-Scanner/2.0"
        }
        with httpx.Client(timeout=7.0, follow_redirects=True, headers=headers, verify=True) as client:
            resp = client.get(url)
            elapsed_ms = int((time.time() - start_time) * 1000)

            final_url = str(resp.url)
            status_code = resp.status_code
            html_text = resp.text or ""
            resp_headers = resp.headers

            # 1. SSL & Protocol（真实证书核验，以最终跳转主机为准）
            has_ssl = final_url.startswith("https://")
            final_host = urllib.parse.urlparse(final_url).hostname or ""
            if has_ssl:
                tls_info = inspect_tls(final_host, port=(urllib.parse.urlparse(final_url).port or 443))
            else:
                tls_info = {"ssl_valid": False, "cert_issuer": "", "cert_not_after": "",
                            "cert_days_left": None, "cert_checked": False,
                            "ssl_error": "The site offers no HTTPS endpoint, so there is no certificate to verify"}
            ssl_valid = bool(tls_info["ssl_valid"])

            # 2. SEO & Viewport Meta
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "No title defined (No Title)"
            title = re.sub(r"\s+", " ", title)[:100]

            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html_text, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else ""
            description = re.sub(r"\s+", " ", description)[:150]

            has_mobile_viewport = bool(re.search(r'<meta[^>]*name=["\']viewport["\']', html_text, re.IGNORECASE))

            # 3. Security Headers
            has_hsts = "strict-transport-security" in resp_headers
            has_x_frame = "x-frame-options" in resp_headers
            has_csp = "content-security-policy" in resp_headers
            server_banner = resp_headers.get("server", "Hidden")

            # 4. Tech Stack Detection
            detected_stack = []
            html_lower = html_text.lower()
            if "wp-content" in html_lower or "wp-includes" in html_lower:
                detected_stack.append("WordPress")
            if "woocommerce" in html_lower:
                detected_stack.append("WooCommerce")
            if "shopify" in html_lower or "cdn.shopify.com" in html_lower:
                detected_stack.append("Shopify")
            if "wix.com" in html_lower or "_wix" in html_lower:
                detected_stack.append("Wix")
            if "elementor" in html_lower:
                detected_stack.append("Elementor Page Builder")
            if "cloudflare" in server_banner.lower():
                detected_stack.append("Cloudflare CDN")

            cms_label = ", ".join(detected_stack) if detected_stack else "Custom build / static framework (Custom Framework)"

            # 5. Technical Maturity Scoring (0 - 100)
            score = 40  # Base for having a live site
            if ssl_valid: score += 25
            if has_mobile_viewport: score += 15
            if has_hsts: score += 10
            if elapsed_ms < 1500: score += 10

            # 6. Diagnosis Summary Formulation
            findings = []
            if ssl_valid:
                days_left = tls_info.get("cert_days_left")
                cert_detail = f" (issued by {tls_info.get('cert_issuer') or 'unknown'}"
                if days_left is not None:
                    cert_detail += f", {days_left} days left before expiry)"
                else:
                    cert_detail += ")"
                findings.append(f"HTTPS certificate chain verified{cert_detail}")
                if days_left is not None and days_left < 30:
                    findings.append(f"Certificate expires within {days_left} days and must be renewed now to avoid browser blocking")
            elif has_ssl:
                findings.append(f"HTTPS is enabled but the certificate did not pass trust-chain verification: {tls_info.get('ssl_error') or 'reason unknown'}")
            else:
                findings.append("No valid SSL certificate configured, so the browser shows a Not Secure warning")

            if has_mobile_viewport:
                findings.append("Mobile viewport adaptation in place")
            else:
                findings.append("No viewport mobile adaptation, so browsing on a phone is poor")

            if not has_hsts:
                findings.append("No HSTS forcing a secure channel")

            summary_text = (
                f"Probe succeeded (HTTP {status_code}, response latency {elapsed_ms}ms). "
                f"Core technology stack: {cms_label}. "
                f"Audit findings: {'; '.join(findings)}."
            )

            return {
                "success": True,
                "has_website": True,
                "input_url": raw_url,
                "final_url": final_url,
                "status_code": status_code,
                "has_ssl": has_ssl,
                "ssl_valid": ssl_valid,
                "cert_issuer": tls_info.get("cert_issuer", ""),
                "cert_not_after": tls_info.get("cert_not_after", ""),
                "cert_days_left": tls_info.get("cert_days_left"),
                "cert_checked": tls_info.get("cert_checked", False),
                "ssl_error": tls_info.get("ssl_error", ""),
                "response_time_ms": elapsed_ms,
                "page_title": title,
                "page_description": description,
                "has_mobile_viewport": has_mobile_viewport,
                "tech_stack": cms_label,
                "server_banner": server_banner,
                "security_headers": {
                    "hsts": has_hsts,
                    "x_frame_options": has_x_frame,
                    "csp": has_csp
                },
                "technical_score": score,
                "audit_summary": summary_text
            }

    except httpx.ConnectError:
        return {
            "success": False,
            "has_website": False,
            "error": "The domain name could not be resolved or no network connection could be established. Please check that the URL was entered correctly.",
            "url": raw_url
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "has_website": True,
            "check_status": "unverified",
            "has_ssl": False,
            "ssl_valid": False,
            "cert_checked": False,
            "error": "Connection to the target server timed out (>7 seconds). The site is extremely slow to reach, which badly affects customer conversion.",
            "url": raw_url,
            "audit_summary": "Connection timed out (>7000ms), which indicates the server has no CDN acceleration or is under-specced, making customer loss very likely."
        }
    except Exception as e:
        # Fallback inspection for non-standard ports or self-signed certs
        return {
            "success": False,
            "has_website": True,
            "check_status": "unverified",
            "has_ssl": False,
            "ssl_valid": False,
            "cert_checked": False,
            "error": f"An exception occurred during the probe: {str(e)}",
            "url": raw_url,
            "audit_summary": f"Probe blocked: {str(e)}"
        }
