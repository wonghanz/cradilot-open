"""
多方案比较层契约测试（简报第 4-5 页 "Here's the exciting part"）。

简报要的不是"推荐一个产品"，而是同一道题把真实备选摆在一起并解释为什么。
这里锁死四件事：
  1. 邮箱题与网站题必须各自给出"选中的那条 + 比较过却没买的其余几条"，
     每一条带目录实价与一句人话理由；
  2. 只有选中的那条进 budget_lines / budget_myr / 采购车，备选的价格一律不算钱；
  3. 目录查不到年价的只能显示"needs a quote"，不许出现数字；本公司不卖的平台不许有价；
  4. 阶段标题与回报周期照简报原文（Quick Wins ROI 2-4 weeks / Productivity / Growth）。

判据一律由 generate_action_roadmap 的真实入参与 core.product_catalog 的实价驱动，
不 mock 目录；只有"价格判据会不会翻"这一条用纯函数的入参直接喂数，验的是规则本身。
"""

import io
import json
import re

import pytest
from pypdf import PdfReader

from core.product_catalog import catalog
from core.recommendation import _decide_email, _option_row, generate_action_roadmap
from sales.lead_dispatcher import LeadDispatcher
from typst_generator.compiler import compile_blueprint_pdf

# 一家典型待补强的小微：没有官网、账套单机、报价走个人邮箱
FRAGILE = {
    "company_name": "Uji Dagang Sdn Bhd",
    "industry": "Auto Parts & Hardware Wholesale",
    "team_size": "21-50 people",
    "annual_turnover": "RM 2M - 10M",
    "web_engine_status": "no_site",
    "dr_backup_status": "no_backup",
    "uses_personal_email": True,
    "email_type": "free_gmail",
    "has_ai_agent": False,
    "current_tools": ["paper", "whatsapp"],
}


def _plan(**overrides):
    data = dict(FRAGILE)
    data.update(overrides)
    return generate_action_roadmap(data, {"overall_score": 62.0})


def _block(roadmap, task_id):
    for phase in roadmap:
        for block in phase.get("option_matrix") or []:
            if block.get("task_id") == task_id:
                return block
    raise AssertionError(f"phase dict carries no option block for {task_id}: "
                         f"{[p.get('option_matrix') for p in roadmap]}")


def _phase_skus(phase):
    return {line["sku"] for line in phase["budget_lines"]} | {
        line["sku"] for line in phase["pricing_pending_lines"]}


# ── 1. 比较块本身 ─────────────────────────────────────────────────────────────

def test_a_five_person_team_is_not_sold_a_dearer_block_and_still_sees_it():
    """5 个人不卖 10 只邮箱：整档更贵就选每席计价那款，但 本公司自营档必须一起出现，
    并写明它从几个人起反而更省——便宜与否由目录算，不由厂商是谁算。"""
    email = _block(_plan(team_size="5-9 people"), "T1")
    assert email["chosen"]["sku"] == "DEMO-GWS-STARTER"
    assert email["chosen"]["annual_myr"] == pytest.approx(155.88 * 5)
    assert email["chosen"]["in_cart"] is True
    assert "Chosen" in email["chosen"]["why"]

    rivals = {row["sku"]: row for row in email["also_considered"]}
    assert set(rivals) == {"DEMO-MAIL-PRO-10U", "DEMO-M365-BASIC"}, rivals
    assert rivals["DEMO-MAIL-PRO-10U"]["annual_myr"] == pytest.approx(831.60)
    for row in rivals.values():
        assert row["in_cart"] is False and row["purchasable"] is True
        assert row["why_not"] and row["price_label"].endswith("a year")
    assert "from 6 people up it becomes the cheaper bill" in rivals["DEMO-MAIL-PRO-10U"]["why_not"]


def test_a_six_plus_team_picks_the_block_on_price_alone():
    """同一道题在 6 席以上自己翻回自有档：判据里没有写死的席位区间。"""
    email = _block(_plan(team_size="6-15 people"), "T1")
    assert email["chosen"]["sku"] == "DEMO-MAIL-PRO-10U"
    assert email["chosen"]["annual_myr"] == pytest.approx(831.60)
    assert email["chosen"]["in_cart"] is True
    assert "935.28" in json.dumps(email["also_considered"], ensure_ascii=False)


def test_twenty_five_seats_are_compared_on_the_catalogues_own_totals():
    """简报例子说"10 人以上每席计价更省"——目录里不是这样，引擎只认目录。

    Mail PRO 按 10 用户一档卖、不足一档按一档计（tests/test_site_audit.py 已锁 21 席
    = RM 2,494.80），25 席是 3 档 RM 2,494.80，仍低于 Google 的 25 x RM 155.88
    = RM 3,897.00 与 Microsoft 的 RM 4,497.00，所以这道题上没有被翻转的余地：
    翻不翻由价格算出来，不是由例子写死。
    """
    seats = 25
    email = _block(_plan(team_size="25-40 people"), "T1")
    assert email["facts_used"]["seats"] == seats
    assert catalog.annual_for("DEMO-MAIL-PRO-10U", seats=seats) == pytest.approx(2494.80)
    assert catalog.annual_for("DEMO-GWS-STARTER", seats=seats) == pytest.approx(3897.00)
    assert catalog.annual_for("DEMO-M365-BASIC", seats=seats) == pytest.approx(4497.00)

    totals = {email["chosen"]["sku"]: email["chosen"]["annual_myr"]}
    totals.update({r["sku"]: r["annual_myr"] for r in email["also_considered"]})
    assert email["chosen"]["sku"] == min(totals, key=lambda sku: totals[sku])
    assert "2,494.80" in json.dumps(email, ensure_ascii=False)
    assert "3,897.00" in json.dumps(email["also_considered"], ensure_ascii=False)


def test_the_price_rule_flips_when_the_catalogue_actually_says_so():
    """价格判据是真会翻的：把更低的每席总价喂进同一条判据，推荐就得跟着换。"""
    rows = {
        "DEMO-MAIL-PRO-10U": {"annual_myr": 2494.80},
        "DEMO-GWS-STARTER": {"annual_myr": 1900.00},
        "DEMO-M365-BASIC": {"annual_myr": 2200.00},
    }
    chosen, reasons, basis = _decide_email(25, {"current_tools": []}, rows)
    assert chosen == "DEMO-GWS-STARTER", "每席总价更低时还不翻，说明判据是写死的结论而不是算出来的"
    assert "1,900.00" in reasons[chosen]
    assert "2,494.80" in reasons["DEMO-MAIL-PRO-10U"]
    assert "annual totals" in basis


def test_a_recorded_microsoft_fact_flips_the_email_pick_and_the_price_follows():
    """判据一是事实：客户答过在用 Microsoft，就选 M365，而且进合计的也得是它。"""
    roadmap = _plan(team_size="6-15 people", current_tools=["whatsapp", "Microsoft Teams"])
    email = _block(roadmap, "T1")
    assert email["chosen"]["sku"] == "DEMO-M365-BASIC"
    assert email["chosen"]["annual_myr"] == pytest.approx(179.88 * 6)
    assert "Microsoft Teams" in email["chosen"]["why"]
    assert "DEMO-MAIL-PRO-10U" in {row["sku"] for row in email["also_considered"]}

    priced = [line["sku"] for line in roadmap[0]["budget_lines"]]
    assert "DEMO-M365-BASIC" in priced and "DEMO-MAIL-PRO-10U" not in priced, priced


def test_a_missing_fact_is_stated_as_missing_instead_of_being_invented():
    """没问过的项不许替客户补前提：Microsoft 那条要说"本次没记录"，备份台数要说"没问过"。"""
    roadmap = _plan(team_size="6-15 people")
    email = _block(roadmap, "T1")
    m365 = next(r for r in email["also_considered"] if r["sku"] == "DEMO-M365-BASIC")
    assert "no Microsoft tool" in m365["why_not"]
    assert "no Microsoft tool" in email["facts_used"]["microsoft_tooling"]

    backup = _block(roadmap, "T3")
    assert backup["chosen"]["sku"] == "DEMO-ACRONIS-WKS"
    assert backup["chosen"]["annual_myr"] is None, "几台没问过，就不许给出总价"
    assert backup["chosen"]["price_state"] == "unit_needs_count"
    assert "number of machines" in backup["chosen"]["price_label"]
    srv = next(r for r in backup["also_considered"] if r["sku"] == "DEMO-ACRONIS-SRV")
    assert srv["annual_myr"] == pytest.approx(4595.88) and srv["in_cart"] is False
    assert "nothing recorded this run" in srv["why_not"]
    assert "not collected" in backup["decision_basis"]


# ── 2. 网站题 ─────────────────────────────────────────────────────────────────

def test_a_retail_business_is_compared_against_the_store_package():
    """简报第 5 页那句 "depending on business"：零售要收款能力，批发不用。"""
    retail = _block(_plan(industry="Retail & Multi-store Chain", team_size="6-15 people"), "T2")
    assert retail["chosen"]["sku"] == "DEMO-ECOM-STANDARD"
    assert retail["chosen"]["annual_myr"] == pytest.approx(3099.00)
    assert "the industry you filed" in retail["decision_basis"]
    assert "DEMO-WP17-BUSINESS" in {r["sku"] for r in retail["also_considered"]}

    wholesale = _block(_plan(industry="Wholesale & Distribution", team_size="6-15 people"), "T2")
    assert wholesale["chosen"]["sku"] == "DEMO-WP17-BUSINESS"
    ecom = next(r for r in wholesale["also_considered"] if r["sku"] == "DEMO-ECOM-STANDARD")
    assert ecom["annual_myr"] == pytest.approx(3099.00) and ecom["in_cart"] is False
    assert "3,099.00" in ecom["why_not"]


def test_a_three_person_trade_with_no_site_at_all_gets_the_starter_tier():
    """5 人以下且事实是"根本没有官网"：RM 263.88 够用，多花的钱没有事实支撑。"""
    web = _block(_plan(team_size="3-6 people"), "T2")
    assert web["chosen"]["sku"] == "DEMO-WP17-BEGINNER"
    assert web["chosen"]["annual_myr"] == pytest.approx(263.88)
    assert "DEMO-WP17-BUSINESS" in {r["sku"] for r in web["also_considered"]}
    assert "264" in json.dumps(web["also_considered"], ensure_ascii=False) or \
           "527.88" in json.dumps(web["also_considered"], ensure_ascii=False)


def test_the_unpriced_option_reads_needs_a_quote_and_never_a_number():
    """Instant Website 没有公开年价：只能显示"待报价"，价格串里一个数字都不许有。"""
    web = _block(_plan(team_size="6-15 people"), "T2")
    iwb = next(r for r in web["also_considered"] if r["sku"] == "DEMO-IWB-STARTER")
    assert iwb["annual_myr"] is None
    assert iwb["price_state"] == "no_public_price"
    assert iwb["price_label"] == "Needs a quote from our catalogue"
    assert not re.search(r"\d", iwb["price_label"]), iwb["price_label"]
    assert "RM" not in iwb["price_label"]
    assert iwb["in_cart"] is False
    # 更要紧的是：这条也进不了预算与采购车
    roadmap = _plan(team_size="6-15 people")
    assert "DEMO-IWB-STARTER" not in _phase_skus(roadmap[0])
    assert "DEMO-IWB-STARTER" not in {i.sku for i in LeadDispatcher().cart_from_roadmap(roadmap)}


def test_magento_and_shopify_are_compared_by_name_and_priced_as_nothing():
    """简报点了名、本公司不卖的两个平台：只以"不卖"的身份出现，没有 SKU、没有价钱。"""
    roadmap = _plan(team_size="6-15 people")
    web = _block(roadmap, "T2")
    not_sold = [r for r in web["also_considered"] if not r["purchasable"]]
    assert {r["product_name"] for r in not_sold} == {"Magento", "Shopify"}
    for row in not_sold:
        assert row["sku"] is None
        assert row["annual_myr"] is None
        assert row["price_label"] == "we do not sell this"
        assert not re.search(r"RM \d", row["price_label"] + row["why_not"])
        assert row["in_cart"] is False

    notes = " ".join(roadmap[0]["third_party_notes"])
    assert "Magento" in notes and "Shopify" in notes and "do not sell" in notes
    blob = json.dumps(roadmap[0]["budget_lines"] + roadmap[0]["pricing_pending_lines"]) + \
        json.dumps([i.sku for i in LeadDispatcher().cart_from_roadmap(roadmap)])
    for platform in ("Magento", "Shopify"):
        assert platform not in blob, f"{platform} 变成了可采购的一行"


# ── 3. 钱只有一条路 ───────────────────────────────────────────────────────────

def test_no_alternative_price_ever_reaches_the_phase_total():
    """比较层的红线：备选一条都不能进 budget_lines、budget_myr 或采购车。"""
    for team_size in ("1-5 people", "5-9 people", "6-15 people", "21-50 people"):
        roadmap = _plan(team_size=team_size, industry="Retail & Multi-store Chain")
        for phase in roadmap:
            priced = _phase_skus(phase)
            for block in phase["option_matrix"]:
                assert block["chosen"]["sku"] in priced, block["chosen"]["sku"]
                for row in block["also_considered"]:
                    if row["sku"]:
                        assert row["sku"] not in priced, (row["sku"], priced)
                    assert row["in_cart"] is False
            assert float(phase["budget_myr"]) == round(
                sum(l["annual_myr"] or 0.0 for l in phase["budget_lines"]), 2)
            if phase["option_matrix"]:
                assert phase["option_matrix_note"], "有比较块却没有说明这表算什么"
            else:
                assert phase["option_matrix_note"] == ""

        cart_skus = {i.sku for i in LeadDispatcher().cart_from_roadmap(roadmap)}
        alternatives = {row["sku"] for ph in roadmap for b in ph["option_matrix"]
                        for row in b["also_considered"] if row["sku"]}
        assert not (cart_skus & alternatives), cart_skus & alternatives


def test_only_the_chosen_option_is_priced_even_when_the_chosen_option_changes():
    """翻转必须带着价钱一起翻：选了谁，budget_lines 里就只有谁。"""
    fixed = _plan(team_size="6-15 people")
    flipped = _plan(team_size="6-15 people", email_type="outlook_business",
                    current_tools=["outlook"])
    assert _block(fixed, "T1")["chosen"]["sku"] == "DEMO-MAIL-PRO-10U"
    assert _block(flipped, "T1")["chosen"]["sku"] == "DEMO-M365-BASIC"
    assert _phase_skus(flipped[0]).isdisjoint({"DEMO-MAIL-PRO-10U"})
    assert round(sum(l["annual_myr"] or 0.0 for l in flipped[0]["budget_lines"]), 2) == \
        float(flipped[0]["budget_myr"])


def test_untouched_pricing_keys_stay_untouched():
    """budget_lines 的行形状与 pricing_pending 的措辞是界面与 PDF 在读的，不许漂移。"""
    phase = _plan(team_size="6-15 people")[0]
    for line in phase["budget_lines"]:
        assert set(("sku", "product_name", "annual_myr", "verify_status", "why")).issubset(line)
    assert any("billed on the actual number of devices" in p for p in phase["pricing_pending"])
    assert all(l["annual_myr"] is None for l in phase["pricing_pending_lines"])


# ── 4. 阶段名与回报周期照简报原文 ─────────────────────────────────────────────

def test_phase_titles_and_roi_window_are_the_briefs_own_words():
    roadmap = _plan()
    titles = [ph["phase_title"] for ph in roadmap]
    assert "Quick Wins" in titles[0], titles
    assert "Productivity" in titles[1], titles
    assert "Growth" in titles[2], titles
    assert titles[0].startswith("Phase 1 · Quick Wins")
    assert roadmap[0]["timeline"] == "2-4 weeks", roadmap[0]["timeline"]
    assert roadmap[1]["timeline"] == "Months 3 - 6"
    assert roadmap[2]["timeline"] == "Months 6 - 12"
    # 简报 Bonus 2 另有一套实施时间线（Month 1-3 → 3-6 → 6-12）。第 1 阶段那一格
    # 与 ROI 的"2-4 weeks"本来就对不上，所以两套口径各自存一份、各自印一处。
    assert [ph["months"] for ph in roadmap] == ["Month 1 - 3", "Month 3 - 6", "Month 6 - 12"]
    page = re.sub(r"\s+", " ", _pdf_text(roadmap))
    for window in ("Month 1 - 3", "Month 3 - 6", "Month 6 - 12"):
        assert window in page, f"实施时间线少了 {window}"


def test_an_idle_phase_publishes_an_empty_comparison_not_a_missing_key():
    """六维达标的企业：比较层不能替它编出备选来。"""
    healthy = {"company_name": "Pinnacle Trading Sdn Bhd", "industry": "Wholesale & Distribution",
               "team_size": "21-50 people", "web_engine_status": "standard", "has_domain": True,
               "has_ssl": True, "dr_backup_status": "managed_cloud", "crm_system": "formal_crm",
               "uses_personal_email": False, "email_type": "business_domain",
               "marketing_tracker": "pixel_and_ga4", "has_ai_agent": True,
               "has_sop": True, "order_reconcile_flow": "auto", "employee_skill_level": "high",
               "current_tools": ["crm", "sql", "website", "cloud", "enterprise_email"]}
    for phase in generate_action_roadmap(healthy, {"overall_score": 92.0}):
        assert phase["option_matrix"] == []
        assert phase["option_matrix_note"] == ""
        assert float(phase["budget_myr"]) == 0.0 and phase["budget_lines"] == []


def test_comparison_copy_is_plain_english_for_the_customer():
    """比较块直接进客户屏幕与 PDF：中文与治理黑话都不许出现在这里。"""
    blob = json.dumps(_plan(team_size="21-50 people"), ensure_ascii=False)
    assert not re.search(r"[\u4e00-\u9fff]", blob)
    for jargon in ("Form A2", "MACC", "17A", "硬锁", "主权", "锁证", "止血", "verified_fact"):
        assert jargon not in blob, jargon


# ── 5. PDF 渲染 ───────────────────────────────────────────────────────────────

def _render(roadmap):
    payload = {
        "metadata": {"company_name": FRAGILE["company_name"], "industry": FRAGILE["industry"],
                     "team_size": "21-50 people", "annual_turnover": "RM 2M - 10M",
                     "report_id": "TEST-OPTIONS-001", "date": "2026-09-20"},
        "dms": {"overall_score": 28.0, "overall_stars": "★★☆☆☆", "tier_label": "Emerging",
                "dimensions": {}},
        "ars": {"final_score": 60.0, "raw_score": 60.0, "penalty_factor": 1.0,
                "is_hard_locked": False},
        "roi": {},
        "roadmap": roadmap,
    }
    pdf_bytes = compile_blueprint_pdf(payload)
    assert pdf_bytes[:5] == b"%PDF-"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages), len(reader.pages)


def _pdf_text(roadmap):
    return _render(roadmap)[0]


def test_the_comparison_section_does_not_blow_up_the_blueprint():
    """篇幅守卫：同一份方案去掉比较段是 8 页（模板自称 6 页，早就不止了），加上是 9 页。

    多出来的一页就是简报要的"把备选摆出来"，可以接受；再往上撑就是排版问题，
    这条用例负责把它拦下来，而不是让人眼翻 PDF 才发现。
    """
    _, pages = _render(_plan(team_size="5-9 people"))
    assert pages <= 9, f"多方案比较把蓝图撑到 {pages} 页，得压缩排版"


def test_the_milestone_table_shows_only_the_short_phase_name():
    """第 4 页那一栏只有 2.8cm：标题带破折号从句与旧的冒号写法都得切成短标签。"""
    from typst_generator.compiler import _phase_label

    roadmap = _plan(team_size="5-9 people")
    assert _phase_label(roadmap[0], "Phase 1") == "Phase 1 · Quick Wins"
    assert _phase_label({"phase_title": "Phase 1: first secure the storefront"}, "x") == "Phase 1"
    assert _phase_label({}, "Phase 2") == "Phase 2"
    text = _pdf_text(roadmap)
    assert "Phase 1 · Quick Wins" in text


def test_the_pdf_prints_the_comparison_under_the_phase_it_belongs_to():
    text = _pdf_text(_plan(team_size="5-9 people"))
    assert "Options we compared" in text
    assert "Where should your company email live?" in text
    assert "Compared, not purchased" in text
    assert "EBiz Mail PRO" in text
    assert "ROI 2-4 weeks" in text
    # 每一行只标一次身份：引导词不能连着产品名再印一遍。
    # 5 个人时 chosen 是每席计价那款，本公司整档作为"比较过、没买"的一行出现。
    assert "Chosen: Google Workspace" in text and "total. Chosen:" not in text
    assert "Compared, not purchased: EBiz Mail PRO" in text
    # 进了合计的才说"在合计里"；算不出金额的那条要说"以报价为准"，
    # 否则这句话与它下面那行 pricing_pending 自相矛盾。
    # （PDF 里 phase's 的撇号是排版体，所以只取产品名后面一小段来判。）
    seg = re.sub(r"\s+", " ", text)
    email_line = re.search(r"Chosen: Google Workspace.{0,120}", seg)
    assert email_line and "total" in email_line.group(0), "算得出金额的 chosen 要说它在合计里"
    ai_page = re.sub(r"\s+", " ", _pdf_text(_plan(has_ai_agent=False, after_hours_leak=True)))
    assert "priced on the quote rather than added to the total" in ai_page, "算不出金额的要说以报价为准"


def test_the_pdf_says_plainly_what_vendor_does_not_sell():
    text = _pdf_text(_plan(team_size="5-9 people"))
    assert "What we do not sell here" in text
    assert "Compared, not sold here" in text
    assert "Magento" in text and "Shopify" in text
    assert "Needs a quote" in text


def test_user_text_with_typst_breakers_still_compiles():
    """动态文案一律走 _tx：{ } $ 这三个字符以前能把整份 PDF 打断。"""
    roadmap = _plan(team_size="5-9 people")
    roadmap[0]["option_matrix"][0]["chosen"]["why"] = "weird {markup} $math #hash [bracket]"
    text = _pdf_text(roadmap)
    assert "Options we compared" in text


def test_legacy_phase_dicts_without_the_new_keys_still_render():
    """界面与旧会话可能送来没有比较块的阶段数据，PDF 不许因此开不了。"""
    roadmap = _plan(team_size="5-9 people")
    for ph in roadmap:
        ph.pop("option_matrix", None)
        ph.pop("option_matrix_note", None)
        ph["phase_title"] = "Phase 1: old colon style title"
    assert "Options we compared" not in _pdf_text(roadmap)


# ── 6. 第 2、3 阶段的比较块（简报把 CRM 与 AI 写在这两阶段里）──────────────────

def _phase_with(roadmap, task_id):
    """找出装着某个比较块的那个阶段。"""
    for phase in roadmap:
        for block in phase.get("option_matrix") or []:
            if block.get("task_id") == task_id:
                return phase
    raise AssertionError(f"no phase carries a comparison block for {task_id}")


def test_the_crm_question_recommends_a_product_we_cannot_sell_and_bills_nothing():
    """本公司没有自营 CRM：这一题要把"我们卖不了"说成结论，而不是拿邮箱补位。"""
    roadmap = _plan(crm_system="spreadsheet")
    block = _block(roadmap, "T4")
    phase2 = _phase_with(roadmap, "T4")

    assert block["purchase"] is False
    assert block["chosen"]["sku"] is None
    assert "CRM" in block["chosen"]["product_name"]
    assert "we cannot sell it to you" in block["chosen"]["why"]
    # 第 1 阶段已经收过的那条邮箱，不能在这一题里再收一次
    mail = next(a for a in block["also_considered"] if a.get("sku") == "DEMO-MAIL-PRO-10U")
    assert "bill it to you twice" in mail["why_not"]
    assert mail["in_cart"] is False
    assert "DEMO-MAIL-PRO-10U" not in [line["sku"] for line in phase2["budget_lines"]]


def test_the_seo_retainer_is_refused_while_the_ad_budget_is_smaller_than_it():
    """全目录最贵的一条由客户自报的广告预算决定，不是一律往上推。"""
    small = _plan(team_size="21-50 people", marketing_tracker="untracked", marketing_spend="1k_5k")
    block = _block(small, "T9")
    phase3 = _phase_with(small, "T9")
    assert block["purchase"] is False
    assert block["chosen"]["sku"] is None
    refused = next(a for a in block["also_considered"] if a.get("sku") == "DEMO-SEO-STANDARD")
    assert "27,456" in refused["why_not"]
    amounts_small = [line["annual_myr"] for line in phase3["budget_lines"]]
    assert 27456.0 not in amounts_small

    big = _plan(team_size="21-50 people", marketing_tracker="untracked", marketing_spend="over_5k")
    block_big = _block(big, "T9")
    amounts_big = [line["annual_myr"] for line in _phase_with(big, "T9")["budget_lines"]]
    assert block_big["purchase"] is True
    assert block_big["chosen"]["sku"] == "DEMO-SEO-STANDARD"
    assert 27456.0 in amounts_big


def test_the_ai_line_names_the_agent_without_inventing_a_price():
    """目录里没有 AI agent 的公开年价，就不许在比较块里长出一个数来。"""
    roadmap = _plan(has_ai_agent=False, after_hours_leak=True)
    block = _block(roadmap, "T8")
    assert block["chosen"]["sku"] == "DEMO-AI-AGENT"
    assert block["chosen"]["annual_myr"] is None
    assert "quote" in block["chosen"]["price_label"].lower()
    assert "quote you once honestly" in block["chosen"]["why"]
    blob = json.dumps(block, ensure_ascii=False)
    assert blob.count("Needs a quote from our catalogue") == 1, "价格标签印了两遍，说明句子自己又复述了一次"
    assert "RM " not in json.dumps(block["also_considered"], ensure_ascii=False)


def test_a_semi_digital_flow_keeps_its_task_and_gets_a_real_two_way_choice():
    """部分在线、月底仍要人工对：既是 ARS 的中间档，也是第 2 阶段的真缺口。"""
    roadmap = _plan(order_reconcile_flow="semi", web_engine_status="standard")
    block = _block(roadmap, "T5")
    offered = set([block["chosen"]["sku"]] + [a["sku"] for a in block["also_considered"]])
    assert offered == {"DEMO-VPS-C1", "DEMO-EBIZ17-AIPRO"}
    assert block["chosen"]["sku"] == "DEMO-VPS-C1"

    no_site = _plan(order_reconcile_flow="semi", web_engine_status="no_site")
    assert _block(no_site, "T5")["chosen"]["sku"] == "DEMO-EBIZ17-AIPRO"


def test_the_pdf_says_a_recommendation_we_cannot_sell_is_not_in_the_bill():
    plan = _plan(crm_system="spreadsheet", marketing_tracker="untracked", marketing_spend="1k_5k")
    # 比较块是长句，Typst 会在列宽处换行：按原文比对只有短语能命中
    text = re.sub(r"\s+", " ", _pdf_text(plan))
    assert "We recommend: A dedicated CRM" in text
    assert "not in our bill" in text
    assert "Compared, and nothing to buy" in text
    assert "Stay on the shared spreadsheet" in text
