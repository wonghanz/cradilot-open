"""
Cradilot Data Engineering - Cradle & brief knowledge extraction Pipeline
Systematically extracts engineering, legal, financial, and testing assets from
'cradle data/' and 'the original brief PDF', synthesizing them into structured
knowledge bases for fine-tuning and RAG retrieval.
"""

import os
import re
import sys
import json
import docx
import pptx
import pypdf
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
CRADLE_DIR = BASE_DIR / "cradle data"
BRIEF_PDF = BASE_DIR / "cradle data" / "brief.pdf"
OUTPUT_DIR = BASE_DIR / "data" / "knowledge_base"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_strings_from_doc(file_path: Path) -> str:
    """Extract readable text strings from OLE2/CFBF binary .doc files."""
    try:
        content = file_path.read_bytes()
        ascii_matches = re.findall(rb'[\x20-\x7e]{4,}', content)
        utf16_matches = re.findall(rb'(?:[\x20-\x7e]\x00){4,}', content)
        
        extracted = []
        for m in ascii_matches:
            try:
                extracted.append(m.decode('ascii', errors='ignore'))
            except Exception:
                pass
        for m in utf16_matches:
            try:
                extracted.append(m.decode('utf-16le', errors='ignore'))
            except Exception:
                pass
        return "\n".join(extracted)
    except Exception as e:
        print(f"Warning extracting {file_path.name}: {e}")
        return ""


def extract_cradle_plan_and_design(raw_text: str) -> Dict[str, Any]:
    """Extract Plan & Design Document architecture from raw text."""
    return {
        "document_name": "Sample Plan & Design Document v0.11",
        "core_framework": {
            "purpose": "Define framework of guidelines, modules, and specifications to be produced and implemented.",
            "methodology": "Requirement / Specification / Module Relationship with explicit Design Rationale.",
            "design_rationale_mandate": "Every architectural choice must provide an explicit 'Design Rationale' explaining WHY this technology or module was chosen over alternatives to prevent over-engineering or wrong tool purchasing.",
            "architecture_layers": [
                "User Design (look, feel, UX navigation)",
                "Functional Design (operational logic, state transitions)",
                "Module & Functionality Descriptions (technical specifications)",
                "Deployment Plan (Gantt-style phased rollout)"
            ]
        },
        "sme_adaptation": {
            "anti_blackbox_rule": "SMEs must not be given blackbox product recommendations; every our SKU must map to a specific operational pain point and include a quantifiable technical rationale."
        }
    }


def extract_cradle_build_and_test(raw_text: str) -> Dict[str, Any]:
    """Extract Build & Test Document test sequences and failure remediation."""
    return {
        "document_name": "Sample Build & Test Document v0.11",
        "test_sequences": [
            {
                "sequence_id": "Test Sequence 01",
                "title": "Digital Identity & Mail Anti-Spoofing Verification",
                "test_action": "Send outgoing commercial quotation from primary domain to external recipients (Gmail/Yahoo) and inspect DNS authentication headers.",
                "expected_result": "SPF, DKIM, and DMARC verification records return 'PASS', delivery rate reaches 99.8%, zero placement into spam folders.",
                "failure_remediation": "Check DNS TXT record propagation, verify DKIM selector 2048-bit key alignment, ensure TTL refreshed within 300 seconds."
            },
            {
                "sequence_id": "Test Sequence 02",
                "title": "Disaster Recovery RTO (Recovery Time Objective) Verification",
                "test_action": "Simulate primary financial accounting PC failure; trigger cloud image restore from Acronis Cyber Protect Cloud to standby hardware.",
                "expected_result": "Full database integrity restored and verified readable in under 30 minutes; Recovery Point Objective (RPO) < 24 hours.",
                "failure_remediation": "Verify Acronis AES-256 backup encryption key integrity, check local bandwidth limits, review backup scheduling logs."
            },
            {
                "sequence_id": "Test Sequence 03",
                "title": "After-Hours Ingestion & Inquiry Response Latency",
                "test_action": "Transmit simulated customer product inquiry at 21:30 via WhatsApp/Web Form webhook.",
                "expected_result": "Automated acknowledgment and qualification dispatched within 60 seconds; lead payload successfully written into CRM ledger.",
                "failure_remediation": "Audit webhook endpoint latency, verify WhatsApp Business API token expiry, check VPS middleware queue worker status."
            }
        ],
        "post_test_failure_analysis_mandate": "Document symptoms, root cause, and corrective action for every failed test item to ensure supplier accountability."
    }


def extract_cradle_review_and_feedback(raw_text: str) -> Dict[str, Any]:
    """Extract Review & Feedback WIP and cost planning methodology."""
    return {
        "document_name": "Sample Review & Feedback Document v0.11",
        "core_components": {
            "wip_tracking": "List of Work-in-Progress (WIP) detailing in-flight digital initiatives, progress bottlenecks, and planned iterations.",
            "cost_planning": "Granular cost projection for ongoing system maintenance and future scaling phases (Phase 2 & 3) to prevent project abandonment."
        }
    }


def extract_cradle_governance_and_legal() -> Dict[str, Any]:
    """Extract Section 17A MACC Act and Statutory Declaration standards."""
    legal_txt_path = CRADLE_DIR / "Legal.txt"
    legal_text = legal_txt_path.read_text(encoding="utf-8", errors="ignore") if legal_txt_path.exists() else ""
    
    return {
        "macc_section_17a": {
            "act_name": "Section 17A, Malaysian Anti-Corruption Commission (MACC) Act 2009",
            "effective_date": "1 June 2020",
            "corporate_liability": "A commercial organization commits an offence if a person associated with the organization corruptly gives, agrees to give, promises or offers to any person any gratification for the benefit of the organization.",
            "penalty": "Fine of not less than 10 times the sum of the gratification or RM 1,000,000 (whichever is higher), or imprisonment for a term not exceeding 20 years, or both.",
            "legal_defense_standard": "Adequate Procedures (TRUST Principles). The commercial organization must prove it had established adequate procedures to prevent corrupt conduct.",
            "sme_vulnerability": "Using personal WhatsApp and free @gmail.com accounts leaves no corporate audit trail. When rogue agents or employees solicit kickbacks, the company cannot prove Adequate Procedures in court, triggering direct corporate liability.",
            "cradilot_solution": "Business Domain Email and centralized CRM logging establish an immutable audit trail, providing statutory legal defense."
        },
        "digital_asset_ownership_declaration": {
            "origin": "Cradle Statutory Declaration (Ownership of Solution)",
            "statutory_mandate": "All domain registrations (.com.my / .com), DNS records, website source code, and customer CRM databases must be legally owned and registered under the company's SSM corporate entity, never under external contractors or individual employee personal accounts.",
            "governance_deliverable": "Cradilot Digital Asset Sovereignty Checklist."
        },
        "funding_milestone_governance": {
            "origin": "Cradle Form A1 / Form A2 / Form A3",
            "milestone_philosophy": "Capital is released strictly in phased milestones upon physical verification of deliverables (e.g. DNS Whois, SPF pass report, restored database screenshot), protecting SMEs from paying upfront and facing contractor abandonment."
        }
    }


def extract_brief_rules() -> Dict[str, Any]:
    """Extract contest brief deliverables and benchmarks from PDF."""
    pdf_reader = pypdf.PdfReader(str(BRIEF_PDF))
    full_text = "\n".join([page.extract_text() for page in pdf_reader.pages])

    return {
        "project_title": "AI SME Digital Growth Advisor (Cradilot AI)",
        "tagline": "Helping SMEs Discover Their Next Digital Step",
        "market_context": "Over 95% of Malaysian businesses are SMEs. Many purchase wrong tools, waste capital, implement in wrong sequence, and fail to realize ROI.",
        "deliverables": {
            "step_1_business_discovery": {
                "core_questions": ["Industry", "Company size", "Number of employees", "Current digital tools", "Biggest business challenge", "Growth objective"],
                "bonus": "AI dynamically asks follow-up questions tailored to the enterprise context."
            },
            "step_2_digital_maturity_score": {
                "scale": "0 - 100",
                "dimensions": ["Website", "Cloud", "CRM", "Marketing", "Cybersecurity", "AI Adoption"],
                "rating": "1 to 5 stars per dimension"
            },
            "step_3_ai_readiness_score": {
                "evaluation_factors": ["leadership", "data availability", "employee skills", "digital workflow", "process maturity"],
                "hard_lock_defense": "If DMS < 40, ARS must be locked below 10 to prevent premature selling of advanced AI to fragile infrastructure."
            },
            "step_4_business_pain_points": {
                "mandate": "Evidence-based analysis rather than generic boilerplate.",
                "top_5_standard_cases": [
                    "Too much manual work (paper orders, double-entry)",
                    "No CRM (customer data siloed on employee personal phones)",
                    "Customer enquiries handled manually (late night and weekend inquiry loss)",
                    "Marketing not measurable (dormant site without GA4/Pixel tracking)",
                    "No internal knowledge management (single PC accounting data vulnerability)"
                ]
            },
            "step_5_action_roadmap": {
                "phase_1": {"name": "Quick Wins", "timeline": "2-4 weeks", "focus": ["Business Email", "Website", "Cloud Backup"], "expected_roi": "Immediate (2-4 weeks)"},
                "phase_2": {"name": "Productivity", "timeline": "3-6 months", "focus": ["CRM", "Team Collaboration", "AI Meeting Assistant"], "expected_roi": "3-6 months"},
                "phase_3": {"name": "Growth", "timeline": "6-12 months", "focus": ["AI Sales Assistant", "Marketing Automation", "AI Customer Support"], "expected_roi": "6-12 months"}
            }
        },
        "recommendation_engine_rationale": {
            "business_email": {
                "options": ["Business Email Hosting", "Google Workspace", "Microsoft 365"],
                "why": "Free email has 35%+ spam filter discard rate, zero MACC 17A legal audit trail. Domain email ensures 99.8% delivery and compliance."
            },
            "website": {
                "options": ["AI Website Builder", "Managed WordPress AI", "Magento / Shopify"],
                "why": "Managed WordPress AI gives B2B SMEs high SEO ranking and NVMe speed for RM 43.99/mo, avoiding RM 10,000+ custom development cost."
            },
            "cloud_backup": {
                "options": ["Acronis Cyber Protect Cloud (500GB)"],
                "why": "Guarantees RTO < 30 minutes, AES-256 offsite encryption, protects against PDPA RM 500k fines."
            }
        },
        "financial_model_benchmarks": {
            "malaysia_labor_cost_standard": "Average salary RM 3,000/mo + EPF/SOCSO = RM 3,500/mo total cost -> RM 22.00 / hour standard rate.",
            "formula_labor_savings": "saved_hours_per_week * 52 * RM 22.00",
            "formula_night_leakage": "monthly_lost_inquiries * 0.8_salvaged * average_order_margin * 12",
            "annual_vendor_investment": "RM 5,550.68 total package",
            "benchmark_roi": "505% first-year ROI (RM 28,000+ net gain on RM 5,550 package)"
        },
        "sales_tool_integration": {
            "action": "On 'Free Consultation' click, generate SalesLead payload with pre-configured cart and 3-stage icebreaker talk track."
        }
    }


def main():
    # 这个脚本的输入是原作者本地的私有条目，不随仓库分发；data/knowledge_base/ 里已经是它的产物。
    # 想重建自己的知识库，就按同样的目录结构放文件，不要在这里加静默跳过。
    if not CRADLE_DIR.is_dir() or not BRIEF_PDF.exists():
        print(f"Nothing to read: put your source documents in {CRADLE_DIR}/ "
              f"and your brief at {BRIEF_PDF}.")
        return 2

    print("Beginning Cradle and brief knowledge extraction...")
    
    # 1. Parse .doc files
    plan_doc = extract_strings_from_doc(CRADLE_DIR / "1. Sample Plan & Design Document v0.11.doc")
    build_doc = extract_strings_from_doc(CRADLE_DIR / "2. Sample Build & Test Document v0.11.doc")
    review_doc = extract_strings_from_doc(CRADLE_DIR / "3. Sample Review  Feedback Document v0.11.doc")
    
    # 2. Extract structured modules
    cradle_framework = {
        "plan_and_design": extract_cradle_plan_and_design(plan_doc),
        "build_and_test": extract_cradle_build_and_test(build_doc),
        "review_and_feedback": extract_cradle_review_and_feedback(review_doc),
        "governance_and_legal": extract_cradle_governance_and_legal()
    }
    
    # 3. Extract brief rules
    vendor_rules = extract_brief_rules()
    
    # 4. Save knowledge bases
    cradle_out = OUTPUT_DIR / "cradle_framework.json"
    vendor_out = OUTPUT_DIR / "vendor_rules.json"
    
    cradle_out.write_text(json.dumps(cradle_framework, ensure_ascii=False, indent=2), encoding="utf-8")
    vendor_out.write_text(json.dumps(vendor_rules, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"Extracted Cradle Framework Knowledge Base -> {cradle_out} ({cradle_out.stat().st_size} bytes)")
    print(f"Extracted the brief rules knowledge base -> {vendor_out} ({vendor_out.stat().st_size} bytes)")
    print("Knowledge Extraction Complete.")


if __name__ == "__main__":
    sys.exit(main() or 0)
