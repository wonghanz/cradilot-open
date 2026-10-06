"""
AI 采用度推断的边界测试。

这一维最容易被做成"看着像推理、其实是编造"：给一个有官网的客户写"已部署 AI"，
或者把"没问过"当成"没有"。锁死四件事：
  1. 有直接回答时绝不推断
  2. 证据不足以排除其它可能时保持 unknown（走中性档，不扣分）
  3. 推断永远不许得出"已部署"这种只有实测/自述才能支持的结论
  4. 推断结果必须在评分卡上标成"推断"并带出依据
"""

import pytest

from core.ai_inference import infer_ai_tier, explain
from core.assessment_facts import normalize, SRC_INFERRED
from core.dms_engine import calculate_dms


def _ai(raw):
    return calculate_dms(raw)["dimensions"]["ai_adoption"]


def test_direct_answer_is_never_overridden_by_inference():
    facts = normalize({"ai_automation_status": "middleware"})
    assert facts["ai"]["tier"] == "deployed"
    assert "inferred" not in facts["ai"]
    assert _ai({"ai_automation_status": "middleware"})["evidence_source"] == "You stated"


def test_blank_interview_stays_unknown_instead_of_guessed():
    """什么都没采到时不得给"没有 AI"——那等于把没问出来写成客户的缺失。"""
    facts = normalize({})
    assert facts["ai"]["tier"] == "unknown"
    assert "ai.tier" not in facts["_provenance"]
    assert _ai({})["score"] == 30.0


def test_no_intake_no_crm_no_data_infers_none_with_basis():
    raw = {"web_engine_status": "outdated", "enquiry_capture": False,
           "crm_system": "personal_phone", "data_availability_status": "unstructured"}
    facts = normalize(raw)
    assert facts["ai"]["tier"] == "none"
    assert facts["_provenance"]["ai.tier"] == SRC_INFERRED
    dim = _ai(raw)
    assert dim["evidence_source"] == "Inferred"
    assert "AI adoption is an inference" in dim["details"]
    assert len(facts["ai"]["inferred"]["basis"]) >= 2


def test_prerequisites_present_infers_at_most_individual_use():
    raw = {"web_engine_status": "modern", "enquiry_capture": True,
           "crm_system": "formal_crm", "has_structured_data": True}
    facts = normalize(raw)
    assert facts["ai"]["tier"] == "individual_use"
    # 关键：前提齐备 ≠ 已部署。绝不能从"有工具"推出"用了 AI"
    assert facts["ai"]["tier"] != "deployed"
    assert "was not confirmed in this run" in "；".join(facts["ai"]["inferred"]["basis"])


def test_inference_never_produces_deployed_or_pilot():
    """任何输入组合都不该推断出需要直接证据才能成立的高档位。"""
    for enquiry in (True, False, None):
        for crm in ("formal_crm", "spreadsheet", "personal_phone", ""):
            for data in ("structured", "spreadsheet", "unstructured", ""):
                raw = {"web_engine_status": "modern", "enquiry_capture": enquiry,
                       "crm_system": crm, "data_availability_status": data}
                tier = infer_ai_tier(normalize(raw))["tier"]
                assert tier in (None, "none", "individual_use"), (raw, tier)


def test_explain_marks_confidence_and_never_asserts_deployment():
    facts = normalize({"web_engine_status": "outdated", "enquiry_capture": False,
                       "crm_system": "personal_phone", "data_availability_status": "unstructured"})
    text = explain(facts, facts["ai"]["inferred"])
    assert "confidence" in text and "inference" in text
    assert "deployed" not in text


def test_machine_evidence_outranks_inference_for_other_fields():
    """机检存在时来源标签必须是实测；只有整组都无实证时才允许出现"推断"。"""
    raw = {"web_engine_status": "modern", "has_domain": True, "enquiry_capture": False,
           "crm_system": "personal_phone", "data_availability_status": "unstructured",
           "_machine_findings": [{"check": "mobile_viewport", "status": "pass"}]}
    result = calculate_dms(raw)
    assert result["dimensions"]["website"]["evidence_source"] == "Measured"
    assert result["dimensions"]["ai_adoption"]["evidence_source"] == "Inferred"
