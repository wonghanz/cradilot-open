"""
Unit & Integration Tests for Task Stream 2 (SQLite LLM Wiki) and Task Stream 3 (Agentic Diagnostic Loop).
Conforms to NodiGuard Security Sentinel Directives (Anti-Ghost-Scoring, Zero Emoji).
"""

import pytest
from fastapi.testclient import TestClient
from app import app
from core.sql_wiki_engine import SqlWikiEngine, CORE_DIMENSIONS, _stated_tool_tokens
from core.ars_engine import calculate_ars
from core.agentic_diagnostic import (
    start_diagnostic_session,
    process_diagnostic_turn,
    finalize_diagnosis_from_wiki
)


@pytest.fixture
def client():
    return TestClient(app)


def test_sqlite_wiki_crud():
    session_id = "test-unit-crud-101"
    dossier = SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="Unit Test Hardware Sdn Bhd",
        industry="汽配五金批发与进出口",
        team_size="6-20 人",
        annual_turnover="RM 2M - 10M"
    )
    assert dossier["session_id"] == session_id
    assert dossier["company_name"] == "Unit Test Hardware Sdn Bhd"

    # Ingest statement with 4 dimensions: web (none), crm (personal_whatsapp), ai (leak), cloud (single_pc)
    user_msg = "我们没有网站，平时都用员工个人WhatsApp接单，单据手写在纸上，下班后晚上下班没人回客户，财务保存在单台电脑没备份。"
    extracted = SqlWikiEngine.extract_and_sync_wiki_nodes(session_id, user_msg)
    assert len(extracted) >= 3

    completeness, explored, missing = SqlWikiEngine.calculate_completeness(session_id)
    assert completeness >= 0.50
    assert "web" in explored
    assert "crm" in explored
    assert "cloud" in explored
    assert "ai" in explored

    tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    assert tree["session_id"] == session_id
    assert tree["dms_ratio"] >= 0.50
    assert len(tree["dimensions"]) == 6
    assert len(tree["pain_points"]) >= 2
    # 反幻觉不变量：问诊阶段只登记证据，不登记金额。损失要等 ROI 环节用客户自己输入的
    # 数字算出来、再由 apply_loss_model 分摊，所以此刻每一条痛点的 loss 都必须还是 0。
    assert tree["total_financial_loss_myr"] == 0.0
    assert all(p["loss_myr"] == 0.0 for p in tree["pain_points"])


def test_anti_ghost_scoring_and_hardlock():
    session_id = "test-unit-anti-ghost-202"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="Anti Ghost Testing Co",
        industry="汽配五金批发与进出口",
        team_size="6-20 人",
        annual_turnover="RM 2M - 10M"
    )

    # Ingest facts indicating immature infrastructure
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        session_id,
        "没有网站，用个人免费gmail发报价单，平时都在员工个人WhatsApp私聊接单，财务在单台电脑，晚上下班没人回"
    )

    result = finalize_diagnosis_from_wiki(session_id)
    assert "dms" in result
    assert "ars" in result
    assert "roi" in result

    # Immature setup must have low DMS and hard-locked ARS <= 10.0
    dms_score = result["dms"]["overall_score"]
    assert dms_score < 40.0
    assert result["ars"]["is_hard_locked"] is True
    assert result["ars"]["final_score"] <= 10.0

    # 财务模型只做纯函数算术；分母不完整时一律不给比率
    roi = result["roi"]
    pending = any(ph.get("pricing_pending") for ph in result["roadmap"])
    assert roi["total_benefits"] > 15000.0
    assert roi["vendor_annual_cost"] > 0.0
    if pending:
        assert roi["roi_percentage"] is None and roi["net_gain"] is None
        assert roi["cost_basis"] == "partial_quote"
    else:
        assert roi["roi_percentage"] > 0.0


def test_fastapi_diag_flow_endpoints(client):
    # 1. Start Session
    start_resp = client.post("/api/diag/start", json={
        "company_name": "API Test Motors Sdn Bhd",
        "industry": "汽配五金批发与进出口",
        "team_size": "6-20 人",
        "annual_turnover": "RM 2M - 10M"
    })
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert "session_id" in start_data
    assert "first_question" in start_data
    assert len(start_data["pills"]) > 0
    session_id = start_data["session_id"]

    # 2. Step 1: User provides partial answer
    step1_resp = client.post("/api/diag/step", json={
        "session_id": session_id,
        "user_answer": "没有网站，都是员工个人WhatsApp接单，单据手写在纸上。"
    })
    assert step1_resp.status_code == 200
    step1_data = step1_resp.json()
    assert step1_data["status"] == "CONTINUE"
    assert step1_data["completeness_score"] > 0
    assert step1_data["next_question"] is not None

    # 3. Check Live Wiki Tree
    wiki_resp = client.get(f"/api/diag/wiki/{session_id}")
    assert wiki_resp.status_code == 200
    wiki_data = wiki_resp.json()
    assert wiki_data["session_id"] == session_id
    assert len(wiki_data["dimensions"]) == 6

    # 4. Step 2: User completes remaining dimensions
    step2_resp = client.post("/api/diag/step", json={
        "session_id": session_id,
        "user_answer": "用个人免费gmail发信，核心账目在单台电脑没备份，晚上下班没人回客户，不打广告靠口碑。"
    })
    assert step2_resp.status_code == 200
    step2_data = step2_resp.json()
    assert step2_data["status"] in ("DIAGNOSIS_COMPLETE", "CONTINUE")
    assert step2_data.get("is_ready_for_scoring") is True or step2_data.get("allow_early_finalize") is True

    # 5. Finalize Diagnosis
    finalize_resp = client.post("/api/diag/finalize", json={"session_id": session_id})
    assert finalize_resp.status_code == 200
    final_data = finalize_resp.json()
    assert "dms" in final_data
    assert "ars" in final_data
    assert "cart" in final_data
    assert len(final_data["cart"]) > 0


def test_ars_scores_the_five_brief_named_factors():
    """简报 Step 3 点名的就是这五项：少任何一项都不算评估过。"""
    inp = SqlWikiEngine.get_full_assessment_input("test-unit-crud-101")
    factors = calculate_ars(inp, 80.0)["sub_scores"]
    assert set(factors) == {"data_availability", "process_maturity", "digital_workflow",
                            "employee_skills", "leadership"}
    assert all(isinstance(f["score"], (int, float)) and f["basis"] in ("verified_fact", "inferred_default")
               for f in factors.values())
    # 评分卡的五个因子卡直接吃这几个字段，少任何一个都是界面空洞
    assert all({"score", "weight", "note", "basis", "evidence_quote"} <= set(f) for f in factors.values())


# 真实一轮抓到的缺陷：问诊把答案存成规范档位，评分层却认不得那几档。
# 客户刚答完"各记各的账"，引擎掉进工具代理给了 85/100；答完"半成文流程"，
# 报告上写成"本轮没采到"。词表在这里只从题库推导一遍、不另抄一份——
# 以后谁加了新档位而引擎没接，这条就要红。
def test_every_answer_the_interview_can_store_is_scored_as_an_answer():
    from core.agentic_diagnostic import PROBE_FACT_KEYS, PROBE_VALUE_ALIASES

    problems = []
    for dim in ("leadership", "employee_skills", "process_maturity",
                "digital_workflow", "data_availability"):
        fact_key = PROBE_FACT_KEYS[dim]
        for canon in sorted(set(PROBE_VALUE_ALIASES[dim].values())):
            factor = calculate_ars({fact_key: canon, "_verified_facts": [fact_key]},
                                   58.0)["sub_scores"][dim]
            note = factor["note"]
            if factor["basis"] != "verified_fact":
                problems.append(f"{dim}={canon} 被判成 {factor['basis']}")
            if "not collected this time" in note or note.startswith("(proxy inference)"):
                problems.append(f"{dim}={canon} 的说明写着没采到: {note[:58]}")
    assert not problems, "问诊存下的档位评分层没接住: " + "; ".join(problems)


def test_a_canonical_value_survives_canonicalisation_unchanged():
    """规范值再过一遍 _canon_value 必须还是自己，否则一档会并掉进另一档。

    "semi" 曾经挂在 manual 的 token 表里，于是"部分在线、月底人工对一遍"这一档
    还没进引擎就被判成"全人工"，60 分变 25 分。
    """
    from core.agentic_diagnostic import PROBE_FACT_KEYS, PROBE_VALUE_ALIASES
    from core.sql_wiki_engine import _canon_value

    for dim, fact_key in PROBE_FACT_KEYS.items():
        for canon in sorted(set(PROBE_VALUE_ALIASES.get(dim, {}).values())):
            got = _canon_value(fact_key, canon, "")
            assert got == canon, f"{fact_key}: 规范值 {canon!r} 被重新归一成 {got!r}"


def test_an_answer_written_to_the_wiki_is_still_that_answer_when_it_is_scored():
    """上面两条查的是两端，缺陷偏偏在中间的缝里：has_sop 的 "partial" 是在
    get_full_assessment_input 里被 {"true,True/false,False}.get() 压成 None 的，
    于是客户明明答过，PDF 却写着"本轮没采到"。这条走完整条缝。

    dossier 故意不带 current_tools：一旦有工具，数据可用性就会掉进兜底代理，
    档位丢失反而被盖住。
    """
    from core.agentic_diagnostic import PROBE_FACT_KEYS, PROBE_VALUE_ALIASES

    session_id = "test-unit-canon-seam-404"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id, company_name="Canon Seam Sdn Bhd",
        industry="Auto Parts & Hardware Wholesale", team_size="6-20",
        annual_turnover="RM 500k - 2M")

    problems = []
    for dim in ("leadership", "employee_skills", "process_maturity",
                "digital_workflow", "data_availability"):
        fact_key = PROBE_FACT_KEYS[dim]
        for canon in sorted(set(PROBE_VALUE_ALIASES[dim].values())):
            SqlWikiEngine.record_stated_fact(session_id, dim, fact_key, canon, f"We answered {canon}")
            factor = calculate_ars(SqlWikiEngine.get_full_assessment_input(session_id),
                                   58.0)["sub_scores"][dim]
            if factor["basis"] != "verified_fact":
                problems.append(f"{dim}={canon} 走完整条缝后被判成 {factor['basis']}")
            elif "not collected this time" in factor["note"]:
                problems.append(f"{dim}={canon} 答过了还写着没采到")
    assert not problems, "; ".join(problems)


def test_step1_stated_tools_score_as_fallback_not_verified_fact():
    """Step 1 的"现在用什么工具"是客户原话：只当数据可用性的兜底输入，不冒充已锁证；
    认不出的工具宁可丢掉也不猜——那一项就保持未采集。"""
    assert _stated_tool_tokens("Accounting software only (SQL, AutoCount, an Excel ledger)") == ["sql", "excel"]
    assert _stated_tool_tokens("Several tools, but they do not talk to each other") == []
    # purpose / workshop 里含 pos、shop 子串，不能被判成 POS 系统或网店
    assert _stated_tool_tokens("Our purpose-built workshop for bearings") == []

    session_id = "test-unit-stated-tools-303"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id, company_name="Stated Tools Sdn Bhd",
        industry="Auto Parts & Hardware Wholesale", team_size="6-20",
        annual_turnover="RM 500k - 2M",
        current_tools="Accounting software only (SQL, AutoCount, an Excel ledger)")

    inp = SqlWikiEngine.get_full_assessment_input(session_id)
    assert "sql" in inp["current_tools"] and "excel" in inp["current_tools"]

    factor = calculate_ars(inp, 80.0)["sub_scores"]["data_availability"]
    assert factor["basis"] == "inferred_default"
    assert factor["score"] >= 60.0
