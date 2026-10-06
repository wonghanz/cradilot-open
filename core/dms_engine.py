"""
Cradilot Core - Digital Maturity Score (DMS) Engine
本公司官方 Step 2 六维评分：纯函数、确定性、零 LLM 参与。

字段一律经 core.assessment_facts.normalize() 取得。此前本引擎读的键名与
/api/assess 构造的键名不一致，导致 cloud 恒为 35、marketing 恒为 30、
cybersecurity 因 has_antivirus 无人赋值而封顶 45，DMS 理论最高只有 62.5
（而第三档门槛是 70，等于任何企业都不可能被评为成熟标杆）。现在每一维都
必须能随输入走完 0-100，并标注该结论的证据出处。
"""

from typing import Dict, Any, Tuple, Optional

from core.assessment_facts import (
    normalize, BACKUP_TIERS, CRM_TIERS, ATTRIBUTION_TIERS,
    SRC_MACHINE, SRC_STATED, SRC_INFERRED, SRC_LABELS
)
from core.ai_inference import explain

# Published DMS dimension weights (sum = 1.0)
DIMENSION_WEIGHTS = {
    "website": 0.15,
    "cloud": 0.20,
    "crm": 0.20,
    "marketing": 0.15,
    "cybersecurity": 0.15,
    "ai_adoption": 0.15,
}

_UNVERIFIED_NOTE = "{n} of the checks behind this dimension could not be verified this time and were counted at a neutral value, not deducted as a gap."


def calculate_stars(score_out_of_100: float) -> str:
    """0-100 转 5 星字符串。"""
    stars = max(1, min(5, round(score_out_of_100 / 20)))
    return "★" * stars + "☆" * (5 - stars)


def _neutral_when_unknown(value: Optional[bool], if_true: float, if_false: float) -> Tuple[float, bool]:
    """
    返回 (得分贡献, 是否为未知中性值)。

    None 表示"没测到"，绝不能当成 False 扣分——那会把一次测量事故写成客户的能力缺失。
    """
    if value is None:
        return (if_true + if_false) / 2.0, True
    return (if_true if value else if_false), False


# ─── 1. Website (15%) ────────────────────────────────────────────────────────
def evaluate_website_dimension(web: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    tier = web.get("tier", "unknown")
    has_site = web.get("has_website")
    if has_site is False or tier == "none":
        return 5.0, {"score": 5.0, "stars": calculate_stars(5.0),
                     "details": "No public company website or own domain: customers in other states or abroad cannot check for themselves that the business really trades."}
    if has_site is None and tier in ("", "unknown"):
        return 50.0, {"score": 50.0, "stars": calculate_stars(50.0),
                      "details": "Whether a website exists was neither asked nor machine-checked this time, so it is scored at a neutral value rather than "
                                 "deducted as missing. Once the Step 2 website audit runs, this becomes a measured result."}

    score = 40.0                      # 有站即有底座
    unknowns = 0
    notes = ["Has its own website"]

    pts, unk = _neutral_when_unknown(web.get("ssl"), 20.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Site-wide HTTPS confirmed" if web.get("ssl") else ("Certificate status not verified this time" if unk else "No HTTPS"))

    pts, unk = _neutral_when_unknown(web.get("mobile_ok"), 15.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Mobile-friendly layout confirmed" if web.get("mobile_ok") else ("Mobile fit not verified" if unk else "Not mobile-friendly"))

    pts, unk = _neutral_when_unknown(web.get("updates_current"), 10.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Content is maintained by someone" if web.get("updates_current") else ("Update frequency not verified" if unk else "Not maintained for a long time"))

    pts, unk = _neutral_when_unknown(web.get("enquiry_capture"), 15.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Captures enquiries online" if web.get("enquiry_capture") else ("Enquiry component not verified" if unk else "No enquiry form or online intake"))

    if tier in ("ecommerce", "advanced"):
        score = min(100.0, score + 10.0)
        notes.append("and also takes orders or handles advanced interactions online")

    score = round(min(100.0, score), 1)
    details = ", ".join(notes)
    if unknowns:
        details += ". " + _UNVERIFIED_NOTE.format(n=unknowns)
    return score, {"score": score, "stars": calculate_stars(score), "details": details}


# ─── 2. Cloud (20%) ──────────────────────────────────────────────────────────
_CLOUD_LADDER = {
    "none": 10.0,
    "manual_usb": 35.0,
    "personal_cloud": 60.0,
    "managed_cloud": 92.0,
    # 未作答：取四档均值作中性估计，并如实标注"未核验"，绝不按最差档打分
    "unknown": 49.0,
}
_CLOUD_NOTES = {
    "none": "The core accounts and documents sit on one computer only: a failed drive or a ransomware attack stops everything.",
    "manual_usb": "Backed up by hand to an external drive or USB stick - this does not survive fire or theft, and there is no proof the last copy worked.",
    "personal_cloud": "Some files are on personal cloud drives, but the core financial accounts are still outside any managed off-site backup and recovery setup.",
    "managed_cloud": "A business-grade daily automatic encrypted off-site backup is in place, with disaster recovery that can actually be tested.",
    "unknown": "The backup approach was not confirmed this time (no answer, or an answer that could not be pinned down), so it is counted at a neutral value rather than deducted as missing.",
}


def evaluate_cloud_dimension(cloud: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    tier = cloud.get("backup_tier", "unknown")
    score = _CLOUD_LADDER.get(tier, _CLOUD_LADDER["unknown"])
    note = _CLOUD_NOTES.get(tier, _CLOUD_NOTES["unknown"])
    if cloud.get("versioning"):
        score = min(100.0, score + 8.0)
        note += " It also keeps a file version history."
    score = round(score, 1)
    return score, {"score": score, "stars": calculate_stars(score), "details": note}


# ─── 3. CRM (20%) ────────────────────────────────────────────────────────────
_CRM_LADDER = {"none": 12.0, "ad_hoc": 40.0, "spreadsheet": 60.0, "formal": 85.0,
               "unknown": 49.0}
_CRM_NOTES = {
    "none": "Customers and deals are scattered across salespeople's personal phones: when someone leaves the relationship leaves too, and there is no shared sales pipeline.",
    "ad_hoc": "There are occasional follow-up notes but no single owner, and the path from quote to order cannot be traced back.",
    "spreadsheet": "Records are kept centrally in an Excel ledger: there is a record, but no reminders, no pipeline, and it can be changed quietly.",
    "formal": "Deals run through a central pipeline with follow-up logs and separated permissions.",
    "unknown": "Where the customer records really live, and who owns them, was not confirmed this time; it is counted at a neutral value rather than deducted as missing.",
}


# 深挖题的评分调整：每项都必须在结论里点名，评委才看得懂分数怎么来的。
# 调整幅度被限制在本档宽度内（见 evaluate_crm_dimension 的 clamp），
# 因此"细节答得好"不会把一家根本没有集中系统的公司抬进正式 CRM 的分段。
_CRM_DEEP = {
    ("followup_owner", "personal"): (-12.0, "Customers are still tied to individual staff"),
    ("followup_owner", "shared_untracked"): (-5.0, "A handover means asking everything again, and follow-ups leave no record"),
    ("followup_owner", "designated"): (6.0, "Follow-up records the company can take over"),
    ("quote_to_order", "rekeyed"): (-6.0, "Quote to order needs retyping"),
    ("quote_to_order", "one_system"): (6.0, "Documents carry over from one system"),
    ("pipeline_visible", "none"): (-10.0, "The number and value of open deals is not visible"),
    ("pipeline_visible", "monthly_only"): (-4.0, "Pipeline figures lag by a month"),
    ("pipeline_visible", "realtime"): (8.0, "Live deal pipeline on screen"),
    ("lead_source_known", "unknown"): (-8.0, "No answer on where customers come from"),
    ("lead_source_known", "asked"): (2.0, "The source is asked about by hand when a deal closes"),
    ("lead_source_known", "tracked"): (6.0, "Enquiry sources can be traced automatically"),
}
_CRM_BANDS = {"none": (0.0, 30.0), "ad_hoc": (25.0, 48.0),
              "spreadsheet": (45.0, 72.0), "formal": (70.0, 100.0),
              "unknown": (30.0, 60.0)}


def evaluate_crm_dimension(crm: Dict[str, Any], context: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    tier = crm.get("tier", "unknown")
    score = _CRM_LADDER.get(tier, _CRM_LADDER["unknown"])
    notes = [_CRM_NOTES.get(tier, _CRM_NOTES["unknown"])]

    unknowns = 0
    if tier == "formal" and crm.get("company_owned_leads") is False:
        score = 65.0
        notes.append("But some deals still travel through personal chat tools, which leaves room for side deals and for customers walking out with a departing staff member.")
    else:
        pts, unk = _neutral_when_unknown(crm.get("company_owned_leads"), 10.0, 0.0)
        score += pts
        unknowns += unk
        if unk:
            notes.append("The evidence on who owns the customer records was not verified this time.")
        elif crm.get("company_owned_leads"):
            notes.append("The customer records belong to the company.")

    pts, unk = _neutral_when_unknown(crm.get("audit_trail"), 5.0, 0.0)
    score += pts
    unknowns += unk
    if unk:
        notes.append("Follow-up records not verified.")
    elif crm.get("audit_trail"):
        notes.append("Follow-ups can be traced back.")

    # 深挖题调整，并限制在本档宽度内
    low, high = _CRM_BANDS.get(tier, (0.0, 100.0))
    for field, value in (("followup_owner", crm.get("followup_owner")),
                         ("quote_to_order", crm.get("quote_to_order")),
                         ("pipeline_visible", crm.get("pipeline_visible")),
                         ("lead_source_known", crm.get("lead_source_known"))):
        delta = _CRM_DEEP.get((field, value))
        if not delta:
            continue
        score += delta[0]
        notes.append(f"{delta[1]} ({delta[0]:+.0f} points).")
    score = max(low, min(high, score))
    score = round(min(100.0, max(0.0, score)), 1)
    details = " ".join(notes)
    if unknowns:
        details += " " + _UNVERIFIED_NOTE.format(n=unknowns)
    return score, {"score": score, "stars": calculate_stars(score), "details": details}


# ─── 4. Marketing (15%) ──────────────────────────────────────────────────────
_ATTR_LADDER = {"none": 15.0, "self_reported": 45.0, "tracked": 72.0, "full": 92.0,
                "unknown": 56.0}
_ATTR_NOTES = {
    "none": "New business comes almost entirely from referrals and familiar customers, which cannot be repeated or measured, so ad spend is pure cost.",
    "self_reported": "There is a rough idea of which channels bring work, but no way to say which spend produced which order.",
    "tracked": "Tracking is in place, so enquiries can be seen by channel, but it is not yet linked through to orders and repeat purchases.",
    "full": "The whole path from exposure to enquiry to order is attributable, so spend and return can be optimised.",
    "unknown": "Where customers come from and how it is tracked was not confirmed this time; it is counted at a neutral value rather than deducted as missing.",
}


def evaluate_marketing_dimension(mkt: Dict[str, Any], web: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    attribution = mkt.get("attribution", "unknown")
    score = _ATTR_LADDER.get(attribution, _ATTR_LADDER["unknown"])
    notes = [_ATTR_NOTES.get(attribution, _ATTR_NOTES["unknown"])]

    channels = mkt.get("paid_channels") or []
    if channels:
        score = min(100.0, score + 6.0)
        notes.append(f"Paid channels: {', '.join(sorted(set(channels))[:4])}.")

    spend = mkt.get("spend_band")
    _SPEND_LABEL = {"none": "no spend", "under_1k": "about RM 1,000 a month",
                    "1k_5k": "RM 1,000-5,000 a month", "over_5k": "more than RM 5,000 a month"}
    if spend:
        notes.append(f"Spend level: {_SPEND_LABEL.get(spend, spend)}.")
    # 花钱本身不是成熟度，只惩罚"花了钱却看不到来源"这个真实存在的错配
    if spend in ("1k_5k", "over_5k") and attribution in ("none", "self_reported"):
        score -= 8.0
        notes.append("There is steady spend, but it cannot be tied to orders, so the money keeps going out without buying back an answer.")
    elif spend in ("1k_5k", "over_5k") and attribution in ("tracked", "full"):
        score += 5.0
        notes.append("Spend level and attribution ability match, so there is a basis for deciding whether to invest more.")

    if attribution in ("tracked", "full") and web.get("has_website") is False:
        score = max(25.0, score - 20.0)
        notes.append("But there is no company website for the traffic to land on, so the tracked visitors never become a company asset.")

    score = round(max(0.0, min(100.0, score)), 1)
    return score, {"score": score, "stars": calculate_stars(score), "details": " ".join(notes)}


# ─── 5. Cybersecurity (15%) ──────────────────────────────────────────────────
def evaluate_cybersecurity_dimension(cyber: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    企业通信与数据防护。此前 has_antivirus 从未被任何调用方赋值，
    导致本维度无论客户实际状况如何都封顶 45 分。现在判据全部来自可核验字段，
    且未核验项走中性值不扣分。
    """
    score = 0.0
    unknowns = 0
    notes = []

    pts, unk = _neutral_when_unknown(
        None if cyber.get("uses_personal_email") is None
        else (not cyber.get("uses_personal_email")), 24.0, 0.0)
    score += pts
    unknowns += unk
    if cyber.get("uses_personal_email") is None:
        notes.append("Not verified whether the outward-facing email address is on the company's own domain")
    elif cyber.get("uses_personal_email"):
        notes.append("Quotes go out from a personal free mailbox, so neither delivery reputation nor company identity is backed by anything")
    else:
        notes.append("Email on the company's own domain is in use")

    pts, unk = _neutral_when_unknown(cyber.get("ssl"), 14.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Encryption in transit confirmed" if cyber.get("ssl") else ("Certificate not verified" if unk else "No HTTPS"))

    pts, unk = _neutral_when_unknown(cyber.get("email_auth_blocking"), 20.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("SPF/DMARC blocking policy in place" if cyber.get("email_auth_blocking")
                 else ("Email anti-spoofing records not verified" if unk else "No SPF/DMARC blocking policy, so the domain can be impersonated in email"))

    pts, unk = _neutral_when_unknown(cyber.get("headers_hardened"), 13.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Basic security response headers present" if cyber.get("headers_hardened")
                 else ("Security headers not verified" if unk else "Basic security headers such as HSTS/CSP are missing"))

    pts, unk = _neutral_when_unknown(cyber.get("endpoint_protection"), 14.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Managed anti-ransomware protection on the computers" if cyber.get("endpoint_protection")
                 else ("Endpoint protection not verified" if unk else "No central control of the computers or anti-ransomware protection"))

    # 公网攻击面只能机检：没做过机检时保持未核验，既不给分也不扣分
    pts, unk = _neutral_when_unknown(cyber.get("attack_surface_ok"), 15.0, 0.0)
    score += pts
    unknowns += unk
    notes.append("Public attack surface closed (no reachable risky ports, no readable sensitive files)"
                 if cyber.get("attack_surface_ok")
                 else ("Attack surface not machine-checked" if unk
                       else "Public attack surface not closed: reachable ports, readable sensitive files or already-disclosed weaknesses"))

    score = round(min(100.0, score), 1)
    details = "; ".join(notes)
    if unknowns:
        details += ". " + _UNVERIFIED_NOTE.format(n=unknowns)
    return score, {"score": score, "stars": calculate_stars(score), "details": details}


# ─── 6. AI Adoption (15%) ────────────────────────────────────────────────────
_AI_LADDER = {"unknown": 30.0, "none": 12.0, "individual_use": 45.0,
              "workflow_pilot": 72.0, "deployed": 92.0}
_AI_NOTES = {
    "unknown": "AI adoption was inferred from the other facts and was not confirmed directly.",
    "none": "Every step is done by hand, with nothing assisted or automated.",
    "individual_use": "Staff use general AI tools on their own here and there, but the company's processes and data are not connected to them.",
    "workflow_pilot": "Automation has been piloted in one step of the work, but it does not yet close the loop across processes.",
    "deployed": "Automated handling is live on the sales or customer service side, replying within seconds around the clock.",
}


def evaluate_ai_adoption_dimension(ai: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    tier = ai.get("tier", "unknown")
    score = _AI_LADDER.get(tier, 30.0)
    notes = [_AI_NOTES.get(tier, _AI_NOTES["unknown"])]
    if ai.get("inferred"):
        notes.append(explain(ai, ai["inferred"]))
    if ai.get("has_agent") and tier not in ("deployed",):
        score = max(score, 88.0)
        notes.append("Automated intake is already running around the clock.")
    if not ai.get("structured_data") and tier in ("workflow_pilot", "deployed"):
        notes.append("But the business data is not structured yet, so there is little real data for AI to read.")
    score = round(min(100.0, score), 1)
    return score, {"score": score, "stars": calculate_stars(score), "details": " ".join(notes)}


# ─── 汇总 ────────────────────────────────────────────────────────────────────
def calculate_dms(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算六维 DMS。接受任意词表的原始输入，内部统一 normalize。

    输出每个维度都带 evidence_source（实测/自述/推断），评分卡与蓝图必须显示，
    这是官方 Step 4 "evidence-based" 要求的核心，也是本产品的差异化。
    """
    facts = data.get("_facts") if isinstance(data, dict) and "_facts" in data else normalize(data)
    ctx = facts.get("_context", {})

    web_score, web_meta = evaluate_website_dimension(facts["web"])
    cloud_score, cloud_meta = evaluate_cloud_dimension(facts["cloud"])
    crm_score, crm_meta = evaluate_crm_dimension(facts["crm"], ctx)
    mkt_score, mkt_meta = evaluate_marketing_dimension(facts["marketing"], facts["web"])
    sec_score, sec_meta = evaluate_cybersecurity_dimension(facts["cyber"])
    ai_score, ai_meta = evaluate_ai_adoption_dimension(facts["ai"])

    prov = facts.get("_provenance", {})

    def _src(group: str) -> str:
        sources = {prov[k] for k in prov if k.startswith(f"{group}.")}
        if SRC_MACHINE in sources:
            return SRC_LABELS[SRC_MACHINE]
        if sources and sources <= {SRC_INFERRED}:
            return SRC_LABELS[SRC_INFERRED]
        return SRC_LABELS[SRC_STATED]

    for group, meta in (("web", web_meta), ("cloud", cloud_meta), ("crm", crm_meta),
                        ("marketing", mkt_meta), ("cyber", sec_meta), ("ai", ai_meta)):
        meta["evidence_source"] = _src(group)

    overall_score = round(
        web_score * DIMENSION_WEIGHTS["website"]
        + cloud_score * DIMENSION_WEIGHTS["cloud"]
        + crm_score * DIMENSION_WEIGHTS["crm"]
        + mkt_score * DIMENSION_WEIGHTS["marketing"]
        + sec_score * DIMENSION_WEIGHTS["cybersecurity"]
        + ai_score * DIMENSION_WEIGHTS["ai_adoption"],
        1,
    )

    if overall_score < 40.0:
        tier = "Emerging / vulnerable"
        badge_color = "coral"
    elif overall_score < 70.0:
        tier = "Transitioning / growing"
        badge_color = "amber"
    else:
        tier = "Optimized / leader"
        badge_color = "emerald"

    return {
        "overall_score": overall_score,
        "overall_stars": calculate_stars(overall_score),
        "tier": tier,
        "badge_color": badge_color,
        "weights": DIMENSION_WEIGHTS,
        "dimensions": {
            "website": web_meta,
            "cloud": cloud_meta,
            "crm": crm_meta,
            "marketing": mkt_meta,
            "cybersecurity": sec_meta,
            "ai_adoption": ai_meta,
        },
        "evidence_provenance": prov,
    }
