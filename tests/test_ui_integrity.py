"""
Integrity test for Cradilot AI frontend assets:
Verifies zero emoji, zero model names in the shipped markup, that the seller's
identity is injected from config rather than baked in, and the presence of all step IDs.
"""

import re
from pathlib import Path

import config
from fastapi.testclient import TestClient
from app import app

ROOT_DIR = Path(__file__).parent.parent
STATIC_DIR = ROOT_DIR / "static"


def _static_files():
    for fpath in STATIC_DIR.rglob("*"):
        if fpath.suffix in (".html", ".js", ".css"):
            yield fpath, fpath.read_text(encoding="utf-8")


def test_vendor_identity_comes_from_config_not_the_markup():
    """换一家公司只改 CRADILOT_VENDOR_NAME，前端文件一个字都不用动。

    模板里留标记，落地页里必须已经没有标记；而静态文件里不许出现任何具体公司名，
    否则这份代码就还长在上一家公司的身份上。
    """
    template = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "{{VENDOR_NAME}}" in template
    assert "{{BRANDING_JSON}}" in template

    served = TestClient(app).get("/").text
    assert "{{VENDOR_NAME}}" not in served
    assert "{{BRANDING_JSON}}" not in served
    assert config.VENDOR_NAME in served

    for fpath, content in _static_files():
        assert config.VENDOR_NAME not in content, f"{fpath.name} hardcodes the company name"


def test_no_gemini_in_static_files():
    for fpath, content in _static_files():
        assert "gemini" not in content.lower(), f"Found 'Gemini' in {fpath.name}"


def test_zero_emoji_in_static_files():
    # Strict regex matching emoji unicode ranges
    emoji_pattern = re.compile(
        r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]"
    )
    for fpath in STATIC_DIR.rglob("*"):
        if fpath.suffix in [".html", ".js"]:
            content = fpath.read_text(encoding="utf-8")
            matches = emoji_pattern.findall(content)
            assert len(matches) == 0, f"Found emoji characters {matches} in {fpath.name}"


def test_step_by_step_structure_in_html():
    html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Unified 6 Stages (Stage 0 to Stage 5)
    assert 'id="stage-0"' in html_content
    assert 'id="stage-1"' in html_content
    assert 'id="stage-2"' in html_content
    assert 'id="stage-3"' in html_content
    assert 'id="stage-4"' in html_content
    assert 'id="stage-5"' in html_content

    # Substep 1.1 - 1.7 in Step 1（简报点名的 "Current digital tools" 是第 6 题，不能丢）
    for n in range(1, 8):
        assert f'id="substep1_{n}"' in html_content, f"Step 1 少了第 {n} 题"
    assert 'id="title1_6"' in html_content and 'id="options1_6"' in html_content
    assert 'id="title1_7"' in html_content
    assert 'id="hint1_7"' in html_content
    assert 'id="customToolsInput"' in html_content

    # Step 2 machine-audit containers (all content comes from /api/audit/site)
    assert 'id="websiteUrlInput"' in html_content
    assert 'id="btnRunScraper"' in html_content
    assert 'id="scrapeLoadingBox"' in html_content
    assert 'id="scrapeResultBox"' in html_content
    assert 'id="machineAuditStats"' in html_content
    assert 'id="machineAuditNote"' in html_content
    assert 'id="machineAuditVuln"' in html_content
    assert 'id="machineAuditFindings"' in html_content

    # 这些写死结论的旧瓷片必须彻底消失，否则会退回"HTML 预置答案、JS 再覆盖"的老路
    # workbenchLossTicker：问诊途中不估金额，真实数字只出现在评分卡与蓝图页
    # matrix*：11 个维度的框架太重，客户界面不铺，明细只在 PDF
    for dead_id in ["statHttpCode", "statSsl", "statLatency", "statScore",
                    "statMobile", "statStack", "statAiCritique", "devAuditResultBox",
                    "workbenchLossTicker", "matrixDmsGrid", "matrixArsGrid",
                    "matrixProgressBar"]:
        assert f'id="{dead_id}"' not in html_content, f"已删除的旧瓷片又出现了: {dead_id}"

    # Stage 3 Dynamic Agentic Probe & Cradilot Live Workbench elements
    assert 'id="diagTitle"' in html_content
    assert 'id="diagHint"' in html_content
    assert 'id="diagOptions"' in html_content
    assert 'id="customAnswerInput"' in html_content
    assert 'id="cotStep1"' in html_content
    assert 'id="cotStep2"' in html_content
    assert 'id="cotStep3"' in html_content
    assert 'id="cotStep4"' in html_content
    assert 'id="dossierSnapshotCard"' in html_content

    # Stage 3 是两段流程：先答题，答完才翻开台账。两段不能同时出现，
    # 所以复核面板必须默认藏着，定稿按钮只在台账里有一个。
    assert 'id="diagAskPanel"' in html_content
    assert 'id="diagFlowPhaseAsk"' in html_content
    assert 'id="diagFlowPhaseReview"' in html_content
    assert 'cockpit-review-panel card-3d hidden" id="diagReviewPanel"' in html_content
    assert 'id="btnEarlyFinalize"' not in html_content

    # 顶部 HUD 只剩 × Cradilot + 公司名 + 阶段，旧的项目标题不许回来
    for dead_class in ["hud-project-title", "hud-title-col"]:
        assert dead_class not in html_content

    # Stage 5 Visual Implementation Timeline elements (Contest Bonus 2)
    assert 'id="visualTimelineCanvas"' in html_content
    assert 'id="tlNode1"' in html_content
    assert 'id="tlNode2"' in html_content
    assert 'id="tlNode3"' in html_content
    assert 'id="agentFlowHud"' in html_content


def test_dynamic_live_question_placeholders_and_js_handlers():
    html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    js_content = (STATIC_DIR / "js" / "app.js").read_text(encoding="utf-8")

    # Verify Step 1 question placeholders
    for title_id in ["title1_1", "title1_2", "title1_3", "title1_4", "title1_5", "title1_6", "title1_7"]:
        assert f'id="{title_id}"' in html_content, f"Missing placeholder {title_id}"

    # Verify options containers are present
    for opt_id in ["options1_2", "options1_3", "options1_4", "options1_5", "options1_6",
                   "options1_7", "diagOptions", "arsFactorGrid"]:
        assert f'id="{opt_id}"' in html_content, f"Missing options container {opt_id}"

    # Verify JavaScript dynamic generation functions are implemented
    assert "submitCompanyNameLive" in js_content
    assert "renderToolsOptions" in js_content
    assert "submitCustomTools" in js_content
    assert "initStep1Live" in js_content
    assert "renderDiagProbe" in js_content
    assert "showDiagPhase" in js_content
    assert "submitDiagTurn" in js_content
    assert "submitCustomDiagAnswer" in js_content
    assert "updateWorkbenchUI" in js_content
    # 问诊途中的金额累计动画已删除：金额只在定稿后按假设算一次
    assert "animateLossTicker" not in js_content
    assert "the return on investment is calculated once the pricing is complete" in js_content
    assert "renderRoiAssumptions" in js_content
    assert "renderCotSteps" in js_content
    assert "focusPhaseCard" in js_content
    assert "downloadPdf" in js_content

