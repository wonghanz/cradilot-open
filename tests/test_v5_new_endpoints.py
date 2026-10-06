"""
Unit and integration tests for Cradilot v5 endpoints:
- POST /api/audit/dev-scan
- POST /api/speech/filter-noise
- POST /api/sales/dispatch-lead
Strict Zero Emoji, zero Gemini mention, local isolation.
"""

import re
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")


def test_speech_filter_noise_endpoint():
    resp = client.post("/api/speech/filter-noise", json={
        "raw_text": "那个就是...我们平时其实财务就是一台电脑做账嘛，根本没有做云端备份，然后偶尔插个U盘拷贝一下。",
        "session_id": "test-session-noise"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "clean_text" in data
    assert len(data["clean_text"]) > 10
    assert not EMOJI_PATTERN.findall(data["clean_text"])
    assert "structured_facts" in data
    assert "estimated_loss_rm" in data
    assert data["estimated_loss_rm"] >= 0


def test_dev_scan_endpoint():
    resp = client.post("/api/audit/dev-scan", json={
        "url": "https://example.com",
        "session_id": "test-session-audit"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "domain" in data
    assert "email_security" in data
    assert "sensitive_files" in data
    assert "key_scan" in data
    assert "dev_audit_score" in data


def test_assess_endpoint_never_asserts_untold_facts():
    """只给公司名与行业时，兜底评估只能说"这些还没采集"，不能替客户承认缺失。"""
    resp = client.post("/api/assess", json={
        "company_name": "Uji Senyap Sdn Bhd", "industry": "汽配五金批发与进出口"})
    assert resp.status_code == 200
    data = resp.json()
    meta = data["metadata"]

    assert meta["data_basis"] == "basic_only"
    assert "Where customer records are kept" in meta["unverified_items"]
    assert "Backups and disaster recovery today" in meta["unverified_items"]
    # 没有任何已核验的缺失事实 → 不得凭空产出痛点清单
    assert data["recommendation"]["primary_pain_points"] == []
    # 收益侧没有依据 → 不给比率，也不给净收益
    assert data["roi"]["cost_basis"] == "no_benefit_basis"
    assert data["roi"]["roi_percentage"] is None
    assert data["roi"]["net_gain"] is None
    sources = data["roi"]["assumptions"]["sources"]
    assert all("Entered by you" not in v for v in sources.values()), "没填过的数字被标成了贵司当场填报"


def test_sales_dispatch_lead_endpoint():
    # 先跑一次真实评估，dispatch 必须绑定真实 assessment，
    # 旧版在这里不给 assessment_data 就会凭空得到 DMS 38 / ROI 505.2%。
    assess = client.post("/api/assess", json={
        "company_name": "Uji Dispatch Sdn Bhd",
        "industry": "汽配五金批发与进出口",
        "website_status": "outdated",
        "backup_strategy": "single_pc",
        "crm_status": "personal_whatsapp",
        "after_hours_leak": True
    })
    assert assess.status_code == 200
    resp = client.post("/api/sales/dispatch-lead", json={
        "assessment_data": assess.json(),
        "session_id": "test-session-dispatch",
        "contact_name": "Dato' Tan Wei Ming",
        "phone": "+60123456789",
        "email": "tan@example.com.my",
        "preferred_time": "afternoon",
        "notes": "希望重点辅导单机财务防勒索异地容灾冷备及申请 Cradle 资助"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "lead_id" in data
    assert data["lead_id"].startswith("LEAD-")
    assert "icebreaker" in data
    assert "checkout_cart" in data
    assert not EMOJI_PATTERN.findall(data["icebreaker"])
