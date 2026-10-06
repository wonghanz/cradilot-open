"""
Unit tests for core/noise_filter.py (Live-to-speech noise filtering and fact extraction).
"""

from core.noise_filter import NoiseFilterEngine


def test_noise_filter_cleaning():
    raw = "哎呀，那个什么，我们工厂真是麻烦，头大死了，其实吧客户都在WhatsApp找我们"
    cleaned = NoiseFilterEngine.clean_text(raw)
    assert "哎呀" not in cleaned
    assert "真是麻烦" not in cleaned
    assert "头大" not in cleaned
    assert "WhatsApp" in cleaned


def test_noise_filter_whatsapp_extraction():
    spoken = "销售都用私人手机WhatsApp聊单，上周还丢了个印尼大单，客户资料全在手机里。"
    res = NoiseFilterEngine.extract_facts(spoken)
    assert "filtered_facts" in res
    assert len(res["filtered_facts"]) > 0
    crm_facts = [f for f in res["filtered_facts"] if f["dimension"] == "crm"]
    assert len(crm_facts) > 0
    assert res["quantified_loss"]["estimated_annual_loss_myr"] >= 18000.0


def test_noise_filter_backup_and_sheet_extraction():
    spoken = "工人都是手写单据，对账对到半夜经常出错，财务软件装在一台旧电脑完全没有备份。"
    res = NoiseFilterEngine.extract_facts(spoken)
    facts = res["filtered_facts"]
    dims = [f["dimension"] for f in facts]
    assert "cloud" in dims
    assert res["quantified_loss"]["estimated_annual_loss_myr"] >= 35000.0
