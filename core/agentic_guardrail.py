"""
Cradilot Core - 采购冲动门禁（聊天流专用）

职责只有一件：客户在还没跑通单据与数据的阶段就要求高价定制 AI 时，
让模型不迎合，而是把节奏拉回三阶段。

这个入口拿不到问诊会话，也没有跑过 DMS/ARS/ROI，所以这里不产生任何数字。
以前它按一张写死的"行业基准表"算出一个 ROI，再命令模型"引用上方确定性纯函数
的计算结果（年净赚 X，ROI Y%）"念给客户——那是把编造的常数包装成算术。
金额一律只在报告页出现，且逐项标注假设出处。

Workflow:
[User Input]
    │
    ▼
(Node 1: 行业归一) ──► (Node 2: 基底与冲动信号检测)
    │
    ├─► [基底未稳 + 采购冲动] ──► BRANCH_CORRECTION_AND_EDUCATION（暂缓推销）
    └─► [诉求与现状匹配]     ──► BRANCH_PHASED_ROADMAP（按三阶段规划）
"""

import re
from typing import Dict, Any
from core.industry_memory import get_industry_grounding

IMPULSE_PATTERNS = [
    r"大模型", r"顶级\s*ai", r"最高端", r"最高级", r"ai\s*销售", r"ai\s*客服",
    r"机器人", r"全自动谈单", r"花\s*[0-9两二2]\s*万", r"20000", r"25000", r"30000", r"定制系统"
]

IMMATURE_PATTERNS = [
    r"纸质", r"纸上", r"送货单", r"手工", r"个人手机", r"whatsapp", r"微信", r"单机", r"单机会计",
    r"没有系统", r"无系统", r"没系统", r"没有官网", r"无官网", r"没官网", r"免费邮箱", r"@gmail", r"@yahoo"
]

BRANCH_CORRECTION = "BRANCH_CORRECTION_AND_EDUCATION"
BRANCH_ROADMAP = "BRANCH_PHASED_ROADMAP"


class AgenticStateDecision:
    def __init__(self,
                 route: str,
                 grounding: Dict[str, Any],
                 immature_signals: Dict[str, bool],
                 rationale: str):
        self.route = route
        self.grounding = grounding
        self.immature_signals = immature_signals
        self.rationale = rationale
        self.impulse_detected = route == BRANCH_CORRECTION

    @property
    def is_hard_locked(self) -> bool:
        """兼容旧字段名：这里的"锁"只是聊天里不顺着推销，不改任何采购结论。"""
        return self.route == BRANCH_CORRECTION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "is_hard_locked": self.is_hard_locked,
            "impulse_detected": self.impulse_detected,
            "rationale": self.rationale,
            "grounding": self.grounding,
            "immature_signals": self.immature_signals,
        }


class AgenticGuardrailEngine:
    """按客户原话判断该不该暂缓推销。不做任何算术，因为这里没有可算的输入。"""

    @staticmethod
    def run_pipeline(user_input: str, company_name: str = "") -> AgenticStateDecision:
        grounding = get_industry_grounding(user_input)
        input_lower = str(user_input or "").lower()

        immature = [p for p in IMMATURE_PATTERNS if re.search(p, input_lower)]
        impulse = [p for p in IMPULSE_PATTERNS if re.search(p, input_lower)]
        signals = {"immature": bool(immature), "impulse": bool(impulse),
                   "immature_hits": immature, "impulse_hits": impulse}

        if immature and impulse:
            route = BRANCH_CORRECTION
            rationale = (
                "In what the customer described, the documents are still on paper, on one computer, or on a salesperson's personal phone. "
                "Buying an expensive custom AI at this stage means the model has no reliable data to read, and every quote it produces has to be checked by hand afterwards. "
                "The gate asks for Phase 1 and Phase 2 first (a company website, email on the company domain, a daily off-site backup, and the data tidied up), "
                "so the cash stays in day-to-day working capital and one failed AI purchase does not burn both the budget and the customer's confidence."
            )
        else:
            route = BRANCH_ROADMAP
            rationale = ("What the customer wants fits the current stage of their infrastructure, so plan it normally along the three-phase roadmap.")

        return AgenticStateDecision(route=route, grounding=grounding,
                                    immature_signals=signals, rationale=rationale)


def build_guarded_prompt_context(decision: AgenticStateDecision, user_input: str) -> str:
    """注入 Gemma 的事实锚点与门禁指令。"""
    g = decision.grounding
    industry = g["industry_name"] or "(industry not confirmed yet - start by asking what the company mainly sells, and to whom)"

    grounding_block = (
        f"[Company fact anchor - only catalogue wording matched to the customer's own words, no statistical inference]\n"
        f"- Industry: {industry}\n"
        f"- This chat entry has run no scoring and holds no quotation: DMS, ARS, ROI and the annual fee are all unknown.\n\n"
        f"[Answer constraints]\n"
        f"1. Do not state any amount, share, number of hours or industry statistic; a figure with no source must not be said at all.\n"
        f"2. When a figure is needed, send the customer back to the assessment report page - every number there carries its source, "
        f"and the assumptions behind the estimate can be edited there and recalculated on the spot.\n"
        f"3. Speak only about the order of the phases and the basis for each judgement; do not promise result figures.\n"
    )

    if decision.route == BRANCH_CORRECTION:
        gatekeeper_block = (
            f"[Gatekeeper instruction: hold the sale back]\n"
            f"Finding: {decision.rationale}\n"
            f"1. Do not echo the idea that buying the dearest AI will close deals by itself, and do not put the customer's idea down either.\n"
            f"2. Make the order clear: the documents and data have to reach a place a system can read first, or the AI has nothing to answer from.\n"
            f"3. Give one thing to do in Phase 1 and one in Phase 2, and how to check each one is done. Quote no prices."
        )
    else:
        gatekeeper_block = (
            f"[Gatekeeper instruction: plan as normal]\n"
            f"Finding: {decision.rationale}\n"
            f"Plan in this order: Phase 1 lays the foundation, Phase 2 hands the repetitive work to a system, Phase 3 covers customer acquisition and the AI-assisted step. "
            f"For each phase, say what is done and how to check it."
        )

    return f"{grounding_block}\n{gatekeeper_block}\n\nUser input:\n{user_input}"
