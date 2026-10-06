"""
Automated tests for Cradilot AI true Agentic dynamic probe generation loop,
scraper AI critique, and cognitive reasoning response structure.
Zero emoji, strict local isolation.
"""

import re
from fastapi.testclient import TestClient
from app import app
from core.sql_wiki_engine import SqlWikiEngine
from core.agentic_diagnostic import (
    start_diagnostic_session,
    generate_scraper_critique,
    get_first_agentic_probe,
    process_diagnostic_turn
)

client = TestClient(app)
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")


def test_scraper_ai_critique_generation():
    crawl_mock = {
        "url": "https://klang-autoparts-example.com",
        "has_ssl": False,
        "response_time_ms": 940,
        "mobile_friendly": False,
        "cms_tech": ["WordPress 5.8", "WooCommerce"],
        "technical_score": 42
    }
    critique = generate_scraper_critique(
        company_name="Klang Precision Auto Parts Sdn Bhd",
        industry="汽配五金批发与进出口",
        crawl_result=crawl_mock
    )
    assert isinstance(critique, str)
    assert len(critique.strip()) > 20
    assert not EMOJI_PATTERN.findall(critique), f"Critique contained emojis: {critique}"
    assert "SSL" in critique or "安全" in critique or "证书" in critique or "加密" in critique


def test_first_agentic_probe_for_step3():
    init_res = start_diagnostic_session(
        company_name="Penang Seafood Chain Sdn Bhd",
        industry="餐饮连锁",
        team_size="21-50 人",
        annual_turnover="RM 2M - 10M"
    )
    session_id = init_res["session_id"]

    probe = get_first_agentic_probe(session_id)
    assert "question" in probe
    assert "options" in probe
    assert len(probe["options"]) >= 2
    assert probe["step_num"] == 3
    assert not EMOJI_PATTERN.findall(probe["question"])

    for opt in probe["options"]:
        assert "label" in opt and "sub" in opt and "val" in opt
        assert not EMOJI_PATTERN.findall(opt["label"])
        assert not EMOJI_PATTERN.findall(opt["sub"])


def test_fastapi_dynamic_probe_flow():
    # 1. Start session
    start_resp = client.post("/api/diag/start", json={
        "company_name": "JB Hardware Trading",
        "industry": "汽配五金批发与进出口",
        "team_size": "6-20 人",
        "annual_turnover": "RM 500k - 2M"
    })
    assert start_resp.status_code == 200
    sess = start_resp.json()["session_id"]

    # 2. Inspect website and verify ai_critique
    inspect_resp = client.post("/api/scrape/inspect-website", json={
        "url": "https://example.com",
        "session_id": sess
    })
    assert inspect_resp.status_code == 200
    web_data = inspect_resp.json()
    assert "ai_critique" in web_data
    assert len(web_data["ai_critique"]) > 10

    # 3. First probe endpoint
    first_probe_resp = client.get(f"/api/diag/first-probe/{sess}")
    assert first_probe_resp.status_code == 200
    p3 = first_probe_resp.json()
    assert p3["step_num"] == 3
    assert len(p3["options"]) >= 2

    # 4. Turn 1 (Step 3 to Step 4)
    step1_resp = client.post("/api/diag/step", json={
        "session_id": sess,
        "user_answer": "财务进销存单据仅存在单台电脑上，完全没有做云端异地备份。"
    })
    assert step1_resp.status_code == 200
    s1_data = step1_resp.json()
    assert s1_data["status"] == "CONTINUE"
    assert s1_data["step_num"] >= 4
    assert "next_probe" in s1_data
    assert len(s1_data["options"]) >= 2

    # 5. Turn 2 (Step 4 to Step 5)
    step2_resp = client.post("/api/diag/step", json={
        "session_id": sess,
        "user_answer": "业务员平时都是用个人手机 WhatsApp 跟进客户，客户资料分散在手机里。"
    })
    assert step2_resp.status_code == 200

    # 6. Turn 3 (Step 5 to Step 6)
    step3_resp = client.post("/api/diag/step", json={
        "session_id": sess,
        "user_answer": "平时给客户发报价单用的是个人免费 Gmail 邮箱。"
    })
    assert step3_resp.status_code == 200

    # 7. Turn 4 (Step 6 to Step 7)
    step4_resp = client.post("/api/diag/step", json={
        "session_id": sess,
        "user_answer": "完全靠老客户转介绍，从来没有做过线上数字化获客追踪。"
    })
    assert step4_resp.status_code == 200

    # 8. Turn 5 (Step 7 to Finalize)
    step5_resp = client.post("/api/diag/step", json={
        "session_id": sess,
        "user_answer": "晚上6点下班后到11点完全无人看管，客户询盘只能第二天上班才处理。"
    })
    assert step5_resp.status_code == 200
    s5_data = step5_resp.json()
    assert s5_data["status"] == "DIAGNOSIS_COMPLETE" or s5_data["is_ready_for_scoring"]

    # 9. Finalize
    fin_resp = client.post("/api/diag/finalize", json={"session_id": sess})
    assert fin_resp.status_code == 200
    fin_data = fin_resp.json()
    assert fin_data["dms"]["overall_score"] < 40
    assert fin_data["ars"]["is_hard_locked"] is True
    # 该画像的方案含待报价项：分母不完整，因此不给比率，只给绝对收益
    roi = fin_data["roi"]
    pending = any(ph.get("pricing_pending") for ph in fin_data["roadmap"])
    assert roi["total_benefits"] > 0
    if pending:
        assert roi["roi_percentage"] is None and roi["cost_basis"] == "partial_quote"
    else:
        assert roi["roi_percentage"] > 0
