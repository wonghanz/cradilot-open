"""
菜单式访谈的离线端到端测试。

为什么单独锁这一条：现场演示最怕的不是评分算错，而是 Ollama 起不来时整个访谈
根本走不完。探针本身是固定菜单、选项自带规范取值，因此只要回答来自菜单点击，
采集→锁证→评分→定稿这条链就不该依赖任何模型。

这里把 engine_client 彻底打桩成"永远返回空"，然后只用菜单标题作答，
断言：访谈能走完、证据里没有占位值、每一项取值都等于被选中的那一档。
"""

import pytest

from core.agentic_diagnostic import (
    start_diagnostic_session, process_diagnostic_turn, get_first_agentic_probe,
    finalize_diagnosis_from_wiki, _menu_match, _fact_from_option, _probe_value_domain,
    _probe_options,
    _validate_probe_schema, PROBE_TEMPLATES, DETERMINISTIC_PROBES,
    DEEP_PROBES,
)
from core.sql_wiki_engine import SqlWikiEngine
from llm.engine_client import engine_client


@pytest.fixture(autouse=True)
def _llm_dead(monkeypatch):
    """把本地模型彻底打桩成不可用：本文件任何一条测试都不许偷偷依赖它。"""
    def _dead(*a, **k):
        return ""

    monkeypatch.setattr(engine_client, "generate", _dead)
    monkeypatch.setattr(engine_client, "check_health", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(engine_client, "probe", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(engine_client, "_is_live", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(engine_client, "is_server_reachable", False, raising=False)


# 每题选定的选项序号 → 期望落证取值（选项顺序来自两张题库的合并表）
CHOICE = 1


def _answer_for(dimension: str, index: int = CHOICE):
    bank = (DETERMINISTIC_PROBES.get(dimension) or PROBE_TEMPLATES.get(dimension)
            or DEEP_PROBES.get(dimension) or {})
    options = bank.get("options") or []
    assert options, f"{dimension} 没有可作答的菜单"
    opt = options[min(index, len(options) - 1)]
    return opt["label"], opt["val"]


def test_every_menu_label_translates_to_a_canonical_fact():
    """两张题库对同一维度用了不同词表，这里逐个选项验证都能翻译成功。"""
    failures = []
    for dim in set(list(PROBE_TEMPLATES) + list(DETERMINISTIC_PROBES)):
        bank = DETERMINISTIC_PROBES.get(dim) or PROBE_TEMPLATES.get(dim) or {}
        for opt in bank.get("options") or []:
            got = _menu_match(dim, opt["label"])
            if not got:
                failures.append(f"{dim}/{opt.get('val')} ← 标题无法解析")
            elif got["fact_value"] in ("", "recorded"):
                failures.append(f"{dim}/{opt.get('val')} → 占位值")
    assert not failures, "；".join(failures)


def test_interview_completes_and_scores_without_any_model():
    session = start_diagnostic_session(
        company_name="Syarikat Pemborong Cheong Wei",
        industry="Wholesale Building Materials",
        team_size="6-15 人",
        annual_turnover="RM 1M - 5M",
        biggest_challenge="客户都在业务员手机里",
        growth_objective="开拓线上询价",
    )
    sid = session["session_id"]
    first = get_first_agentic_probe(sid)
    assert first.get("options"), "首题必须给出可点的菜单"

    asked, turns = set(), 0
    probe = first
    while probe and turns < 16:
        dim = probe.get("dimension") or ""
        if dim in asked:
            break
        asked.add(dim)
        answer, expected_val = _answer_for(dim)
        res = process_diagnostic_turn(sid, answer, dim)
        turns += 1
        assert res.get("menu_resolved") is True, f"{dim} 的菜单回答未走确定性采集"
        assert res.get("status") in ("CONTINUE", "DIAGNOSIS_COMPLETE")
        probe = res.get("next_probe") or {}

    assert len(asked) >= 11, f"只问到 {len(asked)} 项：{sorted(asked)}"

    tree = SqlWikiEngine.get_live_wiki_tree(sid)
    values = [ev["fact_value"]
              for d in tree["dimensions"] for ev in d.get("evidence_list", [])]
    assert values, "访谈结束后证据链不应为空"
    # 菜单回答必须落成规范取值，不能留下"听不懂"的占位
    assert "recorded" not in values, values

    done = finalize_diagnosis_from_wiki(sid)
    assert done.get("dms"), "定稿必须给出 DMS"
    assert done["dms"]["overall_score"] > 0
    for name, meta in done["dms"]["dimensions"].items():
        assert meta["score"] > 0, name
        assert meta["evidence_source"] in ("Measured", "You stated", "Inferred"), name
    # 自述而来的维度不得被标成实测
    assert done["dms"]["dimensions"]["cloud"]["evidence_source"] == "You stated"


def test_explicit_menu_answer_survives_a_later_keyword_guess():
    """回归：后来那段回答里偶然出现的关键词会再插一条低置信度同键记录，
    而读取端按 id 取最后一行——老板明确选的那档就被悄悄顶掉了。"""
    sid = start_diagnostic_session(
        company_name="Uji Sentuh Sdn Bhd", industry="Retail", team_size="1-5 人",
        annual_turnover="RM 500k - 2M", biggest_challenge="", growth_objective=""
    )["session_id"]
    label, _ = _answer_for("crm", 2)                      # 明确选"有统一 CRM 系统"
    assert _menu_match("crm", label)["fact_value"] == "formal_crm"
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        sid, label, "crm", menu_fact=_menu_match("crm", label))
    # 下一题的回答里顺口提到 whatsapp —— 属于另一维度，不得改写 crm_status
    SqlWikiEngine.extract_and_sync_wiki_nodes(
        sid, "晚上都是我自己拿 whatsapp 看一眼，第二天再回", "ai",
        menu_fact=_menu_match("ai", _answer_for("ai", 0)[0]))

    rows = [n for d in SqlWikiEngine.get_live_wiki_tree(sid)["dimensions"]
            for n in d.get("evidence_list", []) if n["fact_key"] == "crm_status"]
    assert len(rows) == 1, f"同一 fact_key 出现 {len(rows)} 行，读取端会取到最后一条"
    assert rows[0]["fact_value"] == "formal_crm", rows[0]["fact_value"]
    assert SqlWikiEngine.get_full_assessment_input(sid)["crm_system"] == "formal_crm"


def test_bonus_round_terminates_on_unparseable_answers():
    """深挖题答不上来时必须靠 anchor 收口，否则同一题会被无限重问。"""
    sid = start_diagnostic_session(
        company_name="Uji Hujung Sdn Bhd", industry="Retail", team_size="1-5 人",
        annual_turnover="RM 500k - 2M", biggest_challenge="", growth_objective=""
    )["session_id"]
    probe = get_first_agentic_probe(sid)
    asked, seen_twice = [], []
    for _ in range(30):
        dim = (probe or {}).get("dimension")
        assert dim, "题序不应提前断裂"
        if dim in asked:
            seen_twice.append(dim)
            break
        asked.append(dim)
        res = process_diagnostic_turn(sid, "嗯…这个我不太清楚，反正就那样啦", dim)
        probe = res.get("next_probe") or {}
        if res.get("status") == "DIAGNOSIS_COMPLETE":
            break
    assert not seen_twice, f"同一题被重复提问：{seen_twice}"
    assert len(asked) <= 20, f"未在有限轮次内收口：{asked}"
    done = finalize_diagnosis_from_wiki(sid)
    assert done["dms"]["overall_score"] > 0
    # 听不懂的回答不得变成负面事实
    values = [ev["fact_value"] for d in
              SqlWikiEngine.get_live_wiki_tree(sid)["dimensions"]
              for ev in d.get("evidence_list", [])]
    assert "recorded" in values, "未采到的答案应记为占位而非具体档位"
    from core.dms_engine import calculate_dms
    crm_score = calculate_dms(SqlWikiEngine.get_full_assessment_input(sid))["dimensions"]["crm"]["score"]
    assert crm_score >= 40.0, f"占位值不得被评分层读成「没有 CRM」：{crm_score}"


def test_menu_answer_lands_the_exact_tier_not_a_default():
    """分别点"无备份/网盘/企业云备份"，cloud 必须给出三个不同的分，而不是恒等。"""
    from core.dms_engine import calculate_dms
    scores = {}
    for idx, expect in ((0, "single_pc"), (1, "manual_usb"), (2, "cloud_auto")):
        label, val = _answer_for("cloud", idx)
        got = _menu_match("cloud", label)
        assert got and got["fact_key"] == "backup_strategy"
        assert got["fact_value"] == expect, f"{label} → {got}"
        scores[expect] = calculate_dms({"backup_strategy": got["fact_value"]})["dimensions"]["cloud"]["score"]
    assert len(set(scores.values())) == 3, f"三档撞成同一个分：{scores}"


# ─── 点选即事实：措辞由模型写，取值必须规范 ──────────────────────────────────

def test_clicked_option_locks_its_fact_whatever_the_wording_is():
    """回归：模型自己写的选项标题（不在任何题库里）此前一律解析失败，
    于是"用户明确选了一档"最后被评分层读成"未作答"。"""
    made_up_label = "已实施部分云盘同步与人工文档管理"
    assert _menu_match("cloud", made_up_label) is None, "标题解析本就不该命中这句自造措辞"

    got = _fact_from_option("cloud", {"val": "manual_usb", "label": made_up_label})
    assert got == {"fact_key": "backup_strategy", "fact_value": "manual_usb",
                   "quote": made_up_label}, got


def test_clicked_option_with_an_unknown_val_is_refused_not_guessed():
    # 模型爱用的 "vulnerable/transition/mature" 不在任何维度词表里，不能当成已知档位入账
    assert _fact_from_option("cloud", {"val": "vulnerable", "label": "随便"}) is None
    assert _fact_from_option("crm", {"val": "mature", "label": "随便"}) is None
    assert _fact_from_option("nonsense_dim", {"val": "none", "label": "x"}) is None
    assert _fact_from_option("cloud", {"label": "没有 val 的选项"}) is None


def test_deep_probe_option_locks_its_own_fact_key():
    spec = DEEP_PROBES["crm_pipeline_visible"]
    opt = spec["options"][2]
    got = _fact_from_option("crm_pipeline_visible", {"val": opt["val"], "label": "看板实时"})
    # fact_key 只取自题面设定，绝不采信客户端传来的键名
    assert got["fact_key"] == spec["options"][0]["fact_key"], got
    assert got["fact_value"] == opt["val"], got


def test_probe_schema_rejects_invented_option_values():
    ok, _ = _validate_probe_schema(
        {"question": "贵司的客户资料现在存在哪里？", "options": [
            {"label": "A", "sub": "", "val": "single_pc"},
            {"label": "B", "sub": "", "val": "cloud_auto"}]}, "cloud")
    assert ok

    bad, msg = _validate_probe_schema(
        {"question": "贵司的客户资料现在存在哪里？", "options": [
            {"label": "A", "sub": "", "val": "vulnerable"},
            {"label": "B", "sub": "", "val": "mature"}]}, "cloud")
    assert not bad and "single_pc" in msg, msg


def test_every_scored_dimension_publishes_a_value_domain():
    """取值表同时是提示词的约束和点选的解释依据，空表意味着该维度的点击无法入账。"""
    dims = set(list(PROBE_TEMPLATES) + list(DETERMINISTIC_PROBES)) | set(DEEP_PROBES)
    empty = [d for d in dims if not _probe_value_domain(d)]
    assert not empty, f"这些维度没有规范取值表：{sorted(empty)}"


def test_turn_prefers_the_clicked_option_end_to_end():
    sid = start_diagnostic_session(
        company_name="Uji Klik Sdn Bhd", industry="Retail", team_size="1-5 人",
        annual_turnover="RM 500k - 2M", biggest_challenge="", growth_objective=""
    )["session_id"]
    res = process_diagnostic_turn(
        sid, "模型自己写的措辞，题库里查不到", "cloud",
        selected_option={"val": "single_pc", "label": "模型自己写的措辞，题库里查不到"})
    assert res.get("menu_resolved") is True
    rows = [n for d in SqlWikiEngine.get_live_wiki_tree(sid)["dimensions"]
            for n in d.get("evidence_list", []) if n["fact_key"] == "backup_strategy"]
    assert rows and rows[-1]["fact_value"] == "single_pc", rows


def test_clicked_ai_tier_reaches_the_score():
    """回归：探针把 ai_tier 写进了证据链，但读取端从来不看它——
    它只用"夜间是否漏单"这个关键词代理反推，于是明确选了档位仍按 30 分的未答档计分。"""
    from core.dms_engine import calculate_dms

    scores = {}
    ladder = _probe_value_domain("ai")            # 每个档位一条，已按脆弱→成熟排列
    assert [r for r, _ in ladder] == ["leak", "partial", "covered"], ladder
    for rung_val, expect in zip(["leak", "partial", "covered"],
                                ["none", "individual_use", "deployed"]):
        sid = start_diagnostic_session(
            company_name="Uji AI Sdn Bhd", industry="Retail", team_size="1-5 人",
            annual_turnover="RM 500k - 2M", biggest_challenge="", growth_objective=""
        )["session_id"]
        opt = next(o for o in _probe_options("ai") if str(o["val"]).lower() == rung_val)
        process_diagnostic_turn(sid, opt["label"], "ai", selected_option=dict(opt))
        assessment = SqlWikiEngine.get_full_assessment_input(sid)
        assert assessment["ai_tier"] == expect, (rung_val, assessment.get("ai_tier"))
        # 明确选过档位后，关键词代理不得再把它抬成别的档
        assert assessment["has_ai_agent"] is None
        scores[expect] = calculate_dms(assessment)["dimensions"]["ai_adoption"]["score"]

    assert len(set(scores.values())) == 3, f"三档 AI 撞成同一个分：{scores}"
