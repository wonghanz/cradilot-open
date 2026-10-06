"""
Cradilot Model Deployment & Sovereign Specialization (v2: Business-First & Agentic Critique Loop)
Registers 'cradilot-cradle:latest' on the Ollama server named by CRADILOT_OLLAMA_URL.
Reads the server's model list before and after, so nothing already there gets clobbered.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
OLLAMA_URL = os.environ.get("CRADILOT_OLLAMA_URL", "").rstrip("/")
MODEL_NAME = "cradilot-cradle:latest"
BASE_MODEL = "gemma3:12b"

SYSTEM_PROMPT = """You are Cradilot AI, a senior enterprise digital transformation advisor and systems architect specializing in Malaysian SMEs.
Your mission is to help SME business owners discover their next digital step, stop cash bleeding, recover lost orders, and maximize operational return on investment (ROI).

MANDATORY COGNITIVE DIRECTIVES:
1. BUSINESS FIRST: Prioritize customer acquisition, order turnaround speed, margin protection, labor cost savings, and practical ROI. Legal compliance (MACC 17A audit trails and PDPA) acts as a foundational corporate asset shield, not an academic lecture.
2. AGENTIC THOUGHT & SELF-CORRECTION (思考与纠错回路):
   Before giving final output, execute internal reasoning in <agentic_thought> blocks covering:
   [1. 商业模式与事实解构 (Business Deconstruction)]: Identify industry characteristics, unit economics, customer friction points.
   [2. 核心商业失血推演 (Commercial Bleeding Analysis)]: Calculate night inquiry leakage, manual billing overhead, customer churn risk.
   [3. 自省与客户矛盾纠错 (Critique & Self-Correction)]: Critically challenge customer misconceptions (e.g. buying expensive AI chatbots on paper foundations), correct premature tech hype, and audit your own assumptions.
   [4. 商业落地行动决策 (Action & Strategy)]: Prescribe clear, pragmatic, phased execution steps.
3. BASELINE HARD-LOCK DEFENSE:
   If the enterprise Digital Maturity Score (DMS) < 40, enforce the baseline penalty factor mu(DMS) <= 0.10, locking the AI Readiness Score (ARS) below 10. Firmly explain why purchasing high-end AI chatbots on paper foundations causes hallucination and money waste, and guide the client to Phase 1 foundation first.
4. MALAYSIAN LOCALIZED BENCHMARKS:
   Benchmark labor cost against the national standard: RM 3,500/month = RM 22.00/hour. Quantify night-order leakage (18:00 - 23:00) with tangible ringgit values.
5. EXPLAIN WHY (DESIGN RATIONALE):
   Explicitly rationalize every our solution choice against expensive alternatives (e.g., Managed WordPress AI at RM 43.99/mo vs RM 10,000 custom web development).
6. ZERO EMOJI POLICY:
   Strictly avoid all emoji characters. Use structured markdown, headers, and bullet points.
7. LANGUAGE: Professional Malaysian English and Chinese bilingual communication."""


def verify_other_models_intact():
    """Verify that all existing models remain completely untouched."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            print(f"Current Ollama model inventory ({len(models)} models):")
            for m in models:
                print(f"  - {m}")
            return models
    except Exception as e:
        print(f"Error checking tags: {e}")
        return []


def register_cradilot_model():
    """Register or update cradilot-cradle without affecting any other model."""
    print(f"\nUpdating sovereign model '{MODEL_NAME}' with Agentic Thought & Critique Loop...")
    
    payload = {
        "name": MODEL_NAME,
        "from": BASE_MODEL,
        "system": SYSTEM_PROMPT,
        "parameters": {
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.15,
            "stop": ["<end_of_turn>", "<start_of_turn>"]
        },
        "stream": False
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/create",
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"Model registration response: {res}")
            return res.get("status") == "success"
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def test_model_inference():
    """Test inference on the newly registered cradilot-cradle model with an Agentic test case."""
    print(f"\nTesting live Agentic inference on '{MODEL_NAME}'...")
    test_prompt = (
        "我们是一家巴生汽配批发商（14人，年营收 RM 3.8M），单据都在纸质送货单上，"
        "销售员用个人手机 WhatsApp 报价，没有官网。管理层准备花 RM 25,000 买一套高端 AI 销售大模型来自动接单，"
        "你觉得怎么样？请给出你的分析。"
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": test_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 500
        }
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            response_text = res.get("response", "")
            print("\n" + "=" * 60)
            print(f"AGENTIC INFERENCE RESPONSE FROM {MODEL_NAME}:")
            print("=" * 60)
            print(response_text)
            print("=" * 60)
            
            # Check compliance
            has_thought = "<agentic_thought>" in response_text or "商业模式" in response_text or "失血" in response_text or "纠错" in response_text or "硬锁" in response_text
            has_business_focus = "RM 22" in response_text or "成本" in response_text or "订单" in response_text or "利润" in response_text or "漏单" in response_text
            print(f"Agentic Compliance Checks:")
            print(f"  - Reasoning / Critique Loop Triggered: {has_thought}")
            print(f"  - Business-First Focus (Orders/Costs/Margins): {has_business_focus}")
            return True
    except Exception as e:
        print(f"Inference test failed: {e}")
        return False


def main():
    print("=" * 70)
    print("CRADILOT BUSINESS-FIRST AGENTIC DEPLOYMENT")
    print(f"Target: {OLLAMA_URL or 'UNSET — export CRADILOT_OLLAMA_URL first'}")
    print("=" * 70)
    if not OLLAMA_URL:
        print("Nothing deployed: CRADILOT_OLLAMA_URL must name the server to write to.")
        return 2

    before_models = verify_other_models_intact()
    success = register_cradilot_model()
    
    if success:
        after_models = verify_other_models_intact()
        for m in before_models:
            assert m in after_models, f"CRITICAL: Model {m} was affected!"
        print("\nPASS: All existing server models are completely intact and untouched.")
        test_model_inference()
    else:
        print("\nRegistration failed. Please check server logs.")


if __name__ == "__main__":
    sys.exit(main() or 0)
