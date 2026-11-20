"""POST /api/providers/{name}/test: real key checks and their plain-words answers.

HTTP is stubbed at httpx.AsyncClient.get with a fake that behaves like the real
endpoints (verified 2026-11-20 with fake keys: Groq /openai/v1/models and
OpenRouter /api/v1/key answer 401; OpenRouter /api/v1/models answers 200 to
anyone). No network, no real keys.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from anyscribe.web.app import create_app

GOOD = "good-key"


@pytest.fixture
def calls(monkeypatch):
    for var in ("GROQ_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "SARGAM_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    seen: list[httpx.Request] = []

    async def fake_get(self, url, headers=None, **_):
        request = httpx.Request("GET", url, headers=headers)  # encodes headers like a real call
        seen.append(request)
        auth = request.headers.get("authorization", "")
        if url == "https://openrouter.ai/api/v1/models":
            return httpx.Response(200, request=request)  # open to anyone
        if url == "https://api.openai.com/v1/models" and auth == "Bearer boom":
            return httpx.Response(503, request=request)
        return httpx.Response(200 if auth == f"Bearer {GOOD}" else 401, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return seen


def _check(name: str, key: str) -> dict:
    return TestClient(create_app()).post(f"/api/providers/{name}/test", json={"api_key": key}).json()


REFUSED = "{} refused this key. Check that you copied all of it, with no extra spaces."


def test_groq_fake_key_is_refused_by_a_real_call(calls):
    assert _check("groq", "gsk_fake") == {
        "success": False,
        "checked": True,
        "message": REFUSED.format("Groq"),
    }
    assert [str(r.url) for r in calls] == ["https://api.groq.com/openai/v1/models"]
    assert calls[0].headers["authorization"] == "Bearer gsk_fake"


def test_groq_good_key_is_accepted(calls):
    assert _check("groq", GOOD) == {
        "success": True,
        "checked": True,
        "message": "Groq accepted this key.",
    }


def test_openrouter_fake_key_is_refused_by_the_key_endpoint(calls):
    assert _check("openrouter", "sk-or-fake") == {
        "success": False,
        "checked": True,
        "message": REFUSED.format("OpenRouter"),
    }
    assert [str(r.url) for r in calls] == ["https://openrouter.ai/api/v1/key"]


def test_openrouter_good_key_is_accepted(calls):
    assert _check("openrouter", GOOD)["message"] == "OpenRouter accepted this key."


def test_sarvam_is_not_checked_and_says_so(calls):
    assert _check("sarvam", "anything") == {
        "success": True,
        "checked": False,
        "message": (
            "Not checked yet: Sarvam has no way to check a key in advance. "
            "It will be checked on your first transcript."
        ),
    }
    assert calls == []  # nothing was sent anywhere


def test_other_error_status_names_it_without_a_raw_headline(calls):
    assert _check("openai", "boom") == {
        "success": False,
        "checked": True,
        "message": "OpenAI answered with an error (503). Try again in a minute.",
    }


def test_unreachable_provider_lets_them_continue(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    async def timeout(self, url, headers=None, **_):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx.AsyncClient, "get", timeout)
    assert _check("groq", "gsk_whatever") == {
        "success": False,
        "checked": False,
        "message": (
            "Couldn't reach Groq to check the key. Check your internet connection, "
            "or continue: the key will be checked on your first transcript."
        ),
    }


def test_key_with_a_character_no_header_can_carry_is_refused(calls):
    # a zero-width space pasted from a web page: httpx can't even encode it
    assert _check("groq", "gsk_ab​cd") == {
        "success": False,
        "checked": True,
        "message": REFUSED.format("Groq"),
    }
    assert calls == []
