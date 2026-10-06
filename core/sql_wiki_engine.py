"""
Cradilot Core - SQLite LLM Wiki Engine
Local Physical Isolation: Stores enterprise operational facts in data/cradilot_wiki.db.
Provides deterministic evidence node persistence, RAG context generation, and completeness tracking.
Conforms strictly to NodiGuard Security Sentinel Directives (parameterized SQL, zero emoji).
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from llm.engine_client import engine_client
from llm.prompt_library import prompt_cradilot_slot_extraction
from core.assessment_facts import DEEP_FACT_KEYS

import config

DB_DIR = config.DATA_DIR
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cradilot_wiki.db"

CORE_DIMENSIONS = ["web", "cloud", "crm", "marketing", "cyber", "ai"]
ARS_FACTORS = ["leadership", "employee_skills", "process_maturity", "digital_workflow", "data_availability"]
ALL_TRACKED_DIMENSIONS = CORE_DIMENSIONS + ARS_FACTORS

# 老板答"不确定"时写入的那一条证据的取值。它只表示"这一题问过了"，
# 永远不得被读成一个档位，也不得进入任何评分聚合或未核验清单的事实侧。
UNKNOWN_FACT_VALUE = "unknown"

# 提问次序：先问一眼就看得见答案的（有没有官网、单据放在哪里、谁在下班后回客户），
# 自我评估类的题（流程成熟度、员工技能、管理层意愿）留到访谈后段再问。
# 维度集合、数量与所有阈值一律不变，这里只改先后；没写进这张表的维度
# 由 _ask_order() 按原声明顺序补在末尾，所以永远不会因为排序而被漏问。
DMS_ASK_ORDER = ["web", "cloud", "crm", "cyber", "ai", "marketing"]
ARS_ASK_ORDER = ["data_availability", "digital_workflow", "process_maturity",
                 "employee_skills", "leadership"]


def _ask_order(priority: List[str], universe: List[str]) -> List[str]:
    """按提问优先级排列维度集合；未列入优先表的维度按原声明顺序排在末尾。"""
    head = [d for d in priority if d in universe]
    return head + [d for d in universe if d not in head]


_DMS_ASK_ORDER = _ask_order(DMS_ASK_ORDER, CORE_DIMENSIONS)
_ARS_ASK_ORDER = _ask_order(ARS_ASK_ORDER, ARS_FACTORS)


def is_unknown_fact_value(value: Any) -> bool:
    """这条证据是不是"答不出来"那一条（而不是某个具体档位）。"""
    return str(value if value is not None else "").strip().lower() == UNKNOWN_FACT_VALUE


def confirmed_nodes(nodes: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """滤掉"不确定"那一条，留下真正答出来的证据。已核验事实清单与提示词只读这个结果。"""
    return [n for n in (nodes or []) if not is_unknown_fact_value(n.get("fact_value"))]


def _coverage_status_text(is_verified: bool, stored: List[Dict[str, Any]]) -> str:
    """一个维度的取证状态文案，三种情形不许互相顶替：
    答出来了 / 问过了但老板说不知道 / 还没问到。"""
    if is_verified:
        return "Verified"
    if stored:
        return "Asked — you were not sure"
    return "Not verified yet"

# 提前出报告所需的最少已核验证据维度数：官方要求「5 分钟内完成分析」，而全部核验需
# 6 维 DMS + 5 项 ARS 共 11 题。此阈值让前端在证据够用时即可收尾，不必跑满 11 轮。
EARLY_FINALIZE_MIN_EVIDENCE = 6

DIMENSION_LABELS = {
    "web": "Your website and online presence",
    "cloud": "Backups and cloud recovery",
    "crm": "Customer records and follow-up (CRM)",
    "marketing": "Digital marketing and lead tracking",
    "cyber": "Business privacy and compliance (PDPA)",
    "ai": "Automation and round-the-clock enquiry handling",
    "leadership": "Management commitment and direction",
    "employee_skills": "Staff skills and readiness to work with AI",
    "process_maturity": "Working standards and written SOP",
    "digital_workflow": "Online paperwork flow and cross-department reconciliation",
    "data_availability": "Business data kept in one structured database"
}


# 事实取值词表归一：LLM 槽位抽取会产出 centralized_crm / managed_cloud / documented_sop
# 等同义写法，而 DMS、ARS 与痛点引擎只认固定枚举。不归一就会把已达标企业误判为缺陷，
# 凭空生成痛点与扣分，违反"痛点必须由真实事实驱动"的底线。
_VALUE_CANON = {
    # 注意：负面/否定档必须排在前面，否则 "no cloud backup" 会命中 "cloud" 被误判为已达标。
    "backup_strategy": [
        ("manual_usb", ("usb", "pendrive", "hard drive", "u盘", "硬盘", "移动硬盘")),
        ("single_pc", ("no backup", "without backup", "not backed", "unbackup", "none", "single",
                       "local only", "no cloud", "没有备份", "没备份", "未备份", "单机", "本地存放")),
        ("cloud_auto", ("cloud", "auto", "managed", "snapshot", "异地", "灾备", "每日备份")),
    ],
    "crm_status": [
        # 必须先于个人档：Excel 台账是"有记录无管道"的独立一档，
        # 早先 "excel" 混在个人档词里，把台账管理打到了无 CRM 的最低档。
        ("spreadsheet", ("excel", "spreadsheet", "ledger", "台账", "电子表格", "表格")),
        ("personal_whatsapp", ("no crm", "without crm", "not crm", "lacks crm", "personal", "whatsapp",
                                "wechat", "paper", "handwritten", "个人", "手机", "纸质", "手写", "微信")),
        ("formal_crm", ("formal", "central", "enterprise", "hubspot", "salesforce", "freshsales",
                        "集中", "客户管理", "统一管理")),
    ],
    "email_type": [
        ("free_gmail", ("no business email", "without business email", "free", "gmail", "yahoo",
                        "hotmail", "personal email", "个人邮箱", "免费邮箱", "私人邮箱")),
        ("business_domain", ("business", "domain", "corporate", "workspace", "企业邮箱", "对公", "域名邮箱")),
    ],
    "web_engine_status": [
        ("outdated", ("no website", "without website", "not updated", "outdated", "dormant", "stale",
                      "old site", "legacy", "旧网站", "老网站", "无人维护", "没人维护", "没有官网", "未维护")),
        ("modern", ("modern", "active", "responsive", "professional", "自适应", "有官网", "全新", "维护良好")),
    ],
    "marketing_tracker": [
        ("none", ("no tracking", "without tracking", "no pixel", "not measurable", "none", "referral",
                  "offline", "ad hoc", "ad_hoc", "无追踪", "没有追踪", "转介绍", "熟客", "靠口碑")),
        ("pixel_and_ga4", ("pixel", "ga4", "retarget", "measurable", "追踪", "归因")),
    ],
    "order_reconcile_flow": [
        # "semi" 必须先于 manual 判：旧版把 semi 挂在 manual 的 token 里，于是
        # "部分在线、月底还要人工对一遍"这一档直接被并成"全人工"，中间的档位没了。
        ("semi", ("semi", "half", "partially", "部分", "半自动", "混合")),
        ("manual", ("no automated", "without automation", "manual", "paper", "hand", "re-key",
                    "手工", "人工", "纸质", "二次录入", "逐张")),
        ("auto", ("auto", "online", "digital", "system", "在线审批", "自动", "系统生成")),
    ],
    "has_sop": [
        # 成文 SOP 是三档而不是一档有无：只写了半套流程的，既不是"有"也不是"没有"。
        ("partial", ("partial", "semi", "draft", "部分", "半成品", "写了大半")),
        ("false", ("no sop", "without sop", "not documented", "no documented", "lacks sop", "informal",
                   "oral", "none", "false", "experience", "没有", "无sop", "未成文", "口头", "全靠")),
        ("true", ("true", "standard", "documented", "formal", "yes", "成文", "规范", "有sop")),
    ],
    "employee_skill_level": [
        ("low", ("no skill", "not willing", "resist", "reluctant", "unable", "low", "limited",
                 "老员工", "抵触", "不会", "排斥", "不熟悉")),
        ("high", ("high", "young", "eager", "willing", "fast", "adept", "乐于", "愿意", "上手快")),
    ],
    "data_availability_status": [
        ("unstructured", ("no database", "without database", "not structured", "unstructured",
                          "paper", "scattered", "siloed", "manual", "handwritten", "spreadsheet only",
                          "纸质", "分散", "账本", "手写", "孤岛")),
        ("structured", ("structured", "sql", "erp", "database", "centralized", "数据库", "进销存")),
    ],
    "after_hours_leak": [
        ("true", ("no response", "not answered", "unanswered", "next day", "leak", "missed", "manual",
                  "true", "没人", "无人", "隔夜", "第二天", "漏单")),
        ("false", ("covered", "auto", "middleware", "ai", "24", "instant", "已部署", "有人", "全天候")),
    ],
    "leadership_willingness": [
        ("reluctant", ("no budget", "not willing", "against", "resist", "reluctant", "skeptical",
                       "doubt", "low", "limited", "reluc", "怀疑", "抵触", "收紧", "不支持", "观望太久")),
        ("conservative", ("conservative", "cautious", "pilot first", "观望", "谨慎", "先试水", "分期")),
        ("high", ("high", "strong", "committed", "坚定", "大力支持", "充足", "明确预算", "愿意投入", "强烈")),
    ],
}


def _canon_value(field: str, raw: Any, default: str) -> str:
    """把槽位值归一到引擎枚举；无法判定时保留原值，交由下游默认分支保守处理。"""
    text = str(default if raw is None else raw).strip().lower()
    if not text:
        return default
    for canonical, tokens in _VALUE_CANON.get(field, []):
        if text == canonical or any(tok in text for tok in tokens):
            return canonical
    return text


# Step 1 的"现在用什么工具"是客户原话，而评分层按整词比对（"sql" in tools），
# 所以先归一到规范 token；认不出的工具宁可丢掉也不猜——那一项就保持"未采集"。
_TOOL_TOKENS: List[List[str]] = [
    ["paper", "纸质", "manual", "handwritten"],
    ["whatsapp", "wechat", "phone call", "telegram"],
    ["sql", "autocount", "accounting", "bookkeeping"],
    ["excel", "spreadsheet", "ledger"],
    ["erp", "pos system", "point of sale", "inventory", "进销存", "stock system"],
    ["crm", "hubspot", "freshsales", "salesforce", "zoho"],
    ["website", "web store", "online shop", "e-commerce", "facebook page"],
    ["cloud", "google drive", "dropbox", "onedrive", "shared drive"],
    ["outlook", "microsoft", "teams"],
    ["gmail", "yahoo", "free email"],
]

_TOOL_CANON = {
    0: "paper", 1: "whatsapp", 2: "sql", 3: "excel", 4: "erp", 5: "crm",
    6: "website", 7: "cloud", 8: "microsoft", 9: "personal_email",
}


def _stated_tool_tokens(text: Any) -> List[str]:
    raw = str(text or "").strip().lower()
    if not raw:
        return []
    found: List[str] = []
    for idx, tokens in enumerate(_TOOL_TOKENS):
        canon = _TOOL_CANON[idx]
        if canon not in found and any(tok in raw for tok in tokens):
            found.append(canon)
    return found


def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe connection to the local SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_wiki_db():
    """Initialize database tables with parameterized schemas."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Enterprise Dossier
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_dossier (
                session_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                team_size TEXT NOT NULL,
                annual_turnover TEXT NOT NULL,
                biggest_challenge TEXT DEFAULT '',
                growth_objective TEXT DEFAULT '',
                current_tools TEXT DEFAULT '',
                business_model TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Schema migrations for enterprise_dossier
        cursor.execute("PRAGMA table_info(enterprise_dossier)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "biggest_challenge" not in cols:
            cursor.execute("ALTER TABLE enterprise_dossier ADD COLUMN biggest_challenge TEXT DEFAULT ''")
        if "growth_objective" not in cols:
            cursor.execute("ALTER TABLE enterprise_dossier ADD COLUMN growth_objective TEXT DEFAULT ''")
        if "current_tools" not in cols:
            cursor.execute("ALTER TABLE enterprise_dossier ADD COLUMN current_tools TEXT DEFAULT ''")

        # 2. Wiki Evidence Nodes (DMS + ARS dimensions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wiki_evidence_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                dimension TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                quote_text TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES enterprise_dossier(session_id)
            )
        """)

        # 3. Pain Points Matrix
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pain_points_matrix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                pain_title TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                financial_loss_myr REAL NOT NULL,
                severity TEXT NOT NULL,
                cradle_gap TEXT NOT NULL,
                vendor_solution TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES enterprise_dossier(session_id)
            )
        """)

        # 4. Diagnostic State Ledger
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diagnostic_state_ledger (
                session_id TEXT PRIMARY KEY,
                current_turn INTEGER DEFAULT 0,
                explored_dimensions TEXT DEFAULT '[]',
                missing_dimensions TEXT DEFAULT '[]',
                explored_ars_factors TEXT DEFAULT '[]',
                missing_ars_factors TEXT DEFAULT '[]',
                completeness_score REAL DEFAULT 0.0,
                is_ready_for_scoring INTEGER DEFAULT 0,
                current_probe_question TEXT DEFAULT '',
                last_updated TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES enterprise_dossier(session_id)
            )
        """)

        # Schema migrations for diagnostic_state_ledger
        cursor.execute("PRAGMA table_info(diagnostic_state_ledger)")
        ledger_cols = [r["name"] for r in cursor.fetchall()]
        if "explored_ars_factors" not in ledger_cols:
            cursor.execute("ALTER TABLE diagnostic_state_ledger ADD COLUMN explored_ars_factors TEXT DEFAULT '[]'")
        if "missing_ars_factors" not in ledger_cols:
            cursor.execute("ALTER TABLE diagnostic_state_ledger ADD COLUMN missing_ars_factors TEXT DEFAULT '[]'")

        # Schema migration for pain_points_matrix: 痛点必须可归属到证据维度，
        # 否则同一事实在规则层与 wiki 层会被重复计入失血总额。
        cursor.execute("PRAGMA table_info(pain_points_matrix)")
        pain_cols = [r["name"] for r in cursor.fetchall()]
        if "dimension" not in pain_cols:
            cursor.execute("ALTER TABLE pain_points_matrix ADD COLUMN dimension TEXT DEFAULT ''")

        # 5. 第②步官网机检快照。210 项明细只在那一刻产生，PDF 与蓝图都在之后才生成；
        #    不落盘的话，报告里"我们查过什么"就没有可复核的出处。
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS site_audit_snapshot (
                session_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                site_level TEXT DEFAULT '',
                level_label TEXT DEFAULT '',
                rows_json TEXT NOT NULL DEFAULT '[]',
                conclusions_json TEXT NOT NULL DEFAULT '[]',
                summary_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES enterprise_dossier(session_id)
            )
        """)

        conn.commit()


# Initialize upon module import
init_wiki_db()


class SqlWikiEngine:
    """Engine handling local SQLite LLM Wiki read, write, extraction and verification."""

    @staticmethod
    def get_db_connection():
        return get_db_connection()

    @staticmethod
    def create_or_get_dossier(session_id: str, company_name: str, industry: str,
                              team_size: str, annual_turnover: str,
                              biggest_challenge: str = "", growth_objective: str = "",
                              current_tools: str = "") -> Dict[str, Any]:
        """Upsert enterprise dossier and initialize state ledger."""
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO enterprise_dossier (session_id, company_name, industry, team_size, annual_turnover,
                                              biggest_challenge, growth_objective, current_tools, business_model, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    company_name=excluded.company_name,
                    industry=excluded.industry,
                    team_size=excluded.team_size,
                    annual_turnover=excluded.annual_turnover,
                    biggest_challenge=CASE WHEN excluded.biggest_challenge != '' THEN excluded.biggest_challenge ELSE enterprise_dossier.biggest_challenge END,
                    growth_objective=CASE WHEN excluded.growth_objective != '' THEN excluded.growth_objective ELSE enterprise_dossier.growth_objective END,
                    current_tools=CASE WHEN excluded.current_tools != '' THEN excluded.current_tools ELSE enterprise_dossier.current_tools END,
                    updated_at=excluded.updated_at
            """, (session_id, company_name, industry, team_size, annual_turnover, biggest_challenge,
                  growth_objective, current_tools, now, now))

            # Initialize diagnostic state ledger if not exists
            cursor.execute("SELECT session_id FROM diagnostic_state_ledger WHERE session_id = ?", (session_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO diagnostic_state_ledger
                    (session_id, current_turn, explored_dimensions, missing_dimensions,
                     explored_ars_factors, missing_ars_factors, completeness_score,
                     is_ready_for_scoring, current_probe_question, last_updated)
                    VALUES (?, 0, ?, ?, ?, ?, 0.0, 0, '', ?)
                """, (session_id, json.dumps([]), json.dumps(CORE_DIMENSIONS),
                      json.dumps([]), json.dumps(ARS_FACTORS), now))

            conn.commit()

        return {
            "session_id": session_id,
            "company_name": company_name,
            "industry": industry,
            "team_size": team_size,
            "annual_turnover": annual_turnover,
            "biggest_challenge": biggest_challenge,
            "growth_objective": growth_objective,
            "current_tools": current_tools
        }

    @staticmethod
    def extract_slots_via_cradilot(session_id: str, user_message: str, target_dim: str = "") -> List[Dict[str, Any]]:
        """
        Use Cradilot Brain (cradilot-cradle:latest) to extract structured business facts and pain points into JSON.
        """
        now = datetime.now().isoformat()
        try:
            tree = SqlWikiEngine.get_live_wiki_tree(session_id)
            dossier = tree.get("dossier", {})
            company_name = dossier.get("company_name", "Your company")
            industry = dossier.get("industry", "General trading")

            existing_facts = []
            for d in tree.get("dimensions", []):
                if d.get("is_verified") and d.get("evidence_list"):
                    for ev in confirmed_nodes(d["evidence_list"]):
                        existing_facts.append(f"{d['dimension_label']}: {ev['quote_text']}")

            target = target_dim or "operational_fact"
            prompt = prompt_cradilot_slot_extraction(
                company_name=company_name,
                industry=industry,
                target_item=target,
                user_answer=user_message,
                existing_facts=existing_facts
            )

            raw_json = engine_client.generate(prompt, format_json=True, max_tokens=350)
            if not raw_json or len(raw_json.strip()) < 5:
                return []

            data = json.loads(raw_json)
            dim = data.get("dimension") or target_dim
            if not dim or (dim not in CORE_DIMENSIONS and dim not in ARS_FACTORS):
                return []
            fact_key = data.get("fact_key") or f"{dim}_status"
            fact_value = data.get("fact_value") or "recorded"
            quote_text = data.get("quote_text") or user_message[:120]
            confidence = float(data.get("confidence", 0.95))

            node = {
                "dimension": dim,
                "fact_key": fact_key,
                "fact_value": str(fact_value),
                "quote_text": quote_text,
                "confidence": confidence
            }

            SqlWikiEngine.record_stated_fact(session_id, dim, fact_key, fact_value,
                                             quote_text, confidence)

            pain = data.get("pain_detected", {})
            if isinstance(pain, dict) and pain.get("has_pain") and pain.get("title"):
                SqlWikiEngine._insert_pain_point(
                    session_id=session_id,
                    title=pain.get("title", f"{dim}: digital readiness gap"),
                    root_cause=pain.get("root_cause", f"For {dim}, current operations have no automation and no recovery cover."),
                    # 模型给的 loss_myr 不许入账：那是在替客户编一个他没算过的数字。
                    # 痛点成立与否由回答支撑，金额一律留给 ROI 环节用客户自己输入的数据算。
                    loss_myr=0.0,
                    severity=pain.get("severity", "HIGH"),
                    cradle_gap=pain.get("cradle_gap", "Against the Cradle baseline: no digital ownership and no business continuity cover."),
                    solution=pain.get("solution", "digital upgrade package"),
                    dimension=dim
                )

            return [node]
        except Exception as e:
            return []

    @staticmethod
    def _match_dimension(msg_lower: str, strong: List[str], weak: List[str], is_target: bool) -> bool:
        """
        跨维度串味防护（Cross-Dimension Contamination Guard）。
        strong = 高特异词（品牌名、完整短语），在任何回答中命中都可视为该维度事实；
        weak   = 上下文依赖词（如 "手机"、"熟客"、"下班"），仅当用户正在回答该维度探针时才采信。
        没有这层区分时，回答 web 的"手机看会乱"会被误判为 crm 事实，
        并连带写入 RM 28,000 失血痛点，既污染证据链又虚增年化损失。
        """
        if any(w in msg_lower for w in strong):
            return True
        return bool(is_target) and any(w in msg_lower for w in weak)

    @staticmethod
    def _fallback_keyword_extraction(session_id: str, user_message: str, target_dim: str = "") -> List[Dict[str, Any]]:
        """
        Offline fallback semantic pattern extractor for 6 DMS dimensions and 5 ARS factors.
        Guarantees deterministic local execution if model is unavailable.
        """
        now = datetime.now().isoformat()
        extracted: List[Dict[str, Any]] = []
        msg_lower = user_message.lower()

        # ── 1. Web Engine Dimension ──
        if any(w in msg_lower for w in ["没有网站", "还没做网站", "无网站", "没有官网", "no website", "facebook only", "只有fb", "只有面子书"]):
            extracted.append({
                "dimension": "web", "fact_key": "web_engine_status", "fact_value": "none",
                "quote_text": user_message, "confidence": 0.95
            })
        elif any(w in msg_lower for w in ["旧网站", "老网站", "没人维护", "没有ssl", "http://", "outdated", "多年没更新", "仅用于展示"]):
            extracted.append({
                "dimension": "web", "fact_key": "web_engine_status", "fact_value": "outdated",
                "quote_text": user_message, "confidence": 0.90
            })
        elif any(w in msg_lower for w in ["现代网站", "有独立域名", "https", "modern", "做过seo", "有官网而且正常运营"]):
            extracted.append({
                "dimension": "web", "fact_key": "web_engine_status", "fact_value": "modern",
                "quote_text": user_message, "confidence": 0.90
            })

        # ── 2. Cloud Backup Dimension ──
        is_cloud = target_dim == "cloud"
        _usb_terms = ["usb", "u盘", "pendrive", "移动硬盘"]
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["单台电脑", "只在一部电脑", "都在前台电脑", "没有备份", "没备份", "excel存桌面"] + _usb_terms,
                ["单机", "存桌面", "装在电脑"],
                is_cloud):
            val = "manual_usb" if any(w in msg_lower for w in _usb_terms) else "single_pc"
            extracted.append({
                "dimension": "cloud", "fact_key": "backup_strategy", "fact_value": val,
                "quote_text": user_message, "confidence": 0.95
            })
            SqlWikiEngine._insert_pain_point(
                session_id=session_id,
                title="Key documents live on one PC or one USB drive",
                root_cause="Finance and customer documents are kept only on a single local PC or on a USB stick that is plugged in and pulled out, with no off-site snapshots of past versions.",
                loss_myr=0.0,
                severity="CRITICAL",
                cradle_gap="Recovery has never been practised, so you only find out whether it works on the day you truly need it.",
                solution="Acronis Cloud Backup (encrypted daily off-site snapshots)",
                dimension="cloud"
            )
        elif SqlWikiEngine._match_dimension(
                msg_lower,
                ["云端备份", "自动备份", "onedrive", "google drive", "cloud backup", "异地备份"],
                ["定时同步", "上云"],
                is_cloud):
            extracted.append({
                "dimension": "cloud", "fact_key": "backup_strategy", "fact_value": "cloud_auto",
                "quote_text": user_message, "confidence": 0.92
            })

        # ── 3. CRM & Customer Pipeline ──
        is_crm = target_dim == "crm"
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["whatsapp", "微信", "个人手机", "手机接单", "在员工手机里", "员工离职带走",
                 "客户资料在", "客源流失", "飞单", "送货单手写", "谈单"],
                ["手机", "纸质单据", "送货单", "手写", "员工离职"],
                is_crm):
            if any(w in msg_lower for w in ["正式crm", "hubspot", "salesforce", "自建系统", "客户系统", "centralized crm"]):
                extracted.append({
                    "dimension": "crm", "fact_key": "crm_status", "fact_value": "formal_crm",
                    "quote_text": user_message, "confidence": 0.90
                })
            else:
                extracted.append({
                    "dimension": "crm", "fact_key": "crm_status", "fact_value": "personal_whatsapp",
                    "quote_text": user_message, "confidence": 0.95
                })
                SqlWikiEngine._insert_pain_point(
                    session_id=session_id,
                    title="Customer details sit on staff members' personal phones and leave with them",
                    root_cause="Enquiries and deals are kept in employees' personal WhatsApp accounts, with no central archive of past customer conversations.",
                    loss_myr=0.0,
                    severity="HIGH",
                    cradle_gap="The company cannot say how many active customers it has, and cannot prove the customers belong to the company.",
                    solution="WhatsApp Business multi-agent inbox + cloud customer records",
                dimension="crm"
                )

        # ── 4. Marketing & Traffic Tracking ──
        is_marketing = target_dim == "marketing"
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["不打广告", "没打广告", "没投过广告", "没有做过广告", "转介绍", "靠口碑",
                 "无追踪", "没装pixel", "没有追踪", "线下为主"],
                ["老客户", "熟客", "没有做过", "没做过"],
                is_marketing):
            extracted.append({
                "dimension": "marketing", "fact_key": "marketing_tracker", "fact_value": "none",
                "quote_text": user_message, "confidence": 0.88
            })
        elif SqlWikiEngine._match_dimension(
                msg_lower,
                ["google ads", "meta ads", "facebook广告", "装了pixel", "ga4", "打广告但转化差", "投流"],
                ["打广告", "投广告", "fb广告", "广告"],
                is_marketing):
            extracted.append({
                "dimension": "marketing", "fact_key": "marketing_tracker", "fact_value": "pixel_and_ga4",
                "quote_text": user_message, "confidence": 0.88
            })

        # ── 5. Cybersecurity & PDPA Compliance ──
        if any(w in msg_lower for w in ["企业邮箱", "公司域名邮箱", "@yourcompany", "domain email", "企业域名"]):
            extracted.append({
                "dimension": "cyber", "fact_key": "email_type", "fact_value": "business_domain",
                "quote_text": user_message, "confidence": 0.92
            })
        elif any(w in msg_lower for w in ["gmail", "yahoo", "hotmail", "免费邮箱", "个人邮箱", "没有企业邮箱", "个人免费"]):
            extracted.append({
                "dimension": "cyber", "fact_key": "email_type", "fact_value": "free_gmail",
                "quote_text": user_message, "confidence": 0.95
            })
            SqlWikiEngine._insert_pain_point(
                session_id=session_id,
                title="Quotes go out from a personal free email account",
                root_cause="Quotes and contracts are sent from a personal mailbox with no company domain behind it and no SPF/DKIM/DMARC records.",
                loss_myr=0.0,
                severity="MEDIUM",
                cradle_gap="The other side's spam filter is more likely to block it, and anyone can pretend to be your sending address.",
                solution="Business Mail Pro business email on your own domain",
                dimension="cyber"
            )

        # ── 6. AI Automation & Night Inquiries ──
        is_ai = target_dim == "ai"
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["24小时有人", "有自动化", "有聊天机器人", "已部署ai", "夜间不漏单", "全天候接单", "自动应答"],
                [],
                is_ai):
            extracted.append({
                "dimension": "ai", "fact_key": "after_hours_leak", "fact_value": "false",
                "quote_text": user_message, "confidence": 0.90
            })
        elif SqlWikiEngine._match_dimension(
                msg_lower,
                ["没人回", "无人看管", "晚上没人", "夜间无人", "下班后没人", "第二天才看",
                 "隔夜才回", "漏单", "无人应答", "没人接"],
                ["无人", "下班", "第二天", "等不及", "手工对账", "核对单据慢"],
                is_ai):
            extracted.append({
                "dimension": "ai", "fact_key": "after_hours_leak", "fact_value": "true",
                "quote_text": user_message, "confidence": 0.95
            })
            SqlWikiEngine._insert_pain_point(
                session_id=session_id,
                title="No one picks up customer enquiries after closing time",
                root_cause="Enquiries that arrive after office hours go unanswered; buyers compare quotes quickly, so a reply the next day often goes to a competitor.",
                loss_myr=0.0,
                severity="CRITICAL",
                cradle_gap="There is no record at all of who receives the first enquiry or how long the reply takes.",
                solution="AI enquiry auto-reply (7x24 lead capture)",
                dimension="ai"
            )

        # ── 7. ARS Factor: Leadership ──
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["管理层支持", "预算充足", "战略决心", "坚定转型", "大力支持", "愿意投入预算", "老板支持"],
                ["增长目标", "预算", "支持", "决心"],
                target_dim == "leadership"):
            val = "high" if any(w in msg_lower for w in ["支持", "充足", "决心", "坚定", "增长", "愿意"]) else "conservative"
            extracted.append({
                "dimension": "leadership", "fact_key": "leadership_willingness", "fact_value": val,
                "quote_text": user_message, "confidence": 0.90
            })

        # ── 8. ARS Factor: Employee Skills ──
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["员工习惯", "抵触", "年轻团队", "愿意学", "学习意愿", "不会用", "排斥", "上手快"],
                ["员工", "人手", "团队"],
                target_dim == "employee_skills"):
            val = "high" if any(w in msg_lower for w in ["年轻", "乐于", "愿意", "上手快"]) else ("low" if any(w in msg_lower for w in ["抵触", "不会", "排斥"]) else "medium")
            extracted.append({
                "dimension": "employee_skills", "fact_key": "employee_skill_level", "fact_value": val,
                "quote_text": user_message, "confidence": 0.90
            })

        # ── 9. ARS Factor: Process Maturity (SOP) ──
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["成文sop", "规范流程", "无sop", "没有sop", "口口相传", "老员工经验", "sop文档", "作业规范"],
                ["faq", "惯例", "标准"],
                target_dim == "process_maturity"):
            val = "standard" if any(w in msg_lower for w in ["有sop", "成文", "规范", "faq"]) else "informal"
            extracted.append({
                "dimension": "process_maturity", "fact_key": "has_sop", "fact_value": "true" if val == "standard" else "false",
                "quote_text": user_message, "confidence": 0.90
            })

        # ── 10. ARS Factor: Digital Workflow ──
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["单据流转", "在线审批", "纸质签批", "月底对账", "月末对账", "跨部门", "手工对账", "对账"],
                ["单据", "录入", "流转"],
                target_dim == "digital_workflow"):
            val = "auto" if any(w in msg_lower for w in ["在线审批", "自动", "系统协同"]) else "manual"
            extracted.append({
                "dimension": "digital_workflow", "fact_key": "order_reconcile_flow", "fact_value": val,
                "quote_text": user_message, "confidence": 0.90
            })

        # ── 11. ARS Factor: Data Availability ──
        if SqlWikiEngine._match_dimension(
                msg_lower,
                ["集中数据库", "统一erp", "数据孤岛", "结构化", "分散纸质", "进销存", "erp系统"],
                ["数据库", "表格", "excel", "纸质"],
                target_dim == "data_availability"):
            val = "structured" if any(w in msg_lower for w in ["数据库", "erp", "结构化", "sql", "进销存"]) else "unstructured"
            extracted.append({
                "dimension": "data_availability", "fact_key": "data_availability_status", "fact_value": val,
                "quote_text": user_message, "confidence": 0.90
            })

        # Persist fallback nodes（走带置信度守卫的 upsert，不得覆盖更确凿的菜单结论）
        for node in extracted:
            SqlWikiEngine.record_stated_fact(
                session_id, node["dimension"], node["fact_key"], node["fact_value"],
                node["quote_text"], node["confidence"])
        return extracted

    @staticmethod
    def extract_and_sync_wiki_nodes(session_id: str, user_message: str, target_dim: str = "",
                                    menu_fact: Optional[Dict[str, str]] = None,
                                    allow_anchor: bool = False) -> List[Dict[str, Any]]:
        """
        Analyze user message, extract structured business evidence into wiki_evidence_nodes,
        detect pain points, and update completeness.
        0. 菜单选择（probe option 的 val）——确定性最高，直接落证并跳过 LLM。
        1. Multi-signal keyword extraction across all 6 DMS dimensions and 5 ARS factors.
        2. Cradilot LLM slot extraction for target dimension if not captured by keywords.
        3. Deterministic anchor fallback for probed target dimension.
        """
        now = datetime.now().isoformat()
        # 1. Multi-signal deterministic extraction
        extracted = SqlWikiEngine._fallback_keyword_extraction(session_id, user_message, target_dim)
        extracted_dims = {n["dimension"] for n in extracted}

        # 0. 菜单答案优先：探针选项本身就带规范取值，无需让模型再猜一次
        if menu_fact and menu_fact.get("fact_key") and target_dim:
            node = {
                "dimension": target_dim,
                "fact_key": menu_fact["fact_key"],
                "fact_value": menu_fact["fact_value"],
                "quote_text": (menu_fact.get("quote") or user_message)[:200],
                "confidence": 0.99,
            }
            SqlWikiEngine.record_stated_fact(session_id, node["dimension"], node["fact_key"],
                                             node["fact_value"], node["quote_text"],
                                             node["confidence"])
            extracted.append(node)
            extracted_dims.add(target_dim)
            return extracted

        # 2. If target_dim was probed and not captured yet, attempt Cradilot LLM slot extraction
        if target_dim and target_dim not in extracted_dims and target_dim in (CORE_DIMENSIONS + ARS_FACTORS):
            llm_nodes = SqlWikiEngine.extract_slots_via_cradilot(session_id, user_message, target_dim)
            if llm_nodes:
                extracted.extend(llm_nodes)
                extracted_dims.update({n["dimension"] for n in llm_nodes})

        # 3. If target_dim was probed but still missing, anchor it with fallback node to prevent re-asking
        if target_dim and target_dim not in extracted_dims and (
                allow_anchor or target_dim in (CORE_DIMENSIONS + ARS_FACTORS)):
            fallback_node = {
                "dimension": target_dim,
                "fact_key": f"{target_dim}_response",
                "fact_value": "recorded",
                "quote_text": user_message[:120],
                "confidence": 0.85
            }
            SqlWikiEngine.record_stated_fact(
                session_id, target_dim, fallback_node["fact_key"],
                fallback_node["fact_value"], fallback_node["quote_text"],
                fallback_node["confidence"])
            extracted.append(fallback_node)

        # Update completeness and state ledger WITHOUT incrementing turn count
        SqlWikiEngine.update_state_ledger(session_id, increment_turn=False)
        return extracted

    # 机检证据的置信度：数值来自探针而非回忆，故高于自述类证据
    MACHINE_CONFIDENCE = 0.98

    @staticmethod
    def record_stated_fact(session_id: str, dimension: str, fact_key: str,
                           fact_value: str, quote: str,
                           confidence: float = 0.99) -> bool:
        """
        写入/更新一条老板自述事实（同一 fact_key 只保留最新一次回答）。

        自述与机检的区别只体现在 quote 前缀与置信度上；两者都进同一条证据链，
        评分卡据此区分"实测"与"自述"。不在此处推断痛点金额。
        """
        if not fact_key or str(fact_value).strip() == "":
            return False
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT confidence FROM wiki_evidence_nodes "
                "WHERE session_id = ? AND fact_key = ? ORDER BY id LIMIT 1",
                (session_id, fact_key))
            row = cursor.fetchone()
            if row is not None and float(row["confidence"] or 0) > float(confidence):
                # 已有一条更确凿的结论：菜单点选不得被后来从别段回答里猜出的关键词覆盖
                return False
            if row is not None:
                cursor.execute(
                    """
                    UPDATE wiki_evidence_nodes
                       SET dimension = ?, fact_value = ?, quote_text = ?, confidence = ?,
                           created_at = ?
                     WHERE session_id = ? AND fact_key = ?
                    """,
                    (dimension, str(fact_value), quote, confidence, now, session_id, fact_key)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO wiki_evidence_nodes
                        (session_id, dimension, fact_key, fact_value, quote_text,
                         confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, dimension, fact_key, str(fact_value), quote,
                     confidence, now)
                )
            conn.commit()
        return True

    @staticmethod
    def record_machine_fact(session_id: str, dimension: str, fact_key: str,
                            status: str, observed: str, title: str,
                            severity: str = "INFO",
                            vendor_solution_skus: Optional[List[str]] = None) -> bool:
        """
        写入一条官网机检结论到证据链。仅 pass/fail 应被写入。

        quote 前缀标注「[Machine check]」，使评分卡能区分"实测到的"与"老板说的"——
        这正是官方 Step 4 要求的 evidence-based，也是本产品的差异点。
        fail 时同时登记痛点，但金额留 0：机检量出的是配置缺口，不是令吉损失，
        凭空写一个损失数字等于替客户做他没做过的测算。
        """
        if status not in ("pass", "fail"):
            return False
        now = datetime.now().isoformat()
        quote = f"[Machine check] {title}: {observed}"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 同一 check 只保留最新一次结论：重复审计不得虚增证据条数，
            # 否则跑两次机检就能凑满"提前定稿"所需的证据数量。
            cursor.execute(
                """
                UPDATE wiki_evidence_nodes
                   SET dimension = ?, fact_value = ?, quote_text = ?, confidence = ?,
                       created_at = ?
                 WHERE session_id = ? AND fact_key = ?
                """,
                (dimension, status, quote, SqlWikiEngine.MACHINE_CONFIDENCE,
                 now, session_id, fact_key)
            )
            if not cursor.rowcount:
                cursor.execute(
                    """
                    INSERT INTO wiki_evidence_nodes
                        (session_id, dimension, fact_key, fact_value, quote_text,
                         confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, dimension, fact_key, status, quote,
                     SqlWikiEngine.MACHINE_CONFIDENCE, now)
                )
            conn.commit()

        if status == "fail":
            SqlWikiEngine._insert_pain_point(
                session_id=session_id,
                title=title,
                root_cause=quote,
                loss_myr=0.0,
                severity=severity if severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL") else "MEDIUM",
                cradle_gap="",
                solution=", ".join(vendor_solution_skus or []),
                dimension=dimension
            )
        return True

    @staticmethod
    def record_site_audit(session_id: str, url: str, site_level: str, level_label: str,
                          rows: List[Dict[str, Any]], conclusions: List[Dict[str, Any]],
                          summary: Dict[str, Any]) -> bool:
        """
        保存第②步的逐项明细。重复审计整体覆盖：跑两次不得凑出两份证据。
        """
        if not session_id or not rows:
            return False
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO site_audit_snapshot
                    (session_id, url, site_level, level_label, rows_json,
                     conclusions_json, summary_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    url = excluded.url,
                    site_level = excluded.site_level,
                    level_label = excluded.level_label,
                    rows_json = excluded.rows_json,
                    conclusions_json = excluded.conclusions_json,
                    summary_json = excluded.summary_json,
                    created_at = excluded.created_at
            """, (session_id, url or "", site_level or "", level_label or "",
                  json.dumps(rows, ensure_ascii=False),
                  json.dumps(conclusions or [], ensure_ascii=False),
                  json.dumps(summary or {}, ensure_ascii=False),
                  datetime.now().isoformat()))
            conn.commit()
        return True

    @staticmethod
    def get_site_audit(session_id: str) -> Dict[str, Any]:
        """读回第②步快照；没查过就是空字典——"没测"不能写成"测了且没问题"。"""
        if not session_id:
            return {}
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT url, site_level, level_label, rows_json, conclusions_json,
                       summary_json, created_at
                  FROM site_audit_snapshot WHERE session_id = ?
            """, (session_id,)).fetchone()
        if not row:
            return {}
        try:
            return {
                "url": row["url"], "site_level": row["site_level"],
                "level_label": row["level_label"], "audited_at": row["created_at"],
                "rows": json.loads(row["rows_json"] or "[]"),
                "conclusions": json.loads(row["conclusions_json"] or "[]"),
                "summary": json.loads(row["summary_json"] or "{}"),
            }
        except (ValueError, TypeError):
            return {}

    @staticmethod
    def _insert_pain_point(session_id: str, title: str, root_cause: str,
                           loss_myr: float, severity: str, cradle_gap: str, solution: str,
                           dimension: str = ""):
        """Insert detected pain point if not already recorded for this session."""
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM pain_points_matrix WHERE session_id = ? AND pain_title = ?", (session_id, title))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO pain_points_matrix
                    (session_id, pain_title, root_cause, financial_loss_myr, severity, cradle_gap, vendor_solution, created_at, dimension)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, title, root_cause, loss_myr, severity, cradle_gap, solution, now, dimension or ""))
                conn.commit()

    @staticmethod
    def calculate_full_completeness(session_id: str) -> Dict[str, Any]:
        """
        Calculate full 6 DMS dimensions and 5 ARS factors information coverage.
        Returns detailed status dictionary.

        explored / missing 的含义不变：该维度只要留下任意一条证据节点就算"问过了"，
        老板选"不确定"写下的那一条同样计入——否则访谈会原地重问同一题。
        confirmed_* 是另算的一档：取值不是 unknown 的证据，也就是真正答出来的事实。
        已核验清单、评分与提示词只读 confirmed 这一档；两个计数都不得互相顶替。
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT dimension FROM wiki_evidence_nodes WHERE session_id = ?
            """, (session_id,))
            rows = cursor.fetchall()
            explored_all = set(row["dimension"] for row in rows)

            cursor.execute("""
                SELECT DISTINCT dimension FROM wiki_evidence_nodes
                 WHERE session_id = ? AND lower(trim(fact_value)) <> ?
            """, (session_id, UNKNOWN_FACT_VALUE))
            confirmed_all = set(row["dimension"] for row in cursor.fetchall())

            explored_dms = [d for d in _DMS_ASK_ORDER if d in explored_all]
            missing_dms = [d for d in _DMS_ASK_ORDER if d not in explored_all]

            explored_ars = [f for f in _ARS_ASK_ORDER if f in explored_all]
            missing_ars = [f for f in _ARS_ASK_ORDER if f not in explored_all]

            confirmed_dms = [d for d in _DMS_ASK_ORDER if d in confirmed_all]
            confirmed_ars = [f for f in _ARS_ASK_ORDER if f in confirmed_all]

            total_target = len(CORE_DIMENSIONS) + len(ARS_FACTORS) # 11
            total_explored = len(explored_dms) + len(explored_ars)
            total_ratio = total_explored / float(total_target)
            dms_ratio = len(explored_dms) / float(len(CORE_DIMENSIONS))
            ars_ratio = len(explored_ars) / float(len(ARS_FACTORS))

            return {
                "explored_dms": explored_dms,
                "missing_dms": missing_dms,
                "dms_ratio": dms_ratio,
                "explored_ars": explored_ars,
                "missing_ars": missing_ars,
                "ars_ratio": ars_ratio,
                "total_explored_count": total_explored,
                "total_ratio": total_ratio,
                "is_dms_complete": len(missing_dms) == 0,
                "is_ars_complete": len(missing_ars) == 0,
                "is_all_complete": (len(missing_dms) == 0 and len(missing_ars) == 0),
                "confirmed_dms": confirmed_dms,
                "confirmed_ars": confirmed_ars,
                "confirmed_count": len(confirmed_dms) + len(confirmed_ars),
                "total_dimension_count": total_target,
            }

    @staticmethod
    def calculate_completeness(session_id: str) -> Tuple[float, List[str], List[str]]:
        """
        Backwards-compatible calculation for 6 DMS dimensions.
        Returns: (completeness_ratio, explored_dimensions, missing_dimensions)
        """
        full = SqlWikiEngine.calculate_full_completeness(session_id)
        return full["dms_ratio"], full["explored_dms"], full["missing_dms"]

    @staticmethod
    def evaluate_readiness(full: Dict[str, Any]) -> Dict[str, Any]:
        """就绪判定的唯一来源。

        is_ready_for_scoring 曾有两处互相矛盾的定义：/api/diag/step 用
        total_explored_count >= 6，get_live_wiki_tree 用 is_all_complete（11 维全齐），
        同名响应字段两个端点给出相反答案。现两处统一调本函数；
        "11 维全部核验完毕" 这一严格含义只保留在 all_completed 字段。
        """
        explored = int(full.get("total_explored_count", 0) or 0)
        can_finalize = bool(full.get("is_dms_complete")) or explored >= EARLY_FINALIZE_MIN_EVIDENCE
        return {
            "can_finalize": can_finalize,
            "is_ready_for_scoring": can_finalize,
            "allow_early_finalize": can_finalize,
            "all_completed": bool(full.get("is_all_complete")),
            "dms_completed": bool(full.get("is_dms_complete")),
            "ars_completed": bool(full.get("is_ars_complete")),
            "evidence_count": explored,
            "evidence_required": len(CORE_DIMENSIONS) + len(ARS_FACTORS),
        }

    @staticmethod
    def update_state_ledger(session_id: str, next_probe_question: str = "", increment_turn: bool = False):
        """
        Recalculate state ledger and persist.
        Only increments current_turn when explicitly requested by process_diagnostic_turn.
        """
        full = SqlWikiEngine.calculate_full_completeness(session_id)
        is_ready = 1 if SqlWikiEngine.evaluate_readiness(full)["is_ready_for_scoring"] else 0
        now = datetime.now().isoformat()

        turn_expr = "current_turn + 1" if increment_turn else "current_turn"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE diagnostic_state_ledger SET
                    explored_dimensions = ?,
                    missing_dimensions = ?,
                    explored_ars_factors = ?,
                    missing_ars_factors = ?,
                    completeness_score = ?,
                    is_ready_for_scoring = ?,
                    current_probe_question = CASE WHEN ? != '' THEN ? ELSE current_probe_question END,
                    current_turn = {turn_expr},
                    last_updated = ?
                WHERE session_id = ?
            """, (
                json.dumps(full["explored_dms"]),
                json.dumps(full["missing_dms"]),
                json.dumps(full["explored_ars"]),
                json.dumps(full["missing_ars"]),
                round(full["total_ratio"], 2),
                is_ready,
                next_probe_question, next_probe_question,
                now, session_id
            ))
            conn.commit()

    @staticmethod
    def get_dossier_created_at(session_id: str) -> Optional[str]:
        """会话起始时间戳（ISO 文本）；供时间预算核算，档案不存在时返回 None。"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT created_at FROM enterprise_dossier WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            return row["created_at"] if row else None

    @staticmethod
    def get_live_wiki_tree(session_id: str) -> Dict[str, Any]:
        """
        Return structured tree data for real-time frontend UI rendering.
        Provides both 6 DMS dimensions and 5 ARS factors verification state.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enterprise_dossier WHERE session_id = ?", (session_id,))
            dossier = cursor.fetchone()

            cursor.execute("SELECT * FROM wiki_evidence_nodes WHERE session_id = ?", (session_id,))
            nodes = cursor.fetchall()

            cursor.execute("SELECT * FROM pain_points_matrix WHERE session_id = ?", (session_id,))
            pains = cursor.fetchall()

            cursor.execute("SELECT * FROM diagnostic_state_ledger WHERE session_id = ?", (session_id,))
            ledger = cursor.fetchone()

        dossier_data = dict(dossier) if dossier else {}
        nodes_by_dim: Dict[str, List[Dict[str, Any]]] = {}
        for n in nodes:
            d = n["dimension"]
            if d not in nodes_by_dim:
                nodes_by_dim[d] = []
            nodes_by_dim[d].append({
                "fact_key": n["fact_key"],
                "fact_value": n["fact_value"],
                "quote_text": n["quote_text"],
                "confidence": n["confidence"],
                "created_at": n["created_at"]
            })

        # 6 DMS Dimensions
        dimensions_status = []
        for d in CORE_DIMENSIONS:
            stored = nodes_by_dim.get(d, [])
            is_verified = bool(confirmed_nodes(stored))
            dimensions_status.append({
                "dimension_code": d,
                "dimension_label": DIMENSION_LABELS.get(d, d),
                "is_verified": is_verified,
                "is_asked": bool(stored),
                "status_text": _coverage_status_text(is_verified, stored),
                "evidence_list": stored
            })

        # 5 ARS Factors
        ars_status = []
        for f in ARS_FACTORS:
            stored = nodes_by_dim.get(f, [])
            is_verified = bool(confirmed_nodes(stored))
            ars_status.append({
                "factor_code": f,
                "factor_label": DIMENSION_LABELS.get(f, f),
                "is_verified": is_verified,
                "is_asked": bool(stored),
                "status_text": _coverage_status_text(is_verified, stored),
                "evidence_list": stored
            })

        total_loss = sum(p["financial_loss_myr"] for p in pains)
        pain_list = [
            {
                "title": p["pain_title"],
                "root_cause": p["root_cause"],
                "dimension": (p["dimension"] or "") if "dimension" in p.keys() else "",
                "loss_myr": p["financial_loss_myr"],
                "severity": p["severity"],
                "solution": p["vendor_solution"],
                "cradle_gap": p["cradle_gap"]
            }
            for p in pains
        ]

        full = SqlWikiEngine.calculate_full_completeness(session_id)
        readiness = SqlWikiEngine.evaluate_readiness(full)
        turn = ledger["current_turn"] if ledger else 0

        return {
            "session_id": session_id,
            "dossier": dossier_data,
            "completeness_score": full["total_ratio"],
            "dms_ratio": full["dms_ratio"],
            "ars_ratio": full["ars_ratio"],
            **readiness,
            "current_turn": turn,
            "dimensions": dimensions_status,
            "ars_factors": ars_status,
            "pain_points": pain_list,
            "total_financial_loss_myr": total_loss
        }

    @staticmethod
    def get_full_assessment_input(session_id: str) -> Dict[str, Any]:
        """
        Construct standard input dictionary for calculate_dms and calculate_ars
        strictly based on facts stored in SQLite.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enterprise_dossier WHERE session_id = ?", (session_id,))
            dossier = cursor.fetchone()

            cursor.execute(
                """SELECT fact_key, fact_value, quote_text, dimension, confidence
                   FROM wiki_evidence_nodes WHERE session_id = ? ORDER BY id ASC""",
                (session_id,))
            nodes = cursor.fetchall()

        # "不确定"那一条只记录"这一题问过了"：它不是档位，所以既不进评分用的取值表，
        # 也不进已核验清单与原话引用——这一维度和"没问到"一样按中性档计入，不扣分。
        # 深挖题（维度名不在这 11 项之内）不受影响：它的"答不出"选项本就是题面里的一个档位。
        scored_nodes = [n for n in nodes
                        if not (n["dimension"] in ALL_TRACKED_DIMENSIONS
                                and is_unknown_fact_value(n["fact_value"]))]
        facts = {n["fact_key"]: n["fact_value"] for n in scored_nodes}
        # 已核验事实清单与其对应用户原话：让评分引擎能区分"事实驱动"与"缺省推断"
        verified_facts = sorted({n["fact_key"] for n in scored_nodes})
        fact_quotes: Dict[str, str] = {}
        for n in scored_nodes:
            key = n["fact_key"]
            quote = (n["quote_text"] or "").strip()
            if quote and key not in fact_quotes:
                fact_quotes[key] = quote
        company_name = dossier["company_name"] if dossier else "SME Client"
        industry = dossier["industry"] if dossier else "General trading"
        team_size = dossier["team_size"] if dossier else "6-20"
        annual_turnover = dossier["annual_turnover"] if dossier else "RM 500k - 2M"
        biggest_challenge = dossier["biggest_challenge"] if dossier and "biggest_challenge" in dossier.keys() else ""
        growth_objective = dossier["growth_objective"] if dossier and "growth_objective" in dossier.keys() else ""
        stated_tools_text = dossier["current_tools"] if dossier and "current_tools" in dossier.keys() else ""

        # 未采集到的项一律留空。本函数绝不替客户"默认"一个答案：
        # 早先这里每项都带负面默认值，等于"没问出来"直接被写成"贵司没有备份/没有 CRM"，
        # 而 after_hours_leak 的默认反向还会把没答过的 AI 维度抬成"已部署自动承接"。
        web_status = _canon_value("web_engine_status", facts.get("web_engine_status"), "")
        backup_strat = _canon_value("backup_strategy", facts.get("backup_strategy"), "")
        crm_status = _canon_value("crm_status", facts.get("crm_status"), "")
        email_type = _canon_value("email_type", facts.get("email_type"), "")
        marketing = _canon_value("marketing_tracker", facts.get("marketing_tracker"), "")
        after_hours_raw = _canon_value("after_hours_leak", facts.get("after_hours_leak"), "")
        after_hours = {"true": True, "false": False}.get(after_hours_raw)   # None = 未答
        # AI 探针的菜单答案本身就是规范档位，优先于"夜间是否漏单"这个关键词代理
        ai_tier_direct = str(facts.get("ai_tier") or "").strip().lower()

        # ARS factors mappings：与上面同一规则，问不出来就留 None/空，由评分层按中性值计入
        # "partial"（写了半套）必须原样带过去：压成 None 等于把客户答过的题报成"没采到"
        has_sop = {"true": True, "false": False, "partial": "partial"}.get(
            _canon_value("has_sop", facts.get("has_sop"), ""))
        order_reconcile = _canon_value("order_reconcile_flow", facts.get("order_reconcile_flow"), "")
        emp_skills = _canon_value("employee_skill_level", facts.get("employee_skill_level"), "")
        # ARS 探针直接采集到的两项（此前从未被引擎消费，leadership 仅用增长目标布尔代理）
        leadership_will = _canon_value(
            "leadership_willingness", facts.get("leadership_willingness"), "")
        data_avail = _canon_value(
            "data_availability_status", facts.get("data_availability_status"), "")

        # 备份档位只在问出来时才翻译；问不出来的保持空值
        dr_status = {"cloud_auto": "managed_cloud", "manual_usb": "pendrive",
                     "single_pc": "no_backup"}.get(backup_strat, "")

        tools: List[str] = []
        if crm_status == "formal_crm":
            tools.append("crm")
        elif crm_status == "personal_whatsapp":
            tools.extend(["whatsapp", "paper"])
        elif crm_status == "spreadsheet":
            tools.append("excel")
        if web_status == "modern":
            tools.append("website")
        if backup_strat == "cloud_auto":
            tools.append("cloud")
        if email_type == "business_domain":
            tools.append("enterprise_email")
        if _canon_value("data_availability_status", facts.get("data_availability_status"), "") == "structured":
            tools.append("sql")

        # Step 1 客户自己报的工具并进同一份清单：评分层的兜底档位与推荐都读这一份
        for token in _stated_tool_tokens(stated_tools_text):
            if token not in tools:
                tools.append(token)

        # 机检结论原样转发给评分层：check→规范字段 的映射只在 assessment_facts 维护一处。
        # 只转 pass/fail 两种确凿结论，未做过的检查保持缺省、绝不默认成 False，
        # 否则"这次没测到"会变成"贵司缺失该能力"并据此扣分。
        machine_findings = [{"check": key, "status": str(value).strip().lower()}
                            for key, value in sorted(facts.items())
                            if str(value).strip().lower() in ("pass", "fail")]
        _verdict = {f["check"]: f["status"] for f in machine_findings}

        has_ssl_final: Optional[bool] = None
        if "https_enforced" in _verdict:
            has_ssl_final = _verdict["https_enforced"] == "pass"
        elif web_status:
            has_ssl_final = web_status == "modern"     # 没问过也没测过：保持未知
        if _verdict.get("certificate") == "fail":
            has_ssl_final = False          # 证书过期/不受信：即使 URL 是 https 也算不合格

        return {
            "company_name": company_name,
            "industry": industry,
            "team_size": team_size,
            "annual_turnover": annual_turnover,
            "biggest_challenge": biggest_challenge,
            "growth_objective": growth_objective,
            "current_tools": stated_tools_text,
            # 每项都用 None/"" 表达"没问过"，交给 assessment_facts 的中性档；
            # 这里任何布尔默认值都会直接变成客户的分数。
            "web_engine_status": {"modern": "standard", "outdated": "dormant",
                                  "none": "no_site"}.get(web_status, ""),
            "has_domain": (False if web_status == "none" else True) if web_status else None,
            "has_ssl": has_ssl_final,
            "cloud_storage_status": {"cloud_auto": "enterprise_cloud",
                                     "manual_usb": "manual_usb",
                                     "single_pc": "single_pc"}.get(backup_strat, ""),
            "dr_backup_status": dr_status,
            "backup_freq": {"cloud_auto": "daily", "single_pc": "never"}.get(backup_strat, ""),
            "has_offsite_backup": (backup_strat == "cloud_auto") if backup_strat else None,
            "crm_system": {"formal_crm": "formal_crm", "spreadsheet": "spreadsheet",
                           "personal_whatsapp": "personal_phone"}.get(crm_status, ""),
            "uses_personal_whatsapp": (crm_status == "personal_whatsapp") if crm_status else None,
            "is_crm_centralized": (crm_status == "formal_crm") if crm_status else None,
            "marketing_tracker": marketing,
            "has_retargeting": (marketing == "pixel_and_ga4") if marketing else None,
            "email_type": email_type,
            "uses_personal_email": (email_type != "business_domain") if email_type else None,
            # after_hours_leak：True=夜间无人值守（无 AI 承接），False=已有承接，None=没问过
            # 客户明确选过档位时，代理值不再参与——否则 has_ai_agent 会把 none 抬成 deployed
            "ai_tier": ai_tier_direct,
            "ai_automation_status": ("" if ai_tier_direct else
                                     ("" if after_hours is None else
                                      ("manual" if after_hours else "middleware"))),
            "has_ai_agent": (None if ai_tier_direct else
                             (None if after_hours is None else (not after_hours))),
            "has_sop": has_sop,
            "order_reconcile_flow": order_reconcile,
            "employee_skill_level": emp_skills,
            "leadership_willingness": leadership_will,
            "data_availability_status": data_avail,
            # 可审计依据：哪些取值来自已锁证事实，以及对应的用户原话
            "_verified_facts": verified_facts,
            "_evidence_quotes": fact_quotes,
            # 深挖题取值：采到过才转发，没采到就不写，让评分停在原档位
            **{k: facts[k] for k in DEEP_FACT_KEYS if k in facts},
            "_machine_findings": machine_findings,
            "current_tools": tools,
        }

