"""
Cradilot Core - Layered Streaming Engine
Decouples Agentic Thought HUD status events from advisor advice token streaming.
Emits SSE events:
- 'event: hud': updates frontend indicators in <500ms (eliminates freeze anxiety)
- 'event: token': real-time token streaming of the final grounded advice
- 'event: done': signals completion with payload
"""

import json
import time
from typing import Iterator, Dict, Any
from core.agentic_guardrail import AgenticGuardrailEngine, build_guarded_prompt_context
from llm.engine_client import engine_client


def generate_layered_agentic_stream(user_input: str, company_name: str = "") -> Iterator[str]:
    """
    Generator yielding SSE formatted chunks:
    1. Emits 3 rapid HUD status events reflecting the State Machine nodes.
    2. Runs guarded prompt against Gemma and streams tokens.
    3. Emits completion payload.
    """
    # ─── Node 1: Fact Deconstruction & Memory Recall ─────────────────────────
    yield f"event: hud\ndata: {json.dumps({'stage': 'deconstruction', 'label': 'Matching your description against the industry directory...', 'active': 1}, ensure_ascii=False)}\n\n"
    time.sleep(0.1)

    decision = AgenticGuardrailEngine.run_pipeline(user_input, company_name)
    grounding = decision.grounding

    # ─── Node 2: 阶段判断（本入口没有评分，只判断该不该暂缓推销） ──────────────
    hits = decision.immature_signals
    calc_label = ("Paper-and-single-PC signals plus a leap-ahead purchase request detected. Re-ordering the recommendations..."
                  if decision.route == "BRANCH_CORRECTION_AND_EDUCATION"
                  else "Your request matches the current stage. Organising the advice along the three-phase roadmap...")
    yield f"event: hud\ndata: {json.dumps({'stage': 'calculating', 'label': calc_label, 'active': 2, 'signals': hits}, ensure_ascii=False)}\n\n"
    time.sleep(0.1)

    # ─── Node 3: Impulse Gatekeeper & Hard-Lock Check ────────────────────────
    if decision.route == "BRANCH_CORRECTION_AND_EDUCATION":
        critique_label = "Leap-ahead purchase impulse detected. Pulling the recommendation order back to phases 1 and 2..."
    else:
        critique_label = "Infrastructure assessment passed. Matching the phased implementation blueprint that fits best..."

    yield f"event: hud\ndata: {json.dumps({'stage': 'critique', 'label': critique_label, 'active': 3, 'hard_locked': decision.is_hard_locked}, ensure_ascii=False)}\n\n"
    time.sleep(0.1)

    # ─── Build Guarded Context & Stream Advice Tokens ────────────────────────
    guarded_prompt = build_guarded_prompt_context(decision, user_input)

    try:
        # Stream response tokens from gemma
        for chunk in engine_client.stream_generate(guarded_prompt, max_tokens=600):
            # Clean newlines for SSE payload
            safe_chunk = chunk.replace("\n", "\\n")
            yield f"event: token\ndata: {safe_chunk}\n\n"
    except Exception:
        # 模型不可用时只说门禁真的知道的事；金额一律不编，指回报告页。
        industry = grounding["industry_name"] or "your industry"
        fallback = (
            f"(The live model did not answer. What follows is the deterministic judgement of the system.)\n"
            f"You were matched to: {industry}.\n"
        )
        fallback += (
            "This question showed both paper documents / orders taken on a personal phone / data kept on one PC, "
            "and a wish to go straight to a costly AI. The system therefore holds back from recommending a large "
            "model: first put the documents and the data into a form a system can read, so the AI has something to "
            "answer from.\n"
            if decision.route == "BRANCH_CORRECTION_AND_EDUCATION"
            else "Your request matches your current infrastructure stage, so the three phases can be taken in order.\n"
        )
        fallback += ("The exact annual fee and the return are on the assessment report page. There every number shows "
                     "its source, and the calculation assumptions can be changed on the spot.")
        safe_fb = fallback.replace("\n", "\\n")
        yield f"event: token\ndata: {safe_fb}\n\n"

    # ─── Final Done Event ───────────────────────────────────────────────────
    done_payload = {
        "status": "complete",
        "route": decision.route,
        "is_hard_locked": decision.is_hard_locked,
        "rationale": decision.rationale,
        "signals": decision.immature_signals,
    }
    yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
