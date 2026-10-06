"""
Cradilot Core - Recommendation Engine & Action Roadmap
Matches diagnosed SME pain points to our product SKUs and explains WHY.
Generates 3-Phase Action Roadmap and evidence-based Top 5 pain points.
同一道题还把目录里真实的备选一起比较（简报第 4-5 页 "Here's the exciting part"），
比较结果挂在阶段的 option_matrix 上，只有选中的那条进合计。

真实性契约（阶段三补链）：痛点必须由已核验事实驱动，禁止无视入参返回固定清单；
未锁证的事实不写入证据链，未命中的风险不编造金额。
同一条契约管着比较层：备选的价格一律用目录实价，查不到年价的只写"待报价"，
判据要的事实没采到就在句子里写明没采到，且备选永远不进 budget_myr、采购车与 ROI 分母。
"""

from typing import Dict, Any, List, Optional

# 痛点金额只有这一个来源：ROI 用同一套假设算出的两笔收益，按机制分到对应维度。
# 旧版自带一张 BENCHMARK_LOSS_MYR（12 个写死金额，例如 crm=28000、ai=23040），
# 既能凭空印出"年度损失上限 RM 44,016"，又与页面上任何一条算式都对不上，
# 还被冠以"贵司本次填报口径"——客户从没填过。删表，改为按 ROI 算式分摊。
_LOSS_LABOR_DIMS = ("crm", "digital_workflow", "process_maturity", "data_availability")
_LOSS_REVENUE_DIMS = ("ai", "web", "marketing")
_NO_AMOUNT_NOTE = ("This is an exposure to risk. It is outside what this audit can turn into a "
                   "ringgit amount, so it is shown by severity only.")


def apply_loss_model(findings: List[Dict[str, Any]],
                     roi_result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 ROI 算出的年度收益按机制分摊到痛点上。

    均分而不是各自估一笔：同一批被省下的工时不会既算进 CRM 又算进对账，
    分给该机制下的各项才不会被加出来一个超过 ROI 的损失总额。
    """
    roi_result = roi_result or {}
    pools = {
        "labor": (float(roi_result.get("annual_labor_savings") or 0.0), _LOSS_LABOR_DIMS),
        "revenue": (float(roi_result.get("annual_salvaged_revenue") or 0.0), _LOSS_REVENUE_DIMS),
    }
    members = {
        kind: [f for f in findings if f.get("dimension") in dims]
        for kind, (amount, dims) in pools.items()
    }
    for f in findings:
        dim = f.get("dimension")
        kind = ("labor" if dim in _LOSS_LABOR_DIMS
                else "revenue" if dim in _LOSS_REVENUE_DIMS else None)
        total = pools[kind][0] if kind else 0.0
        rows = members.get(kind or "", [])
        share = len(rows) or 1
        if kind and total > 0:
            each = round(total / share, 2)
            # 余数给第一条：痛点金额必须精确加回 ROI 的那一笔，不能差一分
            amount = round(total - each * (share - 1), 2) if id(rows[0]) == id(f) else each
            f["loss_myr"] = amount
            f["loss_basis"] = (f"Split with the same ROI formula: this mechanism's annual gain of "
                               f"RM {total:,.2f} divided by {share} confirmed items")
        else:
            f["loss_myr"] = None
            f["loss_basis"] = _NO_AMOUNT_NOTE
    return findings


# 旧库里的 wiki 痛点行可能没有 dimension 字段，只能靠标题特征词归属维度。
# 标题已转英文，但历史会话仍是中文，所以两种都要认；只在行内没有 dimension 时才用。
_DIM_HINT = {
    "cloud": ("backup", "one pc", "usb", "备份", "单机", "异地"),
    "crm": ("customer list", "customer record", "crm", "客户", "客户资料"),
    "ai": ("enquiry", "enquiries", "after hours", "after closing", "询盘", "夜间"),
    "web": ("website", "web presence", "官网", "网站"),
    "cyber": ("email", "mailbox", "ssl", "certificate", "邮箱", "证书"),
    "marketing": ("ads", "advertis", "campaign", "广告", "投放"),
    "digital_workflow": ("reconcil", "delivery note", "对账", "单据"),
    "process_maturity": ("sop", "faq", "procedure", "流程", "标准"),
    "data_availability": ("structured data", "数据"),
    "employee_skills": ("staff", "employee", "training", "员工", "培训"),
}


def _title_marks_dimension(title: str, dim: str) -> bool:
    low = str(title or "").lower()
    return any(tok.lower() in low for tok in _DIM_HINT.get(dim, ()))


def _fact_cited(quote: str, fact_desc: str) -> str:
    """有用户原话就引用原话，没有就只陈述已核验事实本身，绝不伪造引语。"""
    return f"Customer's own words: {quote}" if quote else f"Verified fact: {fact_desc}"


# 痛点清单与路线图共用同一组现状判据：两边各写一遍迟早会分叉成
# "报告里有这条痛点、蓝图里却没有对应任务"。未采集一律 False（不成一条）。
_PHONE_CRM = ("personal_phone", "personal_whatsapp", "whatsapp", "ad_hoc", "wechat")
_LEDGER_CRM = ("spreadsheet", "excel", "excel_ledger", "ledger")


def _crm_state(data: Dict[str, Any]) -> str:
    """'phone' / 'ledger' / ''（'' = 集中式或未采集，两种都不构成痛点）。"""
    crm_sys = str(data.get("crm_system", "") or "").lower()
    if crm_sys in _PHONE_CRM:
        return "phone"
    return "ledger" if crm_sys in _LEDGER_CRM else ""


def _no_after_hours_cover(data: Dict[str, Any]) -> bool:
    """客户答过的 AI 档位优先；没选档位时才用"夜间是否漏单"这个代理，None 不算答案。"""
    ai_tier = str(data.get("ai_tier", "") or "").lower()
    if ai_tier and ai_tier != "unknown":
        return ai_tier in ("none", "individual_use")
    return data.get("has_ai_agent") is False


_STRUCTURED_TOOLS = {"sql", "erp", "crm", "进销存", "database", "pos"}


def _data_layer_missing(data: Dict[str, Any]) -> bool:
    status = str(data.get("data_availability_status", "") or "").lower()
    if status in ("unstructured", "siloed", "spreadsheet"):
        return True
    if status == "structured":
        return False
    tools = [str(t).lower() for t in data.get("current_tools", [])]
    # 一条工具线索都没有 = 没问过，不能反推成"数据全在表格和笔记里"
    return bool(tools) and not _STRUCTURED_TOOLS.intersection(tools)


def _sop_missing(data: Dict[str, Any]) -> bool:
    return data.get("has_sop") is False


def _documents_rekeyed(data: Dict[str, Any]) -> bool:
    """全手工与"部分在线、月底仍要人工对一遍"都是二次录入，只有真自动了才算补齐。

    归一化修好之后 "semi" 不再被并成 "manual"，这两处判定必须自己认得中间档，
    否则答了"半自动"的客户会在路线图里凭空消失。
    """
    return str(data.get("order_reconcile_flow", "")).lower() in ("manual", "semi")


def _attribution_missing(data: Dict[str, Any]) -> bool:
    """线索渠道量不出效果：只靠转介绍，与"在投广告但没装 pixel/GA4"是同一条缺口。"""
    return str(data.get("marketing_tracker", "")).lower() in ("none", "untracked")


def generate_pain_points(
    data: Dict[str, Any],
    dms_result: Optional[Dict[str, Any]] = None,
    wiki_pains: Optional[List[Dict[str, Any]]] = None,
    evidence_quotes: Optional[Dict[str, str]] = None,
    conflict_sink: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    基于已核验事实逐维度判定 Top 5 商业失血点。
    每条痛点必须满足：事实确实成立、证据可溯源、金额标注来源。
    全部维度达标时返回空列表——诚实呈现"未发现重大失血"，而不是套用模板。
    """
    data = data or {}
    evidence_quotes = evidence_quotes or {}
    findings: List[Dict[str, Any]] = []

    def add(dim: str, title: str, fact_desc: str, impact: str, category: str,
            loss: Optional[float] = None, severity: str = "HIGH",
            cradle_gap: str = "", solution: str = "") -> None:
        quote = (evidence_quotes.get(dim) or "").strip()
        findings.append({
            "id": "",
            "title": title,
            "evidence": _fact_cited(quote, fact_desc),
            "quote": quote,
            "impact": impact,
            "category": category,
            "dimension": dim,
            "loss_myr": None if loss is None else loss,
            "severity": severity,
            "cradle_gap": cradle_gap,
            "solution": solution,
            "source": "verified_fact",
        })

    # ── 1. 数据抗灾（cloud）──
    dr_status = str(data.get("dr_backup_status", "")).lower()
    if dr_status == "no_backup":
        add("cloud", "Company accounts live on one computer only",
            "Finance and customer documents are saved only on that single local PC, with no automatic off-site copies",
            "Ransomware or a failed disk can wipe out past quotes, delivery orders and customer records together", "Security",
            severity="CRITICAL",
            cradle_gap="The recovery has never been practised, so whether billing can restart on the day of a failure is unknown.",
            solution="Acronis Cloud Backup (daily off-site encrypted copies)")
    elif dr_status == "pendrive":
        add("cloud", "Backups rely on someone plugging in a hard drive",
            "Backups depend on manually plugging in a portable drive or USB stick, with no off-site copies of past versions",
            "One missed session means those records are gone for good; if the drive and the PC are locked at the same time, nothing can be recovered", "Security",
            severity="HIGH",
            cradle_gap="Nobody has checked whether a backup actually works; its value only shows on the first real restore.",
            solution="Acronis Cloud Backup (automatic incremental copies + ransomware-behaviour blocking)")

    # ── 2. 客户资料归属（crm）──
    crm_state = _crm_state(data)
    if crm_state == "phone":
        add("crm", "Customer records sit on the salesperson's phone; when the person leaves, the customer leaves",
            "Enquiries and follow-up notes are scattered across staff's personal chat apps; the company has no central customer record",
            "Contacts leave with the departing staff member; when a new person takes over, the whole history has to be asked again", "Sales",
            cradle_gap="The company cannot say how many active customers it has, and cannot prove the customers belong to the company.",
            solution="WhatsApp Business multi-seat + cloud customer centre")
    elif crm_state == "ledger":
        add("crm", "The customer list is one spreadsheet, and nobody can see how far each follow-up got",
            "Customers and enquiries are keyed into spreadsheets by hand, with no reminders, no funnel and no edit history",
            "A spreadsheet can be changed quietly; who to follow up rests on personal memory, and busy weeks drop leads", "Sales",
            severity="MEDIUM",
            cradle_gap="The company has no live pipeline and cannot say which deal is stuck at which step.",
            solution="light CRM + cloud customer centre (follow-up history and permission-based handover)")

    # ── 3. 非工作时段应答（ai）──
    if _no_after_hours_cover(data):
        add("ai", "Nobody answers enquiries after working hours",
            "Night and public-holiday enquiries get no response, with no automatic reply in place",
            "Buyers ask the next supplier right away; a reply the next day lands when the chance to close has already dropped", "Revenue",
            cradle_gap="The company has no record of who took the first enquiry or how long the first reply took.",
            solution="AI smart enquiry reply (7x24 automatic first response)")

    # ── 4. 官方门户（web）──
    web_status = str(data.get("web_engine_status", "")).lower()
    if web_status == "no_site":
        add("web", "No website, so out-of-town and overseas customers cannot find the company",
            "The business has no website under its own domain, so out-of-state and overseas buyers cannot verify the company",
            "Bulk enquiries that come through online channels never arrive; the business runs on word-of-mouth referrals", "Marketing",
            cradle_gap="When customers cannot find you in search, buyers who were ready to purchase go to a competitor that does show up.",
            solution="Managed WordPress AI (LiteSpeed NVMe + automatic SSL)")
    elif web_status == "dormant":
        add("web", "The website has not been maintained for years and phones still see a security warning",
            "The website has gone years without updates, missing an SSL certificate and a mobile-friendly layout",
            "The browser flashes a security warning, and customers leave before reading anything", "Marketing",
            severity="MEDIUM",
            cradle_gap="There is a website but no way to send an enquiry, so visitors see it and still cannot make contact.",
            solution="site-wide SSL + mobile rebuild with CDN acceleration")

    # ── 5. 对外邮箱（cyber）──
    if data.get("uses_personal_email", False):
        add("cyber", "Quotes go out from a free personal email address",
            "Quotes and contracts are sent from a personal mailbox with no company domain, without SPF/DKIM/DMARC and without an audit trail",
            "The receiver's spam filter is more likely to block the mail, and anyone can pretend to be your sender", "Compliance",
            severity="MEDIUM",
            cradle_gap="After a staff member leaves, the customer emails that ran through the personal mailbox cannot be recovered, not one of them.",
            solution="Business Mail Pro business-domain email")

    # ── 6. 跨部门单据流转（ARS: digital_workflow）──
    if _documents_rekeyed(data):
        add("digital_workflow", "Month-end checking means typing every document in a second time",
            "Sales, warehouse and finance documents do not flow end to end, so month end still needs a hand check on every figure",
            "The same figures are copied over and over, and one error means retracing the whole month; the checking eats the busiest order days", "Operation",
            cradle_gap="Right now nobody can answer which step a document is stuck at, or who is sitting on it unsigned.",
            solution="Linux VPS + n8n automated document flow + team cloud drive")

    # ── 7. 营销可衡量性（marketing）──
    if _attribution_missing(data):
        add("marketing", "How much ad money went out, and what it brought back, cannot be said",
            "No conversion tracking or ad attribution; new business leans heavily on contacts and waiting for orders",
            "There is no basis for where the next budget should go; it is guesswork", "Marketing",
            severity="MEDIUM",
            cradle_gap="Without tracking, there is no way to tell which ad spend is earning and which is burning.",
            solution="standalone website + Meta Pixel / GA4 conversion tracking")

    # ── 8. 数据结构化（ARS: data_availability）──
    if _data_layer_missing(data):
        add("data_availability", "Product and customer data still sit in spreadsheets and personal notes",
            "Product lists, customers and deal history have not been built up as structured data",
            "AI and automation tools have no data they can read; hooked up as things stand, they would only answer the wrong question", "Technology",
            severity="MEDIUM",
            cradle_gap="Settle the fields first; only then does each later step avoid being redone.",
            solution="Build the stock-sales-purchase / CRM structured data layer first, then attach the AI reply")

    # ── 9. 作业规范（ARS: process_maturity）──
    if _sop_missing(data):
        add("process_maturity", "No written rules for pricing and common customer questions",
            "Answers to frequent customer questions and pricing rules live in the experience of long-time staff",
            "The same customer can get two different prices on two days; a new hire needs months to get up to speed", "Operation",
            severity="LOW",
            cradle_gap="The rules exist only in people's heads; when they are away, nobody can follow them, and AI cannot learn them either.",
            solution="Quote and Q&A SOP write-up + company knowledge base")

    # ── 10. 落地阻力（ARS: employee_skills）──
    if str(data.get("employee_skill_level", "")).lower() == "low":
        add("employee_skills", "Front-line staff are not yet on board with new tools",
            "Key staff are used to doing things by hand and clearly resist a new system",
            "Tools get bought and nobody uses them; the fees are paid and the old routine continues", "People",
            severity="MEDIUM",
            cradle_gap="Run it through on one or two roles first and let people see how much time it saves, then roll it out company-wide.",
            solution="Pilot in batches + visual SOP training")

    # ── 用问诊期已锁定的严重度与方案覆盖规则层文案（按维度精确去重）──
    consumed = set()
    for f in findings:
        dim = f["dimension"]
        matched = None
        for wp in (wiki_pains or []):
            if not isinstance(wp, dict) or id(wp) in consumed:
                continue
            if (wp.get("dimension") or "") == dim:
                matched = wp
                break
            # 老库里没有 dimension 列的行，只能按标题特征词归属；带维度的行一律不猜
            if not wp.get("dimension") and _title_marks_dimension(wp.get("title", ""), dim):
                matched = wp
                break
        if matched is not None:
            f["severity"] = matched.get("severity") or f["severity"]
            f["cradle_gap"] = matched.get("cradle_gap") or f["cradle_gap"]
            f["solution"] = matched.get("solution") or f["solution"]
            f["source"] = "wiki_evidence"
            consumed.add(id(matched))

    # wiki 里已锁证、且规则层未覆盖该事实的痛点才作为独立条目保留（同一维度不重复计损）
    unmet_now = _unmet_dimensions(data)
    covered_dims = {f["dimension"] for f in findings if f.get("dimension")}
    for wp in (wiki_pains or []):
        if not isinstance(wp, dict) or id(wp) in consumed:
            continue
        if not wp.get("title"):
            continue
        wp_dim = (wp.get("dimension") or "").strip()
        if wp_dim and wp_dim in covered_dims:
            continue
        # 事实冲突守卫：该维度经核验为达标时，模型报来的痛点与证据矛盾，剔除并留痕
        if wp_dim and wp_dim not in unmet_now:
            if conflict_sink is not None:
                conflict_sink.append({
                    "title": wp.get("title", ""),
                    "dimension": wp_dim,
                    "loss_myr": 0.0,
                    "reason": "Conflicts with a verified fact (this dimension checked out fine this run); left out of the report",
                })
            continue
        findings.append({
            "id": "",
            "title": wp.get("title", ""),
            "evidence": wp.get("root_cause") or "Decided and evidence-locked during the interview stage by the Cradilot engine",
            "quote": "",
            "impact": "The situation confirmed in the interview does not line up with your other verified facts; it is listed as a to-do on the strength of the fact itself",
            "category": "Operation",
            "dimension": wp_dim,
            "loss_myr": None,
            "severity": wp.get("severity", "HIGH"),
            "cradle_gap": wp.get("cradle_gap", ""),
            "solution": wp.get("solution", ""),
            "source": "wiki_evidence",
        })
        if wp_dim:
            covered_dims.add(wp_dim)

    # DMS 低分维度交叉印证（仅打标，不新增风险）
    dms_result = dms_result or {}
    low_dims = {
        k for k, v in (dms_result.get("dimensions") or {}).items()
        if isinstance(v, dict) and float(v.get("score", 100) or 0) < 40
    }
    for f in findings:
        if f.get("dimension") in low_dims:
            f["dms_confirmed_low"] = True

    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda x: (-float(x.get("loss_myr") or 0.0),
                                 severity_rank.get(x.get("severity"), 4)))
    top5 = findings[:5]
    for i, f in enumerate(top5, start=1):
        f["id"] = f"PP-{i:02d}"
    return top5

def _unmet_dimensions(data: Dict[str, Any]) -> Dict[str, str]:
    """
    单一事实判定来源：返回 {维度: 已核验事实描述}，供路线图选择任务使用，
    与 generate_pain_points 的判定条件保持一致（痛点文案各自更细，故不共用文案）。
    """
    data = data or {}
    unmet: Dict[str, str] = {}

    dr = str(data.get("dr_backup_status", "")).lower()
    if dr in ("no_backup", "pendrive"):
        unmet["cloud"] = "core accounts have no automatic off-site recovery"
    crm_state = _crm_state(data)
    if crm_state == "phone":
        unmet["crm"] = "customer leads are scattered across personal devices"
    elif crm_state == "ledger":
        unmet["crm"] = "customer list sits in a spreadsheet with no follow-up pipeline"
    # AI 判据：客户明确选过档位时以该档位为准，"夜间是否漏单"只是没选时的代理
    if _no_after_hours_cover(data):
        unmet["ai"] = "no response outside working hours"
    web = str(data.get("web_engine_status", "")).lower()
    if web in ("no_site", "dormant"):
        unmet["web"] = "no usable official website"
    if data.get("uses_personal_email", False):
        unmet["cyber"] = "business mail goes through a free personal mailbox"
    if _documents_rekeyed(data):
        unmet["digital_workflow"] = "documents and month-end checking rely on manual re-entry"
    if _attribution_missing(data):
        unmet["marketing"] = "no measurable attribution on the lead channel"
    if _data_layer_missing(data):
        unmet["data_availability"] = "business data is not built up in structured form"
    if _sop_missing(data):
        unmet["process_maturity"] = "no written quote and response rules"
    if str(data.get("employee_skill_level", "")).lower() == "low":
        unmet["employee_skills"] = "front-line staff are not yet ready to work with AI"
    return unmet


_DIM_LABELS = {
    "cloud": "backup and disaster recovery", "crm": "where customer records are kept",
    "ai": "after-hours enquiry handling",
    "web": "website status", "cyber": "business email", "marketing": "ads and result tracking",
    "digital_workflow": "document flow and month-end checking", "data_availability": "how structured the data is",
    "process_maturity": "written quote and response rules", "employee_skills": "staff readiness for new tools",
}

# 每个维度由哪些采集字段说话。字段全空 = 这一项本次没问过也没测过。
_DIM_FIELDS = {
    "cloud": ("dr_backup_status", "cloud_storage_status", "backup_strategy"),
    "crm": ("crm_system", "crm_status"),
    "ai": ("ai_tier", "ai_automation_status", "has_ai_agent", "after_hours_leak"),
    "web": ("web_engine_status", "website_status"),
    "cyber": ("uses_personal_email", "email_type"),
    "marketing": ("marketing_tracker",),
    "digital_workflow": ("order_reconcile_flow",),
    "data_availability": ("data_availability_status", "current_tools"),
    "process_maturity": ("has_sop",),
    "employee_skills": ("employee_skill_level",),
}


def _dim_gathered(data: Dict[str, Any], dim: str) -> bool:
    for key in _DIM_FIELDS.get(dim, ()):
        value = data.get(key)
        if value is None or value == "" or value == []:
            continue
        return True
    return False


# 任务库：每条任务绑定它解决的维度与真实 本公司产品（价格一律从目录查，不写在这里）。
# 任务是否进入路线图，完全由已核验事实决定，不再无条件全量输出。
# 措辞给客户看：只说做什么、做完能核对到什么，不用 Form A2 / MACC / 止血 / 硬锁这类内部话术。
_PHASE_TASKS: List[Dict[str, Any]] = [
    {"task_id": "T1", "phase": 1, "dim": "cyber",
     "skus": ["DEMO-MAIL-PRO-10U"],
     "title": "Switch to email on your own company domain",
     "desc": "Set up mailboxes on your own domain and pass the three checks - SPF, DKIM and DMARC - so quotes never leave from a personal Gmail again.",
     "evidence": "Screenshots of the MX toolbox showing all three checks green; a test record of mail from your address landing in the inbox (not spam) on Gmail and Outlook"},
    {"task_id": "T2", "phase": 1, "dim": "web",
     "skus": ["DEMO-DOM-COM", "DEMO-WP17-BUSINESS"],
     # 简报第 5 页把 Magento 与 Shopify 和 本公司的产品并列举例，但 本公司不卖它们：
     # 走既有的 third_party 机制，让客户面（界面与 PDF）都读到"我们不卖、这里没有价钱"。
     "third_party": ("Magento and Shopify are store platforms we do not sell or host, so nothing is priced "
                     "for them here and nothing of theirs enters your total; if you already run one of them, what "
                     "we can still do together is the domain, the email and the hosting underneath it."),
     "title": "Get your domain and website up",
     "desc": "Register your company domain and launch a website that reads clearly on a phone, has HTTPS, and can take enquiries.",
     "evidence": "Domain Whois showing the domain belongs to your company; homepage screenshots on phone and desktop; a test enquiry visible in the back office"},
    {"task_id": "T3", "phase": 1, "dim": "cloud",
     "skus": ["DEMO-ACRONIS-WKS"],
     "quantum": "devices",
     "title": "Automatic off-site backup for the finance computer",
     "desc": "Put daily automatic encrypted off-site backup on the key staff's computers, and run one real restore drill.",
     "evidence": "One restore-drill record on a real machine: on a different computer, how long it takes to bring the accounts back to working order from the backup"},
    {"task_id": "T4", "phase": 2, "dim": "crm",
     "skus": [],
     "third_party": "A third-party CRM such as Freshsales / HubSpot; we do not sell its own equivalent",
     "title": "Bring customer records back under the company",
     "desc": "Gather the leads scattered across staff's personal phones into one board, with a one-click handover when someone leaves.",
     "evidence": "Migration list checked line by line; one live resignation handover drill where the new person sees every follow-up without asking the old salesperson"},
    {"task_id": "T5", "phase": 2, "dim": "digital_workflow",
     "skus": ["DEMO-VPS-C1"],
     "title": "Documents no longer keyed in twice",
     "desc": "Run an automated flow on one cloud server that links sales, warehouse and finance documents, so month end needs no manual re-typing.",
     "evidence": "A record comparing how long month-end checking takes, timed once before the change and once after"},
    {"task_id": "T6", "phase": 2, "dim": "data_availability",
     "skus": [],
     "title": "Sort products and customers into one lookup-able table",
     "desc": "First tidy products, customers and deal history into structured data, so later reports and AI have something they can actually read.",
     "evidence": "A sample of the data plus field notes, callable directly from a spreadsheet or an interface"},
    {"task_id": "T7", "phase": 2, "dim": "process_maturity",
     "skus": [],
     "title": "Write the pricing rules and common answers down",
     "desc": "Which discounts are allowed and how to answer frequent questions, set out as a first written version, so staff stop asking the boss every time.",
     "evidence": "First versions of the rules and the FAQ document, with version number and effective date stated"},
    {"task_id": "T8", "phase": 3, "dim": "ai",
     "skus": ["DEMO-AI-AGENT"],
     "title": "Evening enquiries get an answer",
     "desc": "WhatsApp price asks from 18:00 to 23:00 are picked up by the AI first, replying within sixty seconds and passing serious buyers to the salesperson on duty.",
     "evidence": "A test with 100 of your customers' real questions, recording how many were answered correctly and the average time to the first reply"},
    {"task_id": "T9", "phase": 3, "dim": "marketing",
     "skus": [],
     "title": "Know which ad brought which order",
     "desc": "Put a board on each channel so you can say, for this month, which ad brought how many enquiries and how many orders.",
     "evidence": "One funnel board that shows enquiries and orders per channel"},
    {"task_id": "T10", "phase": 3, "dim": "employee_skills",
     "skus": [],
     "title": "Pilot one role first",
     "desc": "Let one role try the tool first; only once they clearly master it, decide on rolling it out to the whole team, so nothing is bought that nobody uses.",
     "evidence": "The pilot role's proficiency record; if it does not meet the bar, pause the company-wide purchase"},
]

_PHASE_META = {
    # 简报第 3-5 页给三个阶段各自命了名，并写出对应的回报周期（Quick Wins ROI 2-4 weeks /
    # Productivity 3-6 months / Growth 6-12 months）。旧标题是自造的一套中文直译，
    # 第 1 阶段还写着 Months 1 - 3，与客户手上的简报原文对不上。
    # 破折号后面保留描述性从句，界面与 PDF 直接印整句；分栏短标签由渲染方按破折号切。
    #
    # 简报在两处给了两套时间口径：第 3 页的 ROI 周期（Quick Wins 是 "2-4 weeks"），
    # 与 Bonus 2 的实施时间线（"Month 1-3 → Month 3-6 → Month 6-12"）。第 1 阶段两者
    # 就是对不上的，所以各存一份：timeline 是回报窗口，months 是干到哪个月。
    1: ("Phase 1 · Quick Wins — first secure the storefront and the data", "2-4 weeks",
        "Month 1 - 3"),
    2: ("Phase 2 · Productivity — hand the repetitive work to the systems", "Months 3 - 6",
        "Month 3 - 6"),
    3: ("Phase 3 · Growth — let new customers and repeat orders grow", "Months 6 - 12",
        "Month 6 - 12"),
}


# ── 多方案比较层（简报第 4-5 页 "Here's the exciting part"）────────────────────
# 简报要的不是"推荐一个产品"，而是同一个问题把真实备选摆在一起，解释为什么选它、
# 为什么这次不买另一个。旧版 _PHASE_TASKS 每个任务只钉死一个 SKU，报告里因此
# 只有推荐、没有比较。这一层补的就是这一段。三条硬规矩：
#   1) 判据只用 generate_action_roadmap 已经拿得到的事实（席位数、行业、问诊确认的
#      维度现状）与目录公开价，不调模型、不替客户假设习惯；规则要的事实没采到，
#      就在句子里写明"没采到"，不替客户补前提。
#   2) 只有选中的那条进 budget_lines 与采购车；备选一律 in_cart=False，
#      它写的是"这份要多少钱"，不是"要收你多少钱"。
#   3) 目录查不到年价的（DEMO-IWB-STARTER、按台计价的备份）用 price_state 标出来，
#      绝不换算成看起来像数的东西；本公司不卖的平台连 SKU 都不给。
_NEEDS_QUOTE = "Needs a quote from our catalogue"


def _money(amount: float) -> str:
    return f"RM {amount:,.2f}"


def _gap(chosen_amount: Optional[float], other_amount: Optional[float]) -> str:
    """两笔年价的差额说成一句人话，正负都如实——比较层不许出现"更便宜"却算不出来。"""
    if not chosen_amount or not other_amount:
        return "priced differently"
    diff = round(abs(float(chosen_amount) - float(other_amount)), 2)
    if float(chosen_amount) < float(other_amount):
        return f"{_money(diff)} a year less than"
    if float(chosen_amount) > float(other_amount):
        return f"{_money(diff)} a year more than"
    return "exactly the same as"


def _price_basis(raw: Dict[str, Any], seats: int) -> str:
    """把这笔年价是怎么从公开单价乘出来的写出来，客户自己拿计算器能核。"""
    import math

    per_user = raw.get("annual_myr_per_user")
    if per_user:
        return f"{_money(float(per_user))} per user x {seats} users"
    block = raw.get("seats_block")
    if block and raw.get("annual_myr") is not None:
        blocks = math.ceil(max(1, int(seats)) / int(block))
        return (f"{_money(float(raw['annual_myr']))} per {block} users x {blocks} "
                f"{'block' if blocks == 1 else 'blocks'}")
    if raw.get("annual_myr") is not None:
        return "our published annual price"
    if raw.get("one_off_myr") or raw.get("monthly_myr"):
        return "listed as a monthly fee, with no yearly price published"
    return "no published price"


def _option_row(sku: str, seats: int) -> Dict[str, Any]:
    """一条备选一行。取不到年价的一律标注清楚，不换算、不四舍五入成一个假数。"""
    from core.product_catalog import catalog

    product = catalog.get(sku)
    if product is None:
        return {}
    raw = product.raw or {}
    row: Dict[str, Any] = {"sku": sku, "product_name": product.name,
                           "verify_status": product.verify_status,
                           "purchasable": True, "annual_myr": None}
    per_device = raw.get("annual_myr_per_device")
    if per_device:
        # 单价公开、范围内几台却没问过：总价仍算不出来，只能报"每台每年"这一档
        row["price_state"] = "unit_needs_count"
        row["unit_myr"] = float(per_device)
        row["price_label"] = (f"{_money(float(per_device))} per device a year; "
                              "the total needs the number of machines")
        row["price_basis"] = "we price this per device, not per plan"
        return row
    amount = catalog.annual_for(sku, seats=seats)
    if amount is None:
        row["price_state"] = "no_public_price"
        row["price_label"] = _NEEDS_QUOTE
        row["price_basis"] = _price_basis(raw, seats)
        return row
    row["price_state"] = "priced"
    row["annual_myr"] = amount
    row["price_label"] = f"{_money(amount)} a year"
    row["price_basis"] = _price_basis(raw, seats)
    return row


def _not_sold_row(name: str, why_not: str,
                  label: str = "we do not sell this") -> Dict[str, Any]:
    """本公司不卖的平台：连价签都不给，只把"我们不卖这件事"说清楚。"""
    return {"sku": None, "product_name": name, "verify_status": "not_sold",
            "purchasable": False, "in_cart": False, "annual_myr": None,
            "price_state": "not_sold", "price_label": label,
            "price_basis": "", "why_not": why_not}


def _nothing_to_buy_row(name: str, why_not: str) -> Dict[str, Any]:
    """客户本可以自己动手、一分钱不用给我们的那一档。

    比较层不能只摆"买哪个"，还要摆"其实可以不买"——那是简报"解释为什么"里
    最有说服力的一条，也是本公司自己不卖的那一款。
    """
    return {"sku": None, "product_name": name, "verify_status": "no_purchase",
            "purchasable": False, "in_cart": False, "annual_myr": None,
            "price_state": "no_purchase", "price_label": "Nothing to buy from us",
            "price_basis": "", "why_not": why_not}


# 只有这几条词才算"贵司已经在 Microsoft 那套里办公"。excel / word 不在其中：
# 台账用 Excel 在本产品里是"客户资料躺在表格里"那条弱项，不是整套办公件在用的证据。
_MS_TOOL_TOKENS = ("microsoft", "office 365", "office365", "o365", "outlook",
                   "teams", "onedrive", "sharepoint", "365")


def _microsoft_tooling(data: Dict[str, Any]) -> tuple:
    """(是否记录过, 一句话事实描述)。没记录不等于没有——按老规矩中性陈述，不替客户补前提。

    只认客户自己答过的工具清单：email_type 是派生枚举（business_domain / free_gmail），
    永远不会写着某个厂商的名字，拿它当证据等于替客户假设习惯。
    """
    tools = [str(t).strip() for t in (data.get("current_tools") or []) if str(t).strip()]
    hits = sorted({t for t in tools if any(tok in t.lower() for tok in _MS_TOOL_TOKENS)})
    if hits:
        return True, f"your own answer lists {' and '.join(hits[:3])} among the tools you use today"
    return False, "this run recorded no Microsoft tool among the tools you use today"


# 简报第 5 页那句 "depending on business"：行业决定网站要不要收款能力。
# 只认把货直接卖给终端消费者、要在线上收钱的行当；批发与制造按询盘报价，
# 一个能收询盘的官网就够，不能拿 RM 3,099 的商城包去充数。
_ECOM_INDUSTRY_TOKENS = ("retail", "multi-store", "f&b", "food", "cloud kitchen",
                         "ecommerce", "e-commerce", "grocer", "restaurant", "cafe")


def _sells_to_consumers(industry: Any) -> bool:
    low = str(industry or "").lower()
    return any(tok in low for tok in _ECOM_INDUSTRY_TOKENS)


def _people(seats: int) -> str:
    return "person" if seats == 1 else "people"


def _decide_email(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """邮箱这道题的三种真实解法：选哪一条由席位数与一条办公件事实决定，不由模型决定。"""
    block = (rows.get("DEMO-MAIL-PRO-10U") or {}).get("annual_myr")
    gws = (rows.get("DEMO-GWS-STARTER") or {}).get("annual_myr")
    ms = (rows.get("DEMO-M365-BASIC") or {}).get("annual_myr")
    amounts = {"DEMO-MAIL-PRO-10U": block, "DEMO-GWS-STARTER": gws, "DEMO-M365-BASIC": ms}
    ms_hit, ms_fact = _microsoft_tooling(data)

    # 判据一（事实优先于价钱）：已经在用 Microsoft 办公件时选 M365——三个里它每席最贵，
    # 但决定性事实不是价钱，而是员工的邮件、文件与聊天本来就开在那个面板里。
    # 这条事实本次没采到就不选它，并在备选句子里写明"没采到"，不猜客户用不用。
    if ms_hit:
        chosen = "DEMO-M365-BASIC"
        basis = f"the tooling fact on record ({ms_fact}) and the catalogue prices"
    # 判据二（其余情况一律由目录总价决定，不把任何席位区间写死成结论）：Mail PRO 按 10 用户
    # 一档卖、不足一档按一档计（见 core/product_catalog.py 的 seats_block 与
    # tests/test_site_audit.py::test_mail_pro_is_priced_in_ten_user_blocks 锁住的
    # 21 席 = RM 2,494.80），所以 1-5 人是整档更贵、6-10 人才是整档更省。
    # 简报例子假设"10 人以上每席计价更省"，目录里并不完全成立——谁便宜交给目录算：
    # 小团队就推荐总价更低的那一款，不给一个人卖十只邮箱。
    else:
        priced = [(sku, amt) for sku, amt in amounts.items() if amt]
        chosen = min(priced, key=lambda item: item[1])[0] if priced else "DEMO-MAIL-PRO-10U"
        basis = (f"the team size on record ({seats} {_people(seats)}) compared on "
                 "the catalogue's own annual totals")

    reasons: Dict[str, str] = {}
    picked_amount = amounts.get(chosen)
    if chosen == "DEMO-MAIL-PRO-10U":
        # 一档 10 用户：一档之内与跨档是两句话，不能把 3 档也说成"一档装得下全公司"
        import math

        blocks = max(1, math.ceil(int(seats) / 10))
        mailboxes = blocks * 10
        total = block or 0.0
        if blocks == 1:
            reasons[chosen] = (
                f"Chosen: one 10-user block covers all {seats} {_people(seats)} at {_money(total)} a year - "
                f"{_money(round(total / 10, 2))} a mailbox, {_gap(total, gws)} Google and {_gap(total, ms)} "
                "Microsoft would charge for the same people - with SPF, DKIM, DMARC and the mail archive "
                "included, so customer mail cannot leave with a departing staff member.")
        else:
            reasons[chosen] = (
                f"Chosen: Mail PRO is sold in blocks of 10 users, so your {seats} {_people(seats)} cost "
                f"{_money(total)} a year across {blocks} blocks covering {mailboxes} mailboxes "
                f"({_money(round(total / mailboxes, 2))} each), {_gap(total, gws)} Google and {_gap(total, ms)} "
                "Microsoft for the same people, with the SPF, DKIM and DMARC setup and the mail archive included.")
    elif chosen == "DEMO-GWS-STARTER":
        reasons[chosen] = (
            f"Chosen: for {seats} {_people(seats)} the per-user bill of {_money(gws or 0.0)} a year lands "
            f"{_gap(gws, block)} the Mail PRO blocks the same team would need, and shared documents and Meet "
            "arrive in the same price.")
    else:
        reasons[chosen] = (
            f"Chosen: {ms_fact}, which decides it over price - {_money(ms or 0.0)} a year for {seats} "
            f"{_people(seats)} is {_gap(ms, block)} the email block, and mail, files and chat stay in the panel "
            "your staff already open.")

    if chosen != "DEMO-MAIL-PRO-10U":
        # 不藏本公司自有产品会反败为胜的那个点：从目录价现算，不写死"6 人"
        import math

        per_seat = round((gws or 0.0) / seats, 2) if seats else 0.0
        turns = (f" One block covers 10 mailboxes, so from "
                 f"{math.ceil(block / per_seat)} {_people(math.ceil(block / per_seat))} up it becomes the cheaper "
                 "bill, and that is when we would move you to it."
                 if block and per_seat and (block / per_seat) > seats else "")
        reasons["DEMO-MAIL-PRO-10U"] = (
            f"Not this time: {_money(block or 0.0)} a year, {_gap(block, picked_amount)} what we picked, sold in "
            f"blocks of 10 users, so {seats} {_people(seats)} would be paying for mailboxes they do not have."
            + turns)
    if chosen != "DEMO-GWS-STARTER":
        # 差额方向与对手是谁都得说清：与整档比是"便宜只在团队不扩大时成立"，
        # 与 Microsoft 比则是"它更便宜，但决定性事实指向的是另一家"。
        under_block = bool(gws and picked_amount and gws < picked_amount)
        if chosen == "DEMO-M365-BASIC":
            reasons["DEMO-GWS-STARTER"] = (
                f"Not this time: {_money(gws or 0.0)} a year for {seats} {_people(seats)} is "
                f"{_gap(gws, picked_amount)} what we picked, so it is the cheaper of the two per-user suites - but "
                f"the fact deciding this pick is the tooling your staff already use ({ms_fact}), and the mail "
                "archive that comes with the block is not on its list either.")
        elif under_block:
            reasons["DEMO-GWS-STARTER"] = (
                f"Not this time: {_money(gws or 0.0)} a year for {seats} {_people(seats)}, "
                f"{_gap(gws, picked_amount)} what we picked - cheaper only while the team stays this size, billed "
                "per person from here on, and with no mail archive on its list.")
        else:
            reasons["DEMO-GWS-STARTER"] = (
                f"Not this time: {_money(gws or 0.0)} a year for {seats} {_people(seats)}, "
                f"{_gap(gws, picked_amount)} what we picked, every later hire adds RM 155.88, and the mail archive "
                "that comes with the block is not on its list.")
    if chosen != "DEMO-M365-BASIC":
        priced_three = [amt for amt in amounts.values() if amt]
        rank = ("the dearest of the three" if ms and ms >= max(priced_three)
                else "the cheapest of the three" if ms and ms <= min(priced_three)
                else "priced between the other two")
        reasons["DEMO-M365-BASIC"] = (
            f"Not this time: {_money(ms or 0.0)} a year for {seats} {_people(seats)} is {rank} "
            f"({_gap(ms, picked_amount)} what we picked), and it wins only where staff already work inside "
            f"Outlook and Teams - {ms_fact}.")
    return chosen, reasons, basis


def _decide_website(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """官网这道题：同一个"要有个能收询盘的门面"，四档真实解法按行业与规模分。"""
    beginner = (rows.get("DEMO-WP17-BEGINNER") or {}).get("annual_myr")
    business = (rows.get("DEMO-WP17-BUSINESS") or {}).get("annual_myr")
    ecom = (rows.get("DEMO-ECOM-STANDARD") or {}).get("annual_myr")
    web_fact = str(data.get("web_engine_status") or data.get("website_status") or "").strip().lower()

    # 判据一（行业）：把货直接卖给终端消费者、要在线上收钱的行当选 Ecommerce 12 Standard
    # （RM 3,099 一年，含建好的店铺与收款、送货网关）——介绍页只能挂个电话号码，收不了钱。
    if _sells_to_consumers(data.get("industry")):
        chosen = "DEMO-ECOM-STANDARD"
        basis = f"the industry you filed ({data.get('industry')}: selling to end customers)"
    # 判据二（规模 + 现状）：5 人以下、且事实是"根本没有网站"时选 WP 17 AI Beginner（RM 263.88）：
    # SSL、自动备份、手机能读都在；多出的 RM 264 买的是流量与多站容量，本次没有一条事实指向用得上。
    # 已有站要重建（dormant）不走这条，容量要留余地。
    elif seats <= 5 and web_fact == "no_site":
        chosen = "DEMO-WP17-BEGINNER"
        basis = (f"the team size on record ({seats} {_people(seats)}) and the confirmed fact that there is "
                 "no site to move")
    # 判据三（默认）：其余情况维持 WP 17 AI Business（RM 527.88）——全站 SSL、每日备份、
    # 手机版式、询盘表单加 LiteSpeed NVMe，正好对上"根本没有官网/官网多年没人维护"这条事实。
    else:
        chosen = "DEMO-WP17-BUSINESS"
        basis = "the confirmed website fact and the catalogue prices"

    reasons: Dict[str, str] = {}
    if chosen == "DEMO-ECOM-STANDARD":
        reasons[chosen] = (
            f"Chosen: {str(data.get('industry') or 'your sector')} sells to end customers, so the site has to take "
            f"the order and the payment - {_money(ecom or 0.0)} a year with the store built and the payment and "
            f"delivery gateways wired up, {_gap(ecom, business)} the enquiry-only tier.")
    elif chosen == "DEMO-WP17-BEGINNER":
        reasons[chosen] = (
            f"Chosen: {_money(beginner or 0.0)} a year gives {seats} {_people(seats)} with no site today a page "
            f"with SSL across it and automatic backups, {_gap(beginner, business)} the Business tier.")
    else:
        reasons[chosen] = (
            f"Chosen: {_money(business or 0.0)} a year closes what the confirmed fact is short of in one product - "
            "site-wide SSL, a layout that reads on a phone, daily automatic backups and an enquiry form reaching "
            "your inbox, on LiteSpeed NVMe hosting.")
    if chosen != "DEMO-WP17-BEGINNER":
        reasons["DEMO-WP17-BEGINNER"] = (
            f"Not this time: {_money(beginner or 0.0)} a year is a starter page with no store in it, and yours has "
            "to take the payment as well as the enquiry."
            if chosen == "DEMO-ECOM-STANDARD" else
            f"Not this time: {_money(beginner or 0.0)} a year is a starter page - less room, fewer sites, and not "
            "the rebuild and enquiry handling the confirmed fact calls for.")
    if chosen != "DEMO-WP17-BUSINESS":
        reasons["DEMO-WP17-BUSINESS"] = (
            f"Not this time: {_money(business or 0.0)} a year takes enquiries but not payments, which is the part "
            f"of your business that cannot be skipped - it sits {_gap(business, ecom)} the store package."
            if chosen == "DEMO-ECOM-STANDARD" else
            f"Not this time: {_money(business or 0.0)} a year is {_gap(business, beginner)} the starter page for "
            f"{seats} {_people(seats)} with no site to move, so it would be paying for capacity nothing has asked "
            "for yet.")
    if chosen != "DEMO-ECOM-STANDARD":
        reasons["DEMO-ECOM-STANDARD"] = (
            f"Not this time: {_money(ecom or 0.0)} a year builds a store with payment and delivery gateways, and "
            "nothing confirmed this run points to taking payment on the site; it moves to the top of the list the "
            "day you decide to sell online.")
    reasons["DEMO-IWB-STARTER"] = (
        "It is sold as a monthly fee plus a one-off build charge with no yearly price published, so no amount is "
        "written beside the hosting figures, and it is the option when nobody in-house will keep the site running.")
    return chosen, reasons, basis


def _decide_backup(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """备份这道题：逐台买与一份服务器 licence 是两种形状，不是两个档次。"""
    unit = (rows.get("DEMO-ACRONIS-WKS") or {}).get("unit_myr")
    srv = (rows.get("DEMO-ACRONIS-SRV") or {}).get("annual_myr")
    # 判据一（现状事实）：诊断确认的是"账套在个别员工电脑上"（no_backup / pendrive），
    # 所以按台覆盖才对得上；范围内一共几台从没问过，总价因此留在报价里，不按人头猜。
    chosen = "DEMO-ACRONIS-WKS"
    basis = "the confirmed backup fact; the number of machines was not collected this run"
    reasons = {
        chosen: (
            f"Chosen: the confirmed fact is about files sitting on individual computers, so cover is bought per "
            f"machine at {_money(unit or 0.0)} a device a year. How many machines are in scope was never asked this "
            "run, so the total stays on the quote instead of being guessed at a figure you would be billed for.")
    }
    # 判据二（什么时候换形状）：服务器版 RM 4,595.88 一份 licence 一年，只有账套跑在贵司
    # 自己的服务器或 ERP 数据库上才用得上；逐台买超过约 15 台时它反而更省
    # （16 台 x RM 290.88 = RM 4,654.08）。这两条本次都没有事实支持，所以列进比较、不进合计。
    reasons["DEMO-ACRONIS-SRV"] = (
        f"Not this time: {_money(srv or 0.0)} a year covers a server of its own, and nothing recorded this run "
        "shows your accounts living on one. It becomes the cheaper shape past about 15 machines "
        "(16 devices at RM 290.88 each is RM 4,654.08), so once we know the machine count we re-check it before you buy.")
    return chosen, reasons, basis


def _decide_crm(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """T4：简报把 CRM 写在第 2 阶段，但 本公司不卖 CRM。

    比较层在这里第一次派上用场：把"我们卖不了"这件事本身摆成结论，而不是拿一个
    不相干的产品补位。选中那条不是采购项，所以整块不进合计。
    """
    state = _crm_state(data)
    where = ("leads sitting on staff phones" if state == "phone"
             else "one spreadsheet with nobody assigned to follow up" if state == "ledger"
             else "the way customer records are kept today")
    mail = (rows.get("DEMO-MAIL-PRO-10U") or {}).get("annual_myr")

    chosen = "own_crm"
    basis = "the confirmed fact about where customer records live; we sell no CRM of its own"
    reasons = {
        "own_crm": (
            "Recommended, even though we cannot sell it to you: a CRM is the only shape that keeps a pipeline - "
            f"who owns each lead, what was quoted, what is due next. What the confirmed facts show right now is {where}, "
            "and no hosting or email product replaces that. We will not price you something we do not carry; pick one "
            "on your own headcount, and what we do handle from here is the domain, the mail and the hosting under it."),
        "DEMO-MAIL-PRO-10U": (
            f"Not this time: this is already in your Phase 1 total at {_money(mail or 0.0)} a year for the email "
            "reason, and we are not going to bill it to you twice. It does hold the customer correspondence and its "
            "archive, so a departing staff member cannot take the mail thread with them - but a mailbox has no "
            "pipeline, no owner and no next-action on it."),
        "spreadsheet": (
            "Not this time: that is where you are now, and it is the confirmed reason this phase exists. A shared "
            "sheet costs nothing and works up to a point - it just cannot answer who is following up today, or prove "
            "a departed staff member handed the customer over."),
    }
    return chosen, reasons, basis


def _decide_workflow(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """T5：同一件"单据不再二次录入"，本公司有两种真实形状。"""
    vps = (rows.get("DEMO-VPS-C1") or {}).get("annual_myr")
    shared = (rows.get("DEMO-EBIZ17-AIPRO") or {}).get("annual_myr")
    web = str(data.get("web_engine_status") or data.get("website_status") or "").strip().lower()
    needs_site = web in ("no_site", "dormant")

    if needs_site:
        chosen = "DEMO-EBIZ17-AIPRO"
        basis = ("the confirmed website fact (there is no site standing, or the old one is dormant), so one bill "
                 "carries the site and the document flow")
    else:
        chosen = "DEMO-VPS-C1"
        basis = "the confirmed website fact (a site is already live to keep) and the catalogue prices"

    reasons: Dict[str, str] = {}
    if chosen == "DEMO-EBIZ17-AIPRO":
        reasons[chosen] = (
            f"Chosen: you also need somewhere for the website itself to live, and {_money(shared or 0.0)} a year "
            f"on the shared cloud plan is {_gap(shared, vps)} a bare VPS while carrying the site, the SSL and the "
            "daily backup with it - one bill, not two.")
        reasons["DEMO-VPS-C1"] = (
            f"Not this time: {_money(vps or 0.0)} a year is a server to run the flow on, but the website would then "
            "need somewhere else to live, and that second bill is what makes it dearer here, not the flow itself.")
    else:
        reasons[chosen] = (
            f"Chosen: the flow is a background job that runs on a schedule and holds credentials for your accounting "
            f"and store systems, so it wants a server of its own - {_money(vps or 0.0)} a year, "
            f"{_gap(vps, shared)} the shared cloud plan.")
        reasons["DEMO-EBIZ17-AIPRO"] = (
            f"Not this time: {_money(shared or 0.0)} a year is shared web hosting - the right shape for the site, "
            f"and you already have one, so paying for it again to run one automation job would be "
            f"{_gap(shared, vps)} more a year for capacity you would not visit.")
    return chosen, reasons, basis


def _decide_ai(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """T8：AI agent 只点名不报价——目录里没有公开年价，就不许在客户面前编一个。"""
    chosen = "DEMO-AI-AGENT"
    basis = ("the confirmed after-hours gap; we publish no annual price for the AI agent, "
             "so this line stays on the quote rather than becoming a figure")
    reasons = {
        chosen: (
            "Chosen: an unanswered evening enquiry is the one leak this audit can see but not price. The agent is "
            "scoped by how many questions a month it has to answer and which systems it has to read, so we would "
            "rather quote you once honestly than write a number here that turns out wrong."),
        "rota": (
            "Not this time: an evening rota on staff phones costs nothing and does answer the phone, but it is the "
            "same arrangement that produced the confirmed gap, and it stops working the moment one person is away. "
            "Keep it as the fallback while the quote is with you."),
    }
    return chosen, reasons, basis


def _decide_marketing(seats: int, data: Dict[str, Any], rows: Dict[str, Dict[str, Any]]) -> tuple:
    """T9：全目录最贵的一条在这里被自己拦下来——判据是客户自报的广告预算。"""
    from core.product_catalog import catalog

    spend = str(data.get("marketing_spend") or "").strip().lower()
    seo = rows.get("DEMO-SEO-STANDARD") or {}
    yearly = seo.get("annual_myr")
    monthly = ((catalog.get("DEMO-SEO-STANDARD").raw or {}).get("monthly_myr")
               if catalog.get("DEMO-SEO-STANDARD") else None)
    price_said = (f"{_money(monthly)} a month ({_money(yearly or 0.0)} a year)" if monthly
                  else f"{_money(yearly or 0.0)} a year")

    if spend == "over_5k":
        chosen = "DEMO-SEO-STANDARD"
        basis = "the ad budget you stated (more than RM 5,000 a month), which already exceeds the retainer"
        reasons = {
            chosen: (
                f"Chosen: you already spend more than RM 5,000 a month on ads, so the retainer at {price_said} is "
                "smaller than the budget it is meant to stop leaking. "
                "The confirmed gap is not the spend, it is that nobody can say which ad brought which order."),
            "self_serve": (
                "Not this time: setting up GA4 and the Meta pixel yourselves is free of anything from us, and it is "
                "the right answer at a smaller budget - at the spend you stated, the hours it takes are worth more "
                "than the retainer."),
        }
    else:
        chosen = "self_serve"
        band = ("under RM 1,000 a month" if spend == "under_1k" else
                "RM 1,000-5,000 a month" if spend == "1k_5k" else
                "nothing on paid ads" if spend == "none" else
                "no ad budget was collected this run")
        basis = f"the ad budget on record ({band}) compared against the retainer's own monthly price"
        reasons = {
            chosen: (
                "Recommended, and it costs you nothing from us: install GA4 and the Meta pixel on the site you "
                "already have and read the attribution yourselves. That closes the confirmed gap - nobody can say "
                "which ad brought which order - before any retainer is discussed."),
            "DEMO-SEO-STANDARD": (
                f"Not this time: this is the largest single line in our whole catalogue at {price_said}, and the ad "
                f"budget on record is {band}. Buying the retainer first would cost more than everything it is "
                "supposed to measure. It moves onto the list once the paid spend is consistently above the retainer."),
        }
    return chosen, reasons, basis


# 比较层里那些"不是目录产品"的行：本公司卖不了的与根本不用买的。
# 必须是每次现造的函数——写死在表里就是所有会话共用同一个 dict，一改全串。
def _crm_extras(seats: int, data: Dict[str, Any],
                rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        "own_crm": _not_sold_row("A dedicated CRM (HubSpot, Freshsales, Zoho)", ""),
        "spreadsheet": _nothing_to_buy_row("Stay on the shared spreadsheet", ""),
    }


def _ai_extras(seats: int, data: Dict[str, Any],
               rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        "rota": _nothing_to_buy_row("Keep the evening rota on staff phones", ""),
    }


def _marketing_extras(seats: int, data: Dict[str, Any],
                      rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        "self_serve": _nothing_to_buy_row("Install GA4 and the Meta pixel yourselves", ""),
    }


# 任务号 → 比较规格。replaces 是任务里被比较的那条 SKU：选中的那条顶替它进采购合计，
# 任务里其余条目（比如域名）与算价机制一概不动。
_OPTION_FAMILIES: Dict[str, Dict[str, Any]] = {
    "T1": {
        "question": "Where should your company email live?",
        "replaces": "DEMO-MAIL-PRO-10U",
        "candidates": ["DEMO-MAIL-PRO-10U", "DEMO-GWS-STARTER", "DEMO-M365-BASIC"],
        "decide": _decide_email,
        "not_sold": [],
    },
    "T2": {
        "question": "What should your website be built on?",
        "replaces": "DEMO-WP17-BUSINESS",
        "candidates": ["DEMO-WP17-BEGINNER", "DEMO-WP17-BUSINESS", "DEMO-ECOM-STANDARD",
                       "DEMO-IWB-STARTER"],
        "decide": _decide_website,
        # 简报第 5 页点名的两个平台 本公司不卖：只以"不卖"的身份出现在比较里，
        # 永远没有 SKU、没有价钱、进不了采购车（任务上的 third_party 句是同一条口径）。
        "not_sold": [
            ("Magento", "We neither sell nor host Magento, so it carries no price here and never enters "
                        "your total; if you run it, what we still cover is the domain, the email and the hosting."),
            ("Shopify", "We neither sell nor host Shopify, so it carries no price here and never enters "
                        "your total - whatever you pay Shopify sits outside everything we quote you."),
        ],
    },
    "T3": {
        "question": "How should the company accounts be covered against a failure?",
        "replaces": "DEMO-ACRONIS-WKS",
        "candidates": ["DEMO-ACRONIS-WKS", "DEMO-ACRONIS-SRV"],
        "decide": _decide_backup,
        "not_sold": [],
    },
    # ── 简报第 4 页写进第 2、3 阶段的那几题。本公司不卖 CRM，AI agent 没有公开
    # 年价，SEO 包是全目录最贵的一条——这三件事都必须摆在比较里说给客户听，
    # 而不是只在最后一行悄悄少印一个产品。 ──────────────────────────────────────
    "T4": {
        "question": "What should actually hold your customer records?",
        "candidates": ["DEMO-MAIL-PRO-10U"],
        "extras": _crm_extras,
        "decide": _decide_crm,
        "not_sold": [],
    },
    "T5": {
        "question": "Where should the document flow run?",
        "replaces": "DEMO-VPS-C1",
        "candidates": ["DEMO-VPS-C1", "DEMO-EBIZ17-AIPRO"],
        "decide": _decide_workflow,
        "not_sold": [],
    },
    "T8": {
        "question": "Who answers an enquiry at 9pm?",
        "replaces": "DEMO-AI-AGENT",
        "candidates": ["DEMO-AI-AGENT"],
        "extras": _ai_extras,
        "decide": _decide_ai,
        "not_sold": [
            ("A third-party WhatsApp chatbot (WATI, AiSensy, ManyChat)",
             "We neither sell nor host these, so nothing of theirs enters your total; whatever you pay them "
             "sits outside everything we quote, and the number you give a customer still lives on their servers."),
        ],
    },
    "T9": {
        "question": "How do you find out which ad brought which order?",
        "candidates": ["DEMO-SEO-STANDARD"],
        "extras": _marketing_extras,
        "decide": _decide_marketing,
        "not_sold": [],
    },
}


def _build_option_block(task: Dict[str, Any], seats: int, data: Dict[str, Any],
                        problem: str) -> Optional[Dict[str, Any]]:
    """生成一个任务的多方案比较块；该任务没有可替代解法时返回 None。"""
    fam = _OPTION_FAMILIES.get(str(task.get("task_id") or ""))
    if not fam:
        return None
    rows = {sku: _option_row(sku, seats) for sku in fam["candidates"]}
    rows = {sku: row for sku, row in rows.items() if row}
    extras = (fam.get("extras") or (lambda *_: {}))(seats, data, rows)
    rows.update({key: row for key, row in extras.items() if row})
    order = list(fam["candidates"]) + list(extras)
    if not rows:
        return None
    chosen_sku, reasons, basis = fam["decide"](seats, data, rows)
    if chosen_sku not in rows:
        return None

    chosen = dict(rows[chosen_sku])
    chosen["why"] = reasons.get(chosen_sku) or ""
    # 选中的那条如果压根不是我们能卖的东西（第三方 CRM、或自己动手那一档），
    # 整块就不进合计——推荐一件客户买不到的事，不该变成他账单上的一行。
    purchasable = bool(chosen.get("purchasable", True))
    chosen["in_cart"] = purchasable
    alternatives = []
    for key in order:
        if key == chosen_sku or key not in rows:
            continue
        row = dict(rows[key])
        row["why_not"] = reasons.get(key) or ""
        row["in_cart"] = False
        alternatives.append(row)
    for name, note in fam.get("not_sold") or []:
        alternatives.append(_not_sold_row(name, note))

    return {
        "task_id": task.get("task_id", ""),
        "task_title": task.get("title", ""),
        "problem": problem or "",
        "question": fam["question"],
        "decision_basis": basis,
        "purchase": purchasable,
        "facts_used": {
            "seats": seats,
            "seats_from": (str(data.get("team_size") or "").strip()
                           or "no team size on record, so the engine's 10-seat default was used"),
            "industry": str(data.get("industry") or "").strip() or "not recorded this run",
            "microsoft_tooling": _microsoft_tooling(data)[1],
        },
        "chosen": chosen,
        "also_considered": alternatives,
    }


def _effective_skus(task: Dict[str, Any], block: Optional[Dict[str, Any]]) -> List[str]:
    """算价用的 SKU：被比较的那条换成选中的方案，任务里其余条目（域名等）原样保留。

    这是备选唯一的隔离点——备选与 本公司不卖的平台在这里没有入口，
    所以永远进不了 budget_lines、budget_myr、采购车与 ROI 分母。
    任务本身没有 SKU 时（营销那一题），只有"选中的且真能买到"的那条才补进去。
    """
    skus = list(task.get("skus") or [])
    if not block:
        return skus
    fam = _OPTION_FAMILIES.get(str(task.get("task_id") or "")) or {}
    replaces = fam.get("replaces")
    chosen = str((block.get("chosen") or {}).get("sku") or "")
    if not chosen:
        return skus
    if replaces:
        return [chosen if sku == replaces else sku for sku in skus]
    if block.get("purchase") and chosen not in skus:
        return skus + [chosen]
    return skus


def _task_costing(tasks: List[Dict[str, Any]], seats: int) -> Dict[str, Any]:
    """按目录给一组任务算价。数量算不出来的一律不算，宁可写"待报价"。"""
    from core.product_catalog import catalog

    total = 0.0
    lines: List[Dict[str, Any]] = []
    pending: List[str] = []
    pending_lines: List[Dict[str, Any]] = []

    for task in tasks:
        for sku in task.get("skus") or []:
            product = catalog.get(sku)
            if product is None:
                continue
            if task.get("quantum") == "devices":
                # 没问过有几台电脑在备份范围内，报总价就是编数
                unit = catalog.annual_for(sku, devices=1)
                note = f"{product.name}: RM {unit:,.2f} per device per year, billed on the actual number of devices"
                pending.append(note)
                pending_lines.append({"sku": sku, "product_name": product.name,
                                      "annual_myr": None, "reason": note,
                                      "verify_status": product.verify_status})
                continue
            amount = catalog.annual_for(sku, seats=seats)
            if amount is None:
                note = f"{product.name}: no public price, needs a quote based on actual usage"
                pending.append(note)
                pending_lines.append({"sku": sku, "product_name": product.name,
                                      "annual_myr": None, "reason": note,
                                      "verify_status": product.verify_status})
                continue
            total += amount
            lines.append({"sku": sku, "product_name": product.name, "annual_myr": amount,
                          "verify_status": product.verify_status, "why": product.solves})

    return {"total": round(total, 2), "lines": lines,
            "pending": pending, "pending_lines": pending_lines}


def _phase_roi_text(count: int, avoidable: float) -> str:
    """阶段收益说明。金额一律来自 apply_loss_model 分摊后的同一批数字。"""
    if count == 0:
        return "No new spending in this phase."
    base = f"This phase handles {count} confirmed items. "
    if avoidable > 0:
        return base + (f"Under the calculation assumptions at the foot of the page, these items carry a "
                       f"yearly gain ceiling of RM {avoidable:,.2f} "
                       "(the formula and where the assumptions come from are in the ROI card; change an assumption and it is recalculated).")
    return base + "These items are not converted into separate amounts this run; they are ordered by the confirmed facts and their consequences."


def refresh_roi_milestones(roadmap: List[Dict[str, Any]],
                           findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """金额分摊完成后回填各阶段说明。

    顺序决定必须分两次：阶段预算决定采购车合计，采购车合计是 ROI 的分母，
    ROI 算出的收益再分摊回痛点，才轮到阶段说明里的金额。一次生成就写不出这句。
    """
    loss_by_dim = {
        f.get("dimension"): float(f.get("loss_myr") or 0.0)
        for f in (findings or []) if isinstance(f, dict)
    }
    for ph in (roadmap or []):
        dims = ph.get("addresses_dimensions") or []
        if not dims:
            continue
        total = round(sum(loss_by_dim.get(d, 0.0) for d in dims), 2)
        ph["roi_milestone"] = _phase_roi_text(len(dims), total)
    return roadmap


def generate_action_roadmap(
    data: Dict[str, Any],
    dms_result: Optional[Dict[str, Any]] = None,
    pain_points: Optional[List[Dict[str, Any]]] = None,
    site_audit: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    按已核验事实编排三阶段落地清单。

    任务只有在对应维度确实存在待补事实时才出现；某阶段没事可做就如实说没事，
    不铺满三张卡片充数。价格一律现查目录，查不到的写"待报价"。
    DMS < 40 时第三阶段暂缓，避免底层还没稳就先买 AI。

    site_audit（第②步快照）进来后，整份方案汇总挂在第 1 阶段：客户在一处看到
    "四条结论 + 要买的东西 + 各自价格"，其余两阶段只管执行细节。
    """
    from core.product_catalog import parse_headcount

    unmet = _unmet_dimensions(data)
    dms_score = float((dms_result or {}).get("overall_score", 100.0) or 0.0)
    deferred = dms_score < 40.0
    seats = parse_headcount((data or {}).get("team_size"))
    loss_by_dim = {
        p.get("dimension"): float(p.get("loss_myr") or 0.0)
        for p in (pain_points or []) if isinstance(p, dict)
    }
    solution_summary = _solution_summary(site_audit)

    roadmap: List[Dict[str, Any]] = []
    for phase_no in (1, 2, 3):
        title, timeline, months = _PHASE_META[phase_no]
        chosen = [t for t in _PHASE_TASKS
                  if t["phase"] == phase_no and t["dim"] in unmet]

        if chosen:
            # 先逐任务做多方案比较，再按"选中的那条"算价：比较层不另起一套事实判断，
            # 用的是同一个 seats / industry / 已核验维度现状。任务表本身不被改写，
            # 顶替 SKU 只发生在交给 _task_costing 的副本上。
            phase_tasks: List[Dict[str, Any]] = []
            option_blocks: List[Dict[str, Any]] = []
            for task in chosen:
                block = _build_option_block(task, seats, data, unmet.get(task["dim"], ""))
                priced_task = dict(task)
                priced_task["skus"] = _effective_skus(task, block)
                phase_tasks.append(priced_task)
                if block:
                    option_blocks.append(block)

            modules = [f"{t['title']}: {t['desc']} (your current situation: {unmet[t['dim']]})" for t in phase_tasks]
            evidences = [t["evidence"] for t in phase_tasks]
            addresses = [t["dim"] for t in phase_tasks]
            costing = _task_costing(phase_tasks, seats)
            avoidable = round(sum(loss_by_dim.get(t["dim"], 0.0) for t in phase_tasks), 2)
            roi = _phase_roi_text(len(phase_tasks), avoidable)
            third_party = [t["third_party"] for t in phase_tasks if t.get("third_party")]
        else:
            idle_dims = sorted({t["dim"] for t in _PHASE_TASKS if t["phase"] == phase_no})
            blind = [_DIM_LABELS.get(d, d) for d in idle_dims if not _dim_gathered(data, d)]
            sure = [_DIM_LABELS.get(d, d) for d in idle_dims if _dim_gathered(data, d)]
            if blind and not sure:
                modules = [f"This run collected no evidence to judge this phase ({', '.join(blind)}); "
                           "no tasks are invented. Once the step-3 interview fills the gaps, the plan re-orders itself automatically."]
                evidences = ["To be checked once the interview fills this phase's gaps"]
            elif blind:
                modules = [f"{', '.join(sure)} checked out adequate this run; "
                           f"{', '.join(blind)} were not collected this run, so no tasks were invented for them."]
                evidences = ["Verified items are reviewed once a quarter; items not collected will be checked once the interview fills them in"]
            else:
                modules = [f"Nothing needs fixing in this phase: the part covered by {title} checked out adequate this run, "
                           "and a quarterly review is enough."]
                evidences = ["No new deliverables in this phase; a quarterly review is enough"]
            costing = {"total": 0.0, "lines": [], "pending": [], "pending_lines": []}
            addresses = []
            roi = "No new spending in this phase."
            third_party = []
            phase_tasks = chosen
            option_blocks = []

        locked = bool(deferred and phase_no == 3)
        if locked:
            modules.append("This phase waits for now: your maturity score is below 40. Finish Phases 1 and 2 and pass "
                           "their checks before discussing any AI or automation purchase, or the money is very likely wasted.")
            roi = "This phase's budget stays on hold, to be reassessed once the first two phases pass acceptance."

        roadmap.append({
            "phase": title,
            "phase_title": title,
            "timeline": timeline,
            # 简报 Bonus 2 要的是实施月份区间；timeline 是第 3 页的回报窗口。两个口径并存。
            "months": months,
            "tasks": phase_tasks,
            "modules": modules,
            "acceptance": "; ".join(evidences),
            "cradle_evidences": "; ".join(evidences),
            "roi_milestone": roi,
            "budget_myr": costing["total"],
            "budget_lines": costing["lines"],
            "pricing_pending": costing["pending"],
            "pricing_pending_lines": costing["pending_lines"],
            "third_party_notes": third_party,
            # 简报要的"把备选摆出来并解释为什么"：一个任务一块比较，没有可替代解法就是空表
            "option_matrix": option_blocks,
            "option_matrix_note": (
                "Only a chosen line that we actually sell sits inside this phase's total. Anything else was "
                "compared against your facts and is not being purchased: a price shown on it is what it would cost, "
                "not a charge to you, and where we recommend something we do not sell, there is no price to show."
                if option_blocks else ""),
            "seats_used": seats,
            "addresses_dimensions": addresses,
            "hard_locked": locked,
            # 方案总结只挂在第 1 阶段：整份采购在一处看全，不重复三次
            "solution_summary": solution_summary if phase_no == 1 else None,
        })
    return roadmap


def _solution_summary(site_audit: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    把第②步的四条结论与所需产品汇总成一段，放在蓝图第 1 阶段开头。

    价格与产品名一律取自本公司目录快照；没有审计快照时返回 None，
    由界面如实说明"本次没有可引用的机检结果"，不铺一份通用清单。
    """
    conclusions = (site_audit or {}).get("conclusions") or []
    if not conclusions:
        return None
    products: List[Dict[str, Any]] = []
    seen: set = set()
    for c in conclusions:
        for p in c.get("remedy_products") or []:
            if p.get("sku") and p["sku"] not in seen:
                seen.add(p["sku"])
                products.append(p)
    summary = (site_audit or {}).get("summary") or {}
    gaps = sum(int((c.get("counts") or {}).get("fail") or 0) for c in conclusions)
    when = str((site_audit or {}).get("audited_at") or "").split("T")[0] or "this run"
    return {
        "audited_url": (site_audit or {}).get("url") or "",
        "site_level": (site_audit or {}).get("site_level") or "",
        "level_label": (site_audit or {}).get("level_label") or "",
        "conclusions": [{k: c.get(k) for k in ("title", "result", "rate", "counts")}
                        for c in conclusions],
        "products": products,
        "checks_total": summary.get("items_total"),
        "checks_measured": summary.get("items_measured"),
        "gaps": gaps,
        "note": (f"Website checked on {when}: "
                 f"{summary.get('items_measured', 0)} of {summary.get('items_total', 0)} checks "
                 f"applied to this site, {gaps} confirmed gaps."),
    }
