"""
Cradilot Core - AI 采用度推断 (AI Adoption Inference)

为什么不直接问
──────────────
官方六维里 AI Adoption 必须给分，但老板对"我们用不用 AI"的自我报告最不可靠：
会把"偶尔问 ChatGPT 写文案"说成"已部署 AI"，也会因为听不懂问题而答"没有"。
所以这一维以推断为主、自述为辅，并且评分卡必须标注"推断"及其依据。

推断的边界（很重要）
────────────────────
能推断的是**承接条件是否成立**，不是"他用了什么模型"。
依据是客观前提：有没有可自动 intake 的数字触点、有没有结构化数据可喂、
所在行业是否对响应速度敏感。反过来，绝不能因为"有官网"就推断"已部署 AI"——
那是把可能性写成事实，正是本项目要消灭的那类错误。

因此规则是保守的：只在证据足以排除其它可能时才给出档位，否则保持 unknown
（评分层据此走中性档，不按缺失扣分）。
"""

from typing import Any, Dict, List

# 说明：这里刻意不引入"该行业是否需要 24 小时响应"之类的先验。
# data/industry_catalog.json 并不带这个字段，硬编一个进来等于把推断的输入本身编造出来，
# 而这一维最终会以"依据"的形式写给客户看。只用观测得到的触点、CRM 与数据结构三项。


def infer_ai_tier(facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    输入 normalize() 的输出，推断 ai 档位。

    返回 {"tier", "confidence", "basis": [...], "service_gap"}
    tier 为 None 表示证据不足，交给评分层的中性档。
    """
    web = facts.get("web", {}) or {}
    crm = facts.get("crm", {}) or {}
    ai = facts.get("ai", {}) or {}
    prov = facts.get("_provenance", {}) or {}

    # 触点存在性优先看机检：老板说"有表单"与探针看到表单，可信度差一个量级
    form_measured = "web.enquiry_capture" in prov
    has_intake = web.get("enquiry_capture")
    structured = ai.get("structured_data")
    crm_tier = crm.get("tier")

    basis: List[str] = []
    if has_intake is False:
        basis.append("No automatic enquiry intake was seen on the website")
    if crm_tier in (None, "none", "unknown"):
        basis.append("Customer records are not kept in one central system")
    if structured is False:
        basis.append("There is no readable structured business data")

    # ── 排除式推断：只有在其余档位都不成立时才给结论 ──
    if has_intake is False and crm_tier in (None, "none", "unknown") and structured is False:
        # 没有任何可自动承接的入口，也没有结构化数据 → 谈不上"已接入工作流"
        return {"tier": "none", "confidence": 0.72, "basis": basis,
                "service_gap": "First build an intake channel that answers on its own and get the data into a "
                               "structured form; only then does AI have something to attach to"}

    if has_intake and structured and crm_tier in ("spreadsheet", "formal"):
        ready = ("An online intake channel was measured, with customer records and business data both centralised"
                 if form_measured else
                 "Online intake, centralised records and structured data are all present")
        return {"tier": "individual_use", "confidence": 0.6,
                "basis": [ready, "but whether an AI step already exists was not confirmed in this run"],
                "service_gap": "The conditions are already in place; what is missing is turning the repeated "
                               "Q&A and document handling into a workflow"}

    return {"tier": None, "confidence": 0.0,
            "basis": basis or ["The evidence we have is not enough to infer the level of AI adoption"],
            "service_gap": ""}


def explain(facts: Dict[str, Any], inferred: Dict[str, Any]) -> str:
    """给评分卡/蓝图的一行白话依据。绝不写成"已部署"这种断言。"""
    tier = inferred.get("tier")
    if not tier:
        return "AI adoption was not confirmed directly in this run, so it is scored neutrally and is not used as a deduction."
    why = "; ".join(inferred.get("basis") or [])
    label = {"none": "no automated intake yet", "individual_use": "individual, ad-hoc use",
             "workflow_pilot": "pilot in one place", "deployed": "wired into business processes"}.get(tier, tier)
    return f"AI adoption is an inference ({label}, confidence {inferred.get('confidence')}): {why}."
