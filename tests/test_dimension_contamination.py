"""
Cross-Dimension Contamination Regression Tests (阶段三真实性补链)。
锁死行为：回答某一维度探针时，上下文依赖的泛词（"手机"、"熟客"、"下班"）
不得把其它维度误标为已核验，更不得连带写入虚增的失血痛点金额。
所有用例写入临时数据库，不触碰 data/cradilot_wiki.db。
"""

import sqlite3
import pytest

import core.sql_wiki_engine as swe
from core.sql_wiki_engine import SqlWikiEngine


@pytest.fixture
def wiki_tmp(tmp_path, monkeypatch):
    """Point the wiki engine at a throwaway database and bootstrap its schema."""
    db_file = tmp_path / "contamination_test.db"
    monkeypatch.setattr(swe, "DB_PATH", db_file)
    swe.init_wiki_db()
    SqlWikiEngine.create_or_get_dossier(
        session_id="CONTAM-SESS-1",
        company_name="Penang Wholesale Sdn Bhd",
        industry="批发贸易与进出口分销",
        team_size="6-20 人",
        annual_turnover="RM 2M - 10M",
    )
    return db_file


def _dims(nodes):
    return sorted({n["dimension"] for n in nodes})


def _pain_titles(db_file):
    with sqlite3.connect(str(db_file)) as conn:
        rows = conn.execute(
            "SELECT pain_title, financial_loss_myr FROM pain_points_matrix WHERE session_id = 'CONTAM-SESS-1'"
        ).fetchall()
    return rows


def test_web_answer_must_not_lock_crm(wiki_tmp):
    """真实复现场景：回答官网探针时说"手机看会乱"，不得串到 crm 维度。"""
    answer = "我们有旧网站，手机看会乱，证书好像过期了"
    nodes = SqlWikiEngine._fallback_keyword_extraction("CONTAM-SESS-1", answer, "web")

    assert _dims(nodes) == ["web"], f"web 回答串味到其它维度: {_dims(nodes)}"
    assert _dims(nodes) != ["web", "crm"]
    # 关键：crm 的 RM 28,000 痛点不得被虚增写入
    titles = [t for t, _ in _pain_titles(wiki_tmp)]
    assert not any("客户私域资产散落" in t for t in titles), f"虚增 crm 痛点: {titles}"


def test_generic_terms_still_work_when_dimension_is_targeted(wiki_tmp):
    """同一泛词在它就是探针目标时必须生效，防护不能把召回率一并砍掉。"""
    nodes = SqlWikiEngine._fallback_keyword_extraction(
        "CONTAM-SESS-1", "单据都是手写的，手机里也有几张", "crm")
    assert "crm" in _dims(nodes)

    nodes = SqlWikiEngine._fallback_keyword_extraction(
        "CONTAM-SESS-1", "晚上没人回，第二天才看", "ai")
    assert "ai" in _dims(nodes)


def test_unrelated_target_does_not_ingest_weak_terms(wiki_tmp):
    """回答 marketing 探针时提到的"老客户"是背景词，不得反向确认 crm。"""
    nodes = SqlWikiEngine._fallback_keyword_extraction(
        "CONTAM-SESS-1", "都是老客户介绍来的，没做过广告", "marketing")
    dims = _dims(nodes)
    assert "marketing" in dims
    assert "crm" not in dims, f"泛词把 crm 带进来了: {dims}"


def test_high_specificity_terms_still_cross_capture(wiki_tmp):
    """品牌级强词（whatsapp / gmail / 没有备份）仍允许一次回答捕获多维度——这是特性不是串味。"""
    nodes = SqlWikiEngine._fallback_keyword_extraction(
        "CONTAM-SESS-1", "报价用 gmail 发，账没备份，客户都在 whatsapp 里", "web")
    dims = _dims(nodes)
    assert {"cyber", "cloud", "crm"}.issubset(set(dims)), f"多维度捕获失效: {dims}"


def test_ars_weak_terms_not_ingested_from_dms_answers(wiki_tmp):
    """DMS 回答里的"员工""对账"等泛词不得把 ARS 要素标为已核验（Step 3 评分依据必须真实）。"""
    nodes = SqlWikiEngine._fallback_keyword_extraction(
        "CONTAM-SESS-1", "员工每天用手机录单，月底很麻烦", "cloud")
    dims = _dims(nodes)
    assert "employee_skills" not in dims
    assert "digital_workflow" not in dims, f"ARS 要素被泛词点亮: {dims}"
