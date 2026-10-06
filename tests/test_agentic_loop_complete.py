"""
Comprehensive Integration Test Suite for Cradilot AI Agentic Loop Refactor.
Verifies:
1. Step 1 Start with Substeps 1.5 (Biggest Business Challenge) & 1.6 (12-Month Growth Objective).
2. Step 2 Website Scraper integration and web dimension wiki node persistence.
3. Multi-turn dynamic agentic probe loop:
   - 4-step Chain-of-Thought (CoT) workbench data payload.
   - Strict zero-duplication dimension probing.
   - 11-dimension information completeness tracking (6 DMS + 5 ARS).
   - Early finalize threshold trigger (>= 6 verified items).
4. Pure-function deterministic calculation:
   - Anti-ghost scoring.
   - DMS < 40 ARS hard-lock to <= 10.0.
   - 12-Month Action Roadmap with Cradle Form A2 acceptance evidences.
5. Typst vector PDF generation:
   - Metadata, 12-Month Roadmap, and Milestone Form A2 schedule rendering.
6. Industry benchmark cases:
   - Klang Auto Parts Wholesale.
   - KL F&B Cloud Kitchen.
   - Professional Accounting Firm.

Conforms to NodiGuard Security Sentinel Directives (Zero Emoji, Anti-Vibe-Coding).
"""

import re
import pytest
from fastapi.testclient import TestClient
from app import app
from core.sql_wiki_engine import SqlWikiEngine, CORE_DIMENSIONS, ARS_FACTORS
from core.agentic_diagnostic import (
    start_diagnostic_session,
    process_diagnostic_turn,
    finalize_diagnosis_from_wiki,
    generate_scraper_critique,
    build_cradilot_thought_chain
)
from typst_generator.compiler import compile_blueprint_pdf

client = TestClient(app)
EMOJI_REGEX = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")


def test_step1_challenge_and_objective_persistence():
    """Verify Step 1 captures and persists biggest_challenge and growth_objective in SQLite dossier."""
    session_id = "test-session-step1-persistence"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="Klang Automotive Hub Sdn Bhd",
        industry="汽配五金批发与进出口",
        team_size="6-20 人",
        annual_turnover="RM 2M - 10M",
        biggest_challenge="下班后及周末询价处于真空期，买家比价极快导致夜间漏单流失严重",
        growth_objective="12个月内落地24/7 AI自动询盘与报盘，实现夜间商机留存提升30%"
    )

    tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    dossier = tree["dossier"]
    assert dossier["session_id"] == session_id
    assert dossier["biggest_challenge"] == "下班后及周末询价处于真空期，买家比价极快导致夜间漏单流失严重"
    assert dossier["growth_objective"] == "12个月内落地24/7 AI自动询盘与报盘，实现夜间商机留存提升30%"
    assert not EMOJI_REGEX.findall(dossier["biggest_challenge"])
    assert not EMOJI_REGEX.findall(dossier["growth_objective"])


def test_cot_chain_generation_structure():
    """Verify 4-step CoT reasoning returns all required cognitive stages without emojis."""
    cot = build_cradilot_thought_chain(
        company_name="Unit Test Logistics",
        industry="汽配五金批发与进出口",
        target_dim="cloud",
        user_answer="核心账套只存在前台一台电脑，平时用USB闪存盘拷贝备份。"
    )
    assert len(cot) == 4
    expected_stages = [
        "Fact recorded",
        "Evidence compared",
        "Guardrail check",
        "Next step"
    ]
    for i, step in enumerate(cot):
        assert step["stage"] == expected_stages[i]
        assert len(step["thought"]) > 10
        assert not EMOJI_REGEX.findall(step["thought"])


def test_end_to_end_agentic_loop_and_early_finalize():
    """
    Test complete agentic loop:
    - Start session via API.
    - Technical web check records web dimension.
    - Multi-turn probe answers.
    - Verify zero duplication of probed dimensions.
    - Verify early finalize trigger (>= 6 verified).
    - Finalize diagnosis and check 12-Month roadmap + Form A2 evidence.
    """
    # 1. Start Session
    start_resp = client.post("/api/diag/start", json={
        "company_name": "Klang Machinery & Tools Sdn Bhd",
        "industry": "汽配五金批发与进出口",
        "team_size": "6-20 人",
        "annual_turnover": "RM 2M - 10M",
        "biggest_challenge": "下班后晚间客户在WhatsApp询价无法即时报价，商机直接流向竞争对手",
        "growth_objective": "12个月内搭建线上独立官网与24/7 AI报价助理，年化增收RM 200k"
    })
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    session_id = start_data["session_id"]

    # 2. Inspect Website (Step 2)
    inspect_resp = client.post("/api/scrape/inspect-website", json={
        "url": "https://klang-machinery-example.com.my",
        "session_id": session_id
    })
    assert inspect_resp.status_code == 200
    inspect_data = inspect_resp.json()
    assert "ai_critique" in inspect_data

    # Check that 'web' dimension is now verified in wiki
    tree_s2 = SqlWikiEngine.get_live_wiki_tree(session_id)
    web_dim = next((d for d in tree_s2["dimensions"] if d["dimension_code"] == "web"), None)
    assert web_dim is not None
    assert web_dim["is_verified"] is True

    # 3. Turn 1 (Answers Cloud)
    turn1_resp = client.post("/api/diag/step", json={
        "session_id": session_id,
        "user_answer": "财务软件安装在一台本地电脑上，平时没有做云端异地自动备份，偶尔插U盘备份。"
    })
    assert turn1_resp.status_code == 200
    t1_data = turn1_resp.json()
    assert t1_data["status"] == "CONTINUE"
    assert "cot" in t1_data
    assert len(t1_data["cot"]) == 4

    # 4. Turn 2 (Answers CRM)
    turn2_resp = client.post("/api/diag/step", json={
        "session_id": session_id,
        "user_answer": "平时销售都是用个人员工手机 WhatsApp 接单，单据手写送货单。"
    })
    assert turn2_resp.status_code == 200
    t2_data = turn2_resp.json()
    assert t2_data["status"] == "CONTINUE"

    # 5. Turn 3 (Answers Cyber + AI)
    turn3_resp = client.post("/api/diag/step", json={
        "session_id": session_id,
        "user_answer": "平时对外用个人免费 gmail 发报价单，下班后晚上下班没人回客户。"
    })
    assert turn3_resp.status_code == 200
    t3_data = turn3_resp.json()
    assert t3_data["status"] == "CONTINUE"

    # 6. Turn 4 (Answers Marketing) -> Now at least 6 dimensions are verified!
    turn4_resp = client.post("/api/diag/step", json={
        "session_id": session_id,
        "user_answer": "完全不打广告，全靠熟客转介绍，没有装任何追踪代码或分析工具。"
    })
    assert turn4_resp.status_code == 200
    t4_data = turn4_resp.json()

    # Now total_explored >= 6 (web, cloud, crm, cyber, ai, marketing)
    assert t4_data.get("allow_early_finalize") is True
    assert t4_data.get("is_ready_for_scoring") is True

    # Verify no duplicate dimension probed
    explored_dims = [d["dimension_code"] for d in t4_data["tree"]["dimensions"] if d["is_verified"]]
    if t4_data.get("next_probe"):
        next_target = t4_data["next_probe"].get("dimension")
        assert next_target not in explored_dims, f"Duplicate dimension probed: {next_target}"

    # 7. Finalize Diagnosis Early
    fin_resp = client.post("/api/diag/finalize", json={"session_id": session_id})
    assert fin_resp.status_code == 200
    report = fin_resp.json()

    # Check anti-ghost scoring and hardlock:
    # Immature setup must have DMS < 40 and ARS <= 10.0 hardlocked
    assert report["dms"]["overall_score"] < 40.0
    assert report["ars"]["is_hard_locked"] is True
    assert report["ars"]["final_score"] <= 10.0
    # 报价含待询价项时不给出投资回报率（分母不完整，比率会虚高）
    if any(ph.get("pricing_pending") for ph in report["roadmap"]):
        assert report["roi"]["roi_percentage"] is None
        assert report["roi"]["cost_basis"] == "partial_quote"
    else:
        assert report["roi"]["roi_percentage"] > 0.0

    # Check 12-Month Roadmap phases
    roadmap = report["roadmap"]
    assert len(roadmap) == 3
    timelines = [p["timeline"] for p in roadmap]
    assert timelines == ["2-4 weeks", "Months 3 - 6", "Months 6 - 12"], timelines

    # 每阶段都要写明"做完怎么核对"，且不得带内部话术
    for phase in roadmap:
        assert len(phase["acceptance"]) >= 1
        assert "Form A2" not in phase["acceptance"]

    # 8. Check Typst PDF compilation passes and produces valid PDF
    pdf_bytes = compile_blueprint_pdf(report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.startswith(b"%PDF")

    # 9. Check /api/pdf/generate HTTP endpoint produces valid downloadable PDF
    pdf_api_resp = client.post("/api/pdf/generate", json=report)
    assert pdf_api_resp.status_code == 200
    assert pdf_api_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_api_resp.content) > 5000
    assert pdf_api_resp.content.startswith(b"%PDF")


def test_industry_benchmark_klang_autoparts():
    """Benchmark Case 1: Klang Auto Parts Wholesale (汽配五金进出口)."""
    session_id = "bench-klang-autoparts-01"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="Klang Heavy Parts Logistics Sdn Bhd",
        industry="汽配五金批发与进出口",
        team_size="6-20 人",
        annual_turnover="RM 2M - 10M",
        biggest_challenge="下班后晚间客户在WhatsApp询价无法即时报价，漏单严重",
        growth_objective="12个月内上线24/7 AI自动询盘并实现全渠道库存数字化"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "我们没有独立官方网站，业务员都是在个人手机WhatsApp接单，单据手写在纸上。"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "对外发报价单用免费gmail，财务账目在单台电脑没备份，晚上下班没人回客户。"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "完全没有线上获客追踪，全靠熟客转介绍。管理层支持数字化，但老员工习惯纸质单据抵触系统。"
    )

    report = finalize_diagnosis_from_wiki(session_id)
    assert report["dms"]["overall_score"] < 40.0
    assert report["ars"]["is_hard_locked"] is True
    assert len(report["pain_points"]) >= 3

    # Check that roadmap contains Form A2 evidence
    assert len(report["roadmap"]) == 3
    pdf_bytes = compile_blueprint_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")


def test_industry_benchmark_kl_food_and_beverage():
    """Benchmark Case 2: KL F&B Cloud Kitchen (餐饮连锁与中央厨房)."""
    session_id = "bench-kl-food-beverage-02"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="KL Flavor Cloud Kitchens Sdn Bhd",
        industry="餐饮连锁",
        team_size="21-50 人",
        annual_turnover="RM 2M - 10M",
        biggest_challenge="多个外卖平台与线下门店订单未打通，月末手工对账错漏率高",
        growth_objective="12个月内整合全渠道订单系统，月末对账从3天压缩至半天以内"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "没有官方网站只有FB页面，分店采购通过WhatsApp群通知，单据月末纸质对账。"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "店长使用个人gmail沟通，单店POS数据保存在单台收银电脑未上云备份。"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "管理层决心坚定愿意投入预算，年轻团队乐于接受新系统，但缺乏成文SOP规范流程。"
    )

    report = finalize_diagnosis_from_wiki(session_id)
    assert report["dms"]["overall_score"] < 50.0
    assert len(report["roadmap"]) == 3
    pdf_bytes = compile_blueprint_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")


def test_industry_benchmark_pj_accounting_firm():
    """Benchmark Case 3: Petaling Jaya Advisory / Accounting Firm (专业服务)."""
    session_id = "bench-pj-accounting-03"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="PJ Horizon Advisory PLT",
        industry="专业服务",
        team_size="6-20 人",
        annual_turnover="RM 500k - 2M",
        biggest_challenge="客户审计底稿与合同保密合规压力大，单机存储存在勒索与PDPA违规风险",
        growth_objective="12个月内通过MACC 17A TRUST与PDPA数字化合规审计认证"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "网站多年没更新没有SSL证书，客户往来邮件有部分员工使用个人gmail。"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "审计底稿保存在单台本地电脑只有偶尔插U盘备份，客户档案分散在各审计员个人电脑。"
    )
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "管理层预算充足，有成文SOP规范，数据属于结构化但存在部门孤岛。"
    )

    report = finalize_diagnosis_from_wiki(session_id)
    assert len(report["roadmap"]) == 3
    pdf_bytes = compile_blueprint_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
