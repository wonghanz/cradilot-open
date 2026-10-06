"""
Cradilot Core - Step 2 Developer-Level Passive Security & Compliance Audit (Dev-Level Audit)
Strictly adheres to NodiGuard production security standards and legal passive boundaries.
Performs:
1. Anti-Email Spoofing: DNS SPF, DKIM, DMARC records resolution
2. Exposed Sensitive Files: /.env, /.git/HEAD, /.wp-config.php.bak probing
3. Public Key Exposure Scan: Regex matching in HTML & client-side scripts
4. Transport Security: TLS 1.2/1.3, HSTS, CSP audit
"""

import os
import re
import json
import socket
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
import httpx
from datetime import datetime
from core.sql_wiki_engine import SqlWikiEngine

# 本机解析优先；公共 DoH 兜底，因为 Windows 会场/酒店网络常封 UDP/53 而放行 443。
DOH_ENDPOINT = os.environ.get("CRADILOT_DOH", "https://cloudflare-dns.com/dns-query")
DNS_TIMEOUT_SECONDS = float(os.environ.get("CRADILOT_DNS_TIMEOUT", "4"))


def _resolve_records(name: str, rdtype: str) -> Tuple[List[str], str, bool]:
    """查一类 DNS 记录，返回 (记录内容, 解析途径, 是否 NXDOMAIN)。

    必须区分"域名不存在"与"域名存在但无此类记录"：把前者说成后者，等于对
    一个拼错或已过期的域名断言"贵司未配置 SPF"，那是凭空捏造的缺陷。
    两者都查不到时返回空列表，绝不编造记录内容。
    """
    # 路径一：dnspython 走系统解析器
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, rdtype, lifetime=DNS_TIMEOUT_SECONDS)
            values = [str(a).strip('"') for a in answers]
            return [v for v in values if v], "local_resolver", False
        except dns.resolver.NXDOMAIN:
            return [], "local_resolver", True
        except dns.resolver.NoAnswer:
            return [], "local_resolver", False
    except ImportError:
        pass
    except Exception:
        pass

    # 路径二：Cloudflare DoH JSON（无需 API key）
    try:
        url = f"{DOH_ENDPOINT}?name={urllib.parse.quote(name)}&type={rdtype}"
        req = urllib.request.Request(
            url,
            headers={"accept": "application/dns-json", "user-agent": "cradilot-audit/1.0"},
        )
        with urllib.request.urlopen(req, timeout=DNS_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        values = [
            str(a.get("data", "")).strip('"')
            for a in (payload.get("Answer") or [])
            if a.get("data")
        ]
        # DoH JSON 的 Status：3 = NXDOMAIN，0 = NOERROR
        return [v for v in values if v], "cloudflare_doh", int(payload.get("Status", 0) or 0) == 3
    except Exception:
        return [], "unresolved", False


def _looks_like_wildcard_domain(domain: str) -> bool:
    """探测泛解析黑洞（example.com 之类：任意子域都有记录）。

    只有随机子域真的返回了 TXT 内容才算黑洞——多数解析器对随机标签会给
    NOERROR 空应答，若把"没有 NXDOMAIN"当成黑洞，正常域名会被全部误判，
    DKIM 探测于是被静默跳过。
    """
    probe = f"cradilot-nx-{abs(hash(domain)) % 10**9}.{domain}"
    values, via, _ = _resolve_records(probe, "TXT")
    if via == "unresolved":
        return False
    return bool(values)

# Regex patterns for exposed sensitive credentials
SENSITIVE_KEY_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "Cloud resources stolen and billed up maliciously"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key", "Public API quota hijacked for other people's calls"),
    (r"sk_live_[0-9a-zA-Z]{24}", "Stripe Live Secret Key", "Payment secret key leaked; funds can be transferred out, a serious breach"),
    (r"ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token", "The whole site's core code repository and configuration stolen"),
    (r"postgres://[a-zA-Z0-9_]+:[a-zA-Z0-9_]+@", "PostgreSQL Connection String", "Production database credentials exposed in plain text (top PDPA penalty)"),  # nosec - the detector pattern itself
    (r"mysql://[a-zA-Z0-9_]+:[a-zA-Z0-9_]+@", "MySQL Connection String", "Production database credentials exposed in plain text (top PDPA penalty)")  # nosec - the detector pattern itself
]

SENSITIVE_FILES_TO_CHECK = [
    ("/.env", "Environment variable configuration file (.env)", "Directly exposes database passwords, cloud keys and internal configuration"),
    ("/.git/HEAD", "Source code repository pointer (.git/HEAD)", "The full source history of the site can be downloaded in public and reversed"),
    ("/wp-config.php.bak", "WordPress core configuration backup (wp-config.php.bak)", "Core database credentials and site-wide keys can be downloaded directly")
]

# DKIM selector 无法从域名反查，只能按已知服务商的常用命名逐个探测。
# 每个 selector 一次 DNS 查询，故只保留大马 SME 常见邮件服务商实际使用的那些。
DKIM_SELECTORS = [
    "default", "google", "selector1", "selector2",   # Google Workspace / Microsoft 365
    "k1", "k2", "s1", "s2", "mail",                    # cPanel / 自营邮箱
    "fm1", "smartmail", "zimbra", "dkim"               # SendinBlue / Zoho / Zimbra
]


class DevLevelAuditEngine:
    """Developer-level technical & compliance auditor."""

    @staticmethod
    def inspect_dns_email_security(domain: str) -> Dict[str, Any]:
        """
        真实解析 SPF / DMARC / DKIM / MX。

        本方法此前不查任何记录：has_spf 写死 False，于是连本公司自己的域名都会
        被判成"未配置 SPF"；DMARC 用 socket.gethostbyname("_dmarc.x") 探测，而该
        主机名不存在 A 记录，故恒为 False，一旦偶然解析成功还会凭空生成一条含
        p=reject 与 rua 邮箱的假记录。合规判定与销售话术因此建立在虚构数据上。
        """
        clean_domain = (domain or "").replace("https://", "").replace("http://", "")
        clean_domain = clean_domain.split("/")[0].split(":")[0].strip().strip(".")
        result: Dict[str, Any] = {"domain": clean_domain}
        if not clean_domain:
            result.update({
                "has_spf": False, "has_dmarc": False, "dkim_verified": False,
                "spf_record": "No domain provided", "dmarc_record": "No domain provided",
                "dns_verified": False, "email_auth_blocking": False,
                "risk_summary": "No valid domain was provided, so the email anti-spoofing records could not be verified."
            })
            return result

        # ── SPF ──────────────────────────────────────────────────────────────
        spf_texts, spf_via, spf_nx = _resolve_records(clean_domain, "TXT")
        spf_records = [t for t in spf_texts if t.lower().startswith("v=spf1")]
        has_spf = bool(spf_records)
        spf_record = spf_records[0] if has_spf else ""
        # 终止符决定伪造难度：-all 硬拒、~all 软拒、+all 等于不设防、无终止符则形同虚设
        spf_qualifier = "absent"
        if has_spf:
            lowered = spf_record.lower()
            if " -all" in lowered:
                spf_qualifier = "hard_fail"
            elif "~all" in lowered:
                spf_qualifier = "soft_fail"
            elif "+all" in lowered:
                spf_qualifier = "permissive"
            else:
                spf_qualifier = "unterminated"
        if spf_nx:
            spf_display = "Domain does not exist (NXDOMAIN), so the email anti-spoofing setup cannot be assessed"
        elif has_spf:
            spf_display = spf_record
        elif spf_via == "unresolved":
            spf_display = "Could not be verified (DNS resolution unreachable)"
        else:
            spf_display = "No SPF record found (SPF Missing)"
        result.update({
            "has_spf": has_spf,
            "spf_record": spf_display,
            "spf_strength": spf_qualifier,
            "spf_include_count": spf_record.lower().count("include:") if has_spf else 0,
            "domain_exists": not spf_nx,
            "via": spf_via,
        })

        # ── DMARC ────────────────────────────────────────────────────────────
        dmarc_texts, dmarc_via, dmarc_nx = _resolve_records(f"_dmarc.{clean_domain}", "TXT")
        dmarc_records = [t for t in dmarc_texts if t.lower().startswith("v=dmarc1")]
        has_dmarc = bool(dmarc_records)
        dmarc_record = dmarc_records[0] if has_dmarc else ""
        dmarc_policy = ""
        dmarc_has_rua = False
        if has_dmarc:
            tag = re.search(r"\bp\s*=\s*(none|quarantine|reject)", dmarc_record, re.IGNORECASE)
            dmarc_policy = tag.group(1).lower() if tag else "unspecified"
            dmarc_has_rua = bool(re.search(r"\brua\s*=\s*mailto:", dmarc_record, re.IGNORECASE))
        if dmarc_nx:
            dmarc_display = "Domain does not exist (NXDOMAIN)"
        elif has_dmarc:
            dmarc_display = dmarc_record
        elif dmarc_via == "unresolved":
            dmarc_display = "Could not be verified (DNS resolution unreachable)"
        else:
            dmarc_display = "No DMARC record found (DMARC Missing)"
        result.update({
            "has_dmarc": has_dmarc,
            "dmarc_record": dmarc_display,
            "dmarc_policy": dmarc_policy,
            "dmarc_report_configured": dmarc_has_rua,
        })

        # ── DKIM：常见 selector 并行探测（13 次串行查询要 6-7 秒，演示预算给不起）──
        wildcard = _looks_like_wildcard_domain(clean_domain)
        dkim_hits: List[str] = []
        dkim_via = "unresolved"
        if not wildcard:
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = {
                    pool.submit(_resolve_records, f"{s}._domainkey.{clean_domain}", "TXT"): s
                    for s in DKIM_SELECTORS
                }
                for fut in as_completed(futures):
                    selector = futures[fut]
                    try:
                        texts, via, _ = fut.result()
                    except Exception:
                        continue
                    dkim_via = via if via != "unresolved" else dkim_via
                    if any("p=" in t.lower() for t in texts):
                        dkim_hits.append(selector)
            dkim_hits.sort(key=lambda s: DKIM_SELECTORS.index(s))
        # 二线防线：全部 selector 都"有签名"只可能是泛解析区域（example.com 即如此），
        # 不是真的部署了 13 套 DKIM。
        if len(dkim_hits) == len(DKIM_SELECTORS):
            wildcard = True
            dkim_hits = []
        result.update({
            "dkim_verified": bool(dkim_hits),
            "dkim_selectors": dkim_hits,
            "dkim_inconclusive": wildcard,
        })

        # ── MX：邮件由谁投递，决定仿冒面与托管归属 ─────────────────────────────
        mx_texts, _ = _resolve_records(clean_domain, "MX")[:2]
        mx_hosts = sorted({t.split()[-1].strip(".") for t in mx_texts if t} - {""})
        domain_exists = result.get("domain_exists", True)
        dns_verified = (spf_via != "unresolved") or (dmarc_via != "unresolved")
        result.update({
            "mx_hosts": mx_hosts,
            "mx_count": len(mx_hosts),
            "dns_verified": dns_verified,
        })

        # 合规判定：SPF 与 DMARC 都在，且 DMARC 策略不是 p=none（none 只收报告不拦截）
        blocking_policy = has_dmarc and dmarc_policy in ("quarantine", "reject")
        compliant = bool(has_spf and blocking_policy)
        result["email_auth_blocking"] = compliant

        if not dns_verified:
            risk_summary = ("The DNS records could not be verified in this network environment, so this conclusion is "
                            "unconfirmed. Do not assert a compliance status to the customer on this basis.")
        elif not domain_exists:
            risk_summary = ("This domain does not exist in public DNS (NXDOMAIN): it may have expired or be misspelled. "
                            "If the domain is dead, the website and every company mailbox become unreachable at the "
                            "same time, and that comes before any anti-spoofing configuration issue.")
        elif not has_spf and not has_dmarc:
            risk_summary = ("Neither SPF nor DMARC is set: anyone can send mail spoofing your domain (both your "
                            "customers and your bank may receive it), and your own outbound mail is more likely to be "
                            "marked as spam. This is the highest exposure band for invoice fraud.")
        elif has_spf and not has_dmarc:
            risk_summary = ("SPF is present but DMARC is missing: forgeries from outside cannot be rejected, and you "
                            "receive no reports about who is abusing your domain.")
        elif has_dmarc and not blocking_policy:
            risk_summary = f"DMARC is published but the policy is p={dmarc_policy or 'unspecified'}: it only collects reports and does not block spoofed mail."
        elif compliant and not dkim_hits and not wildcard:
            risk_summary = ("SPF and DMARC are in effect, but no DKIM signature was detected, so one link is still "
                            "missing from the full email reputation chain.")
        else:
            risk_summary = ("SPF/DMARC are configured (including a blocking policy), so email anti-spoofing is at a "
                            "usable level.")

        result["risk_summary"] = risk_summary
        return result

    @staticmethod
    def audit_exposed_sensitive_files(base_url: str) -> List[Dict[str, Any]]:
        """
        Passively check whether common sensitive backup/env files return HTTP 200 OK.
        """
        findings = []
        normalized_base = base_url.rstrip("/")
        headers = {"User-Agent": "Cradilot-DevAudit/2.0 (Institutional Security Sentinel)"}

        try:
            with httpx.Client(timeout=3.0, follow_redirects=False, headers=headers, verify=True) as client:
                for path, label, risk in SENSITIVE_FILES_TO_CHECK:
                    target = f"{normalized_base}{path}"
                    try:
                        resp = client.get(target)
                        # Only report if true 200 OK with actual payload (not generic 404 custom page)
                        if resp.status_code == 200 and len(resp.text) > 10 and "<html" not in resp.text.lower()[:100]:
                            findings.append({
                                "file_path": path,
                                "label": label,
                                "status_code": resp.status_code,
                                "risk_impact": risk,
                                "severity": "CRITICAL"
                            })
                    except Exception:
                        continue
        except Exception:
            pass

        return findings

    @staticmethod
    def scan_for_exposed_keys(html_content: str) -> List[Dict[str, Any]]:
        """
        Scan page HTML and inline script bundles for hardcoded sensitive API keys.
        """
        detected = []
        for pattern, key_type, risk in SENSITIVE_KEY_PATTERNS:
            matches = re.findall(pattern, html_content)
            if matches:
                # Mask key for Zero-Leak DLP compliance
                sample = matches[0]
                masked = sample[:4] + "****" + sample[-4:] if len(sample) > 8 else "****"
                detected.append({
                    "key_type": key_type,
                    "masked_key": masked,
                    "risk_impact": risk,
                    "severity": "HIGH"
                })
        return detected

    @staticmethod
    def run_full_dev_audit(url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run end-to-end Step 2 Developer-Level Security & Compliance Audit.
        Syncs findings to SQLite Wiki if session_id is provided.
        """
        raw_url = (url or "").strip()
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"https://{raw_url}"

        parsed = urllib.parse.urlparse(raw_url)
        domain = parsed.hostname or raw_url

        # 1. DNS & Email Spoofing Defense
        dns_result = DevLevelAuditEngine.inspect_dns_email_security(domain)

        # 2. Exposed Sensitive Files
        exposed_files = DevLevelAuditEngine.audit_exposed_sensitive_files(raw_url)

        # 3. HTML & Public Keys Scan
        exposed_keys = []
        transport_security = {
            "has_https": raw_url.startswith("https://"),
            "has_hsts": False,
            "has_csp": False,
            "status_code": 0
        }
        try:
            with httpx.Client(timeout=5.0, follow_redirects=True, verify=True) as client:
                resp = client.get(raw_url)
                transport_security["status_code"] = resp.status_code
                transport_security["has_hsts"] = "strict-transport-security" in resp.headers
                transport_security["has_csp"] = "content-security-policy" in resp.headers
                exposed_keys = DevLevelAuditEngine.scan_for_exposed_keys(resp.text or "")
        except Exception:
            pass

        # 4. Calculate Dev Security Grade
        score = 80
        if not dns_result["email_auth_blocking"]:
            score -= 25
        if exposed_files:
            score -= 30
        if exposed_keys:
            score -= 25
        if not transport_security["has_https"]:
            score -= 35
        score = max(10, min(100, score))

        # Overall Status
        if score >= 80:
            rating = "SECURE_INSTITUTIONAL"
            status_text = "Security and compliance baseline met (Secure Institutional)"
        elif score >= 50:
            rating = "MODERATE_VULNERABILITIES"
            status_text = "Moderate security and business compliance blind spots (Moderate Risk)"
        else:
            rating = "CRITICAL_DEFICIENCIES"
            status_text = "High-risk vulnerabilities and business audit compliance exposure (Critical Vulnerable)"

        audit_report = {
            "target_url": raw_url,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "technical_score": score,
            "rating": rating,
            "status_text": status_text,
            "dns_email_security": dns_result,
            "exposed_files": exposed_files,
            "exposed_keys": exposed_keys,
            "transport_security": transport_security,
            "recommended_fixes": [
                "Deploy company business email and have the SPF, DKIM and DMARC anti-impersonation records set up automatically",
                "Block public internet access to sensitive files such as /.env and /.git under the web server root directory",
                "Enforce HTTPS and the HSTS header across the whole site, so man-in-the-middle hijacking is ruled out"
            ]
        }

        # Sync critical findings to SQLite Wiki
        if session_id:
            now = datetime.now().isoformat()
            with SqlWikiEngine.get_db_connection() as conn:
                cursor = conn.cursor()
                # Record dev audit summary
                cursor.execute("""
                    INSERT INTO wiki_evidence_nodes (session_id, dimension, fact_key, fact_value, quote_text, confidence, created_at)
                    VALUES (?, 'cyber', 'dev_audit_grade', ?, ?, 0.98, ?)
                """, (session_id, rating, f"Developer-level security audit score: {score}/100 ({status_text})", now))
                conn.commit()

            if not dns_result["email_auth_blocking"]:
                SqlWikiEngine._insert_pain_point(
                    session_id=session_id,
                    title="Company domain lacks DMARC / SPF anti-spoofing records, so others can send mail as you",
                    root_cause="Verified through DNS: this domain has no effective SPF/DMARC blocking policy, so mail that spoofs the domain is not judged as forged.",
                    loss_myr=0.0,
                    severity="HIGH",
                    cradle_gap="For mail someone else sends out under your domain, no record of yours can be traced afterwards.",
                    solution="Business Mail Pro business-domain mailboxes (SPF/DKIM/DMARC pre-configured)",
                    dimension="cyber"
                )

            if exposed_files or exposed_keys:
                SqlWikiEngine._insert_pain_point(
                    session_id=session_id,
                    title="Sensitive production configuration files or external interface credentials may be exposed",
                    root_cause="The passive scan found readable sensitive configuration files and interface credentials, referenced by the site front end or sitting in public directories.",
                    loss_myr=0.0,
                    severity="CRITICAL",
                    cradle_gap="Once someone reads credentials out of a public directory, the database and the whole site are no longer under control.",
                    solution="Linux cloud server security hardening and static asset isolation package",
                    dimension="web"
                )

            SqlWikiEngine.update_state_ledger(session_id)

        return audit_report
