"""
Cradilot Core - 行业目录单一数据源与关键字归一
读取 data/industry_catalog.json，供 HTTP 层、聊天守卫与前端选项共用。

原先本模块自带一张 12 行的"大马行业基准"表：夜间漏单流失率、每周对账工时、客单毛利、
Phase 1 造价、首年净收益、ROI 百分比。这 12 组数字没有任何可核实来源，却会被拼进提示词、
再要求模型"引用上方确定性纯函数的计算结果"念给客户听；行业名也早已与前端目录分叉
（12 条里 8 条在目录里根本选不到）。基准整列删除，行业名统一取目录。
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
INDUSTRY_CATALOG_PATH = BASE_DIR / "data" / "industry_catalog.json"


def _compile_token(token: str) -> "re.Pattern[str]":
    """以 * 结尾的 token 做前缀匹配，其余要求整词相等。

    整词是必需的：裸 "ai" 曾以子串方式命中 Painting / Hair / Detailing，
    把装修队和发廊判成 AI 软件公司。
    """
    escaped = re.escape(token[:-1] if token.endswith("*") else token)
    tail = r"\w*" if token.endswith("*") else r"\b"
    return re.compile(r"\b" + escaped + tail, re.IGNORECASE)


def load_catalog(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    raw = json.loads((path or INDUSTRY_CATALOG_PATH).read_text(encoding="utf-8"))
    return [{
        "val": entry["val"],
        "label": entry["label"],
        "sub": entry["sub"],
        "_en": [_compile_token(t) for t in entry.get("en", [])],
        "_zh": list(entry.get("zh", [])),
    } for entry in raw["industries"]]


CATALOG: List[Dict[str, Any]] = load_catalog()


def public_catalog() -> List[Dict[str, Any]]:
    """前端行业选项的形状：不带编译好的匹配器。"""
    return [{"val": e["val"], "label": e["label"], "sub": e["sub"]} for e in CATALOG]


def detect_industry(text: str) -> Optional[Dict[str, Any]]:
    """按目录顺序取第一个命中。中文子串、英文词边界；未命中返回 None 交由人工确认。

    刻意不做兜底猜测：宁可问一句"贵司属于哪一产业"，也不要给评委一个错的"AI 已识别"。
    旧版在这里回落成"汽配五金"，等于把餐饮、律所、零售商全部当成汽配来判断。
    """
    if not text or not text.strip():
        return None
    for entry in CATALOG:
        if any(p.search(text) for p in entry["_en"]) or any(t in text for t in entry["_zh"]):
            return dict(entry)
    return None


def get_industry_grounding(query_text: str) -> Dict[str, Any]:
    """给聊天守卫用的最小事实锚点：只有一句已归一的行业名，没有行业统计。"""
    hit = detect_industry(query_text)
    return {"industry_name": hit["label"] if hit else "",
            "sub": hit["sub"] if hit else ""}


if __name__ == "__main__":
    for probe in ["我们是巴生做汽配五金批发的", "吉隆坡连锁餐饮中央厨房",
                  "Air Conditioning Services Sdn Bhd"]:
        print(probe, "->", get_industry_grounding(probe)["industry_name"] or "(no match, needs manual confirmation)")
