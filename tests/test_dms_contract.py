"""
DMS 输入契约回归测试。

锁住三类曾经真实发生过、且肉眼看不出来的失效模式：
  1. 调用方与评分引擎用了不同词表，导致某维度对任何输入都给同一个分
  2. 子串匹配顺序错误，让更具体的取值被更宽泛的前缀抢先命中
  3. "本次没测到"被当成"贵司没有"而扣分
任何一条复发，评分卡会在表面上正常的情况下悄悄失真。
"""

import pytest

from core.dms_engine import calculate_dms, DIMENSION_WEIGHTS
from core.assessment_facts import normalize, apply_machine_findings, SRC_MACHINE


# ─── 1. 响应性：每一维都必须随输入走完一个区间 ────────────────────────────────
def _score_for(dim, raw):
    return calculate_dms(raw)["dimensions"][dim]["score"]


def test_cloud_responds_to_every_backup_tier():
    """回归：cloud 权重 20%，却曾因为只认 dr_backup_status 而在 /api/assess 路径上恒为 35。"""
    none = _score_for("cloud", {"backup_strategy": "single_pc"})
    usb = _score_for("cloud", {"backup_strategy": "manual_usb"})
    drive = _score_for("cloud", {"dr_backup_status": "cloud_drive"})
    managed = _score_for("cloud", {"backup_strategy": "cloud_auto"})
    assert none < usb < drive < managed
    assert managed - none >= 70


def test_manual_usb_is_not_swallowed_by_manual_prefix():
    """回归："manual" 曾抢先匹配 "manual_usb"，把有拷盘备份判成完全无备份。"""
    usb = _score_for("cloud", {"backup_strategy": "manual_usb"})
    none = _score_for("cloud", {"backup_strategy": "single_pc"})
    assert usb != none


def test_marketing_responds_to_tracker_alone():
    """回归：agentic 路径的 current_tools 永不含广告 token，marketing 曾恒为 30。"""
    none = _score_for("marketing", {"marketing_tracker": "none"})
    tracked = _score_for("marketing", {"marketing_tracker": "pixel_and_ga4"})
    assert tracked > none + 30


def test_crm_and_cyber_are_not_capped_below_tier_three():
    """回归：has_antivirus 无人赋值曾把 cybersecurity 封顶 45，
    使 DMS 理论最高只有 62.5，而第三档门槛 70 —— 任何企业都评不到"成熟标杆"。"""
    best = {
        "web_engine_status": "advanced", "has_domain": True, "has_ssl": True, "mobile_ok": True,
        "updates_current": True, "enquiry_capture": True, "backup_strategy": "cloud_auto",
        "has_versioning": True, "crm_system": "formal_crm", "is_crm_centralized": True,
        "has_followup_audit_trail": True, "marketing_tracker": "pixel_and_ga4",
        "has_retargeting": True, "current_tools": ["crm", "google ads", "ga4"],
        "email_type": "business_domain", "security_headers_ok": True, "dmarc_blocking": True,
        "endpoint_protection": True, "ai_automation_status": "middleware",
        "has_structured_data": True,
        # 攻击面只能机检：没跑过机检时它保持未核验，满分必须包含"确实测过且干净"
        "_machine_findings": [{"check": "exposed_services", "status": "pass"},
                              {"check": "known_vulnerabilities", "status": "pass"}],
    }
    result = calculate_dms(best)
    assert result["dimensions"]["cybersecurity"]["score"] == 100.0
    assert result["dimensions"]["cybersecurity"]["evidence_source"] == "Measured"
    assert result["overall_score"] >= 70.0
    assert "Optimized / leader" in result["tier"]


def test_open_attack_surface_lowers_cybersecurity_and_is_attributed_to_machine():
    base = {"web_engine_status": "modern", "has_domain": True, "has_ssl": True,
            "email_type": "business_domain", "security_headers_ok": True,
            "dmarc_blocking": True, "endpoint_protection": True}
    clean = dict(base, _machine_findings=[{"check": "exposed_services", "status": "pass"}])
    dirty = dict(base, _machine_findings=[{"check": "exposed_services", "status": "fail"}])
    cs_clean = calculate_dms(clean)["dimensions"]["cybersecurity"]
    cs_dirty = calculate_dms(dirty)["dimensions"]["cybersecurity"]
    assert cs_clean["score"] - cs_dirty["score"] == 15.0
    assert "Public attack surface not closed" in cs_dirty["details"]
    assert cs_dirty["evidence_source"] == "Measured"


def test_never_audited_attack_surface_stays_neutral_not_absent():
    """没做机检 ≠ 攻击面裸奔：既不能给分也不能扣分，并要写明未核验。"""
    result = calculate_dms({"web_engine_status": "modern", "has_domain": True,
                            "has_ssl": True, "email_type": "business_domain"})
    cyber = result["dimensions"]["cybersecurity"]
    assert "Attack surface not machine-checked" in cyber["details"]
    assert "could not be verified this time" in cyber["details"]
    assert cyber["evidence_source"] == "You stated"


def test_worst_case_is_well_below_best_case():
    worst = {"web_engine_status": "no_site", "has_domain": False, "has_ssl": False,
             "backup_strategy": "single_pc", "crm_system": "personal_phone",
             "marketing_tracker": "none", "current_tools": ["paper", "whatsapp"],
             "email_type": "free_gmail", "ai_automation_status": "manual"}
    assert _score_for("website", worst) <= 10
    assert calculate_dms(worst)["overall_score"] < 25


# ─── 2. 未核验不得扣分 ───────────────────────────────────────────────────────
def test_unknown_fields_never_score_as_absent():
    """证书没读到 ≠ 没有证书。三态在评分层必须保留到最后。"""
    only_known = calculate_dms({"web_engine_status": "modern", "has_domain": True})
    assert only_known["dimensions"]["website"]["score"] >= 70
    assert "could not be verified this time" in only_known["dimensions"]["website"]["details"]


def test_machine_fail_is_stricter_than_unknown():
    bad = calculate_dms({"web_engine_status": "modern", "has_domain": True,
                         "_machine_flags": {"has_ssl": False}})
    unknown = calculate_dms({"web_engine_status": "modern", "has_domain": True})
    assert bad["dimensions"]["website"]["score"] < unknown["dimensions"]["website"]["score"]


# ─── 3. 两条路径必须给出同一个分 ─────────────────────────────────────────────
def test_both_input_vocabularies_converge():
    """/api/assess 词表与 wiki 词表描述同一家公司时，分数必须一致。"""
    assess_style = {
        "web_engine_status": "standard", "has_domain": True, "has_ssl": True,
        "cloud_storage_status": "single_pc", "backup_freq": "never",
        "crm_system": "personal_phone", "marketing_tracker": "none",
        "email_type": "free_gmail", "ai_automation_status": "manual",
        "current_tools": ["paper", "whatsapp"],
    }
    wiki_style = {
        "web_engine_status": "standard", "has_domain": True, "has_ssl": True,
        "dr_backup_status": "no_backup", "crm_system": "personal_phone",
        "uses_personal_whatsapp": True, "marketing_tracker": "none",
        "uses_personal_email": True, "has_ai_agent": False,
        "current_tools": ["whatsapp", "paper"],
    }
    a = calculate_dms(assess_style)["overall_score"]
    b = calculate_dms(wiki_style)["overall_score"]
    assert a == b


# ─── 4. 机检证据覆盖自述 ─────────────────────────────────────────────────────
def test_normalize_is_idempotent_and_never_washes_out_facts():
    """二次归一化曾把整份已采集事实静默洗成"未知"——所有维度回到中性档。"""
    once = normalize({"web_engine_status": "modern", "has_domain": True,
                      "crm_system": "formal_crm", "backup_strategy": "cloud_auto"})
    twice = normalize(once)
    assert twice == once
    assert twice["crm"]["tier"] == "formal"
    assert twice["cloud"]["backup_tier"] == "managed_cloud"


def test_reachable_url_overrides_a_stated_no_website():
    """老板说"没有官网"，但他给的网址答了：不能让一句话把网站维度打成 5 分。"""
    stated_none = normalize({"web_engine_status": "no_site", "has_domain": False})
    assert calculate_dms(stated_none)["dimensions"]["website"]["score"] == 5.0

    facts = apply_machine_findings(stated_none, [
        {"check": "header_score", "status": "fail", "observed": "0/5 已配置"},
        {"check": "site_content", "status": "pass", "observed": "正文 47,000 字符"},
    ])
    result = calculate_dms({"_facts": facts})
    assert facts["web"]["has_website"] is True
    assert result["dimensions"]["website"]["score"] > 5.0
    assert result["evidence_provenance"]["web.has_website"] == SRC_MACHINE


def test_machine_findings_override_stated_and_record_provenance():
    facts = normalize({"web_engine_status": "modern", "has_domain": True, "has_ssl": True})
    apply_machine_findings(facts, [
        {"check": "certificate", "status": "fail", "observed": "已过期 30 天"},
        {"check": "mobile_viewport", "status": "pass", "observed": "已声明 viewport"},
    ])
    assert facts["web"]["ssl"] is False          # 机检说过期，老板说"有 https"不算数
    assert facts["web"]["mobile_ok"] is True
    assert facts["_provenance"]["web.ssl"] == SRC_MACHINE


def test_unverified_findings_are_never_applied():
    """unverified 一律不写入：否则一次断网就会永久压低评分。"""
    facts = normalize({"web_engine_status": "modern", "has_domain": True, "has_ssl": True})
    before = dict(facts["web"])
    apply_machine_findings(facts, [{"check": "certificate", "status": "unverified",
                                    "observed": "TLS 握手未完成"}])
    assert facts["web"] == before


def test_placeholder_answer_never_scores_as_a_negative_fact():
    """回归：采不到取值时证据层写占位值 "recorded" 锁证，该占位曾被读成"贵司没有 CRM"。"""
    placeholder = calculate_dms({
        "web_engine_status": "recorded", "backup_strategy": "recorded",
        "crm_system": "recorded", "marketing_tracker": "recorded",
        "email_type": "recorded", "ai_automation_status": "recorded",
    })
    blank = calculate_dms({})
    assert placeholder["dimensions"] == blank["dimensions"]
    assert placeholder["dimensions"]["crm"]["score"] == pytest.approx(51.5)
    assert placeholder["dimensions"]["cloud"]["score"] == 49.0
    assert "was not confirmed this time" in placeholder["dimensions"]["crm"]["details"]
    # 未作答不能被评为"最差企业"：那会让一次听不懂变成客户的分数
    assert placeholder["overall_score"] > 35.0


def test_explicit_negative_answer_still_scores_at_the_floor():
    """对照实验：明确答"没有"必须仍然按最差档计，中性档只留给"没答"。"""
    said_nothing = calculate_dms({"crm_system": "personal_phone",
                                  "backup_strategy": "single_pc",
                                  "marketing_tracker": "none"})
    assert said_nothing["dimensions"]["crm"]["score"] <= 20.0
    assert said_nothing["dimensions"]["cloud"]["score"] <= 18.0
    assert said_nothing["dimensions"]["marketing"]["score"] <= 25.0


def test_every_dimension_reports_evidence_source():
    result = calculate_dms({"web_engine_status": "modern", "has_domain": True})
    for name, meta in result["dimensions"].items():
        assert meta["evidence_source"] in ("Measured", "You stated", "Inferred"), name


def test_deep_crm_answers_cannot_promote_a_wrong_tier():
    """细节全答"最好"也不能把一家没有集中系统的公司抬进正式 CRM 的分段。"""
    base = calculate_dms({"crm_system": "personal_phone"})["dimensions"]["crm"]["score"]
    best = calculate_dms({
        "crm_system": "personal_phone", "followup_owner": "designated",
        "quote_to_order": "one_system", "pipeline_visible": "realtime",
        "lead_source_known": "tracked",
    })["dimensions"]["crm"]
    assert base <= 30.0
    assert best["score"] <= 30.0, f"越档提升：{best}"
    # 调整必须逐条点名，评委才看得懂分数怎么来的
    assert "Live deal pipeline on screen" in best["details"]


def test_deep_answers_absent_leave_the_base_tier_alone():
    stated = calculate_dms({"crm_system": "formal_crm"})["dimensions"]["crm"]["score"]
    with_depth = calculate_dms({"crm_system": "formal_crm",
                                "pipeline_visible": "realtime"})["dimensions"]["crm"]["score"]
    assert with_depth > stated
    assert stated == calculate_dms({"crm_system": "formal_crm",
                                    "pipeline_visible": "recorded"})["dimensions"]["crm"]["score"]


def test_steady_spend_without_attribution_costs_and_with_attribution_earns():
    blind = calculate_dms({"marketing_tracker": "none", "marketing_spend": "over_5k"})
    measured = calculate_dms({"marketing_tracker": "pixel_and_ga4",
                             "current_tools": ["ga4", "pixel"], "marketing_spend": "over_5k"})
    none_spend = calculate_dms({"marketing_tracker": "none", "marketing_spend": "none"})
    b = blind["dimensions"]["marketing"]["score"]
    m = measured["dimensions"]["marketing"]["score"]
    n = none_spend["dimensions"]["marketing"]["score"]
    assert "steady spend, but it cannot be tied to orders" in blind["dimensions"]["marketing"]["details"]
    assert b < n, f"每月花 RM5,000 却看不到来源，应比零投放更差：{b} vs {n}"
    assert m > b


def test_weights_still_sum_to_one():
    assert sum(DIMENSION_WEIGHTS.values()) == pytest.approx(1.0)
