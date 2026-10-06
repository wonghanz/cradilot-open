"""
Comprehensive Automated Test Suite for Cradilot AI
Validates Mathematical Correctness, readiness gate,
Typst 6-Page PDF Generation, Sales Lead Dispatcher, and FastAPI Endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient

from core.dms_engine import calculate_dms
from core.ars_engine import calculate_ars
from core.roi_engine import calculate_roi
from core.recommendation import generate_pain_points, generate_action_roadmap
from typst_generator.compiler import compile_blueprint_pdf
from sales.lead_dispatcher import LeadDispatcher
from app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dms_calculator_baseline():
    scores = {
        "web_engine_status": "dormant",
        "has_domain": True,
        "has_ssl": False,
        "cloud_storage_status": "single_pc",
        "backup_freq": "never",
        "crm_system": "personal_phone",
        "marketing_tracker": "none",
        "email_type": "free_gmail",
        "ai_automation_status": "manual"
    }
    result = calculate_dms(scores)
    assert 0 <= result["overall_score"] <= 100
    assert result["overall_score"] < 50
    assert "Emerging / vulnerable" in result["tier"]


def test_ars_hard_lock_defense():
    # Case 1: Low DMS (< 40) must trigger hard lock penalty mu = 0.10
    low_dms = 35.0
    payload = {
        "current_tools": ["paper", "whatsapp"],
        "has_sop": False,
        "is_open_to_ai": True
    }
    res_locked = calculate_ars(payload, dms_score=low_dms)
    assert res_locked["is_hard_locked"] is True
    assert res_locked["penalty_factor"] == 0.10
    assert res_locked["final_score"] <= 10.0

    # Case 2: Healthy DMS (> 70) no lock penalty mu = 1.0
    high_dms = 75.0
    res_unlocked = calculate_ars(payload, dms_score=high_dms)
    assert res_unlocked["is_hard_locked"] is False
    assert res_unlocked["penalty_factor"] == 1.0


def test_localized_roi_financial_model():
    # RM 3,000 monthly salary base, 15 wasted hours
    res = calculate_roi(
        saved_hours_per_week=15.0,
        monthly_salary_base=3000.0,
        night_orders_salvaged_per_month=9.6,
        average_order_gross_margin=120.0,
        vendor_annual_cost=5550.68
    )
    # Check effective hourly rate is realistic Malaysian standard (~ RM 20/hr)
    assert 18.0 <= res["effective_hourly_rate"] <= 25.0
    assert res["annual_labor_savings"] > 10000.0
    assert res["annual_salvaged_revenue"] > 10000.0
    assert res["net_gain"] > 15000.0
    assert res["roi_percentage"] > 200.0


def test_typst_6_page_pdf_generation():
    dummy = {
        'metadata': {
            'company_name': 'Automated Test SME',
            'industry': '五金机械',
            'team_size': '10 人',
            'annual_turnover': 'RM 2M',
            'report_id': 'TEST-UNIT-001'
        },
        'dms': {
            'overall_score': 45.0,
            'overall_stars': '★★☆☆☆',
            'tier': '起步脆弱阶段',
            'dimensions': {}
        },
        'ars': {
            'final_score': 6.8,
            'raw_score': 68.0,
            'is_hard_locked': True,
            'penalty_factor': 0.10
        },
        'roi': {
            'net_gain': 20000.0,
            'roi_percentage': 400.0,
            'annual_labor_savings': 8500.0,
            'annual_salvaged_revenue': 12000.0,
            'vendor_annual_cost': 5550.68
        }
    }
    pdf_bytes = compile_blueprint_pdf(dummy)
    assert len(pdf_bytes) > 20000
    assert pdf_bytes[:5] == b"%PDF-"


def test_the_blueprint_prints_factor_and_phase_names_whole():
    """PDF 里不许出现自动断字：五个就绪因子名与三个阶段名必须整词出现。

    Typst 默认开 hyphenate，蓝图又全是窄栏表格，实测会把 "Data availability" 排成
    "Data avail-ability"、"Productivity" 排成 "Pro-ductivity"。这是顾问亲手递到
    老板手上的文件，读起来像坏了。断字一旦被重新打开，这条用例要当场红。
    """
    import io
    import re

    from pypdf import PdfReader

    profile = {
        'company_name': 'Verity Auto Parts Sdn Bhd',
        'industry': 'Auto Parts & Hardware Wholesale',
        'team_size': '6-20 people',
        'annual_turnover': 'RM 500k - 2M',
        'web_engine_status': 'basic_site',
        'dr_backup_status': 'no_backup',
        'uses_personal_email': True,
        'email_type': 'free_gmail',
        'has_ai_agent': False,
        'current_tools': ['sql', 'excel'],
    }
    payload = {
        'metadata': {'company_name': profile['company_name'], 'industry': profile['industry'],
                     'team_size': '6-20 people', 'annual_turnover': 'RM 500k - 2M',
                     'report_id': 'TEST-WHOLEWORD-001'},
        'dms': {'overall_score': 48.0, 'overall_stars': '★★☆☆☆', 'tier': 'Emerging',
                'dimensions': {}},
        'ars': {'final_score': 52.0, 'raw_score': 61.0, 'penalty_factor': 0.85,
                'is_hard_locked': False,
                'sub_scores': {
                    'leadership': {'score': 90.0, 'basis': 'inferred_default',
                                   'reason': 'A growth goal was recorded.'},
                    'data_availability': {'score': 85.0, 'basis': 'inferred_default',
                                          'reason': 'A structured system is already in use.'},
                    'employee_skills': {'score': 55.0, 'basis': 'verified_fact',
                                        'reason': 'No written procedure yet.'},
                    'digital_workflow': {'score': 25.0, 'basis': 'verified_fact',
                                         'reason': 'Quotations go through personal phones.'},
                    'process_maturity': {'score': 55.0, 'basis': 'inferred_default',
                                         'reason': 'Handovers are semi-formal.'},
                }},
        'roi': {},
        'roadmap': generate_action_roadmap(profile, {'overall_score': 48.0}),
    }

    reader = PdfReader(io.BytesIO(compile_blueprint_pdf(payload)))
    text = re.sub(r"\s+", " ", "\n".join((p.extract_text() or "") for p in reader.pages))

    for name in ("Leadership", "Data availability", "Employee skills",
                 "Digital workflow", "Process maturity"):
        assert name in text, f"就绪因子「{name}」在 PDF 里被断字切开了"
    for phase in ("Quick Wins", "Productivity", "Growth"):
        assert phase in text, f"阶段名「{phase}」在 PDF 里被断字切开了"


def test_an_inferred_factor_never_claims_it_was_counted_neutrally():
    """推断出来的 85 分不能写着"没采到、按中性值计入"——那是自己打自己的脸。

    中性不中性写在因子自己的 note 里（ars_engine 已经写了），basis 前缀只说这一分
    是不是客户亲口确认，而且必须与界面 chip 用同一套词（static/js/app.js 的
    You stated / Inferred）——同一轮结果不能在屏幕上是一套话、PDF 里是另一套话。
    这条走 render_typst_markup 拿源码，不付一次 Typst 编译的钱。
    """
    from pathlib import Path

    from typst_generator.compiler import render_typst_markup

    payload = {
        'metadata': {'company_name': 'Uji Dagang Sdn Bhd', 'industry': 'Auto Parts',
                     'team_size': '6-20 people', 'report_id': 'TEST-BASIS-001'},
        'dms': {'overall_score': 48.0, 'overall_stars': '★★☆☆☆', 'tier': 'Emerging',
                'dimensions': {}},
        'ars': {'final_score': 52.0, 'raw_score': 61.0, 'penalty_factor': 0.85,
                'is_hard_locked': False,
                'sub_scores': {
                    'leadership': {'score': 90.0, 'basis': 'inferred_default',
                                   'note': 'A growth goal was recorded, but the intent itself '
                                           'was not verified by a direct question.'},
                    'data_availability': {'score': 85.0, 'basis': 'inferred_default',
                                          'note': 'The tools you listed include a structured '
                                                  'system; whether all records live in it was not '
                                                  'verified.'},
                    'employee_skills': {'score': 55.0, 'basis': 'verified_fact',
                                        'note': 'No hands-on training yet.'},
                    'digital_workflow': {'score': 25.0, 'basis': 'verified_fact',
                                         'note': 'Quotations go through personal phones.'},
                    'process_maturity': {'score': 55.0, 'basis': 'inferred_default',
                                         'note': 'Whether written standards exist was not '
                                                 'collected this time, so it is counted at a '
                                                 'neutral value rather than deducted as missing.'},
                }},
        'roi': {},
    }
    src = render_typst_markup(payload)

    assert "counted neutrally" not in src, "basis 前缀又把推断值说成中性值"
    assert "[You stated]" in src or "You stated:" in src
    assert "Inferred:" in src
    assert "counted at a neutral value" in src, "中性值的说明要留在因子自己的 note 里"

    js = (Path(__file__).parent.parent / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert '"verified_fact" ? "You stated" : "Inferred"' in js, \
        "界面 chip 换了词，PDF 的 basis 用词要跟着对齐，否则两个表面各说一套"


def test_sales_lead_dispatcher(tmp_path):
    """采购车只有一条来源：按已确认事实排出的路线图。"""
    from core.recommendation import generate_action_roadmap

    dispatcher = LeadDispatcher(storage_path=tmp_path / "leads.json")
    roadmap = generate_action_roadmap(
        {"team_size": "6-15 人", "email_type": "free_gmail", "uses_personal_email": True,
         "web_engine_status": "no_site", "dr_backup_status": "no_backup",
         "crm_system": "personal_phone", "has_ai_agent": False},
        {"overall_score": 40.0})
    cart = dispatcher.cart_from_roadmap(roadmap)

    assert len(cart) >= 2
    # 真实产品是 EBiz Mail PRO，以 10 用户为一档；旧 SKU 名在官网查无此物
    assert any("MAIL-PRO" in item.sku for item in cart), [i.sku for i in cart]
    assert any("ACRONIS" in item.sku for item in cart), [i.sku for i in cart]
    assert all(item.regular_price_myr >= 0 for item in cart)

    pain_points = [m for ph in roadmap for m in ph["modules"]][:3]
    talk_track = dispatcher.generate_sales_icebreaker(
        company_name="Unit Test Sdn Bhd",
        industry="汽配",
        dms_score=40.0,
        ars_score=6.0,
        ars_locked=True,
        pain_points=pain_points,
        roi_gain=25000.0,
        roi_pct=450.0
    )
    # 话术里不得出现未经核实就念给客户听的法律与试用承诺。
    # 旧断言反过来要求 "MACC Section 17A" 出现，等于把一句无法核实的法律恐吓固化成规格。
    assert "MACC" not in talk_track
    assert "17A" not in talk_track
    assert "trial" not in talk_track
    assert "40.0" in talk_track          # 真实 DMS 分值必须出现
    assert "hard-lock" in talk_track       # ARS 门禁指引必须保留
    assert "25,000.00" in talk_track     # 有报价时按实际算式引用净收益

    # 报价未定时不得凭空给出金额或百分比
    undecided = dispatcher.generate_sales_icebreaker(
        company_name="Unit Test Sdn Bhd", industry="汽配", dms_score=40.0,
        ars_score=6.0, ars_locked=True, pain_points=pain_points,
        roi_gain=None, roi_pct=None
    )
    assert "ROI" not in undecided or "not giving you an approximate return rate" in undecided
    assert "505" not in undecided and "25,000" not in undecided


def test_fastapi_assess_endpoint(client):
    payload = {
        "company_name": "API Test Sdn Bhd",
        "industry": "跨境贸易",
        "team_size": "15 人",
        "annual_turnover": "RM 3M",
        "has_business_email": False,
        "website_status": "outdated",
        "backup_strategy": "single_pc",
        "crm_status": "personal_whatsapp",
        "after_hours_leak": True
    }
    response = client.post("/api/assess", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "dms" in data
    assert "ars" in data
    assert "roi" in data
    assert "cart" in data
    assert data["ars"]["is_hard_locked"] is True


def test_fastapi_pdf_endpoint(client):
    payload = {
        "metadata": {"company_name": "API PDF Corp"},
        "dms": {"overall_score": 50.0, "overall_stars": "★★★☆☆", "tier": "稳步探索"},
        "ars": {"final_score": 15.0, "is_hard_locked": True, "raw_score": 60.0, "penalty_factor": 0.25},
        "roi": {"net_gain": 22000.0, "roi_percentage": 390.0}
    }
    response = client.post("/api/pdf/generate", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_fastapi_submit_lead_endpoint(client):
    payload = {
        "assessment_data": {
            "metadata": {"company_name": "Lead Test Co"},
            "dms": {"overall_score": 40.0},
            "ars": {"final_score": 6.0, "is_hard_locked": True},
            "roi": {"net_gain": 18000.0, "roi_percentage": 350.0}
        },
        "contact_info": {
            "contact_name": "Mr. Lee",
            "contact_phone": "017-8889999",
            "contact_email": "lee@testco.my"
        }
    }
    response = client.post("/api/sales/submit-lead", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "lead_id" in data
