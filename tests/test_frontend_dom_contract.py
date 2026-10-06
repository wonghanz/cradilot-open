"""前端 DOM 契约测试。

第 2 步的教训：HTML 删掉了五块写死的瓷片，JS 却还在往 statHttpCode 里写值——
两边都"没报错"，界面却永远空白。这类漂移必须被机器守住，不能靠人眼对。
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

HTML_IDS = set(re.findall(r'id="([A-Za-z0-9_\-]+)"', HTML))

# JS 引用的字面 id：$("x") / getElementById("x") / querySelector("#x")
_JS_REFS = re.findall(r'\$\("([^"$]+)"\)', JS) + \
    re.findall(r'getElementById\("([^"]+)"\)', JS) + \
    re.findall(r'querySelector(?:All)?\("#([A-Za-z0-9_\-]+)', JS)


def _is_dynamic_template(text):
    return "${" in text or "+" in text


# JS 自己注入的元素（先 innerHTML 再取用）不算漂移
JS_CREATED_IDS = set(re.findall(r'id="([A-Za-z0-9_\-]+)"', JS))


def test_every_literal_id_the_js_touches_exists_in_html():
    missing = sorted({i for i in _JS_REFS
                      if not _is_dynamic_template(i)
                      and i not in HTML_IDS
                      and i not in JS_CREATED_IDS})
    assert not missing, f"app.js 引用了 index.html 里不存在的元素 id: {missing}"


def test_step2_audit_renderers_are_wired_to_the_endpoint_payload():
    # 渲染函数必须存在，且确实被 runWebsiteScraper 调用，而不是只写了没接
    for fn in ["renderMachineAuditStats", "renderMachineAuditVulns", "renderMachineAuditFindings"]:
        assert f"function {fn}(" in JS, f"缺少渲染函数 {fn}"
        assert f"{fn}(data);" in JS, f"{fn} 定义了却没被调用"
    assert 'fetch("/api/audit/site"' in JS, "第 2 步仍在调用旧的 inspect-website，拿不到逐项证据"


def test_no_fabricated_numbers_survive_in_the_frontend():
    # 这些常数曾把"没算出来"伪装成"算出来了"
    for banned in ["|| 505", "|| 28049", "|| 20160", "|| 13440", "RM 5,551",
                   "tier_label", "Math.round(val.stars)",
                   "3402.68", "528.00", "1200.00", "420.00"]:
        assert banned not in JS, f"前端又出现了写死的假数字/假字段: {banned}"


def test_insight_fallback_states_computed_scores_not_a_canned_diagnosis():
    # 旧兜底文案无论实际得分如何都说"处于起步攻坚阶段/单点故障/缺全自动闭环"
    for canned in ["处于起步攻坚阶段", "仍存在单点故障风险", "缺少全自动闭环",
                   "严禁盲目采购"]:
        assert canned not in JS, f"生成失败兜底又写成了预设立场: {canned}"
    assert "deterministicDmsSummary" in JS
    # 两段流并发写入会把正文交错成乱码，必须有序号保护
    assert "state.insightSeq !== seq" in JS


def test_industry_options_have_no_second_copy_of_the_catalogue():
    # 行业目录的唯一来源是 /api/catalog/industries；前端复制一份必然与后端漂移
    assert "defaultIndustries" not in JS
    assert 'fetch("/api/catalog/industries")' in JS
    for sample in ["物联网与智能硬件研发", "跨境物流与车队运输"]:
        assert sample not in JS, f"行业文案被复制进了前端: {sample}"


def test_ai_critique_box_is_gone_from_both_layers():
    # 那个框在未跑任何分析时就显示"公网配置已核验完毕"，是断言不是测量
    assert "ai-critique-box" not in HTML
    assert "statAiCritique" not in HTML
    assert "Cradilot AI 审阅意见" not in JS


def test_hardcoded_blindspot_probe_container_is_gone():
    # 它写死了"检测到置信度为 88%，存在异地数据冷备盲区"——本次什么都没测过
    for dead in ['id="deepProbeBox"', 'id="deepProbeCapsules"', "检测到置信度为 88%"]:
        assert dead not in HTML, f"写死的盲点排查容器又回来了: {dead}"
    for dead_js in ["deepProbeBox", "quickCapsulesGrid", "loss_est"]:
        assert dead_js not in JS, f"前端仍在引用已删除的容器/编造字段: {dead_js}"


def test_blueprint_has_exactly_one_pdf_exit():
    assert HTML.count("downloadPdf(") == 1, "蓝图出现多个下载出口"
    for gone in ["downloadPdfReport", "btnWorkbenchDownloadPdf", 'id="btnDownloadPdf"']:
        assert gone not in HTML, f"重复的 PDF 出口又回来了: {gone}"
        assert gone not in JS, f"重复的 PDF 出口又回来了: {gone}"


def test_timeline_and_roadmap_render_from_the_real_roadmap():
    assert "defaultRoadmap" not in JS, "路线图仍在用写死的三阶段模板"
    assert "renderTimelineCanvas" in JS, "时间轴画布没有接线，仍是静态 HTML"
    for field in ["p.budget_lines", "p.pricing_pending", "p.acceptance",
                  "p.hard_locked", "p.third_party_notes"]:
        assert field in JS, f"渲染器未使用真实字段 {field}"
    # 节点里不得再预置产品名、ROI 周期或 Form A2 里程碑
    for banned in ["Form A2", "ROI: 2-4 周极速见效", "对账工时压降 80%",
                   "Acronis 云端加密异地灾备", "RM 5,550.68"]:
        assert banned not in HTML, f"HTML 又写死了蓝图内容: {banned}"


def _strip_js_comments(text):
    """只查客户看得见的文案；我们自己代码里的注释不算话术泄漏。"""
    lines = []
    for line in text.split("\n"):
        if line.lstrip().startswith("//"):
            continue
        lines.append(line.split(" // ")[0])
    return re.sub(r"/\*.*?\*/", "", "\n".join(lines), flags=re.S)


def test_frontend_roadmap_copy_is_plain_language():
    visible_js = _strip_js_comments(JS)
    for jargon in ["硬锁", "止血", "锁证", "失血", "MACC", "17A", "数据主权", "套包"]:
        assert jargon not in visible_js, f"前端客户文案仍带内部话术: {jargon}"
        assert jargon not in HTML, f"页面文案仍带内部话术: {jargon}"


def test_dynamic_container_contract_matches_the_backend_payload():
    """前端读的键必须等于 agentic_diagnostic 实际发出的键。"""
    diag = (ROOT / "core" / "agentic_diagnostic.py").read_text(encoding="utf-8")

    for key in ['"sop_stage"', '"confidence_score"', '"missing_blindspots"', '"rationale"']:
        assert key in diag, f"后端不再输出 {key}，前端会静默空白"

    container = JS[JS.index("function renderDynamicContainer"):JS.index("function renderDiagProbe")]
    assert "containerData.sop_stage" in container
    assert "containerData.confidence_score" in container
    assert "dynamic_question" in container
    # 旧渲染器读的是这三个后端从未有过的键，所以才永远显示占位文案
    for ghost in ["stage_badge", "question_title", "quick_capsules"]:
        assert ghost not in container, f"前端仍在读不存在的键: {ghost}"
