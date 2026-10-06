"""
Cradilot Typst Generator - 6-Page Industrial Blueprint Compiler
Compiles high-fidelity vector PDF consultation blueprints in under 200 milliseconds.
Every company name the customer reads comes from config (CRADILOT_VENDOR_NAME),
not from this file: a fork changes one environment variable, not twelve templates.
"""

import os
import tempfile
from typing import Dict, Any, List, Optional

import config

try:
    import typst
    TYPST_AVAILABLE = True
except ImportError:
    TYPST_AVAILABLE = False

_UNVERIFIED = "Not verified"


def _vendor() -> str:
    """Whichever company is doing the selling, read at call time and escaped for markup."""
    return _tx(config.VENDOR_NAME)


def _vendor_upper() -> str:
    return _tx(config.VENDOR_NAME.upper())


def _vendor_domain() -> str:
    return _tx(config.VENDOR_DOMAIN)


class NumView:
    """可格式化的数值视图：源值缺失时输出"未经核验"，而不是套用样本企业默认值。"""
    __slots__ = ("v",)

    def __init__(self, value):
        self.v = value

    def _ok(self):
        return self.v is not None and self.v != ""

    def __format__(self, spec):
        if not self._ok():
            return _UNVERIFIED
        try:
            return format(float(self.v), spec)
        except (TypeError, ValueError):
            return _tx(self.v)

    def __str__(self):
        return format(self, ",.2f")



def _tx(value) -> str:
    """Escape user-controlled text so it cannot break Typst markup.

    `{`、`}`、`$` 也在名单里：这三个在 Typst 文本模式里各有含义（进代码块、
    开启数学模式），客户填的公司名与备注里出现一个就够把整份 PDF 编译打断。
    """
    text = str(value if value is not None else "").strip()
    if not text:
        return ""
    for ch in ("\\", "#", "[", "]", "@", "<", ">", "|", "_", "*", "{", "}", "$"):
        text = text.replace(ch, "\\" + ch)
    return text.replace("\n", " ")


def _fmt(value, digits=2):
    """数值缺失时如实标注未核验，不再套用样本企业默认值。"""
    if value is None or value == "":
        return _UNVERIFIED
    try:
        num = float(value)
    except (TypeError, ValueError):
        return _tx(value)
    return f"{num:,.{digits}f}"


_SPEC_BY_DIM = {
    "cyber": "Own main domain with SPF/DKIM/DMARC and a central audit log trail",
    "web": "NVMe LiteSpeed engine, automatic SSL, mobile-friendly layout and enquiry capture",
    "cloud": "Daily encrypted off-site copies (AES-256), recovery time under 30 minutes",
    "ai": "Webhook reply under 1 second, WhatsApp API hookup and leads stored in an ordered form",
    "crm": "One shared deal board, follow-up log and a resignation handover with separated permissions",
    "marketing": "Pixel / GA4 conversion tracking and automated follow-up by lead group",
    "digital_workflow": "Cross-department document approval online, with reconciliation produced automatically",
    "data_availability": "One structured stock-sales-purchase / CRM data layer with an export interface",
    "process_maturity": "Written quote SOP and a structured FAQ knowledge base",
    "employee_skills": "Training for the pilot role and a hands-on proficiency check for working with AI",
}


def _pain_rows_from_evidence(assessment_data):
    """第二页映射表：逐条由已锁证痛点生成，不再输出写死的四行样例。"""
    pains = assessment_data.get("pain_points") or []
    if not isinstance(pains, list) or not pains:
        return ["  [This audit confirmed no fact that is causing a loss, so no product mapping is listed],",
                "  [Not applicable],",
                "  [Not applicable],",
                "  [Company facts were verified as met; no extra infrastructure purchase is needed.]"]
    rows = []
    for p in pains[:4]:
        if not isinstance(p, dict):
            continue
        dim = (p.get("dimension") or "").strip()
        title = _tx(p.get("title") or "Untitled pain point")
        spec = _tx(_SPEC_BY_DIM.get(dim, "Deliverables set by the confirmed facts"))
        sku = _tx(p.get("solution") or "To be settled at acceptance")
        basis = _tx(p.get("evidence") or "")
        impact = _tx(p.get("impact") or "")
        loss = p.get("loss_myr")
        why = f"{basis} — {impact}"
        if loss:
            why += (f" — {p.get('loss_basis') or ('yearly amount under the assumptions of this run: RM ' + _fmt(loss))}"
                    f" (source: {_tx(p.get('source') or 'confirmed fact')})")
        rows += [f"  [{title}],", f"  [{spec}],", f"  [{sku}],", f"  [{why}],"]
    if rows:
        rows[-1] = rows[-1][:-1]
    return rows


def _phase_label(ph, fallback: str) -> str:
    """阶段短标签：简报把阶段名写成 "Phase 1 · Quick Wins — 说明句"，
    表格栏里只要破折号前那半句；旧标题用冒号分隔，两种都要能切。"""
    title = str(ph.get("phase_title") or ph.get("phase") or "").strip()
    if not title:
        return fallback
    head = title.split("—")[0]
    if head == title and ":" in title:
        head = title.split(":")[0]      # 旧会话里存的是 "Phase 1: 说明句" 这种冒号写法
    return head.strip(" ·:") or title


def _strip_lead(text, prefix: str) -> str:
    """去掉引擎句子里的"Chosen:"/"Not this time:"引导词——PDF 那一行已经标过身份，
    留着会印成"Chosen: EBiz Mail PRO ... Chosen: one 10-user block covers..."。"""
    body = str(text or "").strip()
    if body.startswith(prefix):
        body = body[len(prefix):].strip()
        body = body[:1].upper() + body[1:] if body else body
    return body


def _option_matrix_lines(ph: Dict[str, Any]) -> str:
    """简报第 4-5 页的"比较过哪些方案"：选中的那条写明在本阶段合计里，
    其余一律写明没有购买，本公司不卖的平台连价钱都不给。"""
    blocks = [b for b in (ph.get("option_matrix") or []) if isinstance(b, dict)]
    if not blocks:
        return ""
    out = ['  #text(weight: "bold", size: 9pt)[Options we compared] \n']
    body: List[str] = []
    for block in blocks:
        chosen = block.get("chosen") or {}
        basis = str(block.get("decision_basis") or "").strip()
        question = _tx(block.get("question"))
        body.append(f"• {question}" + (f" (decided from {_tx(basis)})" if basis else ""))
        why = str(chosen.get("why") or "")
        for lead in ("Chosen: ", "Recommended, even though we cannot sell it to you: ",
                     "Recommended, and it costs you nothing from us: "):
            why = _strip_lead(why, lead)
        why = _tx(why)
        if block.get("purchase", True):
            in_total = ("in this phase's total." if chosen.get("annual_myr") is not None
                        else "part of this phase, but priced on the quote rather than added to the total.")
            body.append(f"  Chosen: {_tx(chosen.get('product_name'))} - "
                        f"{_tx(chosen.get('price_label'))}, {in_total}"
                        + (f" {why}" if why else ""))
        else:
            # 推荐一件客户买不到、或根本不用买的事，绝不能写成"进了本阶段合计"
            body.append(f"  We recommend: {_tx(chosen.get('product_name'))} - "
                        f"{_tx(chosen.get('price_label'))}, and it is not in our bill."
                        + (f" {why}" if why else ""))
        for row in block.get("also_considered") or []:
            if not isinstance(row, dict):
                continue
            state = str(row.get("price_state") or "")
            sold = bool(row.get("purchasable", True))
            label = ("Compared, not purchased" if sold else
                     "Compared, and nothing to buy" if state == "no_purchase" else
                     "Compared, not sold here")
            price = f" - {_tx(row.get('price_label'))}" if sold or state == "no_purchase" else ""
            note = _tx(_strip_lead(row.get("why_not"), "Not this time: "))
            body.append(f"  {label}: {_tx(row.get('product_name'))}{price}." + (f" {note}" if note else ""))
    out.append("  #text(size: 8.2pt)[\n    " + " \n".join(body) + "\n  ]\n")
    note = str(ph.get("option_matrix_note") or "").strip()
    if note:
        out.append(f"  #text(size: 8pt, fill: rgb(\"#475569\"))[{_tx(note)}]\n")
    return "".join(out)


def _third_party_lines(ph: Dict[str, Any]) -> str:
    """我们不卖的东西也要在 PDF 里讲明白：简报点了名、本公司没有的产品，
    只出现在这一句里，没有价钱，也不进采购车。"""
    notes = [str(n).strip() for n in (ph.get("third_party_notes") or []) if str(n).strip()]
    if not notes:
        return ""
    lines = ['  #text(weight: "bold", size: 9pt)[What we do not sell here] \n']
    lines.append("  #text(size: 8.2pt)[\n    " + " \n".join(f"• {_tx(n)}" for n in notes) + "\n  ]\n")
    return "".join(lines)


def _roadmap_blocks(assessment_data):
    """第三页三阶段：任务、预算、凭据与硬锁全部来自实际编排结果。"""
    roadmap = assessment_data.get("roadmap") or (
        (assessment_data.get("recommendation") or {}).get("roadmap")) or []
    skins = [("rgb(\"#eff6ff\")", "rgb(\"#bfdbfe\")", "rgb(\"#1d4ed8\")"),
             ("rgb(\"#f0fdf4\")", "rgb(\"#bbf7d0\")", "rgb(\"#15803d\")"),
             ("rgb(\"#faf5ff\")", "rgb(\"#e9d5ff\")", "rgb(\"#7e22ce\")")]
    blocks = []
    for i, ph in enumerate(list(roadmap)[:3]):
        if not isinstance(ph, dict):
            continue
        fill, stroke, accent = skins[i % 3]
        title = _tx(ph.get("phase_title") or ph.get("phase") or f"Phase {i + 1}")
        timeline = _tx(ph.get("timeline") or "")
        bullets = "".join(f"  • {_tx(m)} \n" for m in (ph.get("modules") or [])[:6]) or "  • Nothing needs fixing in this phase \n"
        budget = _fmt(ph.get("budget_myr"))
        evid = _tx(ph.get("acceptance") or ph.get("cradle_evidences") or "Same checks as the previous phase")
        roi_ms = _tx(ph.get("roi_milestone") or "")
        lock = ""
        if ph.get("hard_locked"):
            lock = ('  #text(weight: "bold", fill: rgb("#b91c1c"))[This phase is on hold: nothing starts here until the '
                    'previous phase passes its checks, so pricey tools are not bought on an unsteady base.] \n')
        pending = "".join(f"  • {_tx(p)} \n" for p in (ph.get("pricing_pending") or [])[:3])
        compared = _option_matrix_lines(ph)
        not_sold = _third_party_lines(ph)
        sol = ph.get("solution_summary") or {}
        sol_lines = ""
        if sol.get("conclusions"):
            sol_lines = ('  #text(weight: "bold", fill: %s)[Whole package (from the step-2 '
                         'website inspection)] \n' % accent)
            sol_lines += "  " + _tx(sol.get("note") or "") + " \n"
            for c in sol["conclusions"]:
                sol_lines += (f"  • {_tx(c.get('title'))} — *{_tx(c.get('rate'))}*: "
                              f"{_tx(c.get('result'))} \n")
            for p in (sol.get("products") or []):
                sol_lines += f"  • {_tx(p.get('name'))} — {_tx(p.get('price_label'))} \n"
        if blocks:
            blocks.append("#v(0.35cm)")
        roi_window = f"ROI {timeline}" if timeline else ""
        blocks += [
            f"#rect(fill: {fill}, stroke: 1pt + {stroke}, radius: 6pt, inset: 10pt, width: 100%)[",
            "  #grid(",
            "    columns: (3.4cm, 1fr),",
            f"    [ *{title}* \n#text(size: 8.5pt, fill: {accent})[{roi_window}] ],",
            "    [",
            bullets,
            sol_lines,
            f'      #text(weight: "bold", fill: {accent})[{_vendor()} product annual fees for this phase]: RM {budget} \n',
            pending,
            compared,
            not_sold,
            f'      #text(weight: "bold", fill: {accent})[How we check it is done]: {evid} \n',
            f'      #text(weight: "bold", fill: {accent})[Why it is worth doing]: {roi_ms} \n',
        ]
        if lock:
            blocks.append(lock.rstrip("\n"))
        blocks += ["    ]", "  )", "]"]
    if not blocks:
        blocks = ['#rect(stroke: 1pt + rgb("#cbd5e1"), radius: 6pt, inset: 10pt, width: 100%)[',
                  "  [No phase plan was generated in this session, so the roadmap is not verified.]",
                  "]"]
    return blocks


def _milestone_rows(assessment_data):
    """第四页资金治理表：金额与凭据来自实际任务预算累加。"""
    roadmap = assessment_data.get("roadmap") or (
        (assessment_data.get("recommendation") or {}).get("roadmap")) or []
    modes = ["Advance to start", "Released after check", "Final payment on sign-off"]
    rows = []
    for i, ph in enumerate(list(roadmap)[:3]):
        if not isinstance(ph, dict):
            continue
        tasks = ph.get("tasks") or []
        names = ", ".join(_tx(t.get("title")) for t in tasks if isinstance(t, dict) and t.get("title"))
        deliverables = names or "No new deliverables this phase (facts already verified as met)"
        budget = ph.get("budget_myr")
        cost = "RM 0.00 (no new spend)" if not budget else f"RM {_fmt(budget)}"
        if ph.get("hard_locked"):
            cost += " — on hold until the previous phase passes its checks"
        label = _tx(_phase_label(ph, f"Phase {i + 1}"))
        rows += [f"  [{label}],",
                 f"  [{_tx(ph.get('months') or ph.get('timeline') or 'no timeline set yet')}],",
                 f"  [{deliverables}],",
                 f"  [{_tx(ph.get('acceptance') or ph.get('cradle_evidences') or 'No new checks this phase')}],",
                 f"  [{cost}],",
                 f"  [{modes[min(i, 2)]}],"]
    if rows:
        rows[-1] = rows[-1][:-1]
    else:
        rows = ["  [No phase data], [Not verified], [Not verified], [Not verified], [Not verified], [Not verified]"]
    return rows


def _acceptance_blocks(assessment_data):
    """第五页验收序列：只对本次方案实际交付的项目列验收动作。"""
    roadmap = assessment_data.get("roadmap") or (
        (assessment_data.get("recommendation") or {}).get("roadmap")) or []
    seq = []
    for ph in roadmap:
        if not isinstance(ph, dict):
            continue
        for t in (ph.get("tasks") or []):
            if isinstance(t, dict) and t.get("title"):
                seq.append((t.get("title"), t.get("evidence") or "Verify against the archived delivery evidence"))
    if not seq:
        return ['#rect(stroke: 1pt + rgb("#cbd5e1"), radius: 6pt, inset: 10pt, width: 100%)[',
                '  #text(weight: "bold", size: 10.5pt)[No new deliverables in this plan]',
                "  #v(2pt)",
                "  • All six company dimensions and the five-factor facts verified as met, so there is nothing new to accept; review the existing setup quarterly.",
                "]"]
    blocks = []
    for idx, (title, evid) in enumerate(seq[:3], start=1):
        if blocks:
            blocks.append("#v(0.35cm)")
        blocks += [
            '#rect(stroke: 1pt + rgb("#cbd5e1"), radius: 6pt, inset: 10pt, width: 100%)[',
            f'  #text(weight: "bold", size: 10.5pt, fill: rgb("#0f172a"))[Test Sequence {idx:02d}: {_tx(title)}]',
            "  #v(2pt)",
            f"  • *Acceptance evidence*: {_tx(evid)}\n",
            "  • *If it does not pass*: this item does not count as delivered, the final payment for that phase is not released, and Cradilot issues a checklist for the rework.",
            "]",
        ]
    return blocks


def _audit_appendix_blocks(assessment_data: Dict[str, Any]) -> List[str]:
    """附录：第②步主清单的逐项明细。界面只给四条结论，全部证据在这里。"""
    audit = assessment_data.get("site_audit") or {}
    rows = [r for r in (audit.get("rows") or []) if isinstance(r, dict)]
    head = [
        "#pagebreak()",
        "",
        "  #set text(size: 7.8pt)",
        '  #text(size: 13pt, weight: "bold", fill: rgb("#0f172a"))['
        'Appendix A · Website inspection detail]',
        "  #v(3pt)",
    ]
    if not rows:
        head += [
            '  #rect(stroke: 1pt + rgb("#cbd5e1"), radius: 6pt, inset: 10pt, width: 100%)[',
            '    No website inspection was run in this session, so there is no detail to list. \n',
            "    Nothing in this report should be read as \"checked and clear\" for the website.",
            "  ]",
        ]
        return head

    url = _tx((audit.get("url") or "")[:70])
    level = _tx(audit.get("site_level") or "")
    label = _tx(audit.get("level_label") or "")
    summary = audit.get("summary") or {}
    head += [
        f'  #text(fill: rgb("#334155"))[Checked address: {url} · site type {level} ({label})]',
        "  #v(2pt)",
        ("  #text(fill: rgb(\"#334155\"))[Total checks on the master list: "
         f"*{summary.get('items_total', len(rows))}* · applied to this site: "
         f"*{summary.get('items_measured', 0)}* · switched off because the feature is not on "
         f"this site: *{summary.get('not_applicable', 0)}* · only confirmable from inside your "
         f"account: *{summary.get('not_tested', 0)}*]"),
        "  #v(4pt)",
        "  #table(",
        "    columns: (2.9cm, 5.4cm, 1fr, 2.15cm),",
        "    inset: (x: 5pt, y: 3pt),",
        '    stroke: 0.4pt + rgb("#e2e8f0"),',
        "    table.header(",
        "      [Module], [Check], [What we saw, or why it was not checked], [State],",
        "    ),",
    ]
    state_cn = {"fail": "Gap", "pass": "Clear", "unverified": "Not measured",
                "not_applicable": "Not applicable", "not_tested": "Needs inside access"}
    for r in rows:
        seen = _tx(r.get("observed") or r.get("detail") or r.get("skipped_reason")
                   or r.get("how_note") or "")
        state = state_cn.get(r.get("state"), _tx(r.get("state") or ""))
        if r.get("state") == "fail" and r.get("severity") and r["severity"] != "UNKNOWN":
            state += f' · {_tx(r["severity"])}'
        head += [
            f"    [{_tx(r.get('module_title') or r.get('module') or '')}],",
            f"    [{_tx(r.get('label') or r.get('id') or '')}],",
            f"    [{seen}],",
            f"    [{state}],",
        ]
    head += [
        "  )",
        "  #v(5pt)",
        '  #rect(fill: rgb("#f8fafc"), stroke: 0.8pt + rgb("#cbd5e1"), radius: 6pt, inset: 9pt, width: 100%)[',
        '    #text(weight: "bold", fill: rgb("#334155"))[How to read this table] \n',
        "    • *Gap*: measured and confirmed missing — the only rows that cost points. \n",
        "    • *Clear*: measured and already correct; no purchase needed for these. \n",
        "    • *Not measured*: the probe did not return a result on this run. It is excluded from "
        "the score and never converted into a defect. \n",
        "    • *Not applicable*: this site does not have the feature the check depends on "
        "(for example, no checkout means no checkout checks). \n",
        "    • *Needs inside access*: not visible from the public internet; it is a question for "
        "the consultant call, not a finding.",
        "  ]",
    ]
    return head


def render_typst_markup(assessment_data: Dict[str, Any]) -> str:
    """
    Generate valid, clean Typst source markup for the 6-page blueprint report.
    """
    meta = assessment_data.get("metadata", {}) or {}
    company_name = _tx(meta.get("company_name") or "Company not provided")
    industry = _tx(meta.get("industry") or "Industry not provided")
    team_size = _tx(meta.get("team_size") or "Not provided")
    # 修键名不一致：报告写入 annual_turnover，旧代码只读 company_size，故永远落到样本值
    annual_turnover = _tx(meta.get("annual_turnover") or meta.get("company_size") or "Not provided")

    dms = assessment_data.get("dms", {}) or {}
    dms_score = NumView(dms.get("overall_score"))
    dms_stars = _tx(dms.get("overall_stars") or "Not verified")
    dms_tier = _tx(dms.get("tier_label") or dms.get("tier") or _UNVERIFIED)
    dims = dms.get("dimensions", {}) or {}

    def _dim(key):
        d = dims.get(key) or {}
        return (_tx(d.get("stars") or "Not verified"),
                _tx(d.get("details") or d.get("reason") or _UNVERIFIED))

    web_stars, web_details = _dim("website")
    cloud_stars, cloud_details = _dim("cloud")
    crm_stars, crm_details = _dim("crm")
    mkt_stars, mkt_details = _dim("marketing")
    sec_stars, sec_details = _dim("cybersecurity")
    ai_stars, ai_details = _dim("ai_adoption")

    ars = assessment_data.get("ars", {}) or {}
    ars_score = NumView(ars.get("final_score"))
    ars_raw = NumView(ars.get("raw_score"))
    mu_penalty = NumView(ars.get("penalty_factor"))
    if ars.get("is_hard_locked"):
        lock_caption = "Readiness not met: no AI purchase recommended in this round"
    elif ars:
        lock_caption = "Organizational readiness met"
    else:
        lock_caption = _UNVERIFIED

    # 简报 Step 3 点名的五项就绪度因子：算过就得逐项露一次面，
    # 并写明这一分来自客户确认过的事实，还是推断出来的。
    # 用词必须与界面 chip 一致（static/js/app.js 里 verified_fact → "You stated"，
    # 其余 → "Inferred"），同一轮结果不能在屏幕与 PDF 上是两套话；
    # "中性值计入"这类解释留在各因子自己的 note 里，那才是它成立的地方。
    _ARS_ORDER = (("leadership", "Leadership"),
                  ("data_availability", "Data availability"),
                  ("employee_skills", "Employee skills"),
                  ("digital_workflow", "Digital workflow"),
                  ("process_maturity", "Process maturity"))
    _ARS_BASIS = {"verified_fact": "You stated",
                  "inferred_default": "Inferred"}
    ars_factor_rows: List[str] = []
    for _i, (_key, _label) in enumerate(_ARS_ORDER, start=1):
        _f = (ars.get("sub_scores") or {}).get(_key) or {}
        if not _f:
            continue
        _w = _f.get("weight")
        _weight = f"{round(float(_w) * 100)}%" if isinstance(_w, (int, float)) else _UNVERIFIED
        _score = _UNVERIFIED if _f.get("score") is None else f"{round(float(_f['score']))} \\/ 100"
        _why = f"{_ARS_BASIS.get(str(_f.get('basis')), 'No basis recorded')}: {_tx(str(_f.get('note') or ''))}"
        ars_factor_rows.append(f'  [{_i}. {_tx(_label)}], [{_weight}], [{_score}], [{_why}],')
    if ars_factor_rows:
        ars_factor_rows[-1] = ars_factor_rows[-1].rstrip(",")
        ars_matrix_block = [
            '',
            '#v(0.4cm)',
            '#text(weight: "bold", size: 10.5pt)[ARS fact-diagnosis matrix across the 5 readiness factors '
            'named in the challenge:]',
            '#v(4pt)',
            '#table(',
            '  columns: (4.0cm, 1.2cm, 1.6cm, 1fr),',
            '  stroke: 0.5pt + rgb("#cbd5e1"),',
            '  fill: (_, row) => if row == 0 { rgb("#f1f5f9") } else { none },',
            '  align: (col, _) => if col < 3 { center } else { left },',
            '  [*Readiness factor*], [*Weight*], [*Score*], [*Basis and what the facts show today*],',
            *ars_factor_rows,
            ')',
        ]
    else:
        ars_matrix_block = []

    roi = assessment_data.get("roi", {}) or {}
    net_gain = NumView(roi.get("net_gain"))
    roi_pct = NumView(roi.get("roi_percentage"))
    annual_savings = NumView(roi.get("annual_labor_savings"))
    salvaged_rev = NumView(roi.get("annual_salvaged_revenue"))
    annual_cost = NumView(roi.get("vendor_annual_cost"))
    hourly_rate = NumView(roi.get("effective_hourly_rate"))

    # 测算假设与其出处：驱动 ROI 的四个数字里，客户填过的与系统取的必须分开写
    assumptions = roi.get("assumptions") or {}
    a_vals = assumptions.get("values") or {}
    a_srcs = assumptions.get("sources") or {}
    a_labels = assumptions.get("labels") or {}
    assumption_lines = []
    for key in ("saved_hours_per_week", "missed_orders_per_month",
                "order_margin_myr", "monthly_salary_myr"):
        if key not in a_vals:
            continue
        src = str(a_srcs.get(key, ""))
        if "Not collected" in src:
            tag = "not collected this run, left out of the gain"
        elif "Converted" in src:
            tag = "converted from the order margin you reported"
        elif "Entered by you" in src:
            tag = "filled in by your company"
        else:
            tag = "conservative assumption taken by the system"
        assumption_lines.append(
            f"    • {a_labels.get(key) or key}: {float(a_vals[key]):g} ({tag})\n")
    if roi.get("net_gain") is None:
        roi_headline = "The plan's annual fee is still to be quoted by our sales desk for your actual seat count, so no ROI percentage is given this run"
    else:
        roi_headline = (f"Net yearly gain: RM {net_gain:,.2f}"
                        f" (ROI {roi_pct})")

    report_id = _tx(meta.get("report_id") or _UNVERIFIED)

    # 顾问备注与跟进顾问：简报要求 PDF 自带 Consultant notes；没填就不印空框
    c_notes = _tx((meta.get("consultant_notes") or "").strip())
    c_who = _tx((meta.get("assigned_to") or "").strip())
    consultant_block: List[str] = []
    if c_notes or c_who:
        consultant_block = [
            '#rect(fill: rgb("#f8fafc"), stroke: 1pt + rgb("#94a3b8"), radius: 8pt, inset: 10pt, width: 100%)[',
            '  #text(weight: "bold", size: 10pt, fill: rgb("#334155"))[Consultant notes]',
            '  #v(3pt)',
            f'  #text(size: 9pt)[{c_notes or "(no notes were added in this session)"}]',
        ]
        if c_who:
            consultant_block.append(f'  #v(2pt) \n  #text(size: 9pt, weight: "bold")[Follow-up consultant: {c_who}]')
        consultant_block.append(']')
    # 数据基础：未采集项按中性值计入，这一点必须在封面就讲明，否则中性分会被读成实测结论
    basis_note = _tx((meta.get("data_basis_note") or "").strip())
    basis_block: List[str] = []
    if basis_note:
        basis_block = [
            '#v(0.35cm)',
            '#rect(fill: rgb("#fffbeb"), stroke: 1pt + rgb("#f59e0b"), radius: 8pt, inset: 10pt, width: 100%)[',
            '  #text(weight: "bold", size: 9.5pt, fill: rgb("#92400e"))[The data behind this report]',
            '  #v(3pt)',
            f'  #text(size: 9pt)[{basis_note}]',
            ']',
        ]
    date_str = _tx(meta.get("date") or "Not provided")
    biggest_challenge = _tx(meta.get("biggest_challenge") or "Not yet provided")
    growth_objective = meta.get("growth_objective") or "Not yet provided"
    growth_objective = _tx(growth_objective)
    current_tools = _tx(meta.get("current_tools") or "Not provided in this session")
    biggest_challenge_disp = biggest_challenge

    # Use clean, validated Typst markup
    lines = [
        '#set page(',
        '  paper: "a4",',
        '  margin: (x: 1.8cm, top: 2.0cm, bottom: 2.0cm),',
        '  header: [',
        '    #grid(',
        '      columns: (1fr, 1fr),',
        f'      align(left)[#text(size: 8pt, fill: rgb("#64748b"))[{_vendor_upper()} · CRADILOT AI CONSULTING BLUEPRINT]],',
        f'      align(right)[#text(size: 8pt, fill: rgb("#0284c7"))[ID: {report_id}]]',
        '    )',
        '    #line(length: 100%, stroke: 0.5pt + rgb("#cbd5e1"))',
        '  ],',
        '  footer: [',
        '    #grid(',
        '      columns: (1fr, 1fr),',
        '      align(left)[#text(size: 8pt, fill: rgb("#94a3b8"))[Confidential & Proprietary · Powered by Cradilot AI]],',
        '      align(right)[#text(size: 8pt, fill: rgb("#94a3b8"))[Consultant-ready blueprint · generated from this session]]',
        '    )',
        '  ]',
        ')',
        '',
        '#set text(font: ("Segoe UI", "Arial"), size: 10pt, fill: rgb("#0f172a"), hyphenate: false)',
        '#set par(justify: true, leading: 0.65em)',
        '',
        '// ================= PAGE 1: COVER & EXECUTIVE DASHBOARD =================',
        '#align(center)[',
        '  #v(0.6cm)',
        '  #rect(fill: rgb("#0284c7"), radius: 4pt, inset: (x: 12pt, y: 6pt))[',
        f'    #text(fill: white, weight: "bold", size: 9pt)[{_vendor_upper()} · AI SME DIGITAL GROWTH ADVISOR]',
        '  ]',
        '  #v(0.4cm)',
        '  #text(size: 20pt, weight: "bold", fill: rgb("#0f172a"))[SME Digital & AI Growth Engine Implementation Blueprint]',
        '  #v(0.2cm)',
        f'  #text(size: 10pt, fill: rgb("#475569"))[Tailored to the Cradle CIP Spark incubation due-diligence standard and the {_vendor()} business ecosystem]',
        '  #v(0.6cm)',
        ']',
        '',
        '#rect(fill: rgb("#f8fafc"), stroke: 1pt + rgb("#e2e8f0"), radius: 8pt, width: 100%, inset: 10pt)[',
        '  #grid(',
        '    columns: (1fr, 1fr, 1fr),',
        '    gutter: 8pt,',
        f'    [ *Company entity*: {company_name} ],',
        f'    [ *Industry*: {industry} ],',
        f'    [ *Team size*: {team_size} ],',
        f'    [ *Annual turnover*: {annual_turnover} ],',
        f'    [ *Report filing number*: {report_id} ],',
        f'    [ *Diagnosis date*: {date_str} ]',
        '  )',
        '  #v(4pt)',
        '  #line(length: 100%, stroke: 0.5pt + rgb("#e2e8f0"))',
        '  #v(4pt)',
        '  #grid(',
        '    columns: (1fr, 1fr),',
        '    gutter: 10pt,',
        f'    [ *Core business pain / challenge*: #text(fill: rgb("#b91c1c"))[{biggest_challenge}] ],',
        f'    [ *12-month digital growth goal*: #text(fill: rgb("#0369a1"))[{growth_objective}] ],',
        f'    grid.cell(colspan: 2)[ *Digital tools in use today*: #text(fill: rgb("#334155"))[{current_tools}] ]',
        '  )',
        ']',
        *basis_block,
        '',
        '#v(0.5cm)',
        '#grid(',
        '  columns: (1fr, 1fr),',
        '  gutter: 14pt,',
        '  rect(fill: rgb("#f0f9ff"), stroke: 1.5pt + rgb("#0284c7"), radius: 8pt, inset: 12pt, width: 100%)[',
        '    #text(size: 11pt, weight: "bold", fill: rgb("#0369a1"))[Step 2: Digital Maturity Score (DMS)]',
        '    #v(4pt)',
        f'    #text(size: 28pt, weight: "bold", fill: rgb("#0284c7"))[{dms_score}] #text(size: 13pt, fill: rgb("#64748b"))[\\/ 100]',
        '    #v(-4pt)',
        f'    #text(size: 11pt, fill: rgb("#f59e0b"))[{dms_stars}]',
        f'    #text(size: 8.5pt, weight: "bold", fill: rgb("#334155"))[{dms_tier}]',
        '  ],',
        '  rect(fill: rgb("#fef2f2"), stroke: 1.5pt + rgb("#ef4444"), radius: 8pt, inset: 12pt, width: 100%)[',
        '    #text(size: 11pt, weight: "bold", fill: rgb("#b91c1c"))[Step 3: AI Readiness Score (ARS)]',
        '    #v(4pt)',
        f'    #text(size: 28pt, weight: "bold", fill: rgb("#ef4444"))[{ars_score}] #text(size: 13pt, fill: rgb("#64748b"))[\\/ 100]',
        '    #v(-4pt)',
        f'    #text(size: 8.5pt, weight: "bold", fill: rgb("#dc2626"))[{lock_caption} (μ = {mu_penalty:.2f})]',
        f'    #text(size: 8pt, fill: rgb("#7f1d1d"))[Raw score {ars_raw:,.1f}, scaled by factor μ to {ars_score:,.1f}; while readiness is not met, this plan will not recommend expensive AI.]',
        '  ]',
        ')',
        '',
        '#v(0.4cm)',
        '#text(weight: "bold", size: 10.5pt)[DMS fact-diagnosis matrix across the 6 core dimensions:]',
        '#v(4pt)',
        '#table(',
        '  columns: (2.5cm, 1.4cm, 1.8cm, 1fr),',
        '  stroke: 0.5pt + rgb("#cbd5e1"),',
        '  fill: (_, row) => if row == 0 { rgb("#f1f5f9") } else { none },',
        '  align: (col, _) => if col < 3 { center } else { left },',
        '  [*Dimension assessed*], [*Weight*], [*Star rating*], [*What the facts show today (Metric & Benchmark)*],',
        f'  [1. Website], [15%], [{web_stars}], [{web_details}],',
        f'  [2. Cloud], [20%], [{cloud_stars}], [{cloud_details}],',
        f'  [3. CRM], [20%], [{crm_stars}], [{crm_details}],',
        f'  [4. Marketing], [15%], [{mkt_stars}], [{mkt_details}],',
        f'  [5. Cybersec], [15%], [{sec_stars}], [{sec_details}],',
        f'  [6. AI Adoption], [15%], [{ai_stars}], [{ai_details}]',
        ')',
        *ars_matrix_block,
        '',
        '#pagebreak()',
        '',
        '// ================= PAGE 2: ARCHITECTURE & WHY THESE CHOICES =================',
        '#text(size: 15pt, weight: "bold", fill: rgb("#0284c7"))[Page 2: Need-Spec-Module Mapping and the Reason Behind Each Choice (Explain WHY)]',
        '#v(2pt)',
        '#text(size: 9pt, fill: rgb("#64748b"))[Held to the Cradle CIP Spark "Sample Plan & Design Document v0.11" engineering standard, so there is no sales black box]',
        '#v(0.4cm)',
        '',
        '#table(',
        '  columns: (2.8cm, 3.2cm, 3.8cm, 1fr),',
        '  stroke: 0.5pt + rgb("#cbd5e1"),',
        '  fill: (_, row) => if row == 0 { rgb("#f1f5f9") } else { none },',
        '  [*Pain scenario*], [*Engineering specification*], [*Recommended SKU*], [*Why this product was chosen (Explain WHY)*],',
        '@@PAIN_ROWS@@',
        ')',
        '',
        '#v(0.6cm)',
        '#rect(fill: rgb("#f8fafc"), stroke: 1pt + rgb("#e2e8f0"), radius: 6pt, inset: 10pt, width: 100%)[',
        '  #text(weight: "bold", size: 9.5pt)[Lead architect\'s summary of the choices:]',
        '  #v(2pt)',
        '  #text(size: 8.5pt)[',
        '    Until the data layer and the working rules are steady, this plan will not recommend expensive large models. Our own lines (domain email, website hosting, off-site backup) are configured ',
        'only for the problems confirmed this run; the first-year spend follows the settlement on page 6; capabilities that do not appear in the evidence chain are not written into this blueprint.',
        '  ]',
        ']',
        '',
        '#pagebreak()',
        '',
        '// ================= PAGE 3: THREE-PHASE ACTION ROADMAP =================',
        '#text(size: 15pt, weight: "bold", fill: rgb("#0284c7"))[Page 3: 12-Month Phased Implementation Roadmap (12-Month Action Roadmap)]',
        '#v(2pt)',
        '#text(size: 9pt, fill: rgb("#64748b"))[Ordered by the problems confirmed for your business this run: fix the storefront and the data first, then cut manual work, and only then growth and AI]',
        '#v(0.4cm)',
        '',
        '@@ROADMAP_BLOCKS@@',
        '',
        '#pagebreak()',
        '',
        '// ================= PAGE 4: CRADLE MILESTONE GOVERNANCE =================',
        '#text(size: 15pt, weight: "bold", fill: rgb("#0284c7"))[Page 4: Cradle-Grade Phased Purchasing and Delivery Funding Governance Table]',
        '#v(2pt)',
        '#text(size: 9pt, fill: rgb("#64748b"))[Drawing on Cradle CIP Spark grant governance (Form A1/A2/A3): the next tranche of funds is released only after one milestone passes its check]',
        '#v(0.4cm)',
        '',
        '#table(',
        '  columns: (2.8cm, 1.8cm, 3.8cm, 4.2cm, 2.0cm, 1.8cm),',
        '  stroke: 0.5pt + rgb("#cbd5e1"),',
        '  fill: (_, row) => if row == 0 { rgb("#f1f5f9") } else { none },',
        '  [*Phase*], [*Period*], [*Main deliverables*], [*How we check it is done*], [*Cost (MYR)*], [*Payment mode*],',
        '@@MILESTONE_ROWS@@',
        ')',
        '',
        '#v(0.6cm)',
        '#rect(fill: rgb("#fefce8"), stroke: 1pt + rgb("#fef08a"), radius: 6pt, inset: 10pt, width: 100%)[',
        '  #text(weight: "bold", size: 9.5pt, fill: rgb("#854d0e"))[Stage payments: pay for the next step only after you see the result]',
        '  #v(2pt)',
        '  #text(size: 8.5pt, fill: rgb("#713f12"))[',
        '    The thing to fear most is paying everything at once and receiving nothing delivered. This plan moves phase by phase: each phase ends with the check items written in the table above, ',
        '    and only after you confirm the result do you pay for the next phase; if a check does not pass, later spending does not start.',
        '  ]',
        ']',
        '',
        '#pagebreak()',
        '',
        '// ================= PAGE 5: ACCEPTANCE CHECKLIST =================',
        '#text(size: 15pt, weight: "bold", fill: rgb("#0284c7"))[Page 5: System Go-Live Acceptance Test Sequence Cards (Acceptance Checklist)]',
        '#v(2pt)',
        '#text(size: 9pt, fill: rgb("#64748b"))[Every deliverable states what you personally verify, not what was promised verbally]',
        '#v(0.4cm)',
        '',
        '@@ACCEPTANCE_BLOCKS@@',
        '',
        '#v(0.35cm)',
        '',
        '#rect(stroke: 1pt + rgb("#cbd5e1"), radius: 6pt, inset: 10pt, width: 100%)[',
        '  #text(weight: "bold", size: 10.5pt, fill: rgb("#0f172a"))[Work in Progress and Later Evolution Cost Planning (WIP & Cost Planning)]',
        '  #v(2pt)',
        '  • The table above lists each phase\'s product annual fees at our public catalogue prices; items with no catalogue price are marked "price on request" and carry no amount.',
        '  • If the third phase is on hold, it is only because the first two phases have not passed their checks yet; it does not mean these items do not need doing.',
        ']',
        '',
        '#pagebreak()',
        '',
        '// ================= PAGE 6: ROI & LEGAL SHIELD =================',
        '#text(size: 15pt, weight: "bold", fill: rgb("#0284c7"))[Page 6: Localized ROI Settlement and Digital Asset Ownership]',
        '#v(0.4cm)',
        '',
        '#grid(',
        '  columns: (1fr, 1fr),',
        '  gutter: 14pt,',
        '  rect(fill: rgb("#f0fdf4"), stroke: 1.5pt + rgb("#22c55e"), radius: 8pt, inset: 12pt, width: 100%)[',
        '    #text(weight: "bold", size: 10.5pt, fill: rgb("#15803d"))[Return-on-investment calculation (every assumption listed)]',
        '    #v(4pt)',
        *assumption_lines,
        f'    • Effective hourly rate including employer-side costs: *RM {hourly_rate:,.2f} / hr*\n',
        f'    • *Yearly value of saved work time*: *RM {annual_savings:,.2f}*\n',
        f'    • *Gross margin of enquiries caught after hours*: *RM {salvaged_rev:,.2f}*\n',
        f'    • Total first-year plan cost (sum of the purchase list): - RM {annual_cost:,.2f}\n',
        '    #v(4pt)',
        f'    #text(size: 12pt, weight: "bold", fill: rgb("#166534"))[{_tx(roi_headline)}]',
        '  ],',
        '  rect(fill: rgb("#f8fafc"), stroke: 1.5pt + rgb("#64748b"), radius: 8pt, inset: 12pt, width: 100%)[',
        '    #text(weight: "bold", size: 10.5pt, fill: rgb("#334155"))[Who owns the digital assets]',
        '    #v(4pt)',
        '    • *Domain name and DNS control*:\n',
        '      Registered under your company\'s SSM entity, so neither an outside contractor nor a departed employee can move it on their own; renewals and DNS changes are on record.\n',
        '    • *Website source code and customer data*:\n',
        '      Held on hosting and databases under your own account; at handover an export is all it takes, with no third party holding any of it for you.\n',
        '    • *Company domain email with the three checks*:\n',
        '      Once SPF/DKIM/DMARC are live, fake quotes and invoices sent under your domain name are blocked at the receiver\'s side, ',
        '    so finance no longer has to tell real from fake by eye.',
        '  ]',
        ')',
        '',
        *consultant_block,
        '#v(0.8cm)',
        '#rect(fill: rgb("#0284c7"), radius: 8pt, inset: 12pt, width: 100%)[',
        '  #grid(',
        '    columns: (1fr),',
        '    [',
        f'      #text(fill: white, size: 11pt, weight: "bold")[Direct line to your {_vendor()} digital consultant]',
        '      #v(2pt)',
        '      #text(fill: rgb("#e0f2fe"), size: 8.5pt)[',
        f'        When you submit the contact form, this report goes to the {_vendor()} business support centre together with the evidence list behind every conclusion.\n',
        '        The consultant who calls you will have this page in front of them, so you do not have to explain your business from the start.',
        '      ]',
        '      #v(3pt)',
        f'      #text(fill: white, size: 8.5pt, weight: "bold")[Website: {_vendor_domain()}]',
        '    ]',
        '  )',
        ']',
        "@@AUDIT_APPENDIX@@"
    ]
    markup = "\n".join(lines)
    # 动态区块全部取自本次评估的真实证据与编排结果；缺失即标注未经核验
    for token, body in (
        ("@@PAIN_ROWS@@", "\n".join(_pain_rows_from_evidence(assessment_data))),
        ("@@ROADMAP_BLOCKS@@", "\n".join(_roadmap_blocks(assessment_data))),
        ("@@MILESTONE_ROWS@@", "\n".join(_milestone_rows(assessment_data))),
        ("@@ACCEPTANCE_BLOCKS@@", "\n".join(_acceptance_blocks(assessment_data))),
        ("@@AUDIT_APPENDIX@@", "\n".join(_audit_appendix_blocks(assessment_data))),
    ):
        markup = markup.replace(token, body)
    return markup

def compile_blueprint_pdf(assessment_data: Dict[str, Any], output_pdf_path: Optional[str] = None) -> bytes:
    """
    Compile assessment data to a 6-page institutional PDF blueprint using typst.
    """
    typst_markup = render_typst_markup(assessment_data)
    
    with tempfile.NamedTemporaryFile(suffix=".typ", mode="w", encoding="utf-8", delete=False) as f:
        f.write(typst_markup)
        temp_typ_path = f.name
        
    try:
        if TYPST_AVAILABLE:
            if output_pdf_path:
                typst.compile(temp_typ_path, output=output_pdf_path)
                with open(output_pdf_path, "rb") as pdf_file:
                    return pdf_file.read()
            else:
                pdf_bytes = typst.compile(temp_typ_path)
                return pdf_bytes
        else:
            raise RuntimeError("Typst python package is not installed.")
    finally:
        if os.path.exists(temp_typ_path):
            try:
                os.remove(temp_typ_path)
            except Exception:
                pass
