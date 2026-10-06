"""
Unit tests for core/dev_audit.py (Step 2 Developer-Level Passive Security & Compliance Audit).
"""

from core.dev_audit import DevLevelAuditEngine


def test_scan_for_exposed_keys():
    # A syntactically valid but worthless key: the detector must still catch it.
    fake_key = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"  # nosec
    html_sample = f"""
    <html>
      <head><script>const apiKey = "{fake_key}";</script></head>
      <body><div>Welcome to Klang Auto Parts</div></body>
    </html>
    """
    findings = DevLevelAuditEngine.scan_for_exposed_keys(html_sample)
    assert len(findings) == 1
    assert findings[0]["key_type"] == "Google API Key"
    assert "AIza" in findings[0]["masked_key"]
    assert "****" in findings[0]["masked_key"]


def test_dns_email_security():
    dns_res = DevLevelAuditEngine.inspect_dns_email_security("klangautoparts.com.my")
    assert "has_spf" in dns_res
    assert "has_dmarc" in dns_res
    assert "email_auth_blocking" in dns_res
