"""
Cradilot AI - Sales Acceleration & Lead Dispatcher Engine
Transforms SME assessment data into structured high-intent sales leads,
pre-configured cart SKUs, and tailored BD icebreaker talk tracks.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import os
import uuid
from pathlib import Path

import config


@dataclass
class CartItem:
    sku: str
    product_name: str
    billing_cycle: str
    regular_price_myr: float
    promotional_price_myr: float
    # 资助资格必须逐项核实后才写；默认不宣称（MDEC 旧计划页面已显示 Closed）
    cradle_subsidy_eligible: bool = False
    notes: str = ""


@dataclass
class SalesLead:
    lead_id: str
    created_at: str
    company_name: str
    contact_name: str
    contact_phone: str
    contact_email: str
    industry: str
    team_size: str
    annual_turnover: str
    dms_score: float
    dms_tier: str
    dms_stars: str
    ars_score: float
    ars_locked: bool
    primary_pain_points: List[str]
    cart_items: List[Dict[str, Any]]
    total_package_myr: float
    first_month_myr: float
    sales_icebreaker: str
    status: str = "NEW"  # NEW, ASSIGNED, CONTACTED, PROPOSAL_SENT, CLOSED_WON, CLOSED_LOST
    notes: str = ""
    # 简报 "Consultant notes" 与 "Assign Salesperson" 两项要求；备注也会印进 PDF
    consultant_notes: str = ""
    assigned_to: str = ""


class LeadDispatcher:
    """
    Sales acceleration dispatcher for business development teams.
    """
    
    DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "data"
    DEFAULT_LEADS_FILE = config.SALES_LEADS_PATH

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_file = storage_path or self.DEFAULT_LEADS_FILE
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

    def cart_from_roadmap(self, roadmap: List[Dict[str, Any]]) -> List["CartItem"]:
        """
        采购车直接由路线图算出，不再独立判断一次。

        旧做法是按痛点字符串做关键词匹配，还带 `dms_score < 70` 这种兜底，
        于是同一份报告上会出现两个总价：邮箱明明没被诊断为缺口，也进了采购车；
        备份台数按 headcount//3 猜。路线图已经知道每个缺口对应哪个 SKU、多少钱，
        这里只做汇总，保证采购车合计 = ROI 分母 = 各阶段预算之和。
        """
        items: List[CartItem] = []
        picked: set = set()

        for phase in roadmap or []:
            if not isinstance(phase, dict):
                continue
            for line in (phase.get("budget_lines") or []) + (phase.get("pricing_pending_lines") or []):
                sku = line.get("sku")
                if not sku or sku in picked:
                    continue
                picked.add(sku)
                amount = line.get("annual_myr")
                items.append(CartItem(
                    sku=sku,
                    product_name=line.get("product_name") or sku,
                    billing_cycle="Annual",
                    regular_price_myr=amount if amount else 0.0,
                    promotional_price_myr=amount if amount else 0.0,
                    # 资助资格未经核实前一律不宣称（MDEC 旧计划页面已显示 Closed）
                    cradle_subsidy_eligible=False,
                    notes=line.get("reason") or line.get("why") or ""
                ))
        return items

    def generate_sales_icebreaker(
        self,
        company_name: str,
        industry: str,
        dms_score: float,
        ars_score: float,
        ars_locked: bool,
        pain_points: List[str],
        roi_gain: float,
        roi_pct: float
    ) -> str:
        """
        Generate contextual 3-stage talk tracks for sales account managers:
        1. Context Opening Hook (empathetic pain point callout)
        2. 已核验事实与门禁结论（DMS/ARS + 本次机检证据）
        3. ROI Value Proposition (RM 22/hr + Night Inquiry Salvage)
        """
        pain_summary = ", ".join(pain_points[:3]) if pain_points else "digital foundations and process coordination"
        
        lock_note = (
            f"The customer's DMS is only {dms_score:.1f}, so the system automatically triggered the foundation "
            f"hard-lock and held the ARS at {ars_score:.1f}. Do not pitch complex large models. Stress that the "
            "foundation comes first, so the customer does not spend money blindly."
            if ars_locked else
            f"The customer's DMS reached {dms_score:.1f}. The digital base is sound, which gives solid conditions "
            "for a smooth AI agent rollout."
        )

        icebreaker = (
            f"[our account manager talk-track guide - {company_name}]\n\n"
            f"1. Opening Hook:\n"
            f"\"Hello, owner of {company_name}. I am a digitalisation consultant with the partner. Your business "
            f"in {industry} is solid, but this check-up shows core weaknesses such as {pain_summary}. This shows up "
            f"most outside office hours and when emails go out: gaps like these usually become unanswered price "
            f"inquiries and quotation emails landing in spam.\"\n\n"
            f"2. Trust & Protection Anchor:\n"
            f"\"Many vendors will tell you to spend tens of thousands right away on a large model or on custom "
            f"outsourced software. But on the Cradilot assessment: {lock_note} "
            f"In phase one we suggest spending a very small amount first, to get the company-domain email and an "
            f"off-site encrypted backup of the accounts in place properly. The former settles the delivery "
            f"reputation of your quotation emails; the latter removes the risk of having to stop trading when a "
            f"disk fails or ransomware arrives.\"\n\n"
            f"3. ROI Closer:\n"
            + (
                f"\"For this lean package the measured annual net benefit is about RM {roi_gain:,.2f}, with a return "
                f"on investment of {roi_pct:.1f}%. Every figure comes from what you filled in this time and from "
                f"fields the system measured, and we can check them line by line. Your implementation blueprint and "
                f"a pre-configured list are ready; for today we can first arrange a free walk-through of it.\"\n"
                if roi_gain is not None and roi_pct is not None else
                "\"The annual spend of this package has to be quoted by the account manager based on your actual "
                "number of seats, so we are not giving you an approximate return rate now. The blueprint already "
                "lists each item still awaiting a quote together with the suggested specification; once the quote "
                "is back, the net benefit can be recalculated on the spot with the same formula, and we will then "
                "check with you line by line which savings are real.\"\n"
            )
        )
        return icebreaker

    def create_lead(
        self,
        assessment_data: Dict[str, Any],
        contact_info: Dict[str, str],
        notes: str = "",
        consultant_notes: str = "",
        assigned_to: str = ""
    ) -> SalesLead:
        """
        Assemble and persist a full SalesLead record.
        """
        meta = assessment_data.get("metadata", {})
        dms = assessment_data.get("dms", {})
        ars = assessment_data.get("ars", {})
        roi = assessment_data.get("roi", {})
        rec = assessment_data.get("recommendation", {})

        company_name = contact_info.get("company_name") or meta.get("company_name", "Unknown company")
        industry = contact_info.get("industry") or meta.get("industry", "General trading")
        team_size = contact_info.get("team_size") or meta.get("team_size", "1-10")
        annual_turnover = contact_info.get("annual_turnover") or meta.get("annual_turnover", "RM 1M-5M")

        dms_score = float(dms.get("overall_score", 45.0))
        dms_tier = str(dms.get("tier", "Emerging / vulnerable"))
        dms_stars = str(dms.get("overall_stars", "★★☆☆☆"))

        ars_score = float(ars.get("final_score", 10.0))
        ars_locked = bool(ars.get("is_hard_locked", False))

        pain_points = list(rec.get("primary_pain_points") or [])

        # 报价未定时 roi 引擎返回 None：这里如实传下去，
        # 绝不能回退成 25000 / 450% 写进销售要照念的话术里。
        raw_gain = roi.get("net_gain")
        raw_pct = roi.get("roi_percentage")
        roi_gain = float(raw_gain) if raw_gain is not None else None
        roi_pct = float(raw_pct) if raw_pct is not None else None

        # 顾问拿到的清单必须就是客户眼前那份：直接复用报告里的购物车行
        cart_rows = assessment_data.get("cart") or []
        cart_objs = [
            CartItem(
                sku=row.get("sku", ""),
                product_name=row.get("product_name", ""),
                billing_cycle=row.get("billing_cycle", "Annual"),
                regular_price_myr=float(row.get("regular_price_myr") or 0.0),
                promotional_price_myr=float(row.get("promotional_price_myr") or 0.0),
                cradle_subsidy_eligible=False,
                notes=row.get("notes", ""),
            )
            for row in cart_rows if isinstance(row, dict) and row.get("sku")
        ]
        cart_dicts = [asdict(item) for item in cart_objs]

        # 无公开单价的行（如 AI Agent）金额为 0，不计入总价：
        # 否则 ROI 分母被虚降，报给客户的回报率会被抬高。
        total_package = sum(
            item.promotional_price_myr for item in cart_objs
            if item.promotional_price_myr > 0
        )
        first_month = round(total_package / 12.0, 2)

        # Sales icebreaker
        icebreaker = self.generate_sales_icebreaker(
            company_name=company_name,
            industry=industry,
            dms_score=dms_score,
            ars_score=ars_score,
            ars_locked=ars_locked,
            pain_points=pain_points,
            roi_gain=roi_gain,
            roi_pct=roi_pct
        )

        lead_id = f"LEAD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        lead = SalesLead(
            lead_id=lead_id,
            created_at=datetime.now().isoformat(),
            company_name=company_name,
            contact_name=contact_info.get("contact_name", "Owner"),
            contact_phone=contact_info.get("contact_phone", "01X-XXXXXXX"),
            contact_email=contact_info.get("contact_email", "lead@example.com"),
            industry=industry,
            team_size=team_size,
            annual_turnover=annual_turnover,
            dms_score=dms_score,
            dms_tier=dms_tier,
            dms_stars=dms_stars,
            ars_score=ars_score,
            ars_locked=ars_locked,
            primary_pain_points=pain_points,
            cart_items=cart_dicts,
            total_package_myr=round(total_package, 2),
            first_month_myr=first_month,
            sales_icebreaker=icebreaker,
            status="ASSIGNED" if assigned_to.strip() else "NEW",
            notes=notes,
            consultant_notes=consultant_notes.strip(),
            assigned_to=assigned_to.strip()
        )

        self._save_lead_to_disk(lead)
        return lead

    def _save_lead_to_disk(self, lead: SalesLead) -> None:
        """
        Append lead record to local jsonlines file with physical isolation.
        """
        lead_dict = asdict(lead)
        line = json.dumps(lead_dict, ensure_ascii=False) + "\n"
        with open(self.storage_file, "a", encoding="utf-8") as f:
            f.write(line)

    def list_leads(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve recently captured leads for CRM dashboard.
        """
        if not self.storage_file.exists():
            return []

        leads = []
        with open(self.storage_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        leads.append(json.loads(line))
                    except Exception:
                        continue

        # Return latest first
        leads.reverse()
        return leads[:limit]

    def update_lead_status(self, lead_id: str, new_status: Optional[str] = None,
                           notes: Optional[str] = None, consultant: Optional[str] = None,
                           consultant_notes: Optional[str] = None) -> bool:
        """更新线索的管道状态、指派顾问与顾问备注。"""
        if not self.storage_file.exists():
            return False

        leads = []
        updated = False
        with open(self.storage_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("lead_id") == lead_id:
                        if consultant and consultant.strip():
                            record["assigned_to"] = consultant.strip()
                        if consultant_notes is not None:
                            record["consultant_notes"] = consultant_notes.strip()
                        status = new_status
                        if not status and record.get("assigned_to") and record.get("status") == "NEW":
                            status = "ASSIGNED"
                        if status:
                            record["status"] = status
                        if notes:
                            record["notes"] = f"{record.get('notes', '')}\n{notes}".strip()
                        updated = True
                    leads.append(record)
                except Exception:
                    continue

        if updated:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                for r in leads:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

        return updated
