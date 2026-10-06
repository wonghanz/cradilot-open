"""
Cradilot Core - AI Readiness Score (ARS) Engine
Evaluates 5 official elements: leadership, data availability, employee skills,
digital workflow, process maturity.
Enforces the Cradle baseline hard-lock threshold penalty factor mu(DMS).
"""

from typing import Dict, Any

ARS_WEIGHTS = {
    "data_availability": 0.25,
    "process_maturity": 0.20,
    "digital_workflow": 0.20,
    "employee_skills": 0.20,
    "leadership": 0.15
}

def calculate_mu_dms(dms_score: float) -> float:
    """
    Calculate the foundational hard lock penalty factor mu(DMS).
    If enterprise digital maturity is lower than 40, ARS is hard-locked to <= 10.
    """
    if dms_score < 40.0:
        return 0.10 # Hard lock: max ~10 points regardless of leadership enthusiasm
    elif dms_score < 70.0:
        return 0.50 + 0.50 * ((dms_score - 40.0) / 30.0)
    else:
        return 1.00

def calculate_ars(data: Dict[str, Any], dms_score: float) -> Dict[str, Any]:
    """
    Calculate raw and final ARS score with the hard lock penalty.
    每一项子分都会标注依据来源：verified_fact（用户答案已锁证）或
    inferred_default（该维度未采到事实，按保守代理推断），不得把推断冒充实测。
    """
    verified = set(data.get("_verified_facts") or [])
    quotes = data.get("_evidence_quotes") or {}

    def provenance(fact_keys):
        for k in fact_keys:
            if k in verified:
                return "verified_fact", (quotes.get(k) or "")
        return "inferred_default", ""

    # 1. Data Availability (25%): 优先消费探针实测的结构化状态
    tools = [t.lower() for t in data.get("current_tools", [])]
    data_avail = str(data.get("data_availability_status", "")).strip().lower()
    prov_data, quote_data = provenance(["data_availability_status"])
    if data_avail == "structured":
        score_data = 85.0
        data_note = "The core catalogue, customer and transaction data already sits in a structured source that systems can call."
    elif data_avail in ("spreadsheet", "siloed"):
        # 客户答的是"各记各的账"，绝不能掉进下面的工具代理拿 85 分：那等于他刚说完
        # 记录是碎的，系统就判定数据已经结构化了。
        score_data = 45.0
        data_note = "The accounts and customer lists are kept in separate spreadsheets and stand-alone ledgers. Some of it is digital, but nothing joins up, so the same customer exists in three places with three different figures."
    elif data_avail == "unstructured":
        score_data = 15.0
        data_note = "Business data is mostly on paper and in personal chat apps, so no system or model can read it directly."
    elif not tools:
        # 一项工具都没提到过 ≠ 有一套 ERP：旧版在这里给 85 分，等于用沉默换Ready
        prov_data, quote_data = "inferred_default", ""
        score_data = 50.0
        data_note = "How structured the business data is was not collected this time, so it is counted at a neutral value rather than scored as if it were ideal."
    else:
        prov_data, quote_data = "inferred_default", ""
        has_paper = "paper" in tools or "纸质" in str(tools) or "paper documents" in tools
        has_db = "sql" in tools or "crm" in tools or "erp" in tools

        if has_paper and not has_db:
            score_data = 15.0
            data_note = "Core business data lives on paper documents and in people's heads, with no structured database an API or a knowledge assistant could read."
        elif has_db and has_paper:
            score_data = 45.0
            data_note = "The main accounts are in stand-alone software, but delivery orders and customer chats are still typed up from paper by hand, so the records stay badly split."
        else:
            score_data = 85.0
            data_note = "The tools you listed include a structured system (accounting, ERP, POS or a CRM), so some core data already sits in software rather than only on paper. Whether the customer and order records all live in that same system was not verified."

    # 2. Process Maturity (20%): Standard SOPs, FAQ repository
    prov_proc, quote_proc = provenance(["has_sop"])
    sop = data.get("has_sop")
    if sop is None or sop == "":
        prov_proc, quote_proc = "inferred_default", ""
        score_process = 55.0
        process_note = "Whether written quoting and answering standards exist was not collected this time, so it is counted at a neutral value rather than deducted as missing."
    elif sop is True or str(sop).strip().lower() == "true":
        score_process = 80.0
        process_note = "Written sales answers and a common customer-question list (SOP) already exist, so the knowledge can be captured and put online quickly."
    elif str(sop).strip().lower() == "partial":
        # 写了半套既不是"有"也不是"没有"：旧版把它压成 None，于是客户答过的题在报告里
        # 变成"本轮没采到"，分数还正好撞在同一个 55 上，看不出丢了一手事实。
        score_process = 55.0
        process_note = "Some rules are written down but they stop short of covering the quoting and the common questions, so staff still have to ask the owner on the ones that matter most."
    else:
        score_process = 30.0
        process_note = "There is no written standard for how questions are answered (SOP), so the work depends on what long-serving staff happen to remember."

    # 3. Digital Workflow (20%): Online cross-department document flow
    order_flow = str(data.get("order_reconcile_flow", "") or "").strip().lower()
    prov_flow, quote_flow = provenance(["order_reconcile_flow"])
    if order_flow == "manual" or (not order_flow and float(data.get("manual_hours_per_week") or 0) > 10):
        score_workflow = 25.0
        workflow_note = "Documents between departments still move on paper for sign-off and are reconciled by hand, with no automation or shared online workflow in between."
    elif order_flow == "semi":
        score_workflow = 60.0
        workflow_note = "Some of it flows through online spreadsheets, but someone still re-checks and re-types the figures at month end, so format mistakes can slip in."
    elif order_flow in ("auto", "semi_auto") or "auto" in order_flow or "online" in order_flow:
        score_workflow = 85.0
        workflow_note = "Documents between departments are approved online and move through automatically in real time."
    else:
        prov_flow, quote_flow = "inferred_default", ""
        score_workflow = 55.0
        workflow_note = "How much of the document flow is online was not collected this time, so it is counted at a neutral value rather than credited as already automated."

    # 4. Employee Skills (20%): Willingness and ability to collaborate with AI
    emp_readiness = str(data.get("employee_skill_level") or "medium").lower()
    prov_skills, quote_skills = provenance(["employee_skill_level"])
    if emp_readiness == "low":
        score_skills = 30.0
        skills_note = "The team is used to the traditional manual way of working and instinctively resists digital and AI-assisted tools."
    elif emp_readiness == "high":
        score_skills = 85.0
        skills_note = "The team is open to trying new tools and keen to learn how to work alongside them."
    else:
        score_skills = 55.0
        skills_note = "Staff know something about the new tools, but there is no hands-on training or written procedure to follow."

    # 5. Leadership (15%): 优先采用 ARS 探针实测的管理层意愿三档
    leadership_will = str(data.get("leadership_willingness", "")).strip().lower()
    prov_lead, quote_lead = provenance(["leadership_willingness"])
    if leadership_will == "high":
        score_leadership = 90.0
        leadership_note = "Management has a clear budget and a real intent to cut cost and gain time, and is willing to spend on learning by trying, so there is least resistance."
    elif leadership_will == "conservative":
        score_leadership = 62.0
        leadership_note = "Management is watchful and cautious: it prefers a very low-cost pilot first and would spend more only once the cash return is visible."
    elif leadership_will == "reluctant":
        score_leadership = 30.0
        leadership_note = "Management doubts the value of digital change, the budget is tight and internal resistance is high, so a small proven result is needed to convince first."
    else:
        # 未采到意愿事实时才退回增长目标代理判断，并如实标注为推断
        prov_lead, quote_lead = "inferred_default", ""
        has_growth_goal = bool(data.get("growth_objective"))
        if has_growth_goal:
            score_leadership = 90.0
            leadership_note = "(proxy inference) A growth goal was recorded, so management is scored as willing to push this, but the intent itself has not been verified by a direct question."
        else:
            score_leadership = 50.0
            leadership_note = "(proxy inference) No fact about management intent was collected, so it is scored conservatively as a wait-and-see stance."

    raw_score = round(
        score_data * ARS_WEIGHTS["data_availability"] +
        score_process * ARS_WEIGHTS["process_maturity"] +
        score_workflow * ARS_WEIGHTS["digital_workflow"] +
        score_skills * ARS_WEIGHTS["employee_skills"] +
        score_leadership * ARS_WEIGHTS["leadership"],
        1
    )

    # Apply penalty factor mu(DMS)
    mu = calculate_mu_dms(dms_score)
    final_score = round(raw_score * mu, 1)
    is_hard_locked = (dms_score < 40.0)

    if is_hard_locked:
        lock_warning = (
            f"[Cradilot readiness floor lock]: the digital foundation (DMS) scored {dms_score}, below the safe baseline of 40, "
            f"so the hard lock applies (penalty factor μ = {mu}) and the raw score of {raw_score} is held down to {final_score}. "
            f"Do not let an outside vendor talk you into an expensive AI assistant before this is fixed: Phase 1 must first secure the company domain email and the cloud data backup foundation."
        )
    elif mu < 1.0:
        lock_warning = (
            f"The digital foundation (DMS) is in the transition band at {dms_score}, so AI readiness is still held back to a degree (penalty factor μ = {mu:.2f}). "
            f"The fuller AI scope is best unlocked after a light CRM is in shared use."
        )
    else:
        lock_warning = "The digital foundation is solid, so a 24/7 AI sales assistant and a company knowledge base (RAG) can be taken on in full."

    return {
        "raw_score": raw_score,
        "penalty_factor": mu,
        "final_score": final_score,
        "is_hard_locked": is_hard_locked,
        "lock_warning": lock_warning,
        "sub_scores": {
            "data_availability": {"score": score_data, "weight": 0.25, "note": data_note,
                                  "basis": prov_data, "evidence_quote": quote_data},
            "process_maturity": {"score": score_process, "weight": 0.20, "note": process_note,
                                 "basis": prov_proc, "evidence_quote": quote_proc},
            "digital_workflow": {"score": score_workflow, "weight": 0.20, "note": workflow_note,
                                 "basis": prov_flow, "evidence_quote": quote_flow},
            "employee_skills": {"score": score_skills, "weight": 0.20, "note": skills_note,
                                "basis": prov_skills, "evidence_quote": quote_skills},
            "leadership": {"score": score_leadership, "weight": 0.15, "note": leadership_note,
                           "basis": prov_lead, "evidence_quote": quote_lead}
        }
    }
