"""
Cradilot Core - 统一评估事实契约 (Assessment Facts)

为什么需要这个模块
──────────────────
系统此前有两套互不兼容的输入词表喂给同一个 dms_engine：

  /api/assess  →  cloud_storage_status / crm_system / marketing_tracker /
                  email_type / ai_automation_status
  wiki 路径    →  dr_backup_status / uses_personal_whatsapp / uses_personal_email
                  / current_tools(+ads token)

dms_engine 只认后者。结果：
  · cloud 维度在 /api/assess 路径上恒为 35 —— 有企业级每日异地加密备份与完全无备份同分
  · marketing 在 agentic 路径上恒为 30 —— 用户答过的追踪事实被采进 wiki 后丢弃
  · has_antivirus 全库无人赋值 —— cybersecurity 上限锁死 45
  · 由此 DMS 理论最高 62.5，而第三档门槛 70 —— 任何企业都不可能被评为"成熟标杆"

本模块是唯一入口：任何来源先 normalize() 成一套规范字段，再交给评分引擎。
每条事实带来源（机检 / 自述 / 推断），供评分卡如实标注证据出处。
"""

from typing import Any, Dict, List, Optional

from core.ai_inference import infer_ai_tier

# 证据来源。机检 > 自述 > 推断，评分卡与蓝图必须显示出处。
SRC_MACHINE = "machine"
SRC_STATED = "owner_stated"
SRC_INFERRED = "inferred"
SRC_LABELS = {
    SRC_MACHINE: "Measured",
    SRC_STATED: "You stated",
    SRC_INFERRED: "Inferred",
}

BACKUP_TIERS = ("none", "manual_usb", "personal_cloud", "managed_cloud", "unknown")
CRM_TIERS = ("none", "ad_hoc", "spreadsheet", "formal", "unknown")
ATTRIBUTION_TIERS = ("none", "self_reported", "tracked", "full", "unknown")
AI_TIERS = ("unknown", "none", "individual_use", "workflow_pilot", "deployed")

# 深挖题落证的键名。采集端与评分端共用这一份，避免"题问了、答案存了、评分读不到"。
DEEP_FACT_KEYS = ("lead_source_known", "followup_owner", "quote_to_order",
                  "pipeline_visible", "marketing_spend")


def _tri(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    """三态布尔：None 表示未核验，绝不能与 False 混同。"""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "y", "已配置", "是"):
        return True
    if text in ("false", "0", "no", "n", "未配置", "否"):
        return False
    return default


def _as_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip().lower() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip().lower() for v in value if str(v).strip()]


# 采集层在"听到回答但解析不出取值"时会写占位值锁证（避免反复追问同一题）。
# 这类占位绝不能被下游读成真实答案——否则"没听懂"会变成"贵司没有 CRM"并据此扣分。
_JUNK_VALUES = {"", "recorded", "unspecified", "n/a", "na", "-", "未回答", "unknown_sent"}


def _first(raw: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """按别名优先级取第一个存在的、且有实际含义的非空值。"""
    for k in keys:
        if k not in raw:
            continue
        value = raw[k]
        if value is None:
            continue
        # 注意：显式 False 是真实回答，必须保留；只有占位字符串才跳过
        if isinstance(value, str) and value.strip().lower() in _JUNK_VALUES:
            continue
        return value
    return default


# ─── 词表归一 ────────────────────────────────────────────────────────────────
_BACKUP_MAP = {
    "no_backup": "none", "none": "none", "single_pc": "none", "single": "none",
    "manual": "none", "local": "none", "unbackup": "none",
    "pendrive": "manual_usb", "manual_usb": "manual_usb", "usb": "manual_usb",
    "hard drive": "manual_usb", "硬盘": "manual_usb", "u盘": "manual_usb",
    "cloud_drive": "personal_cloud", "google drive": "personal_cloud",
    "onedrive": "personal_cloud", "dropbox": "personal_cloud", "个人网盘": "personal_cloud",
    "managed_cloud": "managed_cloud", "acronis": "managed_cloud", "cloud_auto": "managed_cloud",
    "enterprise_cloud": "managed_cloud", "异地": "managed_cloud", "灾备": "managed_cloud",
}

_CRM_MAP = {
    "none": "none", "no_crm": "none", "paper": "none", "handwritten": "none",
    "personal_whatsapp": "none", "personal_phone": "none", "whatsapp": "none",
    "ad_hoc": "ad_hoc", "wechat": "ad_hoc", "口头": "ad_hoc",
    "spreadsheet": "spreadsheet", "excel": "spreadsheet", "台账": "spreadsheet",
    "formal": "formal", "formal_crm": "formal", "crm": "formal",
    "centralized": "formal", "hubspot": "formal", "salesforce": "formal",
    "freshsales": "formal", "erp": "formal",
}

_WEB_MAP = {
    "no_site": ("none", False, False), "none": ("none", False, False),
    "dormant": ("dormant", False, False), "outdated": ("dormant", False, False),
    "standard": ("modern", True, True), "modern": ("modern", True, True),
    "ecommerce": ("ecommerce", True, True), "advanced": ("advanced", True, True),
}

_PAID_TOKENS = ("facebook ads", "google ads", "tiktok", "meta ads", "ig ads",
                "adwords", "shopee ads", "lazada", "红书", "小红书")

# /api/assess 的旧词表 → 规范 AI 档位。缺这张表会让 ai 恒落到 unknown 中性值。
_AI_STATUS_MAP = {
    "manual": "none", "none": "none", "no_ai": "none", "纯手工": "none",
    "partial": "individual_use", "ad_hoc": "individual_use", "chatgpt": "individual_use",
    "pilot": "workflow_pilot", "trial": "workflow_pilot",
    "middleware": "deployed", "deployed": "deployed", "ai_agent": "deployed",
    "enterprise": "deployed",
}


def _match_tier(value: str, mapping: Dict[str, str], default: str) -> str:
    """按 token 长度降序匹配：必须让 manual_usb 先于 manual 命中。

    字典插入序匹配曾让 "manual" 抢先命中 "manual_usb"，把有拷盘备份的企业
    错判成完全无备份，两者拿到同一个分数。
    """
    if not value:
        return default
    for token in sorted(mapping, key=len, reverse=True):
        if token in value:
            return mapping[token]
    return default


def _backup_tier(raw: Dict[str, Any]) -> str:
    value = str(_first(raw, ["dr_backup_status", "backup_strategy", "cloud_storage_status",
                             "backup_mode", "backup_freq"], "") or "").strip().lower()
    tier = _match_tier(value, _BACKUP_MAP, "")
    if tier:
        return tier
    # 没有任何备份词，但有自动化异地备份的布尔真值
    if _tri(_first(raw, ["has_offsite_backup", "has_automated_backup"])):
        return "managed_cloud"
    return "unknown"        # 没答过 ≠ 没有备份


def _crm_tier(raw: Dict[str, Any]) -> str:
    value = str(_first(raw, ["crm_system", "crm_mode", "crm_status"], "") or "").strip().lower()
    tier = _match_tier(value, _CRM_MAP, "")
    if tier:
        return tier
    tools = _as_list(raw.get("current_tools"))
    if any(t in tools for t in ("crm", "freshsales", "hubspot", "salesforce", "erp")):
        return "formal"
    if any(t in tools for t in ("excel", "spreadsheet", "台账")):
        return "spreadsheet"
    return "unknown"        # 没有任何线索可判：不能按"客户全在员工手机里"打分


def _attribution(raw: Dict[str, Any]) -> str:
    tracker = str(_first(raw, ["marketing_tracker", "attribution"], "") or "").strip().lower()
    tools = _as_list(raw.get("current_tools"))
    measured = ("pixel_and_ga4" in tracker or "pixel" in tracker or "ga4" in tracker
                or any(t in tools for t in ("pixel", "ga4", "analytics", "gtm", "meta pixel")))
    retarget = _tri(raw.get("has_retargeting"))
    if measured and retarget:
        return "full"
    if measured:
        return "tracked"
    if tracker == "none":
        return "none"           # 明确答"完全没有追踪"
    if not tracker:
        return "unknown"        # 没答过，不能按"零追踪"打分
    if tracker in ("referral", "offline", "ad hoc", "ad_hoc"):
        return "self_reported"
    return "self_reported"


def _choice(value: Any, allowed) -> Optional[str]:
    """取值只在枚举内才采信；其余（含占位值）一律视为未采集，不做调整。"""
    text = str(_tri_text(value) or "").strip().lower()
    return text if text in allowed else None


def _tri_text(value: Any) -> Optional[str]:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return None if text.lower() in _JUNK_VALUES else text


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    把任意来源的字段映射到唯一的规范结构。dms_engine 与 ars_engine 只读本函数输出。

    输出保证：六个维度的每个判据都存在（可能是 None 表示未核验），
    因此任何维度都不可能因为"字段名没对上"而退化成常数。
    """
    raw = raw or {}
    if "web" in raw and "cyber" in raw and "_provenance" in raw:
        # 已经是规范结构：再归一化一遍会把所有维度洗成"未知"，静默毁掉已采到的事实
        return raw
    web_tier = str(_first(raw, ["web_engine_status", "website_status", "web_mode"], "") or "").strip().lower()
    web_tuple = _WEB_MAP.get(web_tier)
    has_website = _tri(_first(raw, ["has_website"]), default=None)
    if web_tuple:
        web_state = web_tuple[0]
        if has_website is None:
            has_website = web_state != "none"
    else:
        if has_website is None:
            has_website = _tri(_first(raw, ["has_domain"]), default=None)
        web_state = ("modern" if has_website else "none") \
            if has_website is not None else "unknown"

    ssl = _tri(_first(raw, ["has_ssl", "ssl_valid"]), default=None)
    if ssl is None and web_tuple:
        ssl = web_tuple[2]
    mobile = _tri(_first(raw, ["mobile_ok", "mobile_responsive", "viewport_ok"]), default=None)
    if mobile is None and web_tuple:
        mobile = web_tuple[1]

    paid = [t for t in _as_list(raw.get("current_tools")) if any(p in t for p in _PAID_TOKENS)]
    if not paid and str(_first(raw, ["marketing_channel"], "")) != "":
        paid = [t for t in _as_list(raw.get("marketing_channel"))
                if any(p in t for p in _PAID_TOKENS)]

    email_type = str(_first(raw, ["email_type"], "") or "").strip().lower()
    uses_personal_email = _tri(_first(raw, ["uses_personal_email"]), default=None)
    if email_type:
        uses_personal_email = email_type in ("free_gmail", "gmail", "yahoo", "personal")
    # 未采集时保持 None：不能替客户断言"在用个人邮箱"，那会凭空给出或扣掉整段分数

    ai_tier = str(_first(raw, ["ai_tier"], "") or "").strip().lower()
    if ai_tier not in AI_TIERS or ai_tier == "unknown":
        legacy = str(_first(raw, ["ai_automation_status"], "") or "").strip().lower()
        ai_tier = _AI_STATUS_MAP.get(legacy, ai_tier or "unknown")
    has_agent = _tri(_first(raw, ["has_ai_agent"]))
    if has_agent and ai_tier in ("unknown", "none"):
        ai_tier = "deployed"
    if has_agent is False and ai_tier == "unknown":
        # 明确答"没有"不等于没答：不能落到 unknown 那一档中性分上。
        ai_tier = "none"

    facts: Dict[str, Any] = {
        "web": {
            "tier": web_state,
            "has_website": has_website,
            "has_domain": _tri(_first(raw, ["has_domain"]), default=has_website),
            "ssl": ssl,
            "mobile_ok": mobile,
            "updates_current": _tri(_first(raw, ["updates_current", "site_updated_recently"])),
            "enquiry_capture": _tri(_first(raw, ["enquiry_capture", "has_contact_form"])),
        },
        "cloud": {
            "backup_tier": _backup_tier(raw),
            "offsite_automated_daily": _backup_tier(raw) == "managed_cloud",
            "versioning": _tri(_first(raw, ["has_versioning"])),
        },
        "crm": {
            "tier": _crm_tier(raw),
            "lead_source_known": _choice(_first(raw, ["lead_source_known"]),
                                         ("unknown", "asked", "tracked")),
            "followup_owner": _choice(_first(raw, ["followup_owner"]),
                                       ("personal", "shared_untracked", "designated")),
            "quote_to_order": _choice(_first(raw, ["quote_to_order"]),
                                       ("rekeyed", "semi", "one_system")),
            "pipeline_visible": _choice(_first(raw, ["pipeline_visible"]),
                                         ("none", "monthly_only", "realtime")),
            "company_owned_leads": _tri(
                _first(raw, ["is_crm_centralized", "company_owned_leads"]),
                default=(_crm_tier(raw) == "formal")),
            "audit_trail": _tri(_first(raw, ["has_followup_audit_trail", "audit_trail"])),
            "leaves_with_staff": _tri(_first(raw, ["leads_leave_with_staff"]), default=False),
        },
        "marketing": {
            "paid_channels": paid,
            "spend_band": _choice(_first(raw, ["marketing_spend"]),
                                  ("none", "under_1k", "1k_5k", "over_5k")),
            "attribution": _attribution(raw),
            "has_analytics": _tri(_first(raw, ["has_analytics"]),
                                 default=_attribution(raw) in ("tracked", "full")),
        },
        "cyber": {
            "email_type": ("business_domain" if uses_personal_email is False
                           else "free_gmail" if uses_personal_email is True else None),
            "uses_personal_email": uses_personal_email,
            "ssl": ssl,
            "endpoint_protection": _tri(_first(raw, ["has_antivirus", "endpoint_protection"])),
            "email_auth_blocking": _tri(_first(raw, ["dmarc_blocking", "email_auth_ok"])),
            "headers_hardened": _tri(_first(raw, ["security_headers_ok", "headers_ok"])),
            # 只有机检能填：老板不会自报"我数据库端口开着"
            "attack_surface_ok": _tri(_first(raw, ["attack_surface_ok"]), default=None),
        },
        "ai": {
            "tier": ai_tier,
            "has_agent": has_agent,
            "individual_use": _tri(_first(raw, ["staff_use_ai"]), default=None),
            "structured_data": _tri(_first(raw, ["has_structured_data"]),
                                   default=any(t in _as_list(raw.get("current_tools"))
                                               for t in ("sql", "erp", "进销存", "database"))),
        },
        "_context": {
            "industry": raw.get("industry", ""),
            "team_size": raw.get("team_size", ""),
            "annual_turnover": raw.get("annual_turnover", ""),
            "growth_objective": raw.get("growth_objective", ""),
            "biggest_challenge": raw.get("biggest_challenge", ""),
            "current_tools": _as_list(raw.get("current_tools")),
        },
        "_provenance": {},
    }

    # 上游（机检路径）把探针得出的布尔值放在 _machine_flags 里。
    # 这里既取值也记出处——两者必须同生同灭，否则会出现"标注实测、实际按自述打分"。
    _FIELD_GROUPS = {
        "has_ssl": [("web", "ssl"), ("cyber", "ssl")],
        "mobile_ok": [("web", "mobile_ok")],
        "updates_current": [("web", "updates_current")],
        "enquiry_capture": [("web", "enquiry_capture")],
        "security_headers_ok": [("cyber", "headers_hardened")],
        "dmarc_blocking": [("cyber", "email_auth_blocking")],
        "endpoint_protection": [("cyber", "endpoint_protection")],
        "attack_surface_ok": [("cyber", "attack_surface_ok")],
    }
    for flag, value in (raw.get("_machine_flags") or {}).items():
        truth = _tri(value, default=None)
        if truth is None:
            continue          # 未核验不得写入：一次断网不能永久压低评分
        for group, field in _FIELD_GROUPS.get(flag, []):
            facts[group][field] = truth
            facts["_provenance"][f"{group}.{field}"] = SRC_MACHINE

    # wiki 直接转机会检原始结论，check→字段 的映射只存在于 apply_machine_findings 一处，
    # 新增检查项不会因为"忘了在这张表里再加一行"而采到了却不参与评分。
    if raw.get("_machine_findings"):
        apply_machine_findings(facts, raw["_machine_findings"])

    # AI 维度：只有在既没问到也没测到时才允许推断，且必须把依据与"推断"标签一起带下去。
    if facts["ai"]["tier"] == "unknown":
        inferred = infer_ai_tier(facts)
        if inferred.get("tier"):
            facts["ai"]["tier"] = inferred["tier"]
            facts["ai"]["inferred"] = inferred
            facts["_provenance"]["ai.tier"] = SRC_INFERRED
    return facts


# ─── 机检结论并入 ────────────────────────────────────────────────────────────
# site_audit 的 check id → 规范字段。机检值优先级高于自述：探针看到的比老板记得的准。
_MACHINE_WEB = {
    "https_enforced": ("web", "ssl"),
    "certificate": ("web", "ssl"),
    "mobile_viewport": ("web", "mobile_ok"),
    "site_content": ("web", "updates_current"),
    # 深探里只有这两项的语义是"存在与否"本身，可以直接进判据；
    # 其余上百条只作证据与蓝图素材，不让第②步的可见范围偷偷改变六维分数。
    "lead_form": ("web", "enquiry_capture"),
    "conversion_tracking": ("marketing", "has_analytics"),
}
_MACHINE_CYBER = {
    "header_score": ("cyber", "headers_hardened"),
    "email_authentication": ("cyber", "email_auth_blocking"),
    "mixed_content": ("cyber", "headers_hardened"),
}

# 攻击面收口情况。这一项只能机检：没有老板会自报"我的数据库端口开着"。
# 多条目命中时按最保守结论计（任一 fail 即视为未收口），见 apply_machine_findings。
_SURFACE = ("cyber", "attack_surface_ok")
_MACHINE_SURFACE = {
    "known_vulnerabilities": _SURFACE,
    "software_lifecycle": _SURFACE,
    "exposed_services": _SURFACE,
    "backup_artifacts": _SURFACE,
    "sensitive_paths": _SURFACE,
    "origin_concealment": _SURFACE,
    "wordpress_surface": _SURFACE,
    "wordpress_plugins": _SURFACE,
}

# 只作证据与蓝图素材、不参与任何判据的机检结论（速度、机房、域名到期等）。
_MACHINE_OPS = {
    "response_time", "page_weight", "technology_stack", "hosting_location",
    "domain_registrant", "domain_expiry", "cloudflare", "http_version", "reachability",
    "server_version_disclosure", "cookie_flags",
}


def classify_machine_check(check_id: str) -> Optional[str]:
    """机检结论归属哪一组判据。None = 本引擎不认识这个 check id。"""
    if check_id in _MACHINE_WEB:
        return "web"
    if check_id in _MACHINE_CYBER or check_id in _MACHINE_SURFACE:
        return "cyber"
    if check_id in _MACHINE_OPS:
        return "ops"
    return None


def apply_machine_findings(facts: Dict[str, Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    把 /api/audit/site 的逐项结论并进规范事实，并记录来源。

    只接受 pass/fail：unverified 保持 None（未核验），绝不折算成 False。
    这条不变量是整个证据系统的地面——否则"这次没测到"会变成"贵司缺失该能力"，
    评分引擎就会拿一个测量事故去扣客户的分。
    """
    provenance = facts.setdefault("_provenance", {})
    reached = False
    for f in findings or []:
        status = f.get("status")
        if status not in ("pass", "fail"):
            continue
        truth = (status == "pass")
        check = f.get("check", "")
        mapping = dict(_MACHINE_WEB)
        mapping.update(_MACHINE_CYBER)
        mapping.update(_MACHINE_SURFACE)
        target = mapping.get(check)
        if not target:
            continue
        group, field = target
        # 机检覆盖自述：探针看到的比老板记得的准。
        # 两项机检冲突时按不成立计——证书过期就不能宣称 HTTPS 完好，哪怕 URL 跳转正常。
        if provenance.get(f"{group}.{field}") == SRC_MACHINE:
            truth = bool(facts[group].get(field)) and truth
        facts[group][field] = truth
        provenance[f"{group}.{field}"] = SRC_MACHINE
        if group == "web":
            reached = True      # 能得出 web 组结论，说明首页确实被打开过——fail 同样证明存在

    if reached:
        # 自述"没有官网"但老板给的网址答了：以探针为准，否则评分会因一句话归零。
        web = facts["web"]
        web["has_website"] = True
        web["has_domain"] = True
        provenance["web.has_website"] = SRC_MACHINE
        if web.get("tier") in (None, "", "none"):
            web["tier"] = "modern"
    return facts


def provenance_of(facts: Dict[str, Any], group: str, field: str) -> str:
    return facts.get("_provenance", {}).get(f"{group}.{field}", SRC_STATED)
