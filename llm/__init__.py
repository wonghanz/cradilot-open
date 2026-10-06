"""
Cradilot LLM Package
Exposes the local model client and the prompt library.
"""

from .engine_client import engine_client, EngineClient

__all__ = [
    "engine_client",
    "EngineClient",
]
