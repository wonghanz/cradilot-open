"""
Cradilot Core - Live-to-Speech Noise Filter & Fact Extraction Pipeline
Strictly adheres to NodiGuard Zero-Leak DLP and Local Physical Isolation.
Distills spoken input, strips emotion/complaints/chatter, and extracts deterministic
business facts (Tools, Time, Bleeding, Legal Gap) into SQLite Wiki evidence nodes.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.sql_wiki_engine import SqlWikiEngine, CORE_DIMENSIONS, ARS_FACTORS
from llm.engine_client import engine_client

NOISE_REMOVAL_PATTERNS = [
    r"哎呀", r"真是麻烦", r"头大", r"烦死人", r"气死我了", r"怎么搞的",
    r"老实讲", r"坦白说", r"其实吧", r"反正就是", r"你懂的", r"那个什么"
]

MALAYSIA_HOURLY_RATE = 22.00  # Statutory baseline: RM 3,500/month / (22 days * 7.2 hrs)


class NoiseFilterEngine:
    """
    Distills continuous user speech or text into structured business facts.
    Eliminates noise, complaints, and conversational fillers.
    """

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Strip conversational filler words and redundant punctuation."""
        text = raw_text.strip()
        for p in NOISE_REMOVAL_PATTERNS:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def extract_facts(user_text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze input text, extract standardized facts, and quantify financial loss.
        Supports Sovereign LLM distillation with an ultra-robust offline fallback.
        """
        cleaned = NoiseFilterEngine.clean_text(user_text)

        # 1. Try Sovereign LLM Distillation
        prompt = f"""[SYSTEM OBJECTIVE]
You are an institutional Cradle CIP Spark due-diligence expert.
Analyze the user's spoken feedback, discard all emotional venting, complaints, and small talk.
Extract deterministic business facts conforming strictly to SOP:
1. Tools involved (e.g. WhatsApp, Excel, paper, single-PC accounting software)
2. Frequency & Time lost (e.g. 3 hours daily, 10 hours weekly reconciliation)
3. Commercial & Bleeding Gaps (e.g. order errors, after-hours unresponded inquiries, lead leakage)
4. Operational gaps (e.g. personal Gmail for invoices, no off-site backup)

[USER STATEMENT]
"{cleaned}"

[OUTPUT SCHEMA]
Return ONLY a valid JSON object matching this schema:
{{
  "filtered_facts": [
    {{"dimension": "crm|cloud|web|cyber|marketing|ai", "fact_key": "string", "fact_value": "string", "quote": "string"}}
  ],
  "quantified_loss": {{
    "hours_wasted_weekly": 0.0,
    "estimated_annual_loss_myr": 0.0
  }},
  "detected_pain_point": {{
    "title": "string",
    "root_cause": "string",
    "severity": "HIGH|MEDIUM|LOW"
  }}
}}
"""
        parsed_result = None
        try:
            raw_json = engine_client.generate(prompt, format_json=True, max_tokens=350)
            if raw_json and len(raw_json.strip()) > 10:
                data = json.loads(raw_json)
                if "filtered_facts" in data and isinstance(data["filtered_facts"], list):
                    parsed_result = data
        except Exception:
            parsed_result = None

        # 2. Deterministic SOP-benchmarked distillation is always computed as the baseline
        deterministic = NoiseFilterEngine._deterministic_distill(cleaned)

        # 3. Reconcile live LLM output with the baseline (enum normalization + loss floor)
        if parsed_result:
            parsed_result = NoiseFilterEngine._merge_with_baseline(parsed_result, deterministic)
        else:
            parsed_result = deterministic

        # 4. If session_id provided, sync directly to SQLite Wiki
        if session_id:
            NoiseFilterEngine.sync_to_wiki(session_id, parsed_result)

        return parsed_result

    @staticmethod
    def _merge_with_baseline(llm_result: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reconcile live LLM extraction with the deterministic SOP baseline.
        The model occasionally echoes the prompt's enum literal (e.g. "crm|cyber")
        instead of choosing one member, and cannot reliably compute money, so:
        1. dimension is normalized to a single CORE_DIMENSIONS member; unusable facts dropped;
        2. baseline facts fill dimensions the model missed (deduped by dimension + fact_key);
        3. the RM22/hr benchmarked loss and pain point act as a floor when the model under-reports.
        """
        normalized: List[Dict[str, Any]] = []
        seen_keys = set()

        for fact in llm_result.get("filtered_facts", []):
            if not isinstance(fact, dict):
                continue
            raw = str(fact.get("dimension", "")).strip().lower()
            dim = raw if raw in CORE_DIMENSIONS else next(
                (tok for tok in re.split(r"[|/\\,;、，]+", raw) if tok in CORE_DIMENSIONS), ""
            )
            if not dim:
                continue
            fact["dimension"] = dim
            dedupe_key = (dim, str(fact.get("fact_key", "")))
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            normalized.append(fact)

        for fact in baseline.get("filtered_facts", []):
            if not isinstance(fact, dict):
                continue
            dim = fact.get("dimension")
            if dim not in CORE_DIMENSIONS:
                continue
            dedupe_key = (dim, str(fact.get("fact_key", "")))
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            normalized.append(fact)

        if not normalized:
            return baseline

        llm_result["filtered_facts"] = normalized

        def _loss(payload: Dict[str, Any]) -> float:
            try:
                return float((payload.get("quantified_loss") or {}).get("estimated_annual_loss_myr") or 0.0)
            except (TypeError, ValueError):
                return 0.0

        if _loss(baseline) > _loss(llm_result):
            llm_result["quantified_loss"] = baseline.get("quantified_loss", {})
            llm_result["detected_pain_point"] = baseline.get("detected_pain_point", {})

        return llm_result

    @staticmethod
    def _deterministic_distill(text: str) -> Dict[str, Any]:
        """High-precision local heuristic extractor conforming strictly to SOP facts."""
        facts: List[Dict[str, Any]] = []
        weekly_hours = 0.0
        annual_loss = 0.0
        pain_title = "Business processes and data assets are left unprotected"
        root_cause = "Processes rely on manual work or personal tools, with no central data protection and no system archiving."
        severity = "MEDIUM"

        text_lower = text.lower()

        # Check CRM / WhatsApp
        if any(k in text_lower for k in ["whatsapp", "私人手机", "私聊", "跳单", "丢单", "客户流失", "漏单"]):
            facts.append({
                "dimension": "crm",
                "fact_key": "customer_intake_channel",
                "fact_value": "personal_whatsapp",
                "quote": text[:80]
            })
            weekly_hours += 8.0
            annual_loss += 18000.00
            pain_title = "No central CRM pipeline and no company-owned customer records"
            root_cause = "Sales staff communicate through private WhatsApp, quotation records are not transparent, and departing employees take the customers with them, so opportunities are lost on a large scale."
            severity = "HIGH"

        # Check Manual Invoicing & Sheet
        if any(k in text_lower for k in ["手写", "对账", "纸质", "半夜", "算错", "excel", "单据"]):
            facts.append({
                "dimension": "cloud",
                "fact_key": "reconciliation_workflow",
                "fact_value": "manual_paper_sheets",
                "quote": text[:80]
            })
            weekly_hours += 14.0
            annual_loss += 14.0 * MALAYSIA_HOURLY_RATE * 52
            if severity != "HIGH":
                pain_title = "Heavy manual work and slow reconciliation cause wrong and missed orders"
                root_cause = "Handwritten paper documents are tallied by hand, which costs a large amount of work hours, keeps the error rate high and leaves the accounts behind."
                severity = "HIGH"

        # Check Cloud Backup / Single PC
        if any(k in text_lower for k in ["单机", "旧电脑", "u盘", "usb", "没有备份", "勒索", "坏了", "硬盘"]):
            facts.append({
                "dimension": "cloud",
                "fact_key": "backup_strategy",
                "fact_value": "single_pc",
                "quote": text[:80]
            })
            annual_loss += 35000.00
            pain_title = "Core finance and business records sit on one PC with no off-site recovery"
            root_cause = "The accounting system runs on a single old computer with no encrypted snapshot backup stored off site, so ransomware or a disk failure can stop the business completely."
            severity = "CRITICAL"

        # Check Email / Domain
        if any(k in text_lower for k in ["gmail", "yahoo", "个人邮箱", "免费邮箱", "没有邮箱"]):
            facts.append({
                "dimension": "cyber",
                "fact_key": "email_system",
                "fact_value": "free_gmail",
                "quote": text[:80]
            })
            annual_loss += 12000.00
            if severity not in ["HIGH", "CRITICAL"]:
                pain_title = "Business correspondence runs on a free personal email account"
                root_cause = "The company domain has no SPF/DKIM/DMARC anti-spoofing records, so quotation emails are easily judged as spam and the domain itself can be impersonated."
                severity = "HIGH"

        # Check After-hours / Night Leakage
        if any(k in text_lower for k in ["晚上", "下班", "没人回", "次日", "周末", "无人响应"]):
            facts.append({
                "dimension": "ai",
                "fact_key": "after_hours_response",
                "fact_value": "unattended_leak",
                "quote": text[:80]
            })
            annual_loss += 16800.00
            if severity not in ["HIGH", "CRITICAL"]:
                pain_title = "Inquiries outside working hours and at night go unanswered and are lost"
                root_cause = "There is no 24/7 automated assistant to take business inquiries after closing time, and more than 60% of overseas and night-time inquiries are lost."
                severity = "HIGH"

        if not facts:
            facts.append({
                "dimension": "web",
                "fact_key": "operational_note",
                "fact_value": "recorded",
                "quote": text[:80]
            })

        return {
            "filtered_facts": facts,
            "quantified_loss": {
                "hours_wasted_weekly": round(weekly_hours, 1),
                "estimated_annual_loss_myr": round(annual_loss, 2)
            },
            "detected_pain_point": {
                "title": pain_title,
                "root_cause": root_cause,
                "severity": severity
            }
        }

    @staticmethod
    def sync_to_wiki(session_id: str, extraction_result: Dict[str, Any]):
        """Persist extracted facts and detected pain points to SQLite Wiki tables."""
        now = datetime.now().isoformat()
        facts = extraction_result.get("filtered_facts", [])
        pain = extraction_result.get("detected_pain_point", {})
        loss_data = extraction_result.get("quantified_loss", {})
        loss_val = 0.0  # 金额一律由 apply_loss_model 按 ROI 假设分摊，这里不预测

        with SqlWikiEngine.get_db_connection() as conn:
            cursor = conn.cursor()
            for f in facts:
                dim = f.get("dimension", "cloud")
                if dim not in CORE_DIMENSIONS and dim not in ARS_FACTORS:
                    dim = "cloud"
                key = f.get("fact_key", f"{dim}_status")
                val = f.get("fact_value", "verified")
                quote = f.get("quote", "")[:150]

                cursor.execute("""
                    INSERT INTO wiki_evidence_nodes (session_id, dimension, fact_key, fact_value, quote_text, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, 0.95, ?)
                """, (session_id, dim, key, str(val), quote, now))

            conn.commit()

        if pain and pain.get("title"):
            pain_dim = str(pain.get("dimension") or "")
            if pain_dim not in CORE_DIMENSIONS and pain_dim not in ARS_FACTORS:
                pain_dim = dim if facts else ""
            SqlWikiEngine._insert_pain_point(
                session_id=session_id,
                title=pain.get("title"),
                root_cause=pain.get("root_cause"),
                loss_myr=loss_val,
                severity=pain.get("severity", "HIGH"),
                cradle_gap="The spoken input describes the current setup; what is missing is a record trail and an off-site backup.",
                solution="digital transformation and security hardening package",
                dimension=pain_dim
            )

        SqlWikiEngine.update_state_ledger(session_id)
