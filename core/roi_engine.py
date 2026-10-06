"""
Cradilot Core - Localized ROI Estimation Engine
马来西亚法定雇主成本口径 + 商业挽回模型。

投资额必须等于客户眼前看到的那份采购车合计，因此 vendor_annual_cost
由调用方从 cart 算出后传入；本模块不再自带任何"标准年费"常数。
"""

from typing import Dict, Any, Optional

DEFAULT_HOURLY_RATE = 22.00  # RM 22.00/hr（RM 3,500/月含 EPF·SOCSO ÷ 176 工时推算）
MIN_HOURLY_RATE = 15.0       # 保守下限，避免低薪岗位把节省额算得过低
EMPLOYER_OVERHEAD = 1.167    # EPF 13% + SOCSO + EIS 的雇主侧负担
STANDARD_MONTHLY_HOURS = 176.0

# ─── 测算假设：ROI 完全由这四个数字决定，所以它们必须单独摆出来 ──────────────
# 每周浪费几小时、每月漏几单，机检测不到，五步流程里客户也没填过。旧版把这些数字
# 写死在 finalize（18.0/8.0、14.0/3.0、RM3500、RM120），再由本模块以"已核验事实与
# 贵司自填工时"的名义念给客户——那是把假设伪装成测量，被懂行的评委一问就塌。
# 现在假设集中在此，逐项标注出处，报告页允许客户当场改写重算。
# 键同时覆盖归一化档位（none/spreadsheet/formal）、/api/assess 词表与问诊选项的原始取值，
# 否则同一家公司走不同路径会一个取到档位假设、一个退化成系统默认值。
HOURS_BY_CRM = {"personal_phone": 18.0, "personal_whatsapp": 18.0, "ad_hoc": 18.0,
                "none": 18.0, "spreadsheet": 8.0, "excel_ledger": 8.0,
                "formal": 2.0, "formal_crm": 2.0}
ORDERS_BY_AI_TIER = {"none": 14.0, "individual_use": 9.0, "workflow_pilot": 5.0, "deployed": 2.0}
MONTHLY_SALARY_DEFAULT = 3500.0
ORDER_MARGIN_DEFAULT = 120.0
# 漏接的询盘不是每单都会因为"立刻有人回"就成交，只有这一部分算得进收益。
SALVAGE_SHARE = 0.8
# 客户只报了客单价，毛利按报价的三成取——这是换算，不是测量，出处必须标成假设。
MARGIN_SHARE = 0.30

SRC_FILLED = "Entered by you in this session"
SRC_TIERED = "Conservative assumption from the situation you selected"
SRC_DEFAULT = "Conservative system default"
# 缺口规模类的数字必须有现状依据才能进收益：没问过就按 0 计，不替客户发明一个漏单数。
SRC_NO_BASIS = "Not collected this run, so not counted in the gain"
# 客户报的是客单价，毛利按报价的三成换算：数字来自贵司，换算系数来自我们。
SRC_CONVERTED = "Converted from the order value you entered"

ASSUMPTION_LABELS = {
    "saved_hours_per_week": "Hours a week spent keying data in and hunting for records",
    "missed_orders_per_month": "Enquiries missed after hours and at weekends each month",
    "order_margin_myr": "Average gross margin on one order",
    "monthly_salary_myr": "Monthly salary of the role doing this work",
}


def _provided(raw: Any) -> bool:
    """真 0 是诚实的回答（"这项我们不省/不赚"），只有 None 与空串才是没填。"""
    return not (raw is None or (isinstance(raw, str) and not raw.strip()))


def resolve_assumptions(facts: Dict[str, Any],
                        overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """凑齐 ROI 需要的数字，并说清每一个数字的出处。

    客户填过的一律优先（哪怕与档位假设不同——这是他的生意，不是我们的模型）；
    没填的按已核验的现状档位取保守值，并如实标为假设。
    """
    facts = facts or {}
    overrides = overrides or {}
    values: Dict[str, float] = {}
    sources: Dict[str, str] = {}

    def take(key: str, derived: float, is_derived_real: bool,
             no_basis: bool = False) -> None:
        raw = overrides.get(key)
        try:
            filled = float(raw) if _provided(raw) else None
        except (TypeError, ValueError):
            filled = None
        if filled is not None and filled >= 0:
            values[key] = round(filled, 2)
            sources[key] = SRC_FILLED
        elif no_basis:
            values[key] = 0.0
            sources[key] = SRC_NO_BASIS
        else:
            values[key] = round(derived, 2)
            sources[key] = SRC_TIERED if is_derived_real else SRC_DEFAULT

    crm = str(facts.get("crm_system") or "").strip().lower()
    take("saved_hours_per_week", HOURS_BY_CRM.get(crm, 0.0), crm in HOURS_BY_CRM,
         no_basis=crm not in HOURS_BY_CRM)

    ai_tier = str(facts.get("ai_tier") or "").strip().lower()
    answered = facts.get("has_ai_agent")
    if ai_tier in ORDERS_BY_AI_TIER:
        take("missed_orders_per_month", ORDERS_BY_AI_TIER[ai_tier], True)
    elif answered is False:
        # 答过"夜间没人接"，只是没选档位：按无承接档取，这有依据
        take("missed_orders_per_month", ORDERS_BY_AI_TIER["none"], True)
    elif answered is True:
        take("missed_orders_per_month", ORDERS_BY_AI_TIER["deployed"], False)
    else:
        take("missed_orders_per_month", 0.0, False, no_basis=True)

    take("order_margin_myr", ORDER_MARGIN_DEFAULT, False)
    take("monthly_salary_myr", MONTHLY_SALARY_DEFAULT, False)

    return {
        "values": values,
        "sources": sources,
        "labels": ASSUMPTION_LABELS,
        "salvage_share": SALVAGE_SHARE,
        "margin_share": MARGIN_SHARE,
        "hourly_rate_floor": MIN_HOURLY_RATE,
        "employer_overhead": EMPLOYER_OVERHEAD,
        "standard_monthly_hours": STANDARD_MONTHLY_HOURS,
    }


def assumptions_from_inputs(facts: Optional[Dict[str, Any]] = None,
                            hours_per_week: Optional[float] = None,
                            monthly_salary_myr: Optional[float] = None,
                            missed_orders_per_month: Optional[float] = None,
                            avg_order_value_myr: Optional[float] = None,
                            margin: Optional[float] = None) -> Dict[str, Any]:
    """表单里真填过的数字走自填出处，没填的仍由 resolve_assumptions 兜底并标注。

    这里不再自己拼 values/sources：否则"入参缺失"会被写成"贵司当场填报"，
    同一份报告里就会出现两个互相矛盾的假设来源。
    """
    overrides: Dict[str, Any] = {}
    for key, raw in (("saved_hours_per_week", hours_per_week),
                     ("monthly_salary_myr", monthly_salary_myr),
                     ("missed_orders_per_month", missed_orders_per_month)):
        if _provided(raw):
            overrides[key] = float(raw)

    converted_margin = False
    if _provided(margin):
        overrides["order_margin_myr"] = float(margin)
    elif _provided(avg_order_value_myr):
        overrides["order_margin_myr"] = round(float(avg_order_value_myr) * MARGIN_SHARE, 2)
        converted_margin = True

    resolved = resolve_assumptions(facts or {}, overrides)
    if converted_margin:
        resolved["sources"]["order_margin_myr"] = SRC_CONVERTED
    return resolved



def calculate_roi(
    saved_hours_per_week: float = 15.0,
    monthly_salary_base: float = 3000.0,
    night_orders_salvaged_per_month: float = 9.6,
    average_order_gross_margin: float = 120.0,
    vendor_annual_cost: float = 0.0,
    priced_line_count: Optional[int] = None,
    assumptions: Optional[Dict[str, Any]] = None,
    quote_pending: bool = False
) -> Dict[str, Any]:
    """
    计算 ROI 明细。输入必须来自已核验事实或用户自填值，本函数只做算术，不做假设。

    传入 assumptions（resolve_assumptions 的返回值）时，四个输入数字与它们的出处
    全部取自该结构，本函数不再自己编任何常数。

    net_gain / roi_percentage 在为 None 时表示"报价未定，无从计算"，
    调用方须按 None 处理（显示破折号或"待报价"），不得回退成 0 或任何默认值。
    """
    if assumptions:
        vals = assumptions.get("values") or {}
        saved_hours_per_week = float(vals.get("saved_hours_per_week", saved_hours_per_week))
        monthly_salary_base = float(vals.get("monthly_salary_myr", monthly_salary_base))
        average_order_gross_margin = float(
            vals.get("order_margin_myr", average_order_gross_margin))
        night_orders_salvaged_per_month = round(
            float(vals.get("missed_orders_per_month", night_orders_salvaged_per_month))
            * float(assumptions.get("salvage_share", SALVAGE_SHARE)), 4)
        sources = assumptions.get("sources") or {}
    else:
        assumptions = {}
        sources = {}

    total_monthly_labor_cost = float(monthly_salary_base) * EMPLOYER_OVERHEAD
    calculated_hourly_rate = round(total_monthly_labor_cost / STANDARD_MONTHLY_HOURS, 2)
    effective_hourly_rate = max(MIN_HOURLY_RATE, calculated_hourly_rate)

    annual_hours_saved = round(float(saved_hours_per_week) * 52.0, 2)
    annual_labor_savings = round(annual_hours_saved * effective_hourly_rate, 2)

    annual_salvaged_revenue = round(
        float(night_orders_salvaged_per_month) * float(average_order_gross_margin) * 12.0, 2
    )

    total_benefits = round(annual_labor_savings + annual_salvaged_revenue, 2)
    cost = round(float(vendor_annual_cost or 0.0), 2)

    if total_benefits <= 0:
        # 收益侧没有任何依据：此时哪怕分母只有几百块，算出来的比率也是凭空立起来的
        net_gain = None
        roi_percentage = None
        cost_basis = "no_benefit_basis"
        benchmark_note = (
            "Nothing was collected this time that could support a benefit estimate (neither the weekly hours nor the missed enquiries have a basis), "
            "so no return on investment is given. Complete the step 3 interview, or enter your own figures in the assumptions below, and this will recalculate."
        )
    elif cost > 0 and not quote_pending:
        net_gain = round(total_benefits - cost, 2)
        roi_percentage = round((net_gain / cost) * 100.0, 1)
        cost_basis = "actual_cart"
        benchmark_note = _benefit_note(
            saved_hours_per_week, effective_hourly_rate, annual_labor_savings,
            night_orders_salvaged_per_month, average_order_gross_margin,
            annual_salvaged_revenue, total_benefits, cost, net_gain,
            roi_percentage, sources)
    elif cost > 0:
        # 分母不完整时不给比率：AI 客服与按台计价的备份还没报价，
        # 只按已报价的那几条算出来的百分比会大得离谱，反而砸掉整份报告的可信度。
        net_gain = None
        roi_percentage = None
        cost_basis = "partial_quote"
        benchmark_note = _benefit_note(
            saved_hours_per_week, effective_hourly_rate, annual_labor_savings,
            night_orders_salvaged_per_month, average_order_gross_margin,
            annual_salvaged_revenue, total_benefits, cost, None, None, sources)
    else:
        # 采购车里没有任何一条公开价产品时 ROI 无从计算。留空，
        # 绝不回退到旧版写死的 RM 5,550.68 去算出一个与实际报价无关的百分比。
        net_gain = None
        roi_percentage = None
        cost_basis = "no_priced_cart_items"
        benchmark_note = (
            "The quoted part of this plan still has to be priced by an account manager against your actual seat count and AI modules; "
            "until then no return on investment is stated up front, so the figure cannot end up disagreeing with the real quotation."
        )

    return {
        "monthly_salary_base": monthly_salary_base,
        "employer_overhead_factor": EMPLOYER_OVERHEAD,
        "effective_hourly_rate": effective_hourly_rate,
        "saved_hours_per_week": saved_hours_per_week,
        "annual_hours_saved": annual_hours_saved,
        "annual_labor_savings": annual_labor_savings,
        "night_orders_salvaged_per_month": night_orders_salvaged_per_month,
        "average_order_gross_margin": average_order_gross_margin,
        "annual_salvaged_revenue": annual_salvaged_revenue,
        "total_benefits": total_benefits,
        "vendor_annual_cost": cost,
        "cost_basis": cost_basis,
        "priced_line_count": priced_line_count,
        "net_annual_benefit_myr": net_gain,
        "net_gain": net_gain,
        "roi_percentage": roi_percentage,
        "assumptions": assumptions,
        "benchmark_note": benchmark_note
    }


def _benefit_note(hours: float, rate: float, labor: float, orders: float, margin: float,
                  revenue: float, benefits: float, cost: float, net, pct,
                  sources: Dict[str, str]) -> str:
    """把算式与每个数字的出处一起写清楚。

    假设就是假设：旧版把系统取的档位值说成"贵司自填"，客户当场就能指出他没填过，
    整份报告的可信度随之作废，所以这里只按实际记录到的出处措辞。
    """
    assumed = [ASSUMPTION_LABELS[k] for k in ASSUMPTION_LABELS
               if sources.get(k) in (SRC_TIERED, SRC_DEFAULT)]
    no_basis = [ASSUMPTION_LABELS[k] for k in ASSUMPTION_LABELS
                if sources.get(k) == SRC_NO_BASIS]
    converted = [ASSUMPTION_LABELS[k] for k in ASSUMPTION_LABELS
                 if sources.get(k) == SRC_CONVERTED]
    parts = []
    if assumed:
        parts.append("conservative assumptions taken by the system: " + ", ".join(assumed))
    if no_basis:
        parts.append("not collected this time, so counted as no benefit at all: " + ", ".join(no_basis))
    if converted:
        parts.append(f"converted from the average order value you entered, at {MARGIN_SHARE:.0%}: " + ", ".join(converted))
    origin = ("All four figures are ones you entered yourself" if not parts
              else "Of the figures behind this estimate, " + "; ".join(parts))
    head = (
        f"Time saved: {hours:g} hours a week x {rate:.2f} per hour x 52 weeks = RM {labor:,.2f}; "
        f"enquiries recovered: {orders:g} a month (counted as recoverable at {SALVAGE_SHARE:.0%} of the missed ones) "
        f"x RM {margin:,.2f} margin x 12 months = RM {revenue:,.2f}. "
        f"Total annual benefit RM {benefits:,.2f}, annual cost of the priced part RM {cost:,.2f}. "
    )
    if net is None:
        return head + ("Some items in this plan still have no catalogue price (see the price-on-request items below), so the denominator is incomplete "
                       "and no return on investment is given - a ratio from only the priced lines would be far too high. "
                       f"Once the quotation is complete this can be recalculated. {origin}. "
                       "Edit the assumptions on the page to recalculate.")
    return head + (f"Net benefit RM {net:,.2f} (return on investment {pct}%). {origin}. "
                   "Edit the assumptions on the page for an instant recalculation - these figures depend on how your business actually runs, not on industry averages.")


# ─── 展示层格式化：数字缺失时必须说"待报价"，不能印成 RM 0.00 或让 f-string 崩掉 ─────
# 这些字符串会被拼进给 LLM 的提示词与销售话术，最终念到客户耳朵里。

UNPRICED_LABEL = "Quote on request from our catalogue (depends on your actual seat count)"


def fmt_myr(value: Any, digits: int = 2) -> str:
    """金额：None 或 0 视为"无可靠数字"。

    负值必须照常输出——净收益为负是本系统有意给出的结论之一
    （DMS 过低时它会拒绝推销），把它印成"待报价"等于藏掉不利于成交的事实。
    """
    if value is None or value == "":
        return UNPRICED_LABEL
    try:
        v = float(value)
    except (TypeError, ValueError):
        return UNPRICED_LABEL
    if v == 0:
        return UNPRICED_LABEL
    return f"RM {v:,.{digits}f}"


def fmt_pct(value: Any, digits: int = 1) -> str:
    """百分比：None 显示待定；0 与负值如实显示（负回报也是结论）。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "to be confirmed"
    return f"{v:.{digits}f}%"
