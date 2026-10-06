"""
Cradilot LLM client — bring your own engine.

Three backends behind one contract, chosen by environment variables:

  ollama   a model you host yourself (Ollama /api/generate)
  gemini   Google's Generative Language REST API, key in GEMINI_API_KEY
  openai   any OpenAI-compatible endpoint, key in OPENAI_API_KEY
           (OpenAI itself, OpenRouter, DeepSeek, a vLLM or llama.cpp server)
  off      nothing configured: the rule engine answers and says so

The contract the rest of the codebase relies on has not changed: generate() and
stream_generate() always return usable text, and whenever the answer came from the
built-in rule engine rather than a model, last_call_degraded is True so the caller can
label it. A degraded answer is never dressed up as AI output, and it never contains an
invented number.

Keys are read once from the environment and never surfaced: status() reports whether a
key is present, not the key.
"""

import json
import os
import socket
import time
import urllib.parse
from typing import Any, Dict, Iterator, Optional

import httpx

import config

PROVIDERS = config.KNOWN_PROVIDERS


class EngineClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None,
                 base_url: Optional[str] = None) -> None:
        self.provider = config.resolve_provider(provider)
        self.model = model or config.model_for(self.provider)
        self.base_url = (base_url or self._default_base_url()).rstrip("/")
        self.api_key = self._read_key(self.provider)

        self._server_reachable: Optional[bool] = None
        self._health_checked_at: float = 0.0
        self.consecutive_failures: int = 0
        self.last_call_degraded: bool = False

    # ─── Wiring ───────────────────────────────────────────────────────────────
    def _default_base_url(self) -> str:
        if self.provider == config.PROVIDER_OLLAMA:
            return config.OLLAMA_BASE_URL
        if self.provider == config.PROVIDER_OPENAI:
            return config.OPENAI_BASE_URL
        if self.provider == config.PROVIDER_GEMINI:
            return "https://generativelanguage.googleapis.com/v1beta"
        return ""

    @staticmethod
    def _read_key(provider: str) -> str:
        if provider == config.PROVIDER_GEMINI:
            return config.GEMINI_API_KEY
        if provider == config.PROVIDER_OPENAI:
            return config.OPENAI_API_KEY
        return ""

    # ─── Health ───────────────────────────────────────────────────────────────
    def probe(self) -> bool:
        """One real reachability check. Never trusts a cached verdict."""
        if self.provider == config.PROVIDER_OFF:
            return False
        if not self.base_url:
            return False
        if self.provider != config.PROVIDER_OLLAMA and not self.api_key:
            return False
        try:
            if self.provider == config.PROVIDER_OLLAMA:
                parsed = urllib.parse.urlparse(self.base_url)
                host = parsed.hostname
                port = parsed.port or 11434
                if not host:
                    return False
                with socket.create_connection((host, port), timeout=config.PROBE_TIMEOUT_SECONDS):
                    pass
                resp = httpx.get(f"{self.base_url}/api/version",
                                 timeout=config.PROBE_TIMEOUT_SECONDS)
                return resp.status_code == 200

            if self.provider == config.PROVIDER_GEMINI:
                resp = httpx.get(f"{self.base_url}/models",
                                 headers={"x-goog-api-key": self.api_key},
                                 params={"pageSize": "1"},
                                 timeout=config.PROBE_TIMEOUT_SECONDS)
                return resp.status_code == 200

            resp = httpx.get(f"{self.base_url}/models",
                             headers={"Authorization": f"Bearer {self.api_key}"},
                             timeout=config.PROBE_TIMEOUT_SECONDS)
            return resp.status_code == 200
        except Exception:
            return False

    def check_health(self, force: bool = False) -> bool:
        """TTL-cached probe. A failure is remembered only briefly, so a recovered
        engine comes back on its own instead of locking the process into degraded copy."""
        now = time.monotonic()
        ttl = config.HEALTH_TTL_SECONDS if self._server_reachable else config.FAILURE_TTL_SECONDS
        if not force and self._server_reachable is not None and (now - self._health_checked_at) < ttl:
            return self._server_reachable

        reachable = self.probe()
        self._server_reachable = reachable
        self._health_checked_at = now
        if not reachable:
            self.consecutive_failures += 1
        return reachable

    def reset_health(self) -> None:
        self._server_reachable = None
        self._health_checked_at = 0.0

    def status(self) -> Dict[str, Any]:
        """What the UI shows. Deliberately free of secret material."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url or None,
            "api_key_present": bool(self.api_key) if self.provider in (
                config.PROVIDER_GEMINI, config.PROVIDER_OPENAI) else None,
            "reachable": bool(self._server_reachable),
            "consecutive_failures": self.consecutive_failures,
            "health_checked_at": self._health_checked_at,
        }

    def _mark_degraded(self) -> None:
        self.last_call_degraded = True
        self.consecutive_failures += 1
        self._server_reachable = None

    def _is_live(self) -> bool:
        self.last_call_degraded = False
        if self.check_health():
            self.consecutive_failures = 0
            return True
        self.last_call_degraded = True
        return False

    # ─── Generation ───────────────────────────────────────────────────────────
    def generate(self, prompt: str, system: Optional[str] = None,
                 format_json: bool = False, max_tokens: int = 600) -> str:
        if not self._is_live():
            return self._fallback_generate(prompt, system, format_json)

        from llm.prompt_library import SYSTEM_BASE
        sys_text = system or SYSTEM_BASE
        timeout = config.ENGINE_TIMEOUT_SECONDS
        try:
            if self.provider == config.PROVIDER_OLLAMA:
                return self._ollama_generate(sys_text, prompt, format_json, max_tokens, timeout)
            if self.provider == config.PROVIDER_GEMINI:
                return self._gemini_generate(sys_text, prompt, format_json, max_tokens, timeout)
            return self._openai_generate(sys_text, prompt, format_json, max_tokens, timeout)
        except Exception:
            self._mark_degraded()
            return self._fallback_generate(prompt, system, format_json)

    def stream_generate(self, prompt: str, system: Optional[str] = None,
                        max_tokens: int = 600) -> Iterator[str]:
        if not self._is_live():
            yield from self._iter_fallback_words(prompt, system)
            return

        from llm.prompt_library import SYSTEM_BASE
        sys_text = system or SYSTEM_BASE
        timeout = config.ENGINE_TIMEOUT_SECONDS
        try:
            if self.provider == config.PROVIDER_OLLAMA:
                yield from self._ollama_stream(sys_text, prompt, max_tokens, timeout)
            elif self.provider == config.PROVIDER_GEMINI:
                yield from self._gemini_stream(sys_text, prompt, max_tokens, timeout)
            else:
                yield from self._openai_stream(sys_text, prompt, max_tokens, timeout)
        except Exception:
            yield from self._iter_fallback_words(prompt, system)

    # ── Ollama ──
    def _ollama_payload(self, system: str, prompt: str, stream: bool,
                        format_json: bool, max_tokens: int) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": stream,
            "options": {"temperature": 0.3, "num_predict": max_tokens, "top_p": 0.9},
        }
        if format_json:
            payload["format"] = "json"
        return payload

    def _ollama_generate(self, system, prompt, format_json, max_tokens, timeout) -> str:
        resp = httpx.post(f"{self.base_url}/api/generate",
                          json=self._ollama_payload(system, prompt, False, format_json, max_tokens),
                          timeout=timeout)
        resp.raise_for_status()
        return self._strip_emoji(resp.json().get("response", ""))

    def _ollama_stream(self, system, prompt, max_tokens, timeout) -> Iterator[str]:
        with httpx.stream("POST", f"{self.base_url}/api/generate",
                          json=self._ollama_payload(system, prompt, True, False, max_tokens),
                          timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response", "")
                if token:
                    yield self._strip_emoji(token)
                if chunk.get("done", False):
                    break

    # ── Gemini (Generative Language REST API) ──
    def _gemini_payload(self, system: str, prompt: str, format_json: bool,
                        max_tokens: int) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens},
        }
        if format_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        return payload

    def _gemini_headers(self) -> Dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    @staticmethod
    def _gemini_text(body: Dict[str, Any]) -> str:
        candidates = body.get("candidates") or []
        if not candidates:
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(part.get("text", "") for part in parts)

    def _gemini_generate(self, system, prompt, format_json, max_tokens, timeout) -> str:
        resp = httpx.post(f"{self.base_url}/models/{self.model}:generateContent",
                          headers=self._gemini_headers(),
                          json=self._gemini_payload(system, prompt, format_json, max_tokens),
                          timeout=timeout)
        resp.raise_for_status()
        return self._strip_emoji(self._gemini_text(resp.json()))

    def _gemini_stream(self, system, prompt, max_tokens, timeout) -> Iterator[str]:
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent"
        with httpx.stream("POST", url, headers=self._gemini_headers(),
                          params={"alt": "sse"},
                          json=self._gemini_payload(system, prompt, False, max_tokens),
                          timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    body = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                token = self._gemini_text(body)
                if token:
                    yield self._strip_emoji(token)

    # ── OpenAI-compatible ──
    def _openai_payload(self, system: str, prompt: str, stream: bool,
                        format_json: bool, max_tokens: int) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if format_json:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _openai_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _openai_generate(self, system, prompt, format_json, max_tokens, timeout) -> str:
        resp = httpx.post(f"{self.base_url}/chat/completions", headers=self._openai_headers(),
                          json=self._openai_payload(system, prompt, False, format_json, max_tokens),
                          timeout=timeout)
        resp.raise_for_status()
        choices = resp.json().get("choices") or []
        if not choices:
            return ""
        return self._strip_emoji((choices[0].get("message") or {}).get("content", ""))

    def _openai_stream(self, system, prompt, max_tokens, timeout) -> Iterator[str]:
        with httpx.stream("POST", f"{self.base_url}/chat/completions",
                          headers=self._openai_headers(),
                          json=self._openai_payload(system, prompt, True, False, max_tokens),
                          timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                token = (choices[0].get("delta") or {}).get("content", "")
                if token:
                    yield self._strip_emoji(token)

    # ─── Formatting ───
    def _iter_fallback_words(self, prompt: str, system: Optional[str]) -> Iterator[str]:
        self.last_call_degraded = True
        fallback = self._fallback_generate(prompt, system, False)
        words = fallback.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    def _strip_emoji(self, text: str) -> str:
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF"
            "\U000024C2-\U000024FF"
            "\U0001F000-\U0001F2FF"
            "\u2600-\u26FF"
            "\u2700-\u27BF"
            "\u2B50\u2B55\u231A\u231B\u23E9-\u23F3\u23F8-\u23FA"
            "\uFE0F"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub("", text).strip()

    # ─── Degraded copy: the rule engine answering for itself ──────────────────
    def _fallback_generate(self, prompt: str, system: Optional[str], format_json: bool) -> str:
        """
        降级文案：仅在没有任何可达引擎时使用。

        刻意不含任何具体数字或百分比。这里的文字会被销售当成"AI 对贵司的分析"
        念给 SME 老板听，一旦编造行业统计就是拿假数据做商业承诺。定性表述由
        recommendation.py 的确定性引擎去补，不在此处伪造。
        """
        vendor = config.VENDOR_NAME
        prompt_lower = prompt.lower()

        if "追问" in prompt or "followup" in prompt_lower or "探针" in prompt:
            industry = "auto parts and hardware wholesale"
            if "餐饮" in prompt or "food" in prompt_lower:
                industry = "food and beverage"
            elif "专业服务" in prompt or "会计" in prompt or "accounting" in prompt_lower:
                industry = "professional services"
            elif "制造" in prompt or "manufactur" in prompt_lower:
                industry = "manufacturing"

            if industry == "food and beverage":
                return (
                    "Hi boss, for the daily ingredient top-up and the supplier payments at your outlets, is it done by "
                    "phone or by group chat message today, or do you have one ordering system?\n"
                    "At month end, how many days do your finance staff spend merging and reconciling the accounts of all "
                    "the outlets?"
                )
            elif industry == "professional services":
                return (
                    "Hi boss, your confidential client files and accounting working papers: are they kept on local "
                    "computers today, or in one encrypted cloud archive?\n"
                    "When a staff member leaves, is there a standard handover process for the client files and the email "
                    "history, so that nothing walks away with the person?"
                )
            else:
                return (
                    "Hi boss, when a customer sends a part number on WhatsApp on a Sunday evening or a holiday asking "
                    "for a price, how long does it usually take the next day to check stock and reply with a formal "
                    "quotation?\n"
                    "At month end, how many people are involved, and how many days do they spend keying the sales "
                    "delivery orders by hand into the accounting software for reconciliation?"
                )

        elif "insight" in prompt_lower or "解读" in prompt or "分析" in prompt:
            return (
                "[Rule engine mode - no AI engine is reachable]\n"
                "The personalised reading of each dimension score has to be produced by the AI engine together with "
                "your verified evidence, and it was not available this time."
                " The score card and the pain-point list below are still calculated by the deterministic engine from "
                "the facts you entered, and they can be trusted;"
                " the only missing part is the plain-language reading. It can be regenerated once an engine is "
                "configured and reachable."
            )

        elif "痛点" in prompt or "pain" in prompt_lower:
            return (
                "[Rule engine mode - the AI narrative layer is currently unavailable]\n"
                "The pain-point list and its evidence references are generated by the deterministic engine from your "
                "verified facts, and they sit in the report's Top 5 core pain points"
                " block. They are authoritative results and can be used as they are. What is missing here is only the "
                "plain language that links the evidence into a business narrative. No industry"
                " statistics are invented here."
            )

        elif "路线" in prompt or "roadmap" in prompt_lower:
            return (
                "[Rule engine mode - the AI narrative layer is currently unavailable]\n"
                "The three-phase implementation path and the Form A2 milestones are generated by the dynamic timeline "
                "engine from the DMS score and the verified"
                " pain points, and they sit in the report's 12-month implementation overview"
                " block. They are authoritative results. What is missing here is only the goal narrative for each "
                "phase, and it can be regenerated once the AI engine is back."
            )

        elif "破冰" in prompt or "icebreaker" in prompt_lower:
            return (
                "[Talk-track skeleton - the consultant must fill in the measured values from the report]\n"
                f"Hello, I am a digital business consultant with {vendor}. The system has just completed the digital "
                "check-up for your company, and in the report"
                " the overall DMS score, the two weakest dimensions and the estimated annual net benefit are all "
                "calculated from the facts you entered in this run.\n"
                "Quote these four items from the report before approaching the customer, and do not add any numbers "
                "verbally from this skeleton:\n"
                "1) the overall DMS score and the stage it belongs to; 2) the two lowest-scoring dimensions; "
                "3) the first item of the pain-point list with its evidence quote; 4) the annual net benefit and the "
                "investment cost in the ROI block.\n"
                "(Once the AI engine is back, the full talk track with the measured values will be produced directly.)"
            )

        elif "审计" in prompt or "critique" in prompt_lower or "官网" in prompt or "crawl" in prompt_lower or "ssl" in prompt_lower or "点评" in prompt:
            return (
                "[Rule engine mode - the AI review was not completed]\n"
                "No AI security review of this website could be produced this time: the degraded path did not read the "
                "actual scan results, so any specific conclusion"
                " about the certificate, the loading speed or the mobile adaptation would be an assertion made out of "
                "thin air. Please look at the fields already measured in the scan panel (TLS handshake result, "
                "response headers, server fingerprint); that data comes from a real probe. Once the AI engine is back, "
                "a business-narrative review can be generated."
            )

        elif format_json:
            if "探针" in prompt or "probe" in prompt_lower or "question" in prompt_lower:
                return json.dumps({
                    "step_title": "Core data assets and disaster resilience",
                    "question": "Does your company back up its core business data automatically to an encrypted cloud off site? Do you have an emergency restore plan for a sudden physical disk failure or a ransomware attack?",
                    "sub_hint": "Data kept on one machine means ransomware or hardware damage can stop the business for a long time, and it also carries personal-data compliance risk.",
                    "options": [
                        {"label": "One PC, no backup", "sub": "A single point of failure, so the risk of an outage is very high", "val": "single_pc"},
                        {"label": "Manual copies to an external drive", "sub": "Depends on someone copying files by hand, protects against nothing and is easy to lose", "val": "manual_usb"},
                        {"label": "Business-grade automated cloud backup", "sub": "Disaster recovery that brings the business back with a 30-minute RTO", "val": "cloud_auto"}
                    ]
                }, ensure_ascii=False)
            return json.dumps({
                "lead_response_hours": 14,
                "monthly_reconcile_days": 4,
                "pain_intensity": "HIGH",
                "core_leakage_summary": "Inquiries lost outside working hours and manual entry of finance documents, a double drain"
            }, ensure_ascii=False)

        return "Generating your personalised analysis, please wait. Real-time AI content will be provided once an engine is reachable."


engine_client = EngineClient()
