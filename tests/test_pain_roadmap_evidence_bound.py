"""
痛点与路线图证据驱动回归测试（阶段三去硬编码）。
锁死契约：痛点与路线图必须由已核验事实驱动——
数字化达标的企业必须得到空清单与"无待补强项"，
绝不允许回退到写死的 PP-01..PP-05 模板与固定三阶段计划。
金额同样只允许一个来源：ROI 假设 → calculate_roi → apply_loss_model。
"""

import json

from core.recommendation import (
    generate_pain_points,
    generate_action_roadmap,
    apply_loss_model,
    _unmet_dimensions,
    _LOSS_LABOR_DIMS,
    _LOSS_REVENUE_DIMS,
)

# 数字化已达标企业（六维 + 五要素全部达标）
HEALTHY = {
    "company_name": "Pinnacle Trading Sdn Bhd",
    "industry": "批发贸易与进出口分销",
    "team_size": "21-50 人",
    "annual_turnover": "RM 10M 以上",
    "web_engine_status": "standard",
    "has_domain": True,
    "has_ssl": True,
    "dr_backup_status": "managed_cloud",
    "cloud_storage_status": "enterprise_cloud",
    "has_offsite_backup": True,
    "backup_freq": "daily",
    "crm_system": "formal_crm",
    "is_crm_centralized": True,
    "uses_personal_whatsapp": False,
    "uses_personal_email": False,
    "email_type": "business_domain",
    "marketing_tracker": "pixel_and_ga4",
    "has_retargeting": True,
    "has_ai_agent": True,
    "ai_automation_status": "middleware",
    "has_sop": True,
    "order_reconcile_flow": "auto",
    "employee_skill_level": "high",
    "current_tools": ["crm", "sql", "website", "cloud", "enterprise_email"],
}

# 典型脆弱小微企业
VULNERABLE = {
    **HEALTHY,
    "company_name": "Klang Auto Parts Sdn Bhd",
    "industry": "汽配五金批发与进出口",
    "web_engine_status": "no_site",
    "has_domain": False,
    "has_ssl": False,
    "dr_backup_status": "no_backup",
    "cloud_storage_status": "single_pc",
    "has_offsite_backup": False,
    "backup_freq": "never",
    "crm_system": "personal_phone",
    "is_crm_centralized": False,
    "uses_personal_whatsapp": True,
    "uses_personal_email": True,
    "email_type": "free_gmail",
    "marketing_tracker": "none",
    "has_retargeting": False,
    "has_ai_agent": False,
    "ai_automation_status": "manual",
    "has_sop": False,
    "order_reconcile_flow": "manual",
    "employee_skill_level": "low",
    "current_tools": ["paper", "whatsapp"],
}

LEGACY_CANNED_TITLES = [
    "Too much manual work",
    "No CRM（客户资产私有化，离职即流失）",
    "Customer enquiries handled manually",
    "Marketing not measurable",
    "No internal knowledge management",
]


def test_healthy_company_gets_no_fabricated_pains():
    """去硬编码的核心证明：达标企业必须拿到空清单，而不是模板五件套。"""
    pains = generate_pain_points(HEALTHY, {"overall_score": 92.0, "dimensions": {}})
    assert pains == [], f"达标企业仍被套上模板痛点: {[p['title'] for p in pains]}"


def test_healthy_company_roadmap_reports_no_work():
    roadmap = generate_action_roadmap(HEALTHY, {"overall_score": 92.0})
    assert len(roadmap) == 3
    for phase in roadmap:
        assert any("Nothing needs fixing in this phase" in m for m in phase["modules"]), phase["modules"]
        assert float(phase["budget_myr"]) == 0.0
        assert phase["budget_lines"] == []


def test_vulnerable_company_pains_are_fact_scoped():
    pains = generate_pain_points(VULNERABLE, {"overall_score": 23.0, "dimensions": {}})
    dims = {p["dimension"] for p in pains}
    assert {"cloud", "crm", "ai"}.issubset(dims), dims
    for p in pains:
        assert p["id"].startswith("PP-")
        assert p["source"] in ("verified_fact", "wiki_evidence")
        assert p["evidence"], "痛点必须携带可溯源证据"
        assert not any(legacy in p["title"] for legacy in LEGACY_CANNED_TITLES)


def test_pain_rows_carry_no_amount_until_the_loss_model_runs():
    """金额只有一个来源：generate_pain_points 自己不许印出任何数字。"""
    pains = generate_pain_points(VULNERABLE, {"overall_score": 23.0, "dimensions": {}})
    assert pains, "脆弱画像应当有卡点"
    assert all(p["loss_myr"] is None for p in pains), \
        {p["dimension"]: p["loss_myr"] for p in pains if p["loss_myr"] is not None}

    roi = {"annual_labor_savings": 9655.36, "annual_salvaged_revenue": 13824.0}
    apply_loss_model(pains, roi)

    labor = [p for p in pains if p["dimension"] in _LOSS_LABOR_DIMS]
    revenue = [p for p in pains if p["dimension"] in _LOSS_REVENUE_DIMS]
    assert round(sum(p["loss_myr"] for p in labor), 2) == roi["annual_labor_savings"]
    assert round(sum(p["loss_myr"] for p in revenue), 2) == roi["annual_salvaged_revenue"]
    for p in pains:
        assert p["loss_basis"], "每个金额（或不给金额的决定）都要写明理由"
    # 备份与邮箱是风险敞口，折算成年度损失既无依据也易被客户反驳
    for p in pains:
        if p["dimension"] in ("cloud", "cyber", "employee_skills", "leadership"):
            assert p["loss_myr"] is None, p["dimension"]


def test_user_quote_is_cited_not_fabricated():
    """有原话就引用原话；没给原话时只陈述事实，不得伪造引语。"""
    quoted = generate_pain_points(
        VULNERABLE, {"overall_score": 23.0, "dimensions": {}},
        evidence_quotes={"cloud": "账都存前台那台电脑，没做过备份"})
    cloud_pain = next(p for p in quoted if p["dimension"] == "cloud")
    assert cloud_pain["quote"] == "账都存前台那台电脑，没做过备份"
    assert cloud_pain["evidence"].startswith("Customer's own words:")

    bare = generate_pain_points(VULNERABLE, {"overall_score": 23.0, "dimensions": {}})
    cloud_bare = next(p for p in bare if p["dimension"] == "cloud")
    assert cloud_bare["quote"] == ""
    assert cloud_bare["evidence"].startswith("Verified fact:")


def test_wiki_row_upgrades_copy_but_never_the_amount():
    """wiki 锁证的行可以改写严重度与方案，但金额只能由 apply_loss_model 给。"""
    wiki_pains = [{"title": "核心单据只在一台电脑上", "loss_myr": 30000.0,
                   "severity": "CRITICAL", "cradle_gap": "恢复没演练过", "solution": "Acronis",
                   "dimension": "cloud"}]
    pains = generate_pain_points(VULNERABLE, {"overall_score": 23.0, "dimensions": {}},
                                 wiki_pains=wiki_pains)
    cloud_pain = next(p for p in pains if p["dimension"] == "cloud")
    assert cloud_pain["source"] == "wiki_evidence"
    assert cloud_pain["severity"] == "CRITICAL"
    assert cloud_pain["loss_myr"] is None, "wiki 行不得自带金额"


def test_different_profiles_produce_different_outputs():
    """反模板守卫：两份不同事实必须产出不同痛点集合与不同路线图任务。"""
    semi = {**VULNERABLE, "dr_backup_status": "managed_cloud", "has_offsite_backup": True,
            "web_engine_status": "dormant", "has_domain": True}
    a = {p["dimension"] for p in generate_pain_points(VULNERABLE, {})}
    b = {p["dimension"] for p in generate_pain_points(semi, {})}
    assert a != b, "不同画像输出完全一致，说明仍是模板"
    assert "cloud" in a and "cloud" not in b

    ra = generate_action_roadmap(VULNERABLE, {"overall_score": 23.0})
    rb = generate_action_roadmap(semi, {"overall_score": 55.0})
    assert [t["task_id"] for t in ra[0]["tasks"]] != [t["task_id"] for t in rb[0]["tasks"]]


def test_hard_lock_blocks_phase_three_tasks():
    roadmap = generate_action_roadmap(VULNERABLE, {"overall_score": 23.0})
    phase3 = roadmap[2]
    assert phase3["hard_locked"] is True
    assert any("This phase waits for now" in m for m in phase3["modules"]), phase3["modules"]
    assert "budget stays on hold" in phase3["roi_milestone"]
    # Phase 3 的 AI 产品目录无公开价：只能记为待报价，不得编一个总额出来
    assert float(phase3["budget_myr"]) == 0.0
    assert phase3["pricing_pending"], phase3

    free = generate_action_roadmap({**VULNERABLE, "dr_backup_status": "managed_cloud"},
                                   {"overall_score": 62.0})
    assert free[2]["hard_locked"] is False


def test_roadmap_priced_from_the_real_catalogue():
    """阶段金额必须是目录里查得到的产品，RM 288/1,424 那批手写预算已全部废弃。"""
    roadmap = generate_action_roadmap(VULNERABLE, {"overall_score": 23.0})
    from core.product_catalog import catalog

    priced = [(l["sku"], l["annual_myr"]) for ph in roadmap for l in ph["budget_lines"]]
    assert priced, f"待补事实存在却没有任何报价行：{roadmap}"
    for sku, amount in priced:
        assert catalog.get(sku) is not None, sku
        assert amount and amount > 0

    phase1 = roadmap[0]
    assert float(phase1["budget_myr"]) == round(
        sum(l["annual_myr"] for l in phase1["budget_lines"] if l["annual_myr"]), 2)


def test_customer_copy_carries_no_internal_governance_jargon():
    roadmap = generate_action_roadmap(VULNERABLE, {"overall_score": 23.0})
    blob = json.dumps(roadmap, ensure_ascii=False)
    for jargon in ["Form A2", "MACC", "17A", "硬锁", "主权", "锁证", "止血", "verified_fact"]:
        assert jargon not in blob, f"客户版蓝图仍带内部话术: {jargon}"


def test_cart_and_roadmap_cannot_disagree_on_the_same_plan():
    """回归：采购车曾按痛点字符串另算一次，同一页出现两个总价——
    邮箱没被诊断为缺口也会因为 dms_score < 70 被塞进车里。"""
    from sales.lead_dispatcher import LeadDispatcher

    roadmap = generate_action_roadmap(VULNERABLE, {"overall_score": 23.0})
    cart = LeadDispatcher().cart_from_roadmap(roadmap)

    assert round(sum(p["budget_myr"] for p in roadmap), 2) == round(
        sum(i.promotional_price_myr for i in cart), 2)
    # 没问过备份台数，就不许按 headcount//3 猜出一笔 Acronis 总价
    acronis = [i for i in cart if i.sku == "DEMO-ACRONIS-WKS"]
    assert all(i.promotional_price_myr == 0.0 for i in acronis), [i.promotional_price_myr for i in acronis]
    assert any("billed on the actual number of devices" in i.notes for i in acronis), acronis


def test_sales_packet_reuses_the_report_cart(tmp_path):
    """顾问手里的清单必须就是客户眼前那份，否则电话里念的是另一个价钱。"""
    from sales.lead_dispatcher import LeadDispatcher

    roadmap = generate_action_roadmap(VULNERABLE, {"overall_score": 23.0})
    d = LeadDispatcher(storage_path=tmp_path / "leads.json")
    cart_rows = [
        {"sku": i.sku, "product_name": i.product_name, "billing_cycle": i.billing_cycle,
         "regular_price_myr": i.regular_price_myr, "promotional_price_myr": i.promotional_price_myr,
         "notes": i.notes}
        for i in d.cart_from_roadmap(roadmap)
    ]
    lead = d.create_lead(
        assessment_data={"metadata": {"company_name": "Uji Sdn Bhd"},
                         "dms": {"overall_score": 23.0}, "ars": {}, "roi": {},
                         "recommendation": {"primary_pain_points": []},
                         "cart": cart_rows},
        contact_info={"contact_name": "Tester", "contact_phone": "+60123456789",
                      "contact_email": "t@example.com"},
    )
    assert [c["sku"] for c in lead.cart_items] == [r["sku"] for r in cart_rows]


def test_conflict_guard_drops_pains_contradicted_by_verified_facts():
    """模型偶发把"细节不明"当痛点报金额；与达标事实矛盾时必须剔除并留痕。"""
    conflicts = []
    wiki_pains = [{"title": "CRM 系统细节不明", "root_cause": "未能确认使用范围",
                   "loss_myr": 25000.0, "severity": "HIGH", "cradle_gap": "",
                   "solution": "轻量 CRM", "dimension": "crm"}]
    pains = generate_pain_points(HEALTHY, {}, wiki_pains=wiki_pains,
                                 evidence_quotes={}, conflict_sink=conflicts)
    assert pains == [], f"达标企业仍被套上矛盾痛点: {[p['title'] for p in pains]}"
    assert len(conflicts) == 1
    assert conflicts[0]["dimension"] == "crm"
    assert "Conflicts with a verified fact" in conflicts[0]["reason"]

    # 同一痛点在事实确实不达标时必须保留（守卫不能变成吞掉真风险的开关）
    weak_conflicts = []
    weak_pains = generate_pain_points(VULNERABLE, {}, wiki_pains=wiki_pains,
                                       conflict_sink=weak_conflicts)
    assert any(p["dimension"] == "crm" for p in weak_pains)
    assert weak_conflicts == []


def test_ars_subscores_declare_provenance():
    """ARS 五项必须标明事实驱动还是缺省推断，并能回指用户原话。"""
    from core.ars_engine import calculate_ars

    # 只有增长目标、没有意愿探针事实时：leadership 必须是推断
    inferred = calculate_ars({**HEALTHY, "growth_objective": "接海外询盘",
                              "_verified_facts": [], "_evidence_quotes": {}}, 62.0)
    lead = inferred["sub_scores"]["leadership"]
    assert lead["basis"] == "inferred_default"
    assert "proxy inference" in lead["note"]

    # 有探针事实时：三档意愿必须真正影响分值，并标注为已核验 + 携带原话
    verified = calculate_ars({**HEALTHY, "leadership_willingness": "reluctant",
                              "data_availability_status": "unstructured",
                              "_verified_facts": ["leadership_willingness", "data_availability_status",
                                                  "has_sop", "order_reconcile_flow", "employee_skill_level"],
                              "_evidence_quotes": {"leadership_willingness": "老板觉得现在这样挺好"}}, 62.0)
    v_lead = verified["sub_scores"]["leadership"]
    assert v_lead["basis"] == "verified_fact"
    assert v_lead["score"] == 30.0
    assert v_lead["evidence_quote"] == "老板觉得现在这样挺好"
    assert verified["sub_scores"]["data_availability"]["score"] == 15.0
    assert v_lead["score"] < lead["score"], "保守推断与实测犹豫应当拉开差距"


def test_tls_inspection_fails_honestly():
    """证书核验失败时必须返回未核验与原因，绝不允许默认 True。"""
    from core.web_scraper import inspect_tls

    res = inspect_tls("127.0.0.1", port=1, timeout=1.0)
    assert res["ssl_valid"] is False
    assert res["cert_checked"] is False
    assert res["ssl_error"], "失败必须给出原因而非静默"

    empty = inspect_tls("")
    assert empty["ssl_valid"] is False and empty["ssl_error"]


def test_canon_value_handles_negation_phrases():
    """负面档必须优先匹配，否则 "no documented SOP" 会被 documented 命中判成达标。"""
    from core.sql_wiki_engine import _canon_value

    assert _canon_value("has_sop", "no documented SOP", "false") == "false"
    assert _canon_value("backup_strategy", "no cloud backup at all", "single_pc") == "single_pc"
    assert _canon_value("crm_status", "no CRM in use", "personal_whatsapp") == "personal_whatsapp"
    assert _canon_value("email_type", "no business email", "free_gmail") == "free_gmail"
    assert _canon_value("data_availability_status", "not structured yet", "") == "unstructured"
    assert _canon_value("leadership_willingness", "low enthusiasm, no budget", "") == "reluctant"
    assert _canon_value("marketing_tracker", "no tracking installed", "none") == "none"
    # 正向取值不能被否定档吃掉
    assert _canon_value("has_sop", "documented SOP with FAQ", "false") == "true"
    assert _canon_value("backup_strategy", "automated managed cloud snapshot", "single_pc") == "cloud_auto"
    assert _canon_value("crm_status", "centralized enterprise CRM", "personal_whatsapp") == "formal_crm"


def test_tls_details_are_parsed_not_silently_blank():
    """证书解析失败必须留痕，不得出现 ssl_valid=True 而明细静默为空。"""
    from core.web_scraper import inspect_tls

    res = inspect_tls("www.vendor.example", timeout=8.0)
    if res.get("ssl_valid"):
        assert res.get("cert_issuer"), "核验通过却没有颁发机构，说明明细解析被静默吞掉"
        assert res.get("cert_not_after")
        assert isinstance(res.get("cert_days_left"), int)
    else:
        assert res.get("ssl_error")


def test_unmet_dimensions_is_single_source_of_truth():
    unmet = _unmet_dimensions(VULNERABLE)
    pains = generate_pain_points(VULNERABLE, {})
    assert set(unmet).issuperset({p["dimension"] for p in pains if p["dimension"]})
    assert _unmet_dimensions(HEALTHY) == {}


def test_same_fact_not_double_counted_across_layers():
    """端到端复验发现的缺陷：wiki 痛点标题不含特征词时，同一事实被规则层与 wiki 层各计一次。"""
    wiki_pains = [
        {"title": "核心单据只在一台电脑上", "root_cause": "单机无异地快照",
         "loss_myr": 35000.0, "severity": "CRITICAL", "cradle_gap": "无容灾计划",
         "solution": "Acronis Cloud Backup（每日异地加密快照）",
         "dimension": "cloud"},
    ]
    pains = generate_pain_points(VULNERABLE, {}, wiki_pains=wiki_pains)
    cloud_entries = [p for p in pains if p["dimension"] == "cloud"]
    assert len(cloud_entries) == 1, f"同一 cloud 事实被计了 {len(cloud_entries)} 次"
    dims = [p["dimension"] for p in pains if p["dimension"]]
    assert len(dims) == len(set(dims)), f"同一维度出现重复条目: {dims}"


def test_legacy_wiki_pain_without_dimension_still_deduped_by_title():
    """旧库行没有维度归属时，仍须靠标题特征词去重，不能重复计损。"""
    wiki_pains = [{"title": "云端备份缺失风险", "root_cause": "无异地备份",
                   "loss_myr": 31000.0, "severity": "CRITICAL",
                   "cradle_gap": "", "solution": "Acronis"}]
    pains = generate_pain_points(VULNERABLE, {}, wiki_pains=wiki_pains)
    cloud_entries = [p for p in pains if p["dimension"] == "cloud"]
    assert len(cloud_entries) == 1
    assert cloud_entries[0]["source"] == "wiki_evidence"


def test_synonym_slot_values_do_not_create_phantom_pains():
    """模型把"已达标"写成 centralized_crm / managed_cloud 等同义词时，不得凭空判出缺陷。"""
    from core.sql_wiki_engine import _canon_value

    assert _canon_value("crm_status", "centralized_crm", "personal_whatsapp") == "formal_crm"
    assert _canon_value("backup_strategy", "Automated Cloud Backup", "single_pc") == "cloud_auto"
    assert _canon_value("has_sop", "documented SOP exists", "false") == "true"
    assert _canon_value("employee_skill_level", "Young team, eager to learn", "medium") == "high"
    assert _canon_value("crm_status", "personal whatsapp only", "personal_whatsapp") == "personal_whatsapp"

    # 归一后的取值喂给痛点引擎，必须不再产生对应维度痛点
    normalized = {**HEALTHY, "crm_system": "formal_crm", "dr_backup_status": "managed_cloud"}
    assert generate_pain_points(normalized, {}) == []


_VULNERABLE = VULNERABLE


def test_customer_pain_copy_is_plain_language():
    """痛点文案直接进客户屏幕与 PDF 第 2 页：不许出现治理黑话或无法核实的统计。"""
    pains = generate_pain_points(VULNERABLE, {"overall_score": 23.0, "dimensions": {}})
    blob = json.dumps(pains, ensure_ascii=False)
    for jargon in ["MACC", "17A", "PDPA", "主权", "飞单", "私单", "失血", "止血",
                   "硬锁", "锁证", "Form A2", "违背 Cradle"]:
        assert jargon not in blob, f"痛点文案仍带黑话: {jargon}"
    for invented in ["60%", "70%", "40%", "30%", "55%", "14 小时", "15 分钟", "30 分钟"]:
        assert invented not in blob, f"痛点文案出现未经贵司提供的统计: {invented}"
    for p in pains:
        # 客户文案已整体转英文：同一守卫反向成立——标题里不得再混入未翻译的中文内部话术
        assert not any("\u4e00" <= c <= "\u9fff" for c in p["title"]), p["title"]


def test_backend_customer_copy_carries_no_governance_jargon():
    """痛点、探针题库与开场问句会直接进屏幕和 PDF：黑话与编造的统计一律拦下。"""
    import json as _json
    from core.agentic_diagnostic import PROBE_TEMPLATES
    from core.recommendation import generate_pain_points

    blob = _json.dumps(PROBE_TEMPLATES, ensure_ascii=False)
    blob += _json.dumps(generate_pain_points(VULNERABLE, {}), ensure_ascii=False)
    for jargon in ["MACC", "17A", "PDPA", "反贪", "主权", "失血", "止血", "硬锁",
                   "锁证", "Form A2", "违背 Cradle"]:
        assert jargon not in blob, f"后端客户文案仍带黑话: {jargon}"
    # 这些百分比/小时数此前被当成行业统计念给客户，实际没有任何来源
    for invented in ["40%", "55%", "60%", "70%", "30% 以上", "14 小时", "15 分钟", "30 分钟 RTO"]:
        assert invented not in blob, f"后端文案出现无来源统计: {invented}"


def test_roi_note_names_what_is_assumed_instead_of_claiming_measurement():
    """ROI 说明必须按记录到的出处措辞：没问过的数字不能写成"贵司自填"。"""
    from core.roi_engine import calculate_roi, resolve_assumptions, SRC_FILLED

    derived = resolve_assumptions({"crm_system": "spreadsheet", "ai_tier": "individual_use"})
    res = calculate_roi(vendor_annual_cost=3618.38, assumptions=derived)
    note = res["benchmark_note"]
    assert "conservative assumptions taken by the system" in note
    assert "you entered yourself" not in note
    assert "=" in note and " x " in note, "算式必须与结论一起给出"

    filled = resolve_assumptions(
        {"crm_system": "personal_phone", "ai_tier": "none"},
        {"saved_hours_per_week": 6.0, "missed_orders_per_month": 9.0,
         "order_margin_myr": 200.0, "monthly_salary_myr": 4200.0})
    assert filled["sources"]["saved_hours_per_week"] == SRC_FILLED
    res2 = calculate_roi(vendor_annual_cost=3618.38, assumptions=filled)
    assert res2["saved_hours_per_week"] == 6.0
    assert res2["monthly_salary_base"] == 4200.0
    assert res2["average_order_gross_margin"] == 200.0
    assert "ones you entered yourself" in res2["benchmark_note"]


def test_unverified_gap_sizes_are_not_invented_as_a_fallback_number():
    """没问过的漏接单数不能取一个兜底常数：那是替客户编一个他会当成测量结果的数字。"""
    from core.roi_engine import (ORDERS_BY_AI_TIER, SRC_FILLED, SRC_NO_BASIS,
                                 calculate_roi, resolve_assumptions)

    res = resolve_assumptions({"crm_system": "", "ai_tier": "", "has_ai_agent": None})
    assert res["values"]["missed_orders_per_month"] == 0.0
    assert res["sources"]["missed_orders_per_month"] == SRC_NO_BASIS
    assert res["sources"]["saved_hours_per_week"] == SRC_NO_BASIS
    assert res["sources"]["monthly_salary_myr"] != SRC_FILLED

    # 收益侧没有任何依据时不给出比率，哪怕分母很小
    withheld = calculate_roi(vendor_annual_cost=1400.0, assumptions=res)
    assert withheld["roi_percentage"] is None
    assert withheld["cost_basis"] == "no_benefit_basis"
    assert withheld["total_benefits"] == 0

    # 答过"夜间没人接"才是有依据的最重档
    answered = resolve_assumptions({"crm_system": "personal_phone",
                                    "ai_tier": "", "has_ai_agent": False})
    assert answered["values"]["missed_orders_per_month"] == ORDERS_BY_AI_TIER["none"]
    assert answered["sources"]["missed_orders_per_month"] != SRC_FILLED


def test_industry_memory_exposes_no_invented_benchmarks():
    """行业表只剩目录里的名字：任何"行业平均"数字都必须重新找到出处才能回来。"""
    import json as _json
    from core.industry_memory import CATALOG

    blob = _json.dumps([{k: e[k] for k in ("val", "label", "sub")} for e in CATALOG],
                       ensure_ascii=False)
    for key in ["night_leakage_rate", "weekly_manual_reconcile_hours", "expected_roi_pct",
                "phase1_cost_myr", "avg_ticket_gross_margin_myr"]:
        assert key not in blob, key


def test_partial_quote_withholds_the_return_percentage():
    """分母缺了待报价项就不给比率：只按已报价那几条算出的 ROI 会大得离谱。"""
    from core.roi_engine import calculate_roi, resolve_assumptions

    a = resolve_assumptions({"crm_system": "personal_phone", "ai_tier": "none"})
    full = calculate_roi(vendor_annual_cost=3618.38, assumptions=a)
    partial = calculate_roi(vendor_annual_cost=540.0, assumptions=a, quote_pending=True)

    assert full["roi_percentage"] is not None
    assert partial["roi_percentage"] is None and partial["net_gain"] is None
    assert partial["cost_basis"] == "partial_quote"
    assert "no return on investment is given" in partial["benchmark_note"]
    # 绝对收益仍然给出，页面不留白
    assert partial["total_benefits"] == full["total_benefits"]


def test_salvage_factor_is_visible_in_the_note():
    """假设栏写"每月漏接 25 单"，说明里却是 20 单：换算系数必须出现在句子里。"""
    from core.roi_engine import SALVAGE_SHARE, calculate_roi, resolve_assumptions

    a = resolve_assumptions({}, {"saved_hours_per_week": 10, "missed_orders_per_month": 25,
                                 "order_margin_myr": 100, "monthly_salary_myr": 3000})
    note = calculate_roi(vendor_annual_cost=1000.0, assumptions=a)["benchmark_note"]
    assert f"{SALVAGE_SHARE:.0%}" in note
    assert "20 a month" in note
