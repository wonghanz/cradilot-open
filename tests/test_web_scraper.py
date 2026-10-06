"""
Unit tests for core/web_scraper.py.
Conforms to NodiGuard Sentinel Directives (Zero Emoji, No Hardcoded Secrets).
"""

import pytest
from core.web_scraper import normalize_url, is_ssrf_safe, inspect_company_website


def test_normalize_url():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("https://example.com") == "https://example.com"
    assert normalize_url("") == ""


def test_ssrf_protection():
    # Private and loopback hostnames must be rejected
    assert is_ssrf_safe("localhost") is False
    assert is_ssrf_safe("127.0.0.1") is False
    assert is_ssrf_safe("192.168.1.1") is False
    assert is_ssrf_safe("10.0.0.1") is False
    # Public domains should be allowed
    assert is_ssrf_safe("example.com") is True


def test_inspect_company_website_public():
    # Live inspection of standard public reference site
    res = inspect_company_website("https://example.com")
    assert res["success"] is True
    assert res["has_website"] is True
    assert res["status_code"] == 200
    assert "Example" in res.get("page_title", "")
    assert res.get("response_time_ms", 0) > 0
    assert 0 <= res.get("technical_score", 0) <= 100


def test_inspect_company_website_blocked():
    res = inspect_company_website("http://localhost:8000")
    assert res["success"] is False
    assert "Blocked by the security defense" in res["error"]


def test_fastapi_inspect_website_endpoint():
    from fastapi.testclient import TestClient
    from app import app
    from core.sql_wiki_engine import SqlWikiEngine

    client = TestClient(app)
    session_id = "test-scrape-session-999"
    SqlWikiEngine.create_or_get_dossier(
        session_id=session_id,
        company_name="Scrape Test Sdn Bhd",
        industry="汽配五金批发与进出口",
        team_size="6-20 人",
        annual_turnover="RM 2M - 10M"
    )

    # 1. Test inspection with public domain
    resp = client.post("/api/scrape/inspect-website", json={
        "url": "https://example.com",
        "session_id": session_id
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["has_website"] is True

    # 2. Verify evidence saved in SQLite
    tree = SqlWikiEngine.get_live_wiki_tree(session_id)
    web_dim = next((d for d in tree["dimensions"] if d["dimension_code"] == "web"), None)
    assert web_dim is not None
    assert web_dim["is_verified"] is True
    assert len(web_dim["evidence_list"]) > 0

    # 3. Test "none" website handling
    resp_none = client.post("/api/scrape/inspect-website", json={
        "url": "none",
        "session_id": "test-scrape-none-888"
    })
    assert resp_none.status_code == 200
    assert resp_none.json()["has_website"] is False
