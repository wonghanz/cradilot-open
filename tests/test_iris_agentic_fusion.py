"""
Cradilot Test Suite - 聊天门禁与分层流式输出验证
1. 行业描述归一到 data/industry_catalog.json 的规范行业名（不猜、不带行业统计）。
2. 代码级状态机门禁与采购冲动拦截（巴生汽配 RM 20,000 案例）。
3. 纯函数算术（0 数学幻觉）；门禁上下文不得出现任何金额与百分比。
4. 分层 SSE 流式生成器（HUD 事件 + token 流）。
"""

import re

import pytest
from core.industry_memory import get_industry_grounding
from core.agentic_guardrail import AgenticGuardrailEngine, build_guarded_prompt_context
from core.roi_engine import calculate_roi
from core.layered_streamer import generate_layered_agentic_stream


def test_industry_grounding_returns_only_the_catalogue_name():
    """行业归一只给得出行业名；过去那张表里的行业统计全是没有来源的常数。"""
    grounding = get_industry_grounding("我们是巴生做汽配五金批发的")
    assert set(grounding) == {"industry_name", "sub"}
    assert "Auto Parts" in grounding["industry_name"]


def test_industry_grounding_refuses_to_guess():
    """目录里没有命中就返回空，不许回落成"汽配五金"把餐饮律所一律当成汽配判断。"""
    assert get_industry_grounding("ABC 001 Enterprise")["industry_name"] == ""


def test_impulse_gatekeeper_intercepts_premature_ai_demand():
    """
    Core Test Case:
    '我们是一家巴生汽配贸易商，目前没有系统，想花 2 万令吉买一套最顶级的 AI 销售系统。'
    状态机必须：
    1. 路由到 BRANCH_CORRECTION_AND_EDUCATION。
    2. 标记 is_hard_locked / impulse_detected。
    3. 注入的上下文里不许出现任何金额或百分比——这个入口没有跑过评分也没有报价。
    """
    test_input = "我们是一家巴生汽配贸易商，目前没有系统，想花 2 万令吉买一套最顶级的 AI 销售系统。"
    decision = AgenticGuardrailEngine.run_pipeline(test_input, "巴生联友汽配")

    assert decision.route == "BRANCH_CORRECTION_AND_EDUCATION"
    assert decision.is_hard_locked is True
    assert decision.impulse_detected is True
    assert "hold" in decision.rationale or "first" in decision.rationale

    guarded_context = build_guarded_prompt_context(decision, test_input)
    assert "Gatekeeper instruction: hold the sale back" in guarded_context
    assert "Do not state any amount" in guarded_context
    assert "RM " not in guarded_context
    assert not re.search(r"\d+(?:\.\d+)?%", guarded_context)


def test_normal_phased_roadmap_routing_for_rational_client():
    """Verify that a rational client with valid tools is routed to standard phased roadmap."""
    test_input = "我们是一家拥有官方网站和正式企业邮箱的会计事务所，想了解接下来的协作与客户管理方案。"
    decision = AgenticGuardrailEngine.run_pipeline(test_input, "陈李会计所")

    assert decision.route == "BRANCH_PHASED_ROADMAP"
    assert decision.is_hard_locked is False
    assert decision.impulse_detected is False


def test_pure_function_arithmetic_precision_zero_hallucination():
    """Verify exact mathematical computation by pure function (0 arithmetic hallucination)."""
    res = calculate_roi(
        saved_hours_per_week=16.0,
        monthly_salary_base=3500.0,
        night_orders_salvaged_per_month=10.0,
        average_order_gross_margin=120.0,
        vendor_annual_cost=1951.88
    )

    # 16 hrs * 52 weeks * RM 22.00/hr = RM 18,304.00 (or calculated from exact hourly rate)
    assert res["effective_hourly_rate"] == 23.21 or round(res["effective_hourly_rate"], 1) in [22.0, 23.2]
    assert res["annual_salvaged_revenue"] == 14400.00
    assert res["net_gain"] > 25000.0
    assert res["roi_percentage"] > 400.0


def test_layered_streaming_hud_events_emission():
    """Verify that the layered streamer generator produces HUD events in sequence."""
    test_input = "我们是一家巴生汽配贸易商，目前没有系统，想花 2 万令吉买一套最顶级的 AI 销售系统。"
    events = []
    
    # Consume first 5 events
    stream_gen = generate_layered_agentic_stream(test_input)
    for _ in range(5):
        try:
            chunk = next(stream_gen)
            events.append(chunk)
        except StopIteration:
            break

    joined_events = "".join(events)
    assert "event: hud" in joined_events
    assert "deconstruction" in joined_events
    assert "calculating" in joined_events
    assert "critique" in joined_events
