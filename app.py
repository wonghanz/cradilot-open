"""
Cradilot AI - SME Digital Growth Advisor & Sales Acceleration Engine
Production FastAPI Application conforming to NodiGuard Security Sentinel Directives.
"""

import os
import re
import json
import uuid
import asyncio
import urllib.parse
from html import escape as _escape_html
from datetime import datetime
from typing import Dict, Any, List, Optional

import anyio
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Internal Core Modules
from core.dms_engine import calculate_dms
from core.ars_engine import calculate_ars
from core.roi_engine import calculate_roi, assumptions_from_inputs
from core.industry_memory import public_catalog, detect_industry
from core.recommendation import (
    generate_pain_points,
    generate_action_roadmap,
    apply_loss_model,
    refresh_roi_milestones
)
from typst_generator.compiler import compile_blueprint_pdf
from sales.lead_dispatcher import LeadDispatcher, SalesLead
from llm.engine_client import engine_client
from llm.prompt_library import (
    SYSTEM_BASE,
    prompt_dynamic_followup,
    prompt_dms_insight,
    prompt_pain_analysis,
    prompt_roadmap,
    prompt_icebreaker,
)
from core.layered_streamer import generate_layered_agentic_stream
from core.sql_wiki_engine import SqlWikiEngine
from core.agentic_diagnostic import (
    start_diagnostic_session,
    process_diagnostic_turn,
    finalize_diagnosis_from_wiki,
    generate_scraper_critique,
    get_first_agentic_probe,
    _unverified_items
)
from core.web_scraper import inspect_company_website
from core.site_audit import audit_website
from core.assessment_facts import classify_machine_check, normalize
from core.noise_filter import NoiseFilterEngine
from core.dev_audit import DevLevelAuditEngine

import config

# Initialize Application
app = FastAPI(
    title="Cradilot AI - SME Digital Growth Advisor",
    description=f"{config.VENDOR_TAGLINE} - evidence-bound SME digital audit, deterministic scoring, one PDF",
    version="2.0.0"
)

# An operator must learn at once that they are looking at rule-engine copy, not
# discover it after a customer quote went out.
config.warn_if_unconfigured()

# Same-origin by default: the UI is served by this process, so an unset variable is the
# narrowest setting rather than a wildcard. List your own front-end origins to open it up.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Static Files Directory
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared State / Dispatcher
lead_dispatcher = LeadDispatcher()


# ─── Request / Response Schemas ───────────────────────────────────────────────

class AssessRequest(BaseModel):
    company_name: str = "Klang Auto Parts Sdn Bhd"
    industry: str = "Auto parts & hardware wholesale"
    team_size: str = "6-15"
    annual_turnover: str = "RM 1M - 5M"
    # None = 本次没有采集到，绝不能有默认断言值：写死 False/single_pc/personal_whatsapp
    # 等于替客户承认"没有企业邮箱、没有备份、客户全在员工手机里"，评分会照此扣分。
    has_business_email: Optional[bool] = None
    website_status: Optional[str] = None      # none | outdated | modern | unverified
    backup_strategy: Optional[str] = None     # single_pc | manual_usb | cloud_auto
    crm_status: Optional[str] = None          # personal_whatsapp | excel_ledger | formal_crm
    after_hours_leak: Optional[bool] = None
    # 这四个数字决定 ROI 全部收益，未填时只能落到标注清楚的假设上，不能记成"当场填报"。
    monthly_salary: Optional[float] = None
    labor_hours_wasted: Optional[float] = None
    monthly_lost_inquiries: Optional[float] = None
    avg_order_value: Optional[float] = None


class ChatFollowupRequest(BaseModel):
    company_name: str
    industry: str
    team_size: str
    annual_turnover: str
    current_tools: List[str] = []


class ChatDmsInsightRequest(BaseModel):
    company_name: str
    industry: str
    dms_score: float
    dms_tier: str
    dimensions: Dict[str, Any] = {}
    user_answers: str = ""


class ChatPainAnalysisRequest(BaseModel):
    company_name: str
    industry: str
    dms_score: float
    user_answers: str = ""
    detected_gaps: List[str] = []


class ChatRoadmapRequest(BaseModel):
    company_name: str
    industry: str
    dms_score: float
    pain_points: List[str] = []
    annual_turnover: str = ""


class ChatIcebreakerRequest(BaseModel):
    company_name: str
    industry: str
    contact_name: str = "Owner"
    dms_score: float
    ars_score: float
    ars_locked: bool = False
    pain_points: List[str] = []
    roi_gain: float = 0.0
    roi_pct: float = 0.0
    cart_items: List[str] = []


class ContactInfo(BaseModel):
    contact_name: str
    contact_phone: str
    contact_email: Optional[str] = "lead@example.com"
    company_name: Optional[str] = None
    industry: Optional[str] = None
    team_size: Optional[str] = None
    annual_turnover: Optional[str] = None


class SubmitLeadRequest(BaseModel):
    assessment_data: Dict[str, Any]
    contact_info: ContactInfo
    notes: Optional[str] = ""
    # 简报要求 PDF 带 Consultant notes、销售流程带 Assign Salesperson
    consultant_notes: Optional[str] = ""
    assigned_to: Optional[str] = ""


class UpdateLeadStatusRequest(BaseModel):
    lead_id: str
    status: Optional[str] = None
    notes: Optional[str] = None
    consultant: Optional[str] = None
    consultant_notes: Optional[str] = None


# ─── Static Routes ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the console with this deployment's identity filled in.

    The HTML ships with {{VENDOR_NAME}} markers instead of a company name, so one build
    of the front end serves any seller.
    """
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(content="<h1>Cradilot AI</h1><p>Static index.html not found.</p>")
    html = index_file.read_text(encoding="utf-8")
    safe_name = _escape_html(config.VENDOR_NAME)
    payload = json.dumps(config.branding()).replace("<", "\u003c")
    html = html.replace("{{VENDOR_NAME}}", safe_name)
    html = html.replace("{{BRANDING_JSON}}", payload)
    return HTMLResponse(content=html)


@app.get("/api/system/engine-status")
async def engine_status() -> Dict[str, Any]:
    """AI 引擎真实状态。演示前先看这个：reachable=false 时界面输出走的是降级文案。"""
    def _recheck() -> Dict[str, Any]:
        engine_client.reset_health()
        live = engine_client.check_health(force=True)
        return {
            "provider": engine_client.provider,
            "model": engine_client.model,
            "base_url": engine_client.base_url or None,
            "api_key_present": bool(engine_client.api_key),
            "reachable": live,
            "consecutive_failures": engine_client.consecutive_failures,
        }

    # 探测是阻塞网络调用，交给线程池，不占事件循环。
    status = await anyio.to_thread.run_sync(_recheck)
    status["degraded_copy_in_use"] = not status["reachable"]
    status["note"] = (
        "provider=off or reachable=false means no model answered this run: the plain-language reading "
        "and the talk tracks came from the built-in rule copy, which carries no invented numbers. Scores "
        "and the pain-point list still come from the deterministic engine over your verified facts, so "
        "they can be quoted as usual. Set CRADILOT_LLM_PROVIDER with GEMINI_API_KEY, OPENAI_API_KEY or "
        "CRADILOT_OLLAMA_URL to get model-written prose."
    )
    return status


# ─── Core Assessment Pipeline ───────────────────────────────────────────────────

@app.post("/api/assess")
async def run_assessment(req: AssessRequest) -> Dict[str, Any]:
    """
    Unified deterministic assessment pipeline (Steps 1-5).
    DMS, ARS, ROI computed by pure functions. No LLM hallucination in scores.
    """
    # 只写客户真答过的字段：未答的项在此处不出现，normalize 会把对应判据留成 None，
    # 评分引擎按中性值计入。写默认值进去等于用一句没问过的话把客户打成最差档。
    engine_input: Dict[str, Any] = {
        "company_name": req.company_name,
        "industry": req.industry,
        "team_size": req.team_size,
        "annual_turnover": req.annual_turnover,
    }
    if req.website_status in ("none", "outdated", "modern"):
        engine_input["web_engine_status"] = {
            "modern": "standard", "outdated": "dormant", "none": "no_site"}[req.website_status]
    if req.backup_strategy in ("single_pc", "manual_usb", "cloud_auto"):
        engine_input["dr_backup_status"] = req.backup_strategy
    if req.crm_status in ("personal_whatsapp", "excel_ledger", "formal_crm"):
        engine_input["crm_system"] = (
            "personal_phone" if req.crm_status == "personal_whatsapp" else req.crm_status)
        engine_input["current_tools"] = (
            ["crm"] if req.crm_status == "formal_crm" else ["paper", "whatsapp"])
    if req.has_business_email is not None:
        engine_input["uses_personal_email"] = not req.has_business_email
    if req.after_hours_leak is not None:
        engine_input["has_ai_agent"] = not req.after_hours_leak

    dms_result = calculate_dms(engine_input)
    ars_result = calculate_ars(engine_input, dms_result["overall_score"])

    top_pain_points_raw = generate_pain_points(engine_input, dms_result)
    primary_pain_points = [f"{p['title']}: {p['impact']}" for p in top_pain_points_raw[:5]]

    roadmap = generate_action_roadmap(engine_input, dms_result, top_pain_points_raw)

    # 采购车与路线图同源（与 finalize 路径同一规则）：合计 = 各阶段预算之和 = ROI 分母
    cart_items = lead_dispatcher.cart_from_roadmap(roadmap)
    cart_data = [
        {
            "sku": item.sku,
            "product_name": item.product_name,
            "billing_cycle": item.billing_cycle,
            "regular_price_myr": item.regular_price_myr,
            "promotional_price_myr": item.promotional_price_myr,
            "notes": item.notes
        }
        for item in cart_items
    ]
    # ROI 必须针对客户眼前这份采购车算，而不是一个写死的年费：
    # 原先 vendor_annual_cost 恒为 5550.68，与同一页面上的购物车合计互不对应。
    priced_lines = [i for i in cart_items if i.promotional_price_myr > 0]
    cart_total = round(sum(i.promotional_price_myr for i in priced_lines), 2)

    # 档位假设与问诊路径读同一份归一化事实：同一家公司从两条路进来，
    # ROI 的四个数字与出处必须一致。
    facts = normalize(engine_input)
    roi_result = calculate_roi(
        vendor_annual_cost=cart_total,
        priced_line_count=len(priced_lines),
        assumptions=assumptions_from_inputs(
            facts={"crm_system": facts["crm"]["tier"],
                   "ai_tier": facts["ai"]["tier"],
                   "has_ai_agent": facts["ai"]["has_agent"]},
            hours_per_week=req.labor_hours_wasted,
            monthly_salary_myr=req.monthly_salary,
            missed_orders_per_month=req.monthly_lost_inquiries,
            avg_order_value_myr=req.avg_order_value
        ),
        quote_pending=any(ph.get("pricing_pending") for ph in roadmap)
    )

    apply_loss_model(top_pain_points_raw, roi_result)
    refresh_roi_milestones(roadmap, top_pain_points_raw)

    report_id = f"CRADILOT-{config.REPORT_PREFIX}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # 本端点是问诊未完成时的兜底：没问过的项按中性值计入，必须在报告上写明，
    # 否则一个"未采集"的维度会被读成"实测过且没问题"。清单与评分读的字段同源。
    unverified_items = _unverified_items(engine_input)

    return {
        "metadata": {
            "company_name": req.company_name,
            "industry": req.industry,
            "team_size": req.team_size,
            "annual_turnover": req.annual_turnover,
            "report_id": report_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "data_basis": "basic_only" if len(unverified_items) >= 4 else "partial",
            "data_basis_note": (
                "This report was generated while the Step 3 interview was still incomplete: "
                + ", ".join(unverified_items)
                + " were not collected in this run, and are counted neutrally rather than deducted as"
                  " missing. Once the interview is completed, the scores are recalculated from the answers."
            ),
            "unverified_items": unverified_items,
        },
        "dms": dms_result,
        "ars": ars_result,
        "roi": roi_result,
        "recommendation": {
            "primary_pain_points": primary_pain_points,
            "roadmap": roadmap
        },
        "cart": cart_data
    }


# ─── AI Chat Generation Endpoints (SSE Streaming) ──────────────────────────────

def _sse_stream(text_iterator):
    """Wrap a text iterator into SSE event format."""
    for chunk in text_iterator:
        if chunk:
            safe = chunk.replace("\n", "\\n")
            yield f"data: {safe}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/chat/followup")
async def chat_followup(req: ChatFollowupRequest):
    """
    Stage 2: AI generates 2 precision business probe questions tailored to this SME.
    Streams via SSE for typewriter effect.
    """
    prompt = prompt_dynamic_followup(
        company_name=req.company_name,
        industry=req.industry,
        team_size=req.team_size,
        annual_turnover=req.annual_turnover,
        tools=req.current_tools
    )

    def generate():
        yield from _sse_stream(engine_client.stream_generate(prompt, SYSTEM_BASE, max_tokens=300))

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/chat/dms-insight")
async def chat_dms_insight(req: ChatDmsInsightRequest):
    """
    Stage 4: AI generates personalized DMS dimension analysis for this specific enterprise.
    Streams via SSE.
    """
    prompt = prompt_dms_insight(
        company_name=req.company_name,
        industry=req.industry,
        dms_score=req.dms_score,
        dms_tier=req.dms_tier,
        dimensions=req.dimensions,
        user_answers=req.user_answers
    )

    def generate():
        yield from _sse_stream(engine_client.stream_generate(prompt, SYSTEM_BASE, max_tokens=400))

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/chat/pain-analysis")
async def chat_pain_analysis(req: ChatPainAnalysisRequest):
    """
    Stage 5: AI generates enterprise-specific Top 5 core pain points with evidence chains.
    Streams via SSE.
    """
    prompt = prompt_pain_analysis(
        company_name=req.company_name,
        industry=req.industry,
        dms_score=req.dms_score,
        user_answers=req.user_answers,
        detected_gaps=req.detected_gaps
    )

    def generate():
        yield from _sse_stream(engine_client.stream_generate(prompt, SYSTEM_BASE, max_tokens=700))

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/chat/roadmap")
async def chat_roadmap(req: ChatRoadmapRequest):
    """
    Stage 6: AI generates industry-specific 3-phase implementation roadmap.
    Streams via SSE.
    """
    prompt = prompt_roadmap(
        company_name=req.company_name,
        industry=req.industry,
        dms_score=req.dms_score,
        pain_points=req.pain_points,
        annual_turnover=req.annual_turnover
    )

    def generate():
        yield from _sse_stream(engine_client.stream_generate(prompt, SYSTEM_BASE, max_tokens=700))

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/chat/icebreaker")
async def chat_icebreaker(req: ChatIcebreakerRequest):
    """
    Sales tool: AI generates a personalized icebreaker script for this specific SME decision-maker.
    Streams via SSE.
    """
    prompt = prompt_icebreaker(
        company_name=req.company_name,
        industry=req.industry,
        contact_name=req.contact_name,
        dms_score=req.dms_score,
        ars_score=req.ars_score,
        ars_locked=req.ars_locked,
        pain_points=req.pain_points,
        roi_gain=req.roi_gain,
        roi_pct=req.roi_pct,
        cart_items=req.cart_items
    )

    def generate():
        yield from _sse_stream(engine_client.stream_generate(prompt, SYSTEM_BASE, max_tokens=400))

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class ChatAgenticStreamRequest(BaseModel):
    user_input: str
    company_name: Optional[str] = ""


@app.post("/api/chat/agentic-stream")
async def chat_agentic_stream(req: ChatAgenticStreamRequest):
    """
    IRIS-style layered streaming endpoint:
    1. Emits rapid 'event: hud' status updates in <500ms (eliminates freeze perception).
    2. Streams token-by-token advice from cradilot-cradle model.
    3. Emits 'event: done' with exact pure-function ROI calculation payload.
    """
    return StreamingResponse(
        generate_layered_agentic_stream(req.user_input, req.company_name or ""),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ─── Multi-Turn Agentic Diagnostic Endpoints (SQLite LLM Wiki) ───────────────

class DiagStartRequest(BaseModel):
    company_name: str
    industry: str
    team_size: str
    annual_turnover: str
    biggest_challenge: Optional[str] = ""
    growth_objective: Optional[str] = ""
    # 简报 Step 1 点名的 "Current digital tools"：存客户原话，不是枚举列表
    current_tools: Optional[str] = ""


class DiagStepRequest(BaseModel):
    session_id: str
    user_answer: str
    # 前端回传本轮探针所属维度，使状态机确切知道用户在回答哪一题；
    # 缺省时后端沿用缺失列表推断（向后兼容旧客户端）。
    target_dim: Optional[str] = ""
    # 点选的那个选项原样回传：它的 val 就是规范取值，不必再从措辞反推
    selected_option: Optional[Dict[str, Any]] = None


class DiagFinalizeRequest(BaseModel):
    session_id: str
    # 报告页上客户当场改过的测算假设（工时/漏接询盘/毛利/月薪）；缺省则沿用系统档位假设
    assumptions: Optional[Dict[str, Any]] = None


class AnalyzeCompanyRequest(BaseModel):
    company_name: str


# ─── 行业目录：单一数据源 data/industry_catalog.json，读取与匹配都在 core.industry_memory ──
# 此前 app.py 与 core/industry_memory.py 各有一份行业表和两套匹配规则，12 条基准里
# 8 条的行业名在用户能选到的 10 个行业里根本不存在——同一件事被判定成两个答案。


@app.get("/api/catalog/industries")
async def get_industry_catalog() -> List[Dict[str, Any]]:
    """前端行业选项的唯一来源。"""
    return public_catalog()


@app.post("/api/live/analyze-company-name")
async def analyze_company_name(req: AnalyzeCompanyRequest) -> Dict[str, Any]:
    """
    Live AI analysis of company name: decodes potential industry attributes
    and generates dynamic contextual prompt and tailored options.
    """
    name = req.company_name.strip()
    attr = detect_industry(name)
    base_options = public_catalog()

    if attr:
        ai_text = (f"Trade name read from the live check: \"{name}\". Cradilot AI reads your business as "
                   f"[{attr['val']}]. Please confirm your main industry:")
        sub_hint = ("Cradilot AI pre-matched an industry from the trade name. Pick the industry that fits "
                    "best, so the comparison and the product fit later on match how you really operate.")
        matched_val = attr["val"]
        industry_options = []
        for item in base_options:
            if item["val"] == matched_val:
                industry_options.insert(0, {
                    "val": item["val"],
                    "label": f"{item['label']} [AI recommended match]",
                    "sub": item["sub"],
                    "is_recommended": True
                })
            else:
                industry_options.append(item)
    else:
        ai_text = f"Trade name read from the live check: \"{name}\". Which of these main industries fits your core business?"
        sub_hint = ("Once the industry is set, the report compares you against your industry's baseline and the "
                    "product fit follows how your trade actually delivers.")
        industry_options = base_options

    return {
        "company_name": name,
        "ai_prompt": ai_text,
        "sub_hint": sub_hint,
        "industry_options": industry_options,
        "matched_industry": attr["val"] if attr else None
    }


@app.post("/api/diag/start")
async def diag_start(req: DiagStartRequest) -> Dict[str, Any]:
    """Start an interactive agentic diagnostic session."""
    return start_diagnostic_session(
        company_name=req.company_name,
        industry=req.industry,
        team_size=req.team_size,
        annual_turnover=req.annual_turnover,
        biggest_challenge=req.biggest_challenge or "",
        growth_objective=req.growth_objective or "",
        current_tools=req.current_tools or ""
    )


@app.post("/api/diag/step")
async def diag_step(req: DiagStepRequest) -> Dict[str, Any]:
    """Process an answer turn, sync evidence to SQLite, and return next probe or completion."""
    return process_diagnostic_turn(
        session_id=req.session_id,
        user_answer=req.user_answer,
        target_dim=(req.target_dim or "").strip(),
        selected_option=req.selected_option
    )


@app.get("/api/diag/wiki/{session_id}")
async def diag_wiki(session_id: str) -> Dict[str, Any]:
    """Retrieve live SQLite evidence tree for UI display."""
    tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    if not tree.get("dossier"):
        raise HTTPException(status_code=404, detail="Session not found.")
    return tree


@app.post("/api/diag/finalize")
async def diag_finalize(req: DiagFinalizeRequest) -> Dict[str, Any]:
    """Perform deterministic DMS, ARS, ROI and cart synthesis anchored on SQLite evidence."""
    return finalize_diagnosis_from_wiki(req.session_id, req.assumptions)


@app.get("/api/diag/first-probe/{session_id}")
async def diag_first_probe(session_id: str) -> Dict[str, Any]:
    """Retrieve the first dynamic agentic probe for Step 3."""
    return get_first_agentic_probe(session_id)


# ─── 官网机检（新流程第 ② 步的证据来源） ──────────────────────────────────────

class SiteAuditRequest(BaseModel):
    url: str
    session_id: Optional[str] = ""


# 机检项归属哪个评分维度：分类只存在于 core.assessment_facts，此处不再自建第二张表


def _persist_machine_findings(session_id: str, result: Dict[str, Any]) -> int:
    """把机检结论写进 SQLite 证据链，让确定性评分以实测事实为依据。

    unverified 一律不写：测不到不是"没有"，写进去就会被下游折算成扣分。
    """
    if not SqlWikiEngine.get_live_wiki_tree(session_id).get("dossier"):
        return 0
    written = 0
    for f in result.get("findings", []):
        if f.get("status") == "unverified":
            continue
        # 未登记的 check 归入 ops：仍然留证，但不会被误算进任何判据
        registered = classify_machine_check(f.get("check", ""))
        # 深探一次回上百条：只有参与判据的、或确凿的高危缺口才进证据链，
        # 否则 dossier 会被"图片没做 alt"这类条目淹没，LLM 与界面都读不到重点。
        if not registered and f.get("severity") not in ("CRITICAL", "HIGH"):
            continue
        dimension = registered or "ops"
        if SqlWikiEngine.record_machine_fact(
            session_id=session_id,
            dimension=dimension,
            fact_key=f["check"],
            status=f["status"],
            observed=f.get("observed", ""),
            title=f.get("title", f["check"]),
            severity=f.get("severity", "INFO"),
            vendor_solution_skus=f.get("vendor_skus") or [],
        ):
            written += 1
    if written:
        SqlWikiEngine.update_state_ledger(session_id)
    return written


@app.post("/api/audit/site")
async def audit_site(req: SiteAuditRequest) -> Dict[str, Any]:
    """
    对贵司自己的官网做完整机检，返回逐项结论。

    每项含三态（pass / fail / unverified）、白话说明、以及该缺口导向的真实 our SKU。
    与 /api/scrape/inspect-website 的区别在于后者只回一份笼统的技术摘要；本端点输出的
    才是能进评分卡与蓝图、也能被工程师复核的证据。
    """
    raw_url = (req.url or "").strip()
    if not raw_url or raw_url.lower() in ("none", "no", "无", "没有", "暂无", "无官网"):
        # "没有官网"是企业自述的既成事实，不是检测失败，因此计入评分而非标为未核验
        payload = {
            "success": True,
            "has_website": False,
            "findings": [{
                "check": "site_absent", "title": "Public company website", "status": "fail",
                "observed": "Company confirmed there is no website at the moment",
                "plain": "Without a website of its own, customers in other states and overseas cannot check "
                         "that the business really operates. The first trust is lost before anyone makes contact.",
                "severity": "HIGH",
                "vendor_skus": ["DEMO-DOM-COM", "DEMO-WP17-BUSINESS"],
                "evidence_source": "owner_statement",
            }],
            "summary": {
                "score": 0.0, "graded_checks": 1, "pass": 0, "fail": 1, "unverified": 0,
                "critical": ["No company website"],
                "score_note": "The company has no public website at all, so the web dimension is scored as not in place.",
                "suggested_skus": ["DEMO-DOM-COM", "DEMO-WP17-BUSINESS"],
                "audit_seconds": 0.0,
            },
        }
        if req.session_id:
            payload["recorded_facts"] = _persist_machine_findings(req.session_id, payload)
        return payload

    # 机检全程是阻塞网络调用，放到线程池，避免冻结事件循环拖慢其他客户的会话
    result = await anyio.to_thread.run_sync(audit_website, raw_url)
    if req.session_id and result.get("success"):
        result["recorded_facts"] = _persist_machine_findings(req.session_id, result)
        # 明细与四条结论落盘：PDF 附录与蓝图第 1 阶段的方案汇总都以这份快照为准
        SqlWikiEngine.record_site_audit(
            req.session_id, result.get("url") or raw_url, result.get("site_level") or "",
            result.get("site_level_label") or "", result.get("checklist") or [],
            result.get("conclusions") or [], result.get("checklist_summary") or {})
    return result


# ─── Web Scraping & Technical Audit Endpoint ──────────────────────────────────

class WebInspectRequest(BaseModel):
    url: str
    session_id: Optional[str] = ""


@app.post("/api/scrape/inspect-website")
async def inspect_website(req: WebInspectRequest) -> Dict[str, Any]:
    """
    Perform live website scraping, SSL certificate check, latency test,
    CMS technology detection, and Cradilot AI commercial vulnerability critique.
    Syncs facts to SQLite wiki ledger.
    """
    raw_url = (req.url or "").strip()
    if not raw_url or raw_url.lower() in ["none", "no", "无", "没有", "暂无", "无官网"]:
        if req.session_id:
            SqlWikiEngine.extract_and_sync_wiki_nodes(req.session_id, "We have no official website yet; business runs through offline regulars and social media")
            SqlWikiEngine.update_state_ledger(req.session_id)
        return {
            "success": True,
            "has_website": False,
            "status": "none",
            "audit_summary": "Confirmed: no official website yet. The brand has no digital home of its own.",
            "ai_critique": ("With no official portal of its own, prospects coming from the open market cannot build a "
                            "first trust in the brand. In the Malaysian market, businesses without their own official "
                            "website lose on average more than 55% of larger cross-state or cross-border purchase inquiries.")
        }

    audit_res = inspect_company_website(raw_url)

    company_name = "Your company"
    industry = "General trading"
    if req.session_id:
        tree = SqlWikiEngine.get_live_wiki_tree(req.session_id)
        dossier = tree.get("dossier", {})
        company_name = dossier.get("company_name", company_name)
        industry = dossier.get("industry", industry)

    # Generate Cradilot AI commercial vulnerability critique
    ai_critique = generate_scraper_critique(company_name, industry, audit_res)
    audit_res["ai_critique"] = ai_critique

    if req.session_id:
        ssl_ok = bool(audit_res.get("ssl_valid"))
        scan_ok = bool(audit_res.get("success"))
        if scan_ok:
            status_val = "modern" if (ssl_ok and audit_res.get("technical_score", 0) >= 65) else "outdated"
            summary_quote = f"{audit_res.get('audit_summary', '')} AI note: {ai_critique}"
            node_confidence = 0.98
        else:
            # 没连通就是没测到：写进 scored 字段会被读成"测过且很旧"，只能记一次失败的尝试
            status_val = "unverified"
            summary_quote = (f"The target website could not be reached in this scan, so this conclusion is "
                             f"unverified ({raw_url}). AI note: {ai_critique}")
            node_confidence = 0.55

        # Record verified node in SQLite Wiki
        with SqlWikiEngine.get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO wiki_evidence_nodes (session_id, dimension, fact_key, fact_value, quote_text, confidence, created_at)
                VALUES (?, 'web', ?, ?, ?, ?, ?)
            """, (req.session_id,
                  "web_engine_status" if scan_ok else "web_scan_attempt",
                  status_val, summary_quote, node_confidence, now))
            conn.commit()

        # 仅当真实核验到证书问题（无 HTTPS 或证书链不受信）时才写入 SSL 痛点
        if scan_ok and not ssl_ok:
            SqlWikiEngine._insert_pain_point(
                session_id=req.session_id,
                title="Website certificate invalid or missing, so the browser shows a Not Secure warning",
                root_cause=f"The company website ({audit_res.get('final_url', raw_url)}) failed the valid certificate "
                           f"check in a real TLS handshake ({audit_res.get('ssl_error') or 'no trusted certificate received'}).",
                loss_myr=0.0,
                severity="HIGH",
                cradle_gap="Visitors see the security warning before they leave any contact details.",
                solution="business-grade SSL certificate with smart CDN acceleration",
                dimension="web"
            )

        SqlWikiEngine.update_state_ledger(req.session_id)

    return audit_res


# ─── PDF Generation ─────────────────────────────────────────────────────────────

@app.post("/api/pdf/generate")
async def generate_pdf(payload: Dict[str, Any]):
    """Generate and stream the blueprint PDF via Typst (8 pages, 9 with option comparisons)."""
    try:
        pdf_bytes = compile_blueprint_pdf(payload)
        company_name = payload.get("metadata", {}).get("company_name", "SME").replace(" ", "_")
        filename = f"Cradilot_Blueprint_{company_name}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Compilation Error: {str(e)}")


# ─── Sales Lead Management ──────────────────────────────────────────────────────

@app.get("/api/sales/leads")
async def get_sales_leads() -> List[Dict[str, Any]]:
    """Retrieve captured leads for sales CRM view."""
    return lead_dispatcher.list_leads()


@app.post("/api/sales/submit-lead")
async def submit_sales_lead(req: SubmitLeadRequest) -> Dict[str, Any]:
    """Submit and register a qualified SME lead."""
    lead = lead_dispatcher.create_lead(
        assessment_data=req.assessment_data,
        contact_info=req.contact_info.model_dump(),
        notes=req.notes or "",
        consultant_notes=req.consultant_notes or "",
        assigned_to=req.assigned_to or ""
    )
    return {
        "success": True,
        "lead_id": lead.lead_id,
        "status": lead.status,
        "assigned_to": lead.assigned_to,
        "total_package_myr": lead.total_package_myr,
        "icebreaker_preview": lead.sales_icebreaker[:150] + "..."
    }


@app.post("/api/sales/update-lead-status")
async def update_lead_status(req: UpdateLeadStatusRequest) -> Dict[str, Any]:
    """更新线索状态、指派顾问与顾问备注（简报的 Assign Salesperson 一步）。"""
    updated = lead_dispatcher.update_lead_status(
        req.lead_id, req.status, req.notes,
        consultant=req.consultant, consultant_notes=req.consultant_notes)
    if not updated:
        raise HTTPException(status_code=404, detail="Lead ID not found.")
    record = next((r for r in lead_dispatcher.list_leads(200)
                   if r.get("lead_id") == req.lead_id), {})
    return {"success": True, "lead_id": req.lead_id,
            "status": record.get("status"), "assigned_to": record.get("assigned_to", "")}


# ─── New Blueprint v5.0 Extended Endpoints ────────────────────────────────────

class DevAuditRequest(BaseModel):
    url: str
    session_id: Optional[str] = ""


@app.post("/api/audit/dev-scan")
async def audit_dev_scan(req: DevAuditRequest) -> Dict[str, Any]:
    """Step 2 Developer-Level Passive Security & DNS/SPF/DMARC Compliance Audit."""
    res = DevLevelAuditEngine.run_full_dev_audit(req.url, req.session_id)
    res["success"] = True
    res["domain"] = urllib.parse.urlparse(req.url).hostname or req.url
    res["email_security"] = res.get("dns_email_security", {})
    res["sensitive_files"] = res.get("exposed_files", [])
    res["key_scan"] = {
        "exposed_count": len(res.get("exposed_keys", [])),
        "keys": res.get("exposed_keys", [])
    }
    res["dev_audit_score"] = res.get("technical_score", 0)
    return res


class SpeechNoiseFilterRequest(BaseModel):
    text: Optional[str] = ""
    raw_text: Optional[str] = ""
    session_id: Optional[str] = ""


@app.post("/api/speech/filter-noise")
async def filter_speech_noise(req: SpeechNoiseFilterRequest) -> Dict[str, Any]:
    """Live-to-speech fact distillation: strips noise and extracts standardized business facts."""
    input_text = req.text or req.raw_text or ""
    res = NoiseFilterEngine.extract_facts(input_text, req.session_id)
    res["success"] = True
    quotes = [f["quote"] for f in res.get("filtered_facts", []) if "quote" in f]
    res["clean_text"] = " ".join(quotes) if quotes else input_text
    res["structured_facts"] = res.get("filtered_facts", [])
    res["estimated_loss_rm"] = res.get("quantified_loss", {}).get("estimated_annual_loss_myr", 0.0)
    return res


class DispatchLeadRequest(BaseModel):
    assessment_data: Optional[Dict[str, Any]] = None
    contact_name: Optional[str] = ""
    contact_phone: Optional[str] = ""
    contact_email: Optional[str] = "lead@example.com"
    phone: Optional[str] = ""
    email: Optional[str] = ""
    preferred_callback_time: Optional[str] = "Anytime"
    preferred_time: Optional[str] = ""
    notes: Optional[str] = ""
    session_id: Optional[str] = ""


@app.post("/api/sales/dispatch-lead")
async def dispatch_sales_lead(req: DispatchLeadRequest) -> Dict[str, Any]:
    """Full-pipeline sales dispatch: builds lead packet, pre-configured cart URL, and icebreaker talk tracks."""
    c_name = req.contact_name or "Business owner"
    c_phone = req.contact_phone or req.phone or "+60120000000"
    c_email = req.contact_email or req.email or "lead@example.com"
    c_time = req.preferred_callback_time or req.preferred_time or "Anytime"

    contact_dict = {
        "contact_name": c_name,
        "contact_phone": c_phone,
        "contact_email": c_email,
        "preferred_callback_time": c_time
    }
    # 采购车按真实席位数计价，故把评估里的团队规模带进联系人信息
    contact_dict.setdefault(
        "team_size",
        (req.assessment_data or {}).get("metadata", {}).get("team_size", "")
    )

    assess_data = req.assessment_data
    if not assess_data:
        # 旧版在这里凭空造出一份评分（DMS 38 / 净收益 22,488.32 / ROI 505.2%），
        # 每条未带评估的线索都会拿到同一组假数字，再进 CRM 并被销售念给客户听。
        # 现在只接受真实来源：有 session 就用它已锁证的证据收尾，没有就拒绝。
        if req.session_id:
            tree = SqlWikiEngine.get_live_wiki_tree(req.session_id)
            if tree.get("dossier"):
                assess_data = finalize_diagnosis_from_wiki(req.session_id)
        if not assess_data:
            raise HTTPException(
                status_code=422,
                detail=(
                    "assessment_data is missing, and the session_id does not resolve to a verified diagnostic session. "
                    "A lead has to be bound to a real assessment; the system no longer fills in scores and ROI for a "
                    "lead without one."
                )
            )

    lead = lead_dispatcher.create_lead(
        assessment_data=assess_data,
        contact_info=contact_dict,
        notes=f"Preferred callback time: {c_time}. Notes: {req.notes or 'None'}"
    )
    cart_skus = [item["sku"] for item in lead.cart_items]
    cart_url = f"https://www.vendor.example/cart?skus={','.join(cart_skus)}&ref=cradilot_advisor"

    return {
        "success": True,
        "lead_id": lead.lead_id,
        "created_at": lead.created_at,
        "company_name": lead.company_name,
        "status": lead.status,
        "total_package_myr": lead.total_package_myr,
        "cart_checkout_url": cart_url,
        "checkout_cart": {
            "cart_checkout_url": cart_url,
            "items": lead.cart_items,
            "total_myr": lead.total_package_myr
        },
        "cart_items": lead.cart_items,
        "icebreaker": lead.sales_icebreaker,
        "sales_icebreaker": lead.sales_icebreaker,
        "pdf_blueprint_ready": True
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
