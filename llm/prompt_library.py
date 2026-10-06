"""
Cradilot AI - Unified Prompt Library
All prompts for gemma3:12b generation. Zero emoji, business-grade Chinese/English bilingual output.
Each prompt enforces: no emoji characters, professional Malaysian SME advisory tone.
"""

from typing import Dict, Any, List, Optional

SYSTEM_BASE = (
    "You are Cradilot AI, a senior digital transformation advisor specializing in Malaysian SMEs. "
    "Your output must be: professional, concise, grounded in the specific business details provided, "
    "in plain English that a non-technical business owner can follow. "
    "STRICT RULES: No emoji characters. No generic filler text. No hallucinated figures. "
    "Every claim must be traceable to the user's provided business context."
)


def prompt_dynamic_followup(company_name: str, industry: str, team_size: str,
                             annual_turnover: str, tools: List[str]) -> str:
    tools_str = ", ".join(tools) if tools else "personal WhatsApp and paper documents"
    return (
        f"Company name: {company_name}\n"
        f"Industry: {industry}\n"
        f"Team size: {team_size}\n"
        f"Annual turnover: {annual_turnover}\n"
        f"Tools in use today: {tools_str}\n\n"
        "Using only the real business background above, write 2 sharp followup business probes that go straight at the digital weak spots typical of this industry.\n"
        "Keep every probe short, conversational and realistic (the way a senior business advisor would ask an owner face to face), focused on these two areas:\n"
        "1. How enquiries from customers outside working hours (evenings or weekends) are answered, and how many are lost\n"
        "2. The man-hours consumed by month-end document reconciliation and manual data entry\n"
        "Output format: the 2 probes separated by a line break, no numbering, no explanation, just the questions themselves."
    )


def prompt_dms_insight(company_name: str, industry: str, dms_score: float, dms_tier: str,
                        dimensions: Dict[str, Any], user_answers: str) -> str:
    dim_lines = ""
    for dim, data in dimensions.items():
        stars = data.get("stars", "N/A")
        details = data.get("details", "")
        evidence = data.get("evidence", "")
        tag = f" [evidence: {evidence}]" if evidence else ""
        dim_lines += f"  - {dim}: {stars} — {details}{tag}\n"

    score_text = "Not scored" if dms_score is None else f"{dms_score:.1f}"
    return (
        f"Company: {company_name} (industry: {industry})\n"
        f"Overall digital maturity score: {score_text} / 100 (tier: {dms_tier})\n"
        f"Detail by dimension (items marked as measured have been verified on the public web; items marked as self-reported or inferred must never be presented as verified):\n{dim_lines}\n"
        f"What the owner said about the business: {user_answers}\n\n"
        "Write a digital maturity insight for this company (150-200 words), with these requirements:\n"
        "- Base it on the real scores and dimension data; invent nothing\n"
        "- Name the 2 lowest-scoring dimensions and the concrete business consequence of each\n"
        "- Tone: direct and professional, like a senior advisor who has seen hundreds of SMEs\n"
        "- End with the one most urgent action to take (a single sentence)\n"
        "No heading; output the body text only."
    )


def prompt_pain_analysis(company_name: str, industry: str, dms_score: float,
                          user_answers: str, detected_gaps: List[str]) -> str:
    gaps_str = "\n".join(f"- {g}" for g in detected_gaps)
    return (
        f"Company: {company_name} (industry: {industry}, digital maturity: {dms_score:.1f}/100)\n"
        f"Key facts the owner reported: {user_answers}\n"
        f"Digital gaps detected by the system:\n{gaps_str}\n\n"
        "Based on the real data above only, produce this company's Top 5 list of core business pain points.\n"
        "Format for each pain point:\n"
        "  [Pain point title (plain everyday English, one line that gets to the point, 15 words or fewer)]\n"
        "  [One sentence of evidence (quote what the owner reported, or the specific data detected)]\n"
        "  [Business consequence (say only what happens; apart from figures this company gave us directly, no money amounts and no percentages)]\n\n"
        'Output 5 entries, separated by "---", with no extra commentary.'
    )


def prompt_roadmap(company_name: str, industry: str, dms_score: float,
                    pain_points: List[str], annual_turnover: str) -> str:
    pains_str = "\n".join(f"- {p}" for p in pain_points[:5])
    return (
        f"Company: {company_name} (industry: {industry}, annual turnover: {annual_turnover}, digital maturity: {dms_score:.1f}/100)\n"
        f"Core pain points already identified:\n{pains_str}\n\n"
        "Build a personalised three-phase digital implementation roadmap for this company.\n"
        "Phase split: Phase 1 (weeks 1-4, Quick Wins), Phase 2 (months 2-3, Productivity), Phase 3 (months 6-12, Growth)\n"
        "Output for each phase:\n"
        "  - Phase title and time period\n"
        "  - 3 concrete actions (tailored to this company's real pain points, referencing our products and solutions)\n"
        "  - The measurable business result at the end of the phase\n\n"
        "Keep catalogue product names in English. No extra commentary; output the three phases directly."
    )


def prompt_icebreaker(company_name: str, industry: str, contact_name: str,
                       dms_score: float, ars_score: float, ars_locked: bool,
                       pain_points: List[str], roi_gain: float, roi_pct: float,
                       cart_items: List[str]) -> str:
    lock_note = (
        f"(Note: this company's digital foundation is weak, so ARS has tripped the hard lock guard at {ars_score:.1f}. "
        "Recommending advanced large-model solutions is strictly forbidden; the core recommendation must be the foundation-and-compliance bundle.)"
        if ars_locked else
        f"(This company has a sound digital base, ARS {ars_score:.1f}, so it is reasonable to mention AI productivity solutions.)"
    )
    pains_str = ", ".join(pain_points[:3])
    cart_str = ", ".join(cart_items[:3])
    return (
        f"Prospect details:\n"
        f"  Company: {company_name} (industry: {industry})\n"
        f"  Contact person: {contact_name}\n"
        f"  Digital maturity: {dms_score:.1f}/100\n"
        f"  Core pain points: {pains_str}\n"
        f"  Expected net gain in year one: RM {roi_gain:,.2f} (ROI {roi_pct:.1f}%)\n"
        f"  Recommended bundles: {cart_str}\n"
        f"  {lock_note}\n\n"
        "Write a personalised sales icebreaker script for the our account manager (about 150 words).\n"
        "Structure: icebreaker opening (1 sentence) -> pain point empathy (1-2 sentences quoting real data) -> solution value (1 sentence carrying the ROI figure) -> call to action (1 sentence).\n"
        "Tone: warm and professional, like an advisor who understands the trade, not like a salesperson.\n"
        "No heading, no commentary; output the script text only."
    )


def prompt_pdf_summary(company_name: str, industry: str, dms_score: float,
                        ars_score: bool, pain_points: List[str],
                        roi_gain: float, roi_pct: float) -> str:
    pains_str = "\n".join(f"- {p}" for p in pain_points)
    return (
        f"Company: {company_name} (industry: {industry})\n"
        f"Digital maturity: {dms_score:.1f}/100, AI readiness: {ars_score:.1f}/100\n"
        f"Core pain points:\n{pains_str}\n"
        f"Expected net gain in year one: RM {roi_gain:,.2f} (ROI {roi_pct:.1f}%)\n\n"
        "Write an Executive Summary of 80 words or fewer, to sit on the PDF cover page.\n"
        "Requirements: go straight to the biggest business problem and the value of solving it; objective, professional and convincing. No heading."
    )


def prompt_web_scraper_critique(company_name: str, industry: str, crawl_result: Dict[str, Any]) -> str:
    url = crawl_result.get("url", "")
    has_ssl = crawl_result.get("has_ssl", False)
    latency = crawl_result.get("response_time_ms", 0)
    mobile = crawl_result.get("mobile_friendly", False)
    cms = ", ".join(crawl_result.get("cms_tech", [])) or "unknown / static"
    score = crawl_result.get("technical_score", 50)

    return (
        f"Company name: {company_name}\n"
        f"Industry: {industry}\n"
        f"Website under review: {url}\n"
        f"Technical check data:\n"
        f"  - SSL certificate: {'valid encryption configured' if has_ssl else 'missing / not secure'}\n"
        f"  - Server round-trip latency: {latency} ms\n"
        f"  - Mobile friendliness: {'adapted' if mobile else 'not adapted'}\n"
        f"  - Tech stack detected: {cms}\n"
        f"  - Technical health score: {score} / 100\n\n"
        "As Cradilot AI's senior digital advisor, write a sharp 2-3 sentence business critique based only on the real public-web scan data above, aimed at commercial scenarios in this industry.\n"
        "Requirements:\n"
        "1. Name how the website's current technical state damages prospective customer conversion, overseas buyer trust or search engine ranking for this kind of business.\n"
        "2. Keep the language rigorous, professional and to the point; absolutely no emoji characters.\n"
        "Output the critique text only, no heading."
    )


def prompt_agentic_probe_generation(company_name: str, industry: str, team_size: str,
                                    annual_turnover: str, target_dimension: str,
                                    verified_facts: List[str], step_num: int,
                                    value_domain: Optional[List[tuple]] = None) -> str:
    dim_names = {
        "cloud": "Core data assets and disaster resilience",
        "crm": "Sales pipeline and customer lead retention",
        "cyber": "Business compliance and brand reputation risk",
        "marketing": "Digital customer acquisition and public-channel traffic",
        "ai": "24/7 smart service and the after-hours enquiry defence line",
        "web": "Public image and digital front door",
        "leadership": "Management willingness and resolve to go digital",
        "employee_skills": "Staff willingness to work with machines and to learn new tools",
        "process_maturity": "Written operating procedures and customer Q&A SOP standards",
        "digital_workflow": "Digital collaborative workflow and cross-department reconciliation",
        "data_availability": "Structured business data and one consolidated database"
    }
    dim_label = dim_names.get(target_dimension, target_dimension)
    facts_str = "\n".join(f"- {f}" for f in verified_facts) if verified_facts else "No confirmed facts yet"

    value_domain = value_domain or []
    if value_domain:
        table = "\n".join(f'    "{v}": {meaning}' if meaning else f'    "{v}"'
                          for v, meaning in value_domain)
        val_rule = (
            "The val of an option may only be copied word for word from this dimension's value table below. Do not invent one and do not change its capitalisation:\n"
            f"{table}\n"
            "The table is already ordered from most vulnerable to most mature: output 2 to 4 options, taking one value at a time in the order shown above, and never use the same val twice.\n"
            "You may reword label and sub so they fit this company's industry and size, but val must stay exactly as written in the table.\n"
        )
        val_example = '"val": "<choose one from the value table above>"'
    else:
        val_rule = ""
        val_example = '"val": "vulnerable"'

    return (
        f"Company name: {company_name}\n"
        f"Industry: {industry}\n"
        f"Team size: {team_size}\n"
        f"Annual turnover: {annual_turnover}\n"
        f"Confirmed objective facts:\n{facts_str}\n\n"
        f"Blind spot to probe now: {dim_label} (question {step_num})\n\n"
        "Acting as the Cradilot AI advisor, write one precise business probe question that goes straight at this company's current background and blind spot, and provide 2-4 objective options that match how this industry really operates.\n"
        + val_rule +
        "Output strictly in JSON format, with no markdown code block and no extra text, in this shape:\n"
        "{\n"
        f'  "step_title": "{dim_label}",\n'
        '  "question": "one precise business probe question",\n'
        '  "sub_hint": "why we ask this question: say only where this gets stuck for a company like theirs, with no percentage, hour count or legal clause that they did not give us",\n'
        '  "options": [\n'
        '    {\n'
        '      "label": "Option 1 name (most vulnerable / traditional setup)",\n'
        '      "sub": "Option 1: the concrete business situation and the risk it carries",\n'
        f'      {val_example}\n'
        '    },\n'
        '    {\n'
        '      "label": "Option 2 name (partly in place / in transition)",\n'
        '      "sub": "Option 2: the concrete business situation",\n'
        f'      {val_example}\n'
        '    },\n'
        '    {\n'
        '      "label": "Option 3 name (mature and up to standard)",\n'
        '      "sub": "Option 3: the concrete business situation",\n'
        f'      {val_example}\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Hard requirements: options must contain 2 to 4 entries, question must be longer than 10 characters, and absolutely no emoji characters!"
    )


def prompt_agentic_probe_retry(company_name: str, industry: str, target_dimension: str,
                               step_num: int, error_msg: str) -> str:
    """Prompt to re-generate an agentic probe when the previous output failed schema validation."""
    return (
        f"The last probe JSON generated for company [{company_name}] (industry: {industry}) on indicator [{target_dimension}] failed validation:\n"
        f"Reason: {error_msg}\n\n"
        "Regenerate a strictly valid JSON object right now. Requirements:\n"
        "1. question must be a non-empty, valid question string (more than 10 characters);\n"
        "2. options must be an array with a length between 2 and 4, and every entry must contain label, sub and val;\n"
        "3. step_title must be a dynamic title;\n"
        "4. output standard JSON only. No code block markers (such as ```json) and no notes before or after, and absolutely no emoji characters!"
    )


def prompt_cradilot_slot_extraction(company_name: str, industry: str, target_item: str,
                                    user_answer: str, existing_facts: List[str]) -> str:
    """
    Direct Cradilot Brain JSON extraction prompt.
    Extracts operational facts, values, quote snippets, and detected pain points from user's response.
    """
    facts_context = "\n".join(f"- {f}" for f in existing_facts) if existing_facts else "None yet"
    return (
        f"[Cradilot Brain business fact extraction task]\n"
        f"Company name: {company_name}\n"
        f"Industry: {industry}\n"
        f"Indicator in focus now: {target_item}\n"
        f"Confirmed facts:\n{facts_context}\n"
        f"The customer's latest answer, word for word: \"{user_answer}\"\n\n"
        "Acting as the Cradilot business fact extraction engine, extract structured technical facts and business choke points precisely from the customer's answer.\n"
        "Output strictly in the following JSON format:\n"
        "{\n"
        '  "dimension": "' + target_item + '",\n'
        '  "fact_key": "technical fact key name (for example backup_strategy, crm_status, email_type, marketing_tracker, after_hours_leak, web_engine_status, ars_leadership, ars_skills, ars_process, ars_workflow, ars_data)",\n'
        '  "fact_value": "core value (for example single_pc, personal_whatsapp, free_gmail, none, true, false, high, medium, low)",\n'
        '  "quote_text": "the single most important sentence, in the customer\'s own words, that proves this fact",\n'
        '  "confidence": 0.95,\n'
        '  "pain_detected": {\n'
        '    "has_pain": true,\n'
        '    "title": "choke point title (plain everyday English, 15 words or fewer)",\n'
        '    "root_cause": "one sentence on why this situation is a problem",\n'
        '    "severity": "CRITICAL / HIGH / MEDIUM",\n'
        '    "cradle_gap": "what is still missing, stated in measurable terms (do not invent money amounts, percentages or legal clauses)",\n'
        '    "solution": "the recommended our product or solution"\n'
        '  }\n'
        "}\n"
        "If the customer's situation is healthy and there is no choke point, set pain_detected.has_pain to false.\n"
        "Output plain JSON only. No markdown code block and no emoji characters of any kind!"
    )

