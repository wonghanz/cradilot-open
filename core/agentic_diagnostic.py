"""
Cradilot Core - Gemma-Led Agentic Diagnostic State Machine
Implements multi-turn precision business probes, completeness verification across
DMS 6 dimensions + ARS 5 factors, and evidence-linked diagnosis completion.
Zero emoji, strict local physical isolation.
"""

import os
import re
import uuid
import copy
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from core.sql_wiki_engine import (
    SqlWikiEngine, CORE_DIMENSIONS, ARS_FACTORS, DIMENSION_LABELS,
    ALL_TRACKED_DIMENSIONS, UNKNOWN_FACT_VALUE, is_unknown_fact_value, confirmed_nodes
)
from core.dms_engine import calculate_dms
from core.ars_engine import calculate_ars
from core.roi_engine import calculate_roi, resolve_assumptions
from core.recommendation import (
    generate_pain_points, generate_action_roadmap, apply_loss_model,
    refresh_roi_milestones)
from sales.lead_dispatcher import LeadDispatcher
from llm.engine_client import engine_client
from llm.prompt_library import (
    prompt_agentic_probe_generation,
    prompt_agentic_probe_retry,
    prompt_web_scraper_critique
)

lead_dispatcher = LeadDispatcher()

# Precision Probe Bank covering DMS 6 Dimensions and ARS 5 Factors
PROBE_TEMPLATES = {
    # ── DMS 6 Dimensions ──
    "cloud": {
        "step_title": "Core Data Assets and Disaster Resilience (Cloud Resilience)",
        "question": "Checking the safety of your core business assets: where are your day-to-day accounts, purchasing and sales stock records and delivery notes kept today — on one office computer, or automatically backed up to a cloud copy in another location? If ransomware hit or a hard drive died, what is your recovery plan?",
        "sub_hint": "When everything sits on one computer, ransomware or a drive failure can take the whole accounting history with it, and recovery is measured in days.",
        "options": [
            {
                "label": "One computer, no backup",
                "sub": "Accounts and order documents live only on the front-desk or finance PC. If that machine dies, the whole company's books stop.",
                "val": "single_pc"
            },
            {
                "label": "Manual copy to a USB or external drive",
                "sub": "Staff plug in a drive now and then and copy files by hand. It costs man-hours and does not protect against fire, loss or theft.",
                "val": "manual_usb"
            },
            {
                "label": "Automated encrypted cloud backup",
                "sub": "Encrypted and synced to another location every day, and the recovery can be demonstrated on the spot.",
                "val": "cloud_auto"
            }
        ]
    },
    "crm": {
        "step_title": "Sales Pipeline and Customer Asset Retention (CRM & Customer Pipeline)",
        "question": "Checking where your customer records are kept: do repeat orders and new enquiries today sit mainly in a salesperson's personal WhatsApp, or are they entered into one company-wide customer system? If that person resigned, would the customer history stay with the company?",
        "sub_hint": "When customers are handled on a personal phone, a departing employee takes the conversation history with it and the company cannot rebuild it.",
        "options": [
            {
                "label": "Salesperson's personal WhatsApp and paper notes",
                "sub": "Customer details and chat history are scattered across staff personal phones, follow-up is invisible, and customers leave when the staff member does.",
                "val": "personal_whatsapp"
            },
            {
                "label": "Excel spreadsheet, compiled by hand",
                "sub": "Consolidated by hand from time to time, several versions overwriting each other, and only the person filling it in knows how far a deal has got.",
                "val": "excel_manual"
            },
            {
                "label": "Standardised CRM pipeline, kept centrally",
                "sub": "Leads from every channel land in one place, deal progress is visible on a board, and customer records stay with the company as a shared pool.",
                "val": "formal_crm"
            }
        ]
    },
    "cyber": {
        "step_title": "Outbound Email and Domain Impersonation (Email & Domain Security)",
        "question": "Checking compliance and brand reputation: when you send a formal quotation, purchase contract or invoice to a customer, do you use a personal free mailbox (such as @gmail.com) or a business mailbox on your own company domain?",
        "sub_hint": "A personal free mailbox has no domain ownership and no SPF/DKIM/DMARC records, so the other side's firewall is more likely to judge it as spam and anyone can imitate the sender.",
        "options": [
            {
                "label": "Personal free mailbox (@gmail.com, @yahoo.com)",
                "sub": "Quotations are easily classified as spam by the receiver's firewall, and anyone can pretend to be that sender.",
                "val": "free"
            },
            {
                "label": "Business mailbox on your own domain (@yourcompany.com)",
                "sub": "Domain ownership is clear, SPF/DKIM/DMARC are in place, and mail and correspondence stay with the company after staff leave.",
                "val": "business"
            }
        ]
    },
    "marketing": {
        "step_title": "Digital Acquisition and Traffic Conversion (Marketing & Traffic Tracking)",
        "question": "Auditing digital marketing and lead tracking: which channels bring you new customers today, and when you pay for online ads do you have conversion tracking installed (such as Meta Pixel or Google GA4) for retargeting?",
        "sub_hint": "Without conversion tracking you cannot say which spend brought which order, so the budget can only be spent by feel.",
        "options": [
            {
                "label": "Repeat customers and trade shows only, nothing tracked",
                "sub": "Relying entirely on traditional contacts and waiting for orders: one narrow source of customers, and no way to measure acquisition cost or the conversion funnel.",
                "val": "referral_only"
            },
            {
                "label": "Occasional social ads but no conversion tracking",
                "sub": "Running Facebook or Google ads without a pixel or lead funnel, so a large part of the ad spend achieves nothing.",
                "val": "ad_hoc_ads"
            },
            {
                "label": "Full digital marketing with automated retargeting",
                "sub": "Search engine SEO/SEM plus automated lead retargeting, with data closing the loop across the whole deal conversion path.",
                "val": "full_retargeting"
            }
        ]
    },
    "web": {
        "step_title": "Public Image and Digital Front Door (Web Engine & Domain)",
        "question": "Auditing your public image and digital front door: does your company run a live official website today (with a valid SSL certificate and its own domain), or do you rely mainly on social media pages?",
        "sub_hint": "When out-of-town and overseas customers cannot find you by search, that enquiry traffic can only land on competitors who can be found.",
        "options": [
            {
                "label": "No website at all today, mainly repeat customers and phone calls",
                "sub": "Customers cannot find the company entity through a search engine, so credit checking before a purchase cannot be done.",
                "val": "none"
            },
            {
                "label": "An old website built long ago, no SSL certificate and nobody maintaining it",
                "sub": "Opening it on a phone shows an insecure warning, and customers close it before they ever see the content.",
                "val": "outdated"
            },
            {
                "label": "A modern official website, mobile friendly with SSL encryption",
                "sub": "Site-wide HTTPS encryption and a clear product showcase, able to reliably receive purchase enquiries and leads from home and abroad.",
                "val": "modern"
            }
        ]
    },
    "ai": {
        "step_title": "Who Answers Enquiries After Closing Time (After-hours Response)",
        "question": "Checking your after-hours deal defence: in the evening (18:00 to 23:00) or on public holidays, when a new customer sends an urgent enquiry, can anything answer automatically and lock in the buying intent?",
        "sub_hint": "Many enquiries arrive after office hours and at weekends, and buyers rarely ask only one supplier — reply the next day and that customer has already finished asking around.",
        "options": [
            {
                "label": "Nobody responds, it waits until the next working day",
                "sub": "Enquiries that arrive at evening are only seen the next day, and in that window the customer has already asked someone else.",
                "val": "leak"
            },
            {
                "label": "The owner or a key staff member stays up answering on a personal phone",
                "sub": "It burns the key people's own energy, tired replies quote the wrong floor price, and product quotations cannot be given consistently.",
                "val": "manual_stare"
            },
            {
                "label": "An auto-responder or AI assistant already covers it 7x24",
                "sub": "The system sends the first reply, captures the specification and contact details, and sales picks it up the next day.",
                "val": "covered"
            }
        ]
    },

    # ── ARS 5 Factors ──
    "leadership": {
        "step_title": "Management Resolve and Strategy Budget (Leadership & Strategic Vision)",
        "question": "Checking leadership for digital transformation: does your management give this digital upgrade clear budget support and the resolve to learn from trial and error?",
        "sub_hint": "With the same tools, whether someone sets the scope and the acceptance criteria makes a large difference to how fast things land.",
        "options": [
            {
                "label": "Management is firmly behind it, with a clear budget and cost-and-efficiency targets",
                "sub": "Willing to put resources behind process automation and human-machine collaboration, and to push digitalisation forward as it goes.",
                "val": "high"
            },
            {
                "label": "Management is cautiously waiting, hoping to test cheaply first and see results",
                "sub": "Prefers to invest in stages as results appear, and would scale up only after a clear ROI in cash.",
                "val": "conservative"
            },
            {
                "label": "Management is sceptical about digitalisation, pushed mainly by competitor pressure",
                "sub": "No proactive change plan, the budget is extremely tight, and internal resistance to rolling anything out is high.",
                "val": "reluctant"
            }
        ]
    },
    "employee_skills": {
        "step_title": "Staff Willingness to Work With Tools and Their Learning Base (Employee Skills & Readiness)",
        "question": "Checking team skills and willingness to collaborate: how do your front-line sales and admin staff feel about using a new system or AI tools in place of manual work?",
        "sub_hint": "Front-line acceptance decides whether a new tool really gets used, so a purchase does not end up as decoration.",
        "options": [
            {
                "label": "The team is young, happy to try new tools and picks things up quickly",
                "sub": "Open and positive about working alongside automation, and able to fold new tools into daily routines fast.",
                "val": "high"
            },
            {
                "label": "Staff are used to the traditional way and need proper training and instructions",
                "sub": "Not resistant to new tools but without a digital base, needing clear and easy-to-follow SOP support to adjust.",
                "val": "medium"
            },
            {
                "label": "Key staff resist strongly and trust handwriting and long-standing customers more",
                "sub": "Clearly resistant to changing how they work, and worried the new system adds another clock-in burden.",
                "val": "low"
            }
        ]
    },
    "process_maturity": {
        "step_title": "Written Operating Procedures and Knowledge Retention (Process Maturity & SOP)",
        "question": "Checking your standard operating procedures: has your company written down an SOP for sales quoting and for common customer questions (FAQ)?",
        "sub_hint": "A structured SOP and Q&A library is what an AI assistant has to answer from; without it the assistant can only guess at your business.",
        "options": [
            {
                "label": "Mature written SOPs and a common customer Q&A library (FAQ) already exist",
                "sub": "Business processes are standardised, new staff can be trained from documents, and knowledge has begun to accumulate as a company digital asset.",
                "val": "standard"
            },
            {
                "label": "Some processes exist as verbal agreements but were never written into proper documents",
                "sub": "Relying mainly on long-serving staff's personal memory and day-to-day talk, with no uniform, structured knowledge record.",
                "val": "semi"
            },
            {
                "label": "No SOP at all; everyone improvises from their own experience",
                "sub": "Process varies a lot, and staff turnover easily loses the service standard along with consistent quality.",
                "val": "informal"
            }
        ]
    },
    "digital_workflow": {
        "step_title": "Digital Workflow and Cross-department Reconciliation (Digital Workflow & Collaboration)",
        "question": "Checking cross-department collaboration: from a customer order, to warehouse dispatch, to month-end financial reconciliation, how do your documents move and get verified today?",
        "sub_hint": "Paper delivery notes and re-keying at month end are hours the team repeats every month on work the customer never sees — usually the first place digitalisation pays back.",
        "options": [
            {
                "label": "Documents are approved and routed online, statements generated by the system",
                "sub": "Cross-department data is connected in real time, month-end reconciliation is quick, and repeated re-entry errors are almost gone.",
                "val": "auto"
            },
            {
                "label": "Photos sent in a WeChat group or Excel files passed around, re-entered by hand at month end",
                "sub": "Inconsistent formats and missed documents are a risk, and finance spends several days checking order by order by hand.",
                "val": "semi_auto"
            },
            {
                "label": "Handwritten paper delivery notes (DO) all the way, typed into a PC one by one at month end",
                "sub": "Heavy internal friction, documents easily lost or damaged, and error rates and labour cost stay high.",
                "val": "manual"
            }
        ]
    },
    "data_availability": {
        "step_title": "Business Data Structure and One Consolidated Database (Data Availability & Structure)",
        "question": "Checking the availability of your core data: in what form are your product catalogue, customer records and past transaction data stored today?",
        "sub_hint": "A structured database is the base that connects an AI sales model and automated reporting, and it stops a model inventing quotations out of thin air.",
        "options": [
            {
                "label": "Already held in one cloud database or a standard purchasing/sales stock ERP system",
                "sub": "Has a standard API or spreadsheet export, so it connects cleanly to an AI knowledge base and data dashboards.",
                "val": "structured"
            },
            {
                "label": "Partly in one desktop program, partly on personal phones and scattered spreadsheets",
                "sub": "Clear data silos, and pulling data across departments means copying and converting it by hand.",
                "val": "siloed"
            },
            {
                "label": "Data scattered across handwritten books, invoice receipts and staff personal WeChat",
                "sub": "No structured digital record at all, so the company's core intangible assets cannot be counted or retrieved.",
                "val": "unstructured"
            }
        ]
    }
}


# ─── 逃生口：每一道题都必须给"我不知道"和"情况不是这几个选项"两条出路 ──────────
# 题面只有 2-4 个事实档位时，答不出或情况不在选项里的老板只能瞎选一档，
# 那一档随后就被当成已核验事实去评分、去生成痛点、去推销。
# 这两条出路必须在校验之后追加：_validate_probe_schema 只接受 2-4 个选项，
# 先追加会把模型写的好题一并判成坏题。
ESCAPE_UNSURE_VAL = "__unsure"
ESCAPE_DESCRIBE_VAL = "__describe"

ESCAPE_OPTIONS: List[Dict[str, str]] = [
    {"val": ESCAPE_UNSURE_VAL, "label": "Not sure",
     "sub": "It stays an open question, not a bad mark"},
    {"val": ESCAPE_DESCRIBE_VAL, "label": "Other — I'll describe it",
     "sub": "Type or dictate the way it actually works"},
]

# "不确定"这一条证据的措辞与置信度：它只记录"这一题问过了"。
UNCERTAIN_QUOTE = "Asked in this session; you said you were not sure"
UNCERTAIN_CONFIDENCE = 0.2


def with_escape_hatches(options: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """把两条出路追加到题面选项之后，返回一个新列表。

    三张题库都是模块级字典，就地 append 会把逃生口永久印进题库本体
    （PROBE_TEMPLATES[dim].copy() 只是浅拷贝，options 那个列表仍是共享的）。
    """
    merged: List[Dict[str, Any]] = [dict(o) for o in (options or []) if isinstance(o, dict)]
    present = {str(o.get("val", "")).strip().lower() for o in merged}
    for extra in ESCAPE_OPTIONS:
        if extra["val"] not in present:
            merged.append(dict(extra))
    return merged


def _escape_choice(selected_option: Any, user_answer: str) -> str:
    """这一轮点的是哪条逃生口，不是逃生口就返回 ""。

    菜单点选认 val。开场胶囊那类只回传文字的回答，只认与逃生口标题逐字相同
    （或以 "标题: " 开头）的情况，绝不做关键词匹配——老板顺口说的
    "not sure about the cost" 不能被当成一次选择。
    """
    if isinstance(selected_option, dict):
        val = str(selected_option.get("val", "")).strip().lower()
        if val in (ESCAPE_UNSURE_VAL, ESCAPE_DESCRIBE_VAL):
            return val
    text = str(user_answer or "").strip().lower()
    if not text:
        return ""
    for extra in ESCAPE_OPTIONS:
        label = extra["label"].strip().lower()
        if text in (label, extra["val"]) or text.startswith(label + ":"):
            return extra["val"]
    return ""


def _uncertain_fact_key(dimension: str) -> str:
    """"不确定"这一条挂在哪个 fact_key 上。

    11 项主题用它评分用的规范键：老板后来答出来时，同一行会被升级成真正的档位。
    深挖题与兜底轮没有规范评分键（深挖题的档位另有其键，且答"不知道"会落成扣分），
    沿用访谈既有的 "<维度>_response" 记法，只表示这一题问过了。
    """
    return PROBE_FACT_KEYS.get(dimension) or f"{dimension}_response"


def _dim_display_name(dimension: str) -> str:
    """客户读得到的维度名；深挖题用它的题面标题。"""
    deep = DEEP_PROBES.get(dimension)
    if deep:
        return str(deep.get("step_title") or dimension)
    return DIMENSION_LABELS.get(dimension, dimension)


def _validate_probe_schema(data: Any, dimension: str = "") -> Tuple[bool, str]:
    """Validate that generated probe matches strict frontend and state machine schema."""
    if not isinstance(data, dict):
        return False, "Output is not a valid JSON object"
    q = data.get("question", "")
    if not isinstance(q, str) or len(q.strip()) < 10:
        return False, f"The question is too short or empty (length {len(q.strip()) if isinstance(q, str) else 0})"
    opts = data.get("options", [])
    if not isinstance(opts, list) or len(opts) < 2 or len(opts) > 4:
        return False, f"options must contain 2 to 4 entries (current count {len(opts) if isinstance(opts, list) else 0})"
    for i, opt in enumerate(opts):
        if not isinstance(opt, dict) or not opt.get("label"):
            return False, f"Entry {i+1} in the options list has an empty label"

    # 取值必须落在本维度的规范词表里，否则这次点击无法转成可评分的事实
    domain = _probe_value_domain(dimension) if dimension else []
    if domain:
        allowed = [v for v, _ in domain]
        picked: List[str] = []
        for i, opt in enumerate(opts):
            val = str((opt or {}).get("val", "")).strip().lower()
            if val not in allowed:
                return False, (f"Option {i+1} has val=\"{val}\", which is not an accepted value for this dimension; "
                               f"pick each one from {allowed} only (nothing invented)")
            picked.append(val)
        if len(set(picked)) != len(picked):
            return False, f"Two options land on the same tier: {picked}; each val may only be used once"
        if picked != sorted(picked, key=lambda v: allowed.index(v)):
            want = sorted(picked, key=lambda v: allowed.index(v))
            return False, f"Options must be given from most vulnerable to most mature; the correct order for this set is: {want}"
    return True, ""


def _industry_says(industry: str, *tokens: str) -> bool:
    """英文行业名按整词匹配（否则 retail 会被当成 ai），中文行业名按子串匹配。"""
    low = (industry or "").lower()
    for token in tokens:
        if token.isascii():
            if re.search(r"(?<![a-z0-9])" + re.escape(token.lower()) + r"(?![a-z0-9])", low):
                return True
        elif token in industry:
            return True
    return False


def start_diagnostic_session(company_name: str, industry: str, team_size: str, annual_turnover: str,
                            biggest_challenge: str = "", growth_objective: str = "",
                            current_tools: str = "") -> Dict[str, Any]:
    """
    Initialize an agentic diagnostic session.
    Creates SQLite dossier with Step 1 complete business discovery metadata.
    """
    session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name=company_name,
        industry=industry,
        team_size=team_size,
        annual_turnover=annual_turnover,
        biggest_challenge=biggest_challenge,
        growth_objective=growth_objective,
        current_tools=current_tools
    )


    # First probe: tailored to the specific industry supply chain bottlenecks
    if _industry_says(industry, "auto parts", "汽配", "五金"):
        first_q = (
            f"Hello! Let me start with two questions about how a Malaysian {industry} business usually runs.\n\n"
            f"In auto parts and hardware wholesale and import/export, owners report two core risks: first, customers urgently needing parts after closing hours with nobody able to quote straight away; "
            f"second, documents scattered across paper delivery notes or a staff member's personal WhatsApp.\n\n"
            f"How does your company handle enquiries that arrive after closing today (after 7pm)? Are your reconciliation documents handwritten, or already handled by a system?"
        )
        first_pills = [
            "Nobody replies after closing; documents are handwritten on paper delivery notes",
            "Staff take orders on personal phones over WhatsApp, finance sits on one desktop PC",
            "Orders are already system-managed, but urgent night enquiries are often missed"
        ]
    elif _industry_says(industry, "food", "beverage", "restaurant", "kitchen", "catering", "cafe", "餐饮"):
        first_q = (
            f"Hello! Let me start with two questions about how a Malaysian {industry} business usually runs.\n\n"
            f"Chain outlets and central kitchens most often get stuck in two places: night-time stock and document reconciliation across several outlets, and answering takeaway and supply enquiries.\n\n"
            f"How do your outlet replenishment orders and night-time purchase documents move today? Is there a central reconciliation system?"
        )
        first_pills = [
            "Each outlet photographs documents to finance over WhatsApp every night",
            "Documents are checked by hand, and month-end reconciliation means days of overtime",
            "We already have integrated POS and stock control, but no automatic clearing"
        ]
    elif _industry_says(industry, "iot", "smart hardware", "embedded", "firmware", "sensor", "物联", "智能硬件"):
        first_q = (
            f"Hello! Let me start with two questions about how a Malaysian {industry} business usually runs.\n\n"
            f"For technology companies in IoT and smart hardware, the two most core risks are usually: firmware source code and hardware drawings scattered across engineers' individual machines with no automated off-site version backup; "
            f"and overseas customers and system integrators sending enquiries at night with no 24/7 technical support response.\n\n"
            f"Does your company keep its core engineering assets (source code / drawings) in centrally encrypted off-site cloud backup? How are technical questions outside working hours answered?"
        )
        first_pills = [
            "Drawings and firmware sit on engineers' computers, with no automated off-site backup",
            "Engineers reply from their personal WhatsApp, so night enquiries are often missed",
            "We have version control, but need a highly available cloud gateway and 24/7 smart selection support"
        ]
    elif _industry_says(industry, "it", "software", "ai", "saas", "technology", "科技", "软件"):
        first_q = (
            f"Hello! Let me start with two questions about how a Malaysian {industry} business usually runs.\n\n"
            f"In software development and technical services, the biggest pain is usually technicians dealing with customers from personal free mailboxes, which weakens customer compliance trust, and systems running without an SLA-grade, DDoS-protected cloud host in another location.\n\n"
            f"Does your company use a business mailbox on its own corporate domain for customer contact today? Is there cloud disaster recovery for your core services or customer data?"
        )
        first_pills = [
            "The team still uses free Gmail, and the server runs in one place with no off-site recovery",
            "Requirements are discussed over personal WhatsApp and documents are scattered, so nothing is compliant to trace",
            "We have a basic cloud server, and need business-grade domain protection and SLA disaster recovery"
        ]
    elif _industry_says(industry, "consulting", "consultancy", "accounting", "audit", "legal", "professional", "专业服务", "咨询", "会计"):
        first_q = (
            f"Hello! Let me start with two questions about how a Malaysian {industry} business usually runs.\n\n"
            f"Accounting and professional firms most often get stuck in two places: client tax and supporting documents sent to and from personal free mailboxes, and working papers stored only on an employee's individual machine.\n\n"
            f"Which mailbox does your firm mainly use today to exchange client documents? Is client data backed up safely off site?"
        )
        first_pills = [
            "Usually a personal free Gmail for client documents, data on the front-desk computer",
            "Client documents received over personal WhatsApp, occasionally copied to a USB drive",
            "We have our own business domain mailbox and are looking for automatic encrypted backup"
        ]
    else:
        first_q = (
            f"Hello! Let me start with two questions about how a Malaysian {industry} business usually runs.\n\n"
            f"Small businesses most often get stuck in two places: salespeople each dealing with customers on their own phone, so when someone resigns the customers go with them; and the core accounting books kept on one single computer.\n\n"
            f"What tool does your company mainly use today to receive customer orders? Is your core data automatically backed up to the cloud?"
        )
        first_pills = [
            "No website; deals run through personal WhatsApp and handwritten delivery notes",
            "Business documents are kept on one front-desk computer, with no cloud backup",
            "We have basic digitalisation, but no automatic tool to capture night-time enquiries"
        ]

    # 开场那两问同样要有逃生口：老板答不出，或情况不是这三条时，不能逼他挑一个档位。
    # 统一成与其它探针一样的选项结构（三条预设答案没有规范取值，val 留空即按文字作答）。
    first_pills = with_escape_hatches([{"val": "", "label": p, "sub": ""} for p in first_pills])

    SqlWikiEngine.update_state_ledger(session_id, next_probe_question=first_q, increment_turn=False)
    live_tree = SqlWikiEngine.get_live_wiki_tree(session_id)

    # Initial Dynamic Container protocol —— 置信度与盲区必须来自本次已锁证的事实
    full = SqlWikiEngine.calculate_full_completeness(session_id)
    init_container = {
        "container_id": f"box_probe_init_{uuid.uuid4().hex[:4]}",
        "sop_stage": "Step 1: Business Model and Supply Chain Probe (Business Discovery)",
        "confidence_score": round(full["total_ratio"], 2),
        "missing_blindspots": (full["missing_dms"] + full["missing_ars"])[:3],
        "dynamic_question": {
            "title": f"Business model and day-to-day reconciliation check — {industry}",
            "prompt": first_q,
            "rationale": "",
        },
        "visual_state": "EXPAND_CONTAINER"
    }

    return {
        "session_id": session_id,
        "company_name": company_name,
        "industry": industry,
        "first_question": first_q,
        "pills": first_pills,
        "dynamic_container": init_container,
        "tree": live_tree
    }


def generate_scraper_critique(company_name: str, industry: str, crawl_result: Dict[str, Any]) -> str:
    """
    Call Cradilot LLM to perform an incisive commercial audit of the scraped website.
    """
    prompt = prompt_web_scraper_critique(company_name, industry, crawl_result)
    try:
        critique = engine_client.generate(prompt, max_tokens=250)
        # last_call_degraded means the text below came from the built-in rule engine, not a
        # model. It cannot cite this scan, so discard it and use the grounded review instead.
        if (critique and not engine_client.last_call_degraded
                and len(critique.strip()) > 15 and "[Rule engine mode" not in critique):
            return critique.strip()
    except Exception:
        pass

    # Grounded review: restates only what this run's probe measured.
    has_ssl = crawl_result.get("has_ssl", False)
    latency = crawl_result.get("response_time_ms", 0)
    mobile = crawl_result.get("mobile_friendly", False)
    if not has_ssl:
        return f"For a {industry} business, the scan found no valid SSL certificate on this site, so the browser shows a red 'not secure' warning before the customer has read a word. For a buyer who has never dealt with you, that usually ends the enquiry there."
    elif not mobile:
        return f"The site does have encryption, but it fails the mobile responsive check. Most SME buyers look on a phone first, and a page they have to zoom and drag to read quietly costs enquiries."
    elif latency > 800:
        return f"The scan measured {latency} ms of server round-trip on this run, so the first screen loads slowly. A slow first screen loses buyers before the page has earned their attention."
    else:
        return f"The site's basic network configuration is sound: HTTPS encryption is on and responses are normal ({latency} ms). The next step is to connect an automated lead conversion funnel and a 24/7 smart response channel."


def generate_agentic_probe(session_id: str, target_dim: str, step_num: int) -> Dict[str, Any]:
    """
    Generate an agentic probe via Cradilot LLM tailored to this enterprise,
    anchored on SQLite dossier and verified facts.
    Includes strict Schema validation and 1-attempt retry.
    """
    tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    dossier = tree.get("dossier", {})
    company_name = dossier.get("company_name", "Your company")
    industry = dossier.get("industry", "General trading")
    team_size = dossier.get("team_size", "6-20 people")
    annual_turnover = dossier.get("annual_turnover", "RM 2M - 10M")

    # Collect known facts from verified dimensions（"不确定"那一条不是事实，不进提示词）
    verified_facts = []
    for d in tree.get("dimensions", []):
        if d.get("is_verified") and d.get("evidence_list"):
            for ev in confirmed_nodes(d["evidence_list"]):
                verified_facts.append(f"{d['dimension_label']}: {ev['quote_text']}")
    for f in tree.get("ars_factors", []):
        if f.get("is_verified") and f.get("evidence_list"):
            for ev in confirmed_nodes(f["evidence_list"]):
                verified_facts.append(f"{f['factor_label']}: {ev['quote_text']}")

    prompt = prompt_agentic_probe_generation(
        company_name=company_name,
        industry=industry,
        team_size=team_size,
        annual_turnover=annual_turnover,
        target_dimension=target_dim,
        verified_facts=verified_facts,
        step_num=step_num,
        value_domain=_probe_value_domain(target_dim)
    )

    data = None
    try:
        raw_json = engine_client.generate(prompt, format_json=True, max_tokens=400)
        parsed = json.loads(raw_json)
        is_valid, err_msg = _validate_probe_schema(parsed, target_dim)
        if is_valid:
            data = parsed
        else:
            # Schema validation failed: retry once with targeted error feedback
            retry_prompt = prompt_agentic_probe_retry(company_name, industry, target_dim, step_num, err_msg)
            retry_raw = engine_client.generate(retry_prompt, format_json=True, max_tokens=400)
            retry_parsed = json.loads(retry_raw)
            retry_valid, _ = _validate_probe_schema(retry_parsed, target_dim)
            if retry_valid:
                data = retry_parsed
    except Exception:
        pass

    if data:
        # Guarantee dimension code and step_title are present
        data["dimension"] = target_dim
        if not data.get("step_title"):
            dim_label = DIMENSION_LABELS.get(target_dim, target_dim)
            data["step_title"] = dim_label
        # 校验只看模型写的档位选项（2-4 个），逃生口在校验通过之后才追加
        data["options"] = with_escape_hatches(data.get("options"))
        return data

    # High-quality fallback template contextualized to this industry
    # 深拷贝：.copy() 是浅拷贝，直接 append 会把逃生口永久写进共享题库
    fallback = copy.deepcopy(PROBE_TEMPLATES.get(target_dim, PROBE_TEMPLATES["cloud"]))
    dim_label = DIMENSION_LABELS.get(target_dim, target_dim)
    fallback["step_title"] = dim_label
    fallback["dimension"] = target_dim
    fallback["options"] = with_escape_hatches(fallback.get("options"))
    return fallback


def build_dynamic_container_payload(session_id: str, probe: Dict[str, Any], target_dim: str, step_num: int) -> Dict[str, Any]:
    """
    Build standard Dynamic Container JSON protocol conforming strictly to Blueprint Section 4.
    Front-end dynamically renders card DOM with 0 hardcoded questions.
    """
    full = SqlWikiEngine.calculate_full_completeness(session_id)
    confidence = full["total_ratio"]
    missing = full["missing_dms"] + full["missing_ars"]

    stage_name = DIMENSION_LABELS.get(target_dim, target_dim)
    sop_step = min(5, max(1, step_num - 1))
    sop_stage = f"Step {sop_step}: {stage_name}"

    return {
        "container_id": f"box_probe_{target_dim}_{uuid.uuid4().hex[:4]}",
        "sop_stage": sop_stage,
        "confidence_score": round(confidence, 2),
        "missing_blindspots": missing[:3],
        "dynamic_question": {
            "title": probe.get("step_title") or f"{stage_name} focused check",
            "prompt": probe.get("question", ""),
            "rationale": probe.get("sub_hint") or "",
        },
        "visual_state": "EXPAND_CONTAINER"
    }


def get_first_agentic_probe(session_id: str) -> Dict[str, Any]:
    """Retrieve the first dynamic agentic probe following website inspection."""
    full = SqlWikiEngine.calculate_full_completeness(session_id)
    # 首题同样按提问优先级取第一项 missing（先问一眼看得见的）
    target_dim = _pick_next_target(full) or "cloud"
    probe = generate_agentic_probe(session_id, target_dim, 3)
    probe["dimension"] = target_dim
    probe["step_num"] = 3
    probe["dynamic_container"] = build_dynamic_container_payload(session_id, probe, target_dim, 3)
    return probe


# 评分层的真实门禁条件就一条，写在 core/recommendation.generate_action_roadmap
# （deferred = dms_score < 40.0），core/ars_engine 的 is_hard_locked 是同一条。
# 这里把它念出来，不改它，也不另编一个数字。
PHASE3_DEFERRED_BELOW_DMS = 40.0


def _cot_step(key: str, stage: str, title: str, thought: str, confirmed: bool) -> Dict[str, Any]:
    """前端按 key 定位这四步，字段形状不得随意增减。"""
    return {
        "stage": stage,
        "title": title,
        "thought": thought,
        "summary": thought,
        "key": key,
        "active": True,
        "confirmed": bool(confirmed),
    }


def _cot_quote(text: Any, limit: int = 90) -> str:
    """引用客户原话或选项标题时截断，思考卡不是把长答案再念一遍的地方。"""
    clean = " ".join(str(text or "").split())
    if not clean:
        return ""
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "..."


def build_cradilot_thought_chain(company_name: str, industry: str, target_dim: str, user_answer: str,
                                 recorded: Optional[Dict[str, Any]] = None,
                                 completeness: Optional[Dict[str, Any]] = None,
                                 machine_rows: Optional[List[Dict[str, Any]]] = None,
                                 site_audit: Optional[Dict[str, Any]] = None,
                                 dms_provisional: Optional[float] = None,
                                 next_dim: str = "",
                                 closing: bool = False) -> List[Dict[str, Any]]:
    """
    Four-step chain of thought for the step-3 workbench, in plain English.

    与旧版的区别在于这里不再预告还没算出来的东西：每一步只准引用调用方当场递进来
    的数据（本轮采到的证据与它的出处、取证完整度、第②步快照、纯函数即时分数），
    没递进来的就直说没递进来。confirmed 只在该步的陈述确实有在场证据支撑时才为 True，
    前端据此把序号换成对勾；答不出的那一格永远是"未确定"，不会被念成缺失。
    """
    dim_label = _dim_display_name(target_dim)
    comp = completeness or {}
    asked = comp.get("total_explored_count")
    total = comp.get("total_dimension_count", len(ALL_TRACKED_DIMENSIONS))
    confirmed_n = comp.get("confirmed_count")
    answered = bool(recorded) and not (recorded or {}).get("uncertain")

    # ── 1. 本轮究竟记下了什么，凭什么记下的 ──
    if recorded and recorded.get("uncertain"):
        s1 = (f"Noted for {dim_label}: you said you were not sure. That is kept as an open question, "
              f"not as a fact about your business.")
        confirmed1 = True
    elif recorded:
        quote = _cot_quote(recorded.get("quote"))
        basis = str(recorded.get("basis") or "this answer")
        s1 = f"Recorded for {dim_label}"
        s1 += f": \"{quote}\"" if quote else f": {recorded.get('value') or 'your answer'}"
        s1 += f" — taken from {basis}."
        confirmed1 = True
    elif asked is not None:
        s1 = (f"Nothing new was confirmed for {dim_label} in this round. {asked} of {total} areas have been "
              f"asked about so far.")
        confirmed1 = False
    else:
        s1 = (f"This step was not handed the evidence record for {dim_label}, so it claims nothing about "
              f"what was captured.")
        confirmed1 = False
    if asked is not None and recorded:
        s1 += f" {asked} of {total} areas have now been asked about."

    # ── 2. 第②步的机检对这个维度说了什么 ──
    rows = [r for r in (machine_rows or []) if isinstance(r, dict)]
    audit = site_audit or {}
    audit_summary = audit.get("summary") or {}
    graded = audit_summary.get("items_graded")
    if rows:
        clear = sum(1 for r in rows if str(r.get("state", "")).lower() == "pass")
        gaps = [str(r.get("title") or r.get("check") or "") for r in rows
                if str(r.get("state", "")).lower() == "fail"]
        s2 = (f"The step-2 machine check on {audit.get('url') or 'the address you gave'} already measured "
              f"{len(rows)} item(s) about {dim_label}: {clear} came back clear")
        if gaps:
            s2 += f", and {len(gaps)} came back as a gap that was measured, not guessed ({'; '.join(gaps[:2])})"
        s2 += "."
        confirmed2 = True
    elif audit and graded is not None:
        s2 = (f"The step-2 machine check graded {graded} items on {audit.get('url') or 'the address you gave'} "
              f"({audit_summary.get('pass') or 0} clear, {audit_summary.get('fail') or 0} with a measured gap), but it "
              f"has no measurement for {dim_label}, so this area rests on what you told us.")
        confirmed2 = bool(graded) and answered
    else:
        s2 = (f"No step-2 machine check is stored for this session, so {dim_label} rests on your answer alone, "
              f"and no cost figure is attached to it at this stage.")
        confirmed2 = answered
    if recorded and recorded.get("uncertain"):
        s2 += " You were not sure about this area, so it stays open and is not counted against you."
        if not rows:
            confirmed2 = False

    # ── 3. 真实门禁规则此刻是否生效 ──
    if dms_provisional is None:
        s3 = ("The scoring functions decide this from the stored evidence; this step was not handed those figures, "
              "so no number is quoted here.")
        confirmed3 = False
    elif not confirmed_n:
        s3 = (f"No area holds a confirmed answer yet, so the provisional score of {dms_provisional:g} rests entirely "
              f"on neutral placeholders. The guardrail is not judged on placeholders.")
        confirmed3 = False
    else:
        held = (f"holding phase 3 back right now" if dms_provisional < PHASE3_DEFERRED_BELOW_DMS
                else f"not holding phase 3 back at this moment")
        s3 = (f"Guardrail as it is written in this build: phase 3 of the plan, the AI and automation purchase, is "
              f"deferred while the digital maturity score is below {PHASE3_DEFERRED_BELOW_DMS:g}. On the "
              f"{confirmed_n} area(s) confirmed so far the provisional score is {dms_provisional:g}, so the rule is "
              f"{held}; it is recalculated from the stored evidence when the interview closes.")
        confirmed3 = True

    # ── 4. 接下来做什么 ──
    open_codes = (comp.get("missing_dms") or []) + (comp.get("missing_ars") or [])

    def _open_note(exclude: str = "") -> str:
        rest = [_dim_display_name(d) for d in open_codes if d != exclude]
        if not rest:
            return f" All {total} areas have been asked about." if not exclude else ""
        shown = ", ".join(rest[:3]) + (f" and {len(rest) - 3} more" if len(rest) > 3 else "")
        return f" Still not asked about: {shown}."

    if closing:
        s4 = (f"All {total} areas have now been asked about for {company_name}. The scorecard and the phased plan are "
              f"built from the {confirmed_n if confirmed_n is not None else 'confirmed'} area(s) holding a confirmed "
              f"answer; areas left open are counted neutrally and are not deducted as missing.")
        confirmed4 = confirmed_n is not None
    elif next_dim:
        s4 = f"Next for {company_name}: {_dim_display_name(next_dim)}.{_open_note(next_dim)} Nothing enters the plan before that answer is stored."
        confirmed4 = bool(comp)
    else:
        s4 = (f"The next question is picked from the areas still without an evidence record.{_open_note()} "
              f"This step was not handed that list, so it names no question.")
        confirmed4 = False

    return [
        _cot_step("mode_fact", "Fact recorded",
                  "1. Business model and fact deconstruction (Business Deconstruction)", s1, confirmed1),
        _cot_step("bleeding_inference", "Evidence compared",
                  "2. Core business choke point inference (Bottlenecks)", s2, confirmed2),
        _cot_step("guardrail_reflection", "Guardrail check",
                  "3. Self-review and customer impulse correction (Critique & Self-Correction)", s3, confirmed3),
        _cot_step("action_decision", "Next step",
                  "4. Action decision for delivery (Action & Strategy)", s4, confirmed4),
    ]


# ─── 深挖题：CRM 与 Marketing 的"真实运作方式" ────────────────────────────────
# 11 道主题每题只产出一个档位 token，评出分够，但不足以描述"这家公司的销售到底怎么跑"。
# 官方 Step 2 要的是能据此给出建议的理解，所以这四题作为奖励轮：
# 主题答完且时间预算还有余时才问，答了则细化评分，没答则维持原档不扣分。
DEEP_PROBES: Dict[str, Dict[str, Any]] = {
    "crm_lead_source": {
        "step_title": "Where enquiries came from, and whether that can be traced",
        "question": "Look back at your last 5 closed customers: can you say where each one first came from? "
                    "(for example: referred by an existing customer / Facebook / Google search / a trade show / an agent)",
        "sub_hint": "If the source cannot be named, there is no way to judge which channel deserves more money and which one is burning it.",
        "options": [
            {"label": "Cannot say, I only remember it was a friend", "sub": "Cannot judge where to invest",
             "val": "unknown", "fact_key": "lead_source_known"},
            {"label": "We ask where they came from when the deal closes", "sub": "Aware of it, but done manually",
             "val": "asked", "fact_key": "lead_source_known"},
            {"label": "The system shows the source (UTM / pixel / form)", "sub": "Source can be traced automatically",
             "val": "tracked", "fact_key": "lead_source_known"},
        ],
    },
    "crm_followup_owner": {
        "step_title": "Who owns the follow-up, and the handover risk",
        "question": "For a customer going from first enquiry to closed deal, does the person following up ever change? "
                    "If your most experienced salesperson resigned tomorrow, could anyone carry on their open customers?",
        "sub_hint": "Who the customer records belong to decides whether a resignation equals a lost customer.",
        "options": [
            {"label": "Whoever brought the customer keeps them; nobody else can take over", "sub": "Customer assets sit with the individual",
             "val": "personal", "fact_key": "followup_owner"},
            {"label": "Someone is assigned to take over, but they must ask everything again", "sub": "Ownership exists, history does not",
             "val": "shared_untracked", "fact_key": "followup_owner"},
            {"label": "Follow-up notes are in the company system, whoever takes over can read them", "sub": "Customer assets belong to the company",
             "val": "designated", "fact_key": "followup_owner"},
        ],
    },
    "crm_quote_to_order": {
        "step_title": "How documents move from quotation to order",
        "question": "From the quotation to the order and then to the invoice, does the same record carry the details across, "
                    "or does someone have to type the same content in again?",
        "sub_hint": "Re-keying is the main source of leaked man-hours and wrong amounts.",
        "options": [
            {"label": "Entered again or copied out by hand", "sub": "Man-hour and error costs keep building up",
             "val": "rekeyed", "fact_key": "quote_to_order"},
            {"label": "Some shared templates, but still checked by hand", "sub": "Semi-automatic",
             "val": "semi", "fact_key": "quote_to_order"},
            {"label": "The quotation turns straight into the order and invoice", "sub": "One data source throughout",
             "val": "one_system", "fact_key": "quote_to_order"},
        ],
    },
    "crm_pipeline_visible": {
        "step_title": "Open deals management can actually see",
        "question": "Could you tell me right now: how many customers you are negotiating with, roughly what they add up to, "
                    "and which one is most likely to close this week?",
        "sub_hint": "A pipeline you cannot see is revenue you cannot predict.",
        "options": [
            {"label": "Cannot say; I have to ask around", "sub": "Revenue cannot be predicted",
             "val": "none", "fact_key": "pipeline_visible"},
            {"label": "Only works it out at the month-end roll-up", "sub": "One month behind",
             "val": "monthly_only", "fact_key": "pipeline_visible"},
            {"label": "A live board is visible any time", "sub": "Predictable and open to intervention",
             "val": "realtime", "fact_key": "pipeline_visible"},
        ],
    },
    "marketing_channel_mix": {
        "step_title": "Channels spent on, and the yearly scale",
        "question": "Over the past year, which channels did you spend money on for advertising and promotion? Roughly how much per month?",
        "sub_hint": "Only where there is spend is there an attribution question; the size of the spend sets the budget tier of the solution.",
        "options": [
            {"label": "Never spent anything; organic and referrals only", "sub": "No paid spend",
             "val": "none", "fact_key": "marketing_spend"},
            {"label": "One or two channels, around RM 1,000 a month", "sub": "Small trial spend",
             "val": "under_1k", "fact_key": "marketing_spend"},
            {"label": "RM 1,000-5,000 a month", "sub": "Steady spend",
             "val": "1k_5k", "fact_key": "marketing_spend"},
            {"label": "More than RM 5,000 a month", "sub": "Already a major acquisition cost",
             "val": "over_5k", "fact_key": "marketing_spend"},
        ],
    },
}

# ─── 菜单答案 → 规范事实（确定性，不依赖 LLM）────────────────────────────────
# 每个探针都是固定菜单，选项本身就带规范取值。既然取值已知，就不该再让模型猜一次，
# 更不该在猜不出时落一个 "recorded" 占位——那个占位曾被评分层读成"贵司没有 CRM"。
#
# 两张题库对同一维度用了不同词表（ai: leak/manual_stare/covered 对 manual/partial/middleware；
# web: none/outdated/modern 对 no_site/dormant/standard），因此这里把两套全部映射到
# SqlWikiEngine.get_full_assessment_input 实际读取的那一套规范取值上。
PROBE_FACT_KEYS: Dict[str, str] = {
    "web": "web_engine_status",
    "cloud": "backup_strategy",
    "crm": "crm_status",
    "marketing": "marketing_tracker",
    "cyber": "email_type",
    "ai": "ai_tier",
    "leadership": "leadership_willingness",
    "employee_skills": "employee_skill_level",
    "process_maturity": "has_sop",
    "digital_workflow": "order_reconcile_flow",
    "data_availability": "data_availability_status",
}

PROBE_VALUE_ALIASES: Dict[str, Dict[str, str]] = {
    "web": {"none": "none", "no_site": "none", "outdated": "outdated", "dormant": "outdated",
            "modern": "modern", "standard": "modern"},
    "cloud": {"single_pc": "single_pc", "manual_usb": "manual_usb", "cloud_auto": "cloud_auto"},
    "crm": {"personal_whatsapp": "personal_whatsapp", "excel_manual": "spreadsheet",
            "excel_ledger": "spreadsheet", "formal_crm": "formal_crm"},
    "marketing": {"none": "none", "referral_only": "none", "untracked": "untracked",
                  "ad_hoc_ads": "untracked", "pixel_and_ga4": "pixel_and_ga4",
                  "full_retargeting": "pixel_and_ga4"},
    "cyber": {"free": "free_gmail", "free_gmail": "free_gmail", "business": "business_domain",
              "business_domain": "business_domain", "compliant": "business_domain"},
    "ai": {"leak": "none", "manual": "none", "manual_stare": "none", "none": "none",
           "partial": "individual_use", "ad_hoc": "individual_use", "chatgpt": "individual_use",
           "pilot": "workflow_pilot", "middleware": "deployed", "covered": "deployed",
           "deployed": "deployed"},
    "leadership": {"reluctant": "reluctant", "conservative": "conservative", "high": "high"},
    "employee_skills": {"low": "low", "medium": "medium", "mixed": "medium", "high": "high"},
    "process_maturity": {"false": "false", "informal": "false", "semi": "partial",
                         "partial": "partial", "standard": "true", "true": "true"},
    "digital_workflow": {"manual": "manual", "semi": "semi", "semi_auto": "semi", "auto": "auto"},
    "data_availability": {"unstructured": "unstructured", "siloed": "unstructured",
                          "spreadsheet": "spreadsheet", "structured": "structured"},
}


# 每题的规范取值梯度，一律"由脆弱到成熟"。两张题库各自的排列方向并不一致
# （leadership 一库写 high 在前，另一库写 reluctant 在前），若直接合并展示，
# 客户看到的选项阶梯会是乱的，喂给模型的取值表也会是乱的。
PROBE_RUNG_ORDER: Dict[str, List[str]] = {
    "web": ["none", "outdated", "modern"],
    "cloud": ["single_pc", "manual_usb", "cloud_auto"],
    "crm": ["personal_whatsapp", "spreadsheet", "formal_crm"],
    "marketing": ["none", "untracked", "pixel_and_ga4"],
    "cyber": ["free_gmail", "business_domain"],
    "ai": ["none", "individual_use", "workflow_pilot", "deployed"],
    "leadership": ["reluctant", "conservative", "high"],
    "employee_skills": ["low", "medium", "high"],
    "process_maturity": ["false", "partial", "true"],
    "digital_workflow": ["manual", "semi", "auto"],
    "data_availability": ["unstructured", "spreadsheet", "structured"],
}


def _rung_index(dimension: str, val: str) -> int:
    """该取值在本维度梯度里的位置；不在表里排到最后（不打乱已有顺序）。"""
    order = PROBE_RUNG_ORDER.get(dimension) or []
    aliases = PROBE_VALUE_ALIASES.get(dimension) or {}
    rung = aliases.get(val, val)
    return order.index(rung) if rung in order else len(order)


def _probe_options(dimension: str) -> List[Dict[str, Any]]:
    """合并两张题库的同维度选项，并按脆弱→成熟的梯度排列。

    按标题去重：两库常用同一 val 配不同措辞，按 val 去重会丢掉其中一库的标题，
    那一库的点击就解析不出来。
    """
    merged: List[Dict[str, Any]] = []
    seen: set = set()
    for bank in (PROBE_TEMPLATES, DETERMINISTIC_PROBES):
        for opt in (bank.get(dimension) or {}).get("options", []) or []:
            val = str(opt.get("val", "")).strip().lower()
            label = str(opt.get("label", "")).strip().lower()
            if not val or not label or label in seen:
                continue
            seen.add(label)
            merged.append(opt)
    return sorted(merged, key=lambda o: _rung_index(dimension, str(o.get("val", "")).strip().lower()))


def _probe_value_domain(dimension: str) -> List[tuple]:
    """
    本维度的规范取值梯度：一个档位一条，按"由脆弱到成熟"排列。

    AI 可以改写标题措辞，但取值必须从这里逐字选——同一档位重复出现等于少问一题。
    """
    if dimension in DEEP_PROBES:
        out, seen = [], set()
        for o in DEEP_PROBES[dimension]["options"]:
            v = str(o.get("val", "")).strip().lower()
            if v and v not in seen:
                seen.add(v)
                out.append((v, str(o.get("label") or "")))
        return out

    aliases = PROBE_VALUE_ALIASES.get(dimension)
    if not aliases:
        return []
    out, seen = [], set()
    for opt in _probe_options(dimension):          # 已按梯度排序
        raw = str(opt.get("val", "")).strip().lower()
        rung = aliases.get(raw)
        if rung and rung not in seen:
            seen.add(rung)
            out.append((raw, str(opt.get("label") or "")))
    return out


def _fact_from_option(dimension: str, option: Any) -> Optional[Dict[str, str]]:
    """
    用户点选的那个选项本身就是证据，不需要再从措辞里猜。

    只认本维度的规范取值词表：取值不在表里（例如模型自造的 "vulnerable"）返回 None，
    交回文本解析路径——宁可少锁一证，也不能把陌生取值当成已知档位。
    """
    if not isinstance(option, dict):
        return None
    val = str(option.get("val", "")).strip().lower()
    label = str(option.get("label", "")).strip()
    if not val:
        return None

    if dimension in DEEP_PROBES:
        match = next((o for o in DEEP_PROBES[dimension]["options"]
                      if str(o.get("val", "")).strip().lower() == val), None)
        if not match:
            return None
        return {"fact_key": match["fact_key"], "fact_value": val,
                "quote": (label or match.get("label") or val)[:200]}

    fact_key = PROBE_FACT_KEYS.get(dimension)
    aliases = PROBE_VALUE_ALIASES.get(dimension) or {}
    if not fact_key or val not in aliases:
        return None
    bank_label = next((str(o.get("label") or "") for o in _probe_options(dimension)
                       if str(o.get("val", "")).strip().lower() == val), "")
    return {"fact_key": fact_key, "fact_value": aliases[val],
            "quote": (label or bank_label or val)[:200]}


def _menu_match(dimension: str, answer: str) -> Optional[Dict[str, str]]:
    """
    把一次菜单回答翻译成 (fact_key, fact_value) 证据。

    匹配强度：val 全等 > 选项标题全等 > 选项标题被回答包含。
    自由文本一律返回 None，交给关键词抽取与 LLM 路径——不能把没把握的话当成选择。
    """
    text = str(answer or "").strip().lower()
    fact_key = PROBE_FACT_KEYS.get(dimension)

    # 深挖题的选项自带 fact_key（键名本身就限定了维度），取值按原文入库
    if fact_key is None:
        deep = DEEP_PROBES.get(dimension)
        if not deep:
            return None
        option = next((o for o in deep.get("options") or []
                       if text in (str(o.get("label", "")).strip().lower(),
                                   str(o.get("val", "")).strip().lower())
                       or (len(str(o.get("label", ""))) > 5
                           and str(o.get("label", "")).strip().lower() in text)), None)
        if not option:
            return None
        return {"fact_key": option["fact_key"], "fact_value": str(option["val"]).lower(),
                "quote": option.get("label") or str(answer)[:200]}

    if not text:
        return None
    options = _probe_options(dimension)
    alias = PROBE_VALUE_ALIASES.get(dimension, {})

    matched_val: Optional[str] = None
    matched_label: str = ""
    for opt in options:
        if str(opt.get("val", "")).strip().lower() == text:
            matched_val, matched_label = opt.get("val"), opt.get("label", "")
            break
    if matched_val is None:
        for opt in options:
            label = str(opt.get("label", "")).strip().lower()
            if label and (label == text or (len(label) > 5 and label in text)):
                matched_val, matched_label = opt.get("val"), opt.get("label", "")
                break
    if matched_val is None:
        return None

    value = alias.get(str(matched_val).strip().lower())
    if value is None:
        # 词表没覆盖到的取值：宁可回落 LLM，也不要写一个引擎读不懂的值
        return None
    return {"fact_key": fact_key, "fact_value": value,
            "quote": matched_label or str(answer)[:200]}


# ─── 时间预算：官方要求「5 分钟内完成分析」，此前无任何代码保障这一点 ──────────────
# 完成门槛要求 6 维 DMS + 5 项 ARS 全部核验＝11 题。菜单点选已改走确定性采集（近乎零延迟），
# 但自由文本仍要经模型解读（engine_client 自述单题 10-20 秒）。预算耗尽后一律改用零延迟的
# 规则探针收敛，宁可少问两题，也不要把一份卡住的报告交给评委。
DIAG_TIME_BUDGET_SECONDS = float(os.environ.get("CRADILOT_DIAG_BUDGET_SECONDS", "210"))

DETERMINISTIC_PROBES: Dict[str, Dict[str, Any]] = {
    "web": {
        "step_title": "Official website and domain assets",
        "question": "Does your company have a public official website or its own domain today? If yes, when did someone last update the content?",
        "sub_hint": "The website is where out-of-state and overseas customers form their first trust in you, and it sets the volume of branded enquiries.",
        "options": [
            {"label": "No website; only WhatsApp and referrals", "sub": "Strangers from the public internet cannot verify the company", "val": "no_site"},
            {"label": "A website exists, but not updated for years and broken on mobile", "sub": "An entrance with no conversion, like an old business card left behind", "val": "dormant"},
            {"label": "A website maintained regularly, adaptive on phones", "sub": "The digital front door foundation is already in place", "val": "standard"}
        ]
    },
    "cloud": {
        "step_title": "Core data disaster recovery and cloud backup",
        "question": "Where are your accounting ledger, customer quotations and engineering drawings stored today? If that computer's hard drive failed tomorrow, how long before you could trade again?",
        "sub_hint": "Single-machine storage stops the whole business when ransomware or a hardware fault hits, and the recovery time sets the size of the loss.",
        "options": [
            {"label": "Only on one computer, no second copy", "sub": "One point of failure; the books can be lost in one go", "val": "single_pc"},
            {"label": "Occasionally copied to an external drive or USB stick", "sub": "Depends on people remembering; no cover for fire or theft", "val": "manual_usb"},
            {"label": "Business-grade cloud backup, encrypted automatically every day", "sub": "Off-site recovery in place, with fast restart capability", "val": "cloud_auto"}
        ]
    },
    "crm": {
        "step_title": "Customer asset records and who owns the follow-up",
        "question": "Are your customer enquiry records and follow-up progress kept in a company system, or on a salesperson's own phone WhatsApp? What happens if that person leaves?",
        "sub_hint": "Who the customer records belong to decides whether a resignation equals a lost customer.",
        "options": [
            {"label": "On staff personal phones and WeChat, no company summary", "sub": "A resignation takes the customer relationship with it", "val": "personal_whatsapp"},
            {"label": "A central Excel ledger", "sub": "Records exist, but no reminders and no funnel", "val": "excel_ledger"},
            {"label": "One CRM system managing every deal", "sub": "Customer assets already belong to the company", "val": "formal_crm"}
        ]
    },
    "marketing": {
        "step_title": "Where customers come from, and whether results can be measured",
        "question": "Which channels bring most of your customers today? Could you say how many orders a particular ad or platform spend actually produced last month?",
        "sub_hint": "Promotion spend that cannot be attributed turns into pure cost.",
        "options": [
            {"label": "All referrals, with no tracking at all", "sub": "Growth cannot be repeated or optimised", "val": "none"},
            {"label": "Ads or platform listings, but the closed-deal source is invisible", "sub": "Input and output cannot be measured", "val": "untracked"},
            {"label": "Pixel and analytics installed, conversions visible per channel", "sub": "Acquisition can already be optimised with data", "val": "pixel_and_ga4"}
        ]
    },
    "cyber": {
        "step_title": "Corporate communication and business privacy compliance",
        "question": "When you send quotations and contracts out, is it from a corporate-domain mailbox or a personal Gmail? Who can freely pull up customer records and staff contracts?",
        "sub_hint": "A corporate-domain mailbox affects your delivery reputation, and document access affects your compliance responsibility.",
        "options": [
            {"label": "Quotations sent from a personal free mailbox", "sub": "Delivery reputation and company image both suffer", "val": "free_gmail"},
            {"label": "A business mailbox exists, but document access is not tiered", "sub": "Good front of house, weak internal control", "val": "business_domain"},
            {"label": "Business mailbox, with sensitive documents tiered by role", "sub": "Both communication and access are controlled", "val": "compliant"}
        ]
    },
    "ai": {
        "step_title": "Automated cover outside working hours",
        "question": "For enquiries arriving after 7pm and at weekends, do you reply the next day, or can someone or something respond immediately? Roughly what share of urgent jobs is lost this way?",
        "sub_hint": "How fast the first reply lands on an urgent job decides who gets the order.",
        "options": [
            {"label": "Read the next day, nobody on watch", "sub": "Deals keep leaking outside working hours", "val": "manual"},
            {"label": "The owner or staff reply occasionally from a personal phone", "sub": "Depends on someone watching; not reliable", "val": "partial"},
            {"label": "An auto-responder or AI assistant covers 24 hours", "sub": "An always-on order-taking foundation already exists", "val": "middleware"}
        ]
    },
    "leadership": {
        "step_title": "Management willingness to digitalise, and budget",
        "question": "If this check concluded that some foundation work needs budget within a year, would your own stance be to wait and see, to pilot it in small steps, or is there already a clear budget?",
        "sub_hint": "The decision-maker's willingness is the first element of the AI readiness assessment.",
        "options": [
            {"label": "Wait and see until others prove it works", "sub": "Delaying the window costs more", "val": "reluctant"},
            {"label": "Happy to pilot a small piece first, then decide", "sub": "Workable, needs staged verification", "val": "conservative"},
            {"label": "Budget and timetable are already agreed", "sub": "Conditions to move are in place", "val": "high"}
        ]
    },
    "employee_skills": {
        "step_title": "Staff readiness to work alongside AI",
        "question": "If you put in a new system, or let AI answer customers for you, who among your current staff would be first to use it? What is the general attitude of the longer-serving staff to new tools?",
        "sub_hint": "Whether a tool actually lands usually depends on front-line acceptance, not on features.",
        "options": [
            {"label": "Long-serving staff resist and the will to learn is low", "sub": "The rollout itself is the main risk", "val": "low"},
            {"label": "One or two younger staff willing to try", "sub": "Can be pushed from a pilot outward", "val": "mixed"},
            {"label": "The team generally is willing to learn new tools", "sub": "Conditions for scaled delivery are in place", "val": "high"}
        ]
    },
    "process_maturity": {
        "step_title": "Operating standards and written processes",
        "question": "For quoting, raising orders and reconciliation, is there a standard process written down as a document, or does it rest mainly on the experience of long-serving staff and verbal instruction?",
        "sub_hint": "A process that is not written down cannot be automated, and is hard to hand over.",
        "options": [
            {"label": "No written process; it runs on experience and verbal instruction", "sub": "A key role stopping means the work stops", "val": "false"},
            {"label": "Some written rules exist, but they are not enforced", "sub": "A skeleton without the loop closed", "val": "partial"},
            {"label": "Written SOPs for the main roles", "sub": "The precondition for automation is there", "val": "true"}
        ]
    },
    "digital_workflow": {
        "step_title": "Document flow across departments and how reconciliation is done",
        "question": "From raising the sales order to posting it in finance, does one system pass it through automatically, or does someone re-enter the documents? At month end, how many people and how many days does reconciliation take?",
        "sub_hint": "Re-keying is the main source of leaked man-hours and errors.",
        "options": [
            {"label": "Copied by hand or re-entered", "sub": "Man-hour and error costs keep building up", "val": "manual"},
            {"label": "Partly online, but month-end still needs a manual roll-up", "sub": "Semi-automatic, and people finish it off", "val": "semi"},
            {"label": "Everything online with automatic routing and approval", "sub": "The collaboration chain is already digital", "val": "auto"}
        ]
    },
    "data_availability": {
        "step_title": "How structured your business data is",
        "question": "Do you have one database or purchasing/sales stock system where past sales, customers and stock movements can be looked up? Or are the records spread across individual computers and chat histories?",
        "sub_hint": "Without structured data, no AI application has anything to work on.",
        "options": [
            {"label": "Records scattered, no single database", "sub": "No data-driven decision can be made at all", "val": "unstructured"},
            {"label": "Excel ledgers, each maintained separately", "sub": "Data exists but there is no agreed definition", "val": "spreadsheet"},
            {"label": "A single purchasing/sales stock or ERP database", "sub": "The AI data precondition is already met", "val": "structured"}
        ]
    }
}


def _session_elapsed_seconds(session_id: str) -> Optional[float]:
    """自档案建立以来的墙钟秒数；取不到起始时间时返回 None 表示不施加预算。"""
    started = SqlWikiEngine.get_dossier_created_at(session_id)
    if not started:
        return None
    try:
        started_dt = datetime.fromisoformat(started)
    except (ValueError, TypeError):
        return None
    reference = started_dt if started_dt.tzinfo else started_dt
    delta = (datetime.now() - reference).total_seconds()
    return delta if delta >= 0 else None


def _deterministic_probe(dimension: str) -> Dict[str, Any]:
    """零 LLM 延迟的规则探针：时间预算耗尽或 AI 引擎不可达时的收敛手段。"""
    template = DETERMINISTIC_PROBES.get(dimension) or DETERMINISTIC_PROBES["cloud"]
    return {
        "step_title": template["step_title"],
        "question": template["question"],
        "sub_hint": template["sub_hint"],
        "options": with_escape_hatches(template["options"]),
        "generated_by": "deterministic_rule_engine"
    }


def _pick_next_target(full: Dict[str, Any]) -> str:
    """下一个要问的维度。missing_* 已由取证层按提问优先级排好（先看得见的，
    后自我评估的），所以这里只取第一项；DMS 问完才轮到 ARS。"""
    missing_dms = full.get("missing_dms") or []
    missing_ars = full.get("missing_ars") or []
    if missing_dms:
        return missing_dms[0]
    if missing_ars:
        return missing_ars[0]
    return ""


MACHINE_QUOTE_PREFIX = "[Machine check]"


def _machine_rows_for(tree: Dict[str, Any], dimension: str) -> List[Dict[str, Any]]:
    """第②步机检留给这个维度的结论。证据链里它们带 [Machine check] 前缀，
    取值只有 pass / fail 两种实测结论，未测到的从不入库。"""
    rows: List[Dict[str, Any]] = []
    for group in (tree.get("dimensions") or []) + (tree.get("ars_factors") or []):
        code = group.get("dimension_code") or group.get("factor_code")
        if code != dimension:
            continue
        for ev in (group.get("evidence_list") or []):
            quote = str(ev.get("quote_text") or "")
            if not quote.startswith(MACHINE_QUOTE_PREFIX):
                continue
            title, _, observed = quote[len(MACHINE_QUOTE_PREFIX):].partition(":")
            rows.append({"title": title.strip(), "observed": observed.strip(),
                         "state": str(ev.get("fact_value") or "")})
    return rows


def _round_record(dimension: str, extracted: List[Dict[str, Any]],
                  menu_fact: Optional[Dict[str, str]], escape: str = "") -> Optional[Dict[str, Any]]:
    """本轮对这个维度究竟记下了什么、凭什么记下。思考卡第一步只准引用这个答案。"""
    if escape == ESCAPE_UNSURE_VAL:
        return {"uncertain": True, "value": UNKNOWN_FACT_VALUE, "quote": "",
                "basis": "the Not sure answer you picked"}
    nodes = [n for n in (extracted or []) if isinstance(n, dict) and n.get("dimension") == dimension]
    node = None
    if menu_fact:
        # 点选那一档优先：关键词路径可能先记下同维度的一条从原话里猜出来的记录
        node = next((n for n in nodes if n.get("fact_key") == menu_fact.get("fact_key")
                     and n.get("fact_value") == menu_fact.get("fact_value")), None)
    if node is None:
        node = nodes[-1] if nodes else None
    if node is None:
        return None
    quote = str(node.get("quote_text") or "")
    if quote.startswith(MACHINE_QUOTE_PREFIX):
        return {"value": str(node.get("fact_value") or ""), "quote": "",
                "basis": "the step-2 machine check"}
    return {"value": str(node.get("fact_value") or ""), "quote": quote,
            "basis": "the option you picked" if menu_fact else "what you typed"}


def process_diagnostic_turn(session_id: str, user_answer: str, target_dim: str = "",
                            selected_option: Any = None) -> Dict[str, Any]:
    """
    Ingest user's latest response into SQLite Wiki, evaluate dual DMS/ARS completeness,
    and generate the next precision probe via Cradilot LLM or signal completion.
    Turn increments only once per invocation.
    """
    tree_before = SqlWikiEngine.get_live_wiki_tree(session_id)
    dossier = tree_before.get("dossier", {})
    company_name = dossier.get("company_name", "Your company")
    industry = dossier.get("industry", "General trading")

    # If target_dim not provided, determine from missing items（清单已按提问优先级排列）
    if not target_dim:
        full_before = SqlWikiEngine.calculate_full_completeness(session_id)
        target_dim = _pick_next_target(full_before) or "operational_fact"

    # 0. 逃生口排在一切取值解析之前：这两条回答不是事实，既不许被关键词猜成某个档位，
    #    也不许交给模型猜——猜出来的档位会被当成客户明确说过的话去评分和推销。
    escape = _escape_choice(selected_option, user_answer)
    if escape == ESCAPE_DESCRIBE_VAL:
        # 不记任何东西、不推进轮次：把光标交给页面下方那个自由文本框，
        # 老板打字或口述的答案随后照常走自定义回答那条既有路径。
        return {
            "status": "CONTINUE",
            "session_id": session_id,
            "await_free_text": True,
            "read_back": "Go ahead — tell it to me in your own words.",
            "target_dim": target_dim,
            "turn_incremented": False,
            "menu_resolved": False,
            "captured_fact": "",
            "next_probe": None,
            "next_question": None,
            "options": [],
            "pills": [],
            "tree": tree_before,
        }

    menu_fact: Optional[Dict[str, str]] = None
    read_back = ""
    if escape == ESCAPE_UNSURE_VAL:
        # 1a. 只留一条"这一题问过了、答不出"的证据：不写痛点、不设档位。
        #     没确认的事按中性值计入，绝不是扣分项；后来答出来了同一行会被升级成档位。
        unsure_key = _uncertain_fact_key(target_dim)
        SqlWikiEngine.record_stated_fact(
            session_id, target_dim, unsure_key, UNKNOWN_FACT_VALUE,
            UNCERTAIN_QUOTE, UNCERTAIN_CONFIDENCE)
        extracted = [{"dimension": target_dim, "fact_key": unsure_key,
                      "fact_value": UNKNOWN_FACT_VALUE, "quote_text": UNCERTAIN_QUOTE,
                      "confidence": UNCERTAIN_CONFIDENCE}]
        read_back = (f"Recorded: {_dim_display_name(target_dim)} — you were not sure. "
                     "It stays an open item and costs you nothing on the score.")
    else:
        # 1b. Sync structured evidence into SQLite via Cradilot Brain extraction
        #     点选即事实：先认下过的那个选项的规范取值，自由文本才回退到措辞解析
        menu_fact = _fact_from_option(target_dim, selected_option) or _menu_match(target_dim, user_answer)
        extracted = SqlWikiEngine.extract_and_sync_wiki_nodes(
            session_id, user_answer, target_dim, menu_fact=menu_fact,
            allow_anchor=target_dim in DEEP_PROBES)

    # 2. Check completeness across both DMS 6 dimensions and ARS 5 factors
    full = SqlWikiEngine.calculate_full_completeness(session_id)
    missing_dms = full["missing_dms"]
    missing_ars = full["missing_ars"]
    total_explored = full["total_explored_count"]
    is_all_complete = full["is_all_complete"]
    readiness = SqlWikiEngine.evaluate_readiness(full)

    elapsed = _session_elapsed_seconds(session_id)
    budget_spent = elapsed is not None and elapsed > DIAG_TIME_BUDGET_SECONDS

    # 2b. 奖励轮：主题全部锁证且时间还有余时，追问一题深挖题。
    #     没答或答得不明确也记为"问过"（anchor key），保证不会原地反复问同一题。
    updated_tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    # 四步思考只引用此刻手上这些数据：本轮记下的证据、取证完整度、
    # 第②步留给这个维度的机检结论、快照计数、以及纯函数按已存证据算出的即时分数。
    engine_input_now = SqlWikiEngine.get_full_assessment_input(session_id)
    cot_context = {
        "recorded": _round_record(target_dim, extracted, menu_fact, escape),
        "completeness": full,
        "machine_rows": _machine_rows_for(tree_before, target_dim),
        "site_audit": SqlWikiEngine.get_site_audit(session_id),
        "dms_provisional": float(calculate_dms(engine_input_now).get("overall_score") or 0.0),
    }

    def _cot(next_dim: str = "", closing: bool = False) -> List[Dict[str, Any]]:
        return build_cradilot_thought_chain(company_name, industry, target_dim, user_answer,
                                            next_dim=next_dim, closing=closing, **cot_context)

    stored_keys = set(engine_input_now.get("_verified_facts") or [])
    pending_deep = [d for d, spec in DEEP_PROBES.items()
                    if spec["options"][0]["fact_key"] not in stored_keys
                    and f"{d}_response" not in stored_keys]
    if (is_all_complete or (budget_spent and readiness["can_finalize"])) and pending_deep \
            and not budget_spent:
        deep_dim = pending_deep[0]
        # 深拷贝后再追加逃生口：DEEP_PROBES 是模块级题库，就地 append 会改到本体
        deep_probe = copy.deepcopy(DEEP_PROBES[deep_dim])
        deep_probe["options"] = with_escape_hatches(deep_probe.get("options"))
        deep_probe["dimension"] = deep_dim
        deep_probe["step_num"] = total_explored + 2
        SqlWikiEngine.update_state_ledger(
            session_id, next_probe_question=deep_probe["question"], increment_turn=True)
        return {
            "status": "CONTINUE",
            "session_id": session_id,
            "extracted_nodes_count": len(extracted),
            "menu_resolved": bool(menu_fact),
            "captured_fact": (menu_fact or {}).get("fact_value") or "",
            "read_back": read_back,
            "completeness_score": full["total_ratio"],
            "dms_ratio": full["dms_ratio"],
            "ars_ratio": full["ars_ratio"],
            "time_budget_exhausted": False,
            "ai_degraded": bool(engine_client.last_call_degraded),
            "elapsed_seconds": round(elapsed, 1) if elapsed is not None else None,
            "step_num": deep_probe["step_num"],
            "deep_dive": True,
            **readiness,
            "cot": _cot(deep_dim),
            "next_probe": deep_probe,
            "next_question": deep_probe["question"],
            "sub_hint": deep_probe.get("sub_hint", ""),
            "options": deep_probe.get("options", []),
            "pills": [o["label"] for o in deep_probe.get("options", [])],
            "tree": updated_tree,
        }

    # 3. Increment turn count explicitly for this user interaction
    SqlWikiEngine.update_state_ledger(session_id, increment_turn=True)
    updated_tree = SqlWikiEngine.get_live_wiki_tree(session_id)

    # Completion gate: 全部 11 项核验完毕，或时间预算已耗尽但已有足够证据出分。
    # 官方硬指标是「5 分钟内完成分析」，宁可如实标注覆盖面不足，也不要把报告卡住。
    if is_all_complete or (budget_spent and readiness["can_finalize"]):
        confirmed_now = full.get("confirmed_count", 0)
        total_dims = full.get("total_dimension_count", total_explored)
        if is_all_complete:
            close_reason = "ALL_EVIDENCE_VERIFIED"
            if confirmed_now >= total_explored:
                message = (
                    "All business facts are now verified! The 6 DMS technical facts and the 5 ARS factors have each been "
                    "checked against the local SQLite evidence chain, and the report is ready for deterministic scoring and blueprint generation."
                )
            else:
                message = (
                    f"Every one of the {total_dims} areas has now been asked about. {confirmed_now} of them hold a confirmed "
                    f"answer; the {total_explored - confirmed_now} left open stay open items, counted neutrally and not "
                    "deducted as missing. The report is ready for deterministic scoring and blueprint generation."
                )
        else:
            close_reason = "TIME_BUDGET"
            message = (
                f"The time budget for one assessment has been reached ({int(elapsed or 0)} seconds), so scoring closes early "
                f"with {confirmed_now}/{readiness['evidence_required']} areas holding a confirmed answer. "
                "The report will state the evidence coverage, and unverified dimensions are not counted as deductions."
            )
        return {
            "status": "DIAGNOSIS_COMPLETE",
            "session_id": session_id,
            "message": message,
            "close_reason": close_reason,
            "menu_resolved": bool(menu_fact),
            "captured_fact": (menu_fact or {}).get("fact_value") or "",
            "read_back": read_back,
            "completeness_score": full["total_ratio"],
            "elapsed_seconds": round(elapsed, 1) if elapsed is not None else None,
            "cot": _cot(closing=True),
            "tree": updated_tree,
            "next_probe": None,
            "next_question": None,
            "pills": [],
            **readiness
        }

    # Otherwise, pick next target dimension with strict zero repetition
    # （missing_* 已按提问优先级排列：先问一眼看得见的，自我评估的题排在后面）
    next_target = _pick_next_target(full)

    step_num = total_explored + 2
    # 预算耗尽后不再为每道题付 10-20 秒的 LLM 延迟，改用零延迟规则探针继续收敛。
    if budget_spent:
        probe = _deterministic_probe(next_target)
        ai_degraded = True
    else:
        probe = generate_agentic_probe(session_id, next_target, step_num)
        # 必须在本次调用后立刻读：engine_client 在每次调用开始时清零该标记。
        ai_degraded = bool(engine_client.last_call_degraded)
    probe["dimension"] = next_target
    probe["step_num"] = step_num
    # 逃生口兜底：到了客户手上的每一道题都必须带着那两条出路（追加是幂等的）
    probe["options"] = with_escape_hatches(probe.get("options"))

    next_q = probe.get("question", "")
    pills = [opt.get("label", "") for opt in probe.get("options", [])]

    SqlWikiEngine.update_state_ledger(session_id, next_probe_question=next_q, increment_turn=False)

    dynamic_container = build_dynamic_container_payload(session_id, probe, next_target, step_num)

    return {
        "status": "CONTINUE",
        "session_id": session_id,
        "extracted_nodes_count": len(extracted),
        "menu_resolved": bool(menu_fact),
        "captured_fact": (menu_fact or {}).get("fact_value") or "",
        "read_back": read_back,
        "completeness_score": full["total_ratio"],
        "dms_ratio": full["dms_ratio"],
        "ars_ratio": full["ars_ratio"],
        "time_budget_exhausted": budget_spent,
        "ai_degraded": ai_degraded,
        "elapsed_seconds": round(elapsed, 1) if elapsed is not None else None,
        "step_num": step_num,
        **readiness,
        "cot": _cot(next_target),
        "next_probe": probe,
        "next_question": next_q,
        "sub_hint": probe.get("sub_hint", ""),
        "options": probe.get("options", []),
        "pills": pills,
        "dynamic_container": dynamic_container,
        "tree": updated_tree
    }


# 报告页"本次未采集"清单与评分层读的字段一一对应，避免清单与分数各说各话。
_UNVERIFIED_KEYS = (
    ("Whether a website exists and its state", ("web_engine_status", "has_domain")),
    ("Backups and disaster recovery today", ("dr_backup_status", "cloud_storage_status")),
    ("Where customer records are kept", ("crm_system", "uses_personal_whatsapp")),
    ("Whether company email uses your own domain", ("email_type", "uses_personal_email")),
    ("Ad spend and result tracking", ("marketing_tracker",)),
    ("Who picks up enquiries after closing", ("ai_tier", "ai_automation_status", "has_ai_agent")),
)


def _unverified_items(engine_input: Dict[str, Any]) -> List[str]:
    return [label for label, keys in _UNVERIFIED_KEYS
            if all(engine_input.get(k) in (None, "", [], {}) for k in keys)]


def finalize_diagnosis_from_wiki(session_id: str,
                                 assumption_overrides: Optional[Dict[str, Any]] = None
                                 ) -> Dict[str, Any]:
    """
    Execute deterministic pure-function calculation (DMS, ARS, ROI, Pain Points, Cart)
    strictly anchored to the facts verified in SQLite Wiki.
    Guarantees 0 score hallucination.

    assumption_overrides：报告页上客户当场改过的测算假设（工时/漏接询盘/毛利/月薪）。
    机检测不到这四个数字，所以它们只能是标注清楚出处的假设；客户一改，整份报告重算。
    """
    engine_input = SqlWikiEngine.get_full_assessment_input(session_id)
    wiki_tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    dossier = wiki_tree["dossier"]
    # 第②步的 210 项明细：评分只用其中几项，蓝图与 PDF 附录要引用全部
    site_audit = SqlWikiEngine.get_site_audit(session_id)

    # 从 SQLite 证据链提取用户原话，供痛点引擎做可溯源引用（无原话不伪造引语）。
    # "这一题答不出"那一条不是原话，不得被引用成客户主张过的事。
    evidence_quotes: Dict[str, str] = {}
    for group in (wiki_tree.get("dimensions", []) + wiki_tree.get("ars_factors", [])):
        code = group.get("dimension_code") or group.get("factor_code")
        if not code:
            continue
        for ev in confirmed_nodes(group.get("evidence_list")):
            quote = (ev.get("quote_text") or "").strip()
            if quote and code not in evidence_quotes:
                evidence_quotes[code] = quote

    dms_result = calculate_dms(engine_input)
    ars_result = calculate_ars(engine_input, dms_result["overall_score"])

    pain_conflicts: List[Dict[str, Any]] = []
    top_pain_points_raw = generate_pain_points(
        engine_input,
        dms_result,
        wiki_pains=wiki_tree.get("pain_points") or [],
        evidence_quotes=evidence_quotes,
        conflict_sink=pain_conflicts,
    )
    primary_pain_points = [f"{p['title']}: {p['impact']}" for p in top_pain_points_raw[:5]]

    roadmap = generate_action_roadmap(engine_input, dms_result, top_pain_points_raw,
                                      site_audit=site_audit)

    # 采购车与路线图同源：合计金额、ROI 分母与各阶段预算必须对得上
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
    # ROI 的分母必须就是客户在这份报告里看到的那个金额。旧版写死 5550.68，
    # 与购物车合计无关，导致同一页面上的"年费"和"回报率"互相矛盾。
    priced_lines = [i for i in cart_items if i.promotional_price_myr > 0]
    cart_total = round(sum(i.promotional_price_myr for i in priced_lines), 2)

    # 旧版在这里写死 18.0/8.0 工时与 14.0/3.0 笔晚间商机，再配以 RM 3,500 月薪、
    # RM 120 毛利，然后以"已核验事实与贵司自填工时"的名义念给客户。这四个数字
    # 机检测不到、流程里也没问过，现在统一由 resolve_assumptions 给出并标注出处。
    assumptions = resolve_assumptions(engine_input, assumption_overrides)
    roi_result = calculate_roi(
        vendor_annual_cost=cart_total,
        priced_line_count=len(priced_lines),
        assumptions=assumptions,
        quote_pending=any(ph.get("pricing_pending") for ph in roadmap)
    )

    # 痛点金额只认这一个来源：把 ROI 算出的两笔收益按机制分摊回对应维度，
    # 再回填各阶段说明——阶段里的钱与痛点里的钱与 ROI 卡片里的钱必须同为一道算式。
    apply_loss_model(top_pain_points_raw, roi_result)
    refresh_roi_milestones(roadmap, top_pain_points_raw)

    report_id = f"CRADILOT-SQL-{session_id}-{uuid.uuid4().hex[:4].upper()}"
    unverified_items = _unverified_items(engine_input)

    return {
        "metadata": {
            "session_id": session_id,
            "company_name": dossier.get("company_name", "SME"),
            "industry": dossier.get("industry", "General trading"),
            "team_size": dossier.get("team_size", "6-20 people"),
            "annual_turnover": dossier.get("annual_turnover", "RM 1M - 5M"),
            "biggest_challenge": dossier.get("biggest_challenge", ""),
            "growth_objective": dossier.get("growth_objective", ""),
            "current_tools": dossier.get("current_tools", ""),
            "report_id": report_id,
            "data_basis": "interview" if not unverified_items else "interview_partial",
            "data_basis_note": ("" if not unverified_items else
                                "This interview did not reach, within the time budget: " + ", ".join(unverified_items)
                                + ". These items are counted at a neutral value and were not deducted as missing; the report recalculates once they are answered."),
            "unverified_items": unverified_items,
        },
        "dms": dms_result,
        "ars": ars_result,
        "roi": roi_result,
        "pain_points": top_pain_points_raw,
        "pain_conflicts": pain_conflicts,
        "primary_pain_points": primary_pain_points,
        "roadmap": roadmap,
        "recommendation": {
            "primary_pain_points": primary_pain_points,
            "roadmap": roadmap
        },
        "cart": cart_data,
        "site_audit": site_audit,
        "wiki_tree": wiki_tree
    }

