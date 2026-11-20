"""Tests for error classification and retry logic."""

from unittest.mock import MagicMock, patch

import pytest

from anyscribe.core.errors import (
    AuthenticationError,
    NoCreditError,
    RateLimitError,
    ScribeAPIError,
    ServerError,
    classify_api_error,
    with_retry,
)


class TestClassifyAPIError:
    def test_401_returns_auth_error(self):
        err = classify_api_error(401, "Unauthorized", "openai")
        assert isinstance(err, AuthenticationError)
        assert err.status_code == 401
        assert err.provider == "openai"
        assert not err.retryable
        # Full hint line, anchored on the `anyscribe` prefix: a bare
        # "scribe config set" check is a substring of the "anyscribe ..." form
        # and so passes whichever voice the source string uses — it pins nothing.
        assert "  Fix: anyscribe config set openai_api_key YOUR_KEY" in err.user_message

    def test_403_returns_auth_error(self):
        err = classify_api_error(403, "Forbidden", "deepgram")
        assert isinstance(err, AuthenticationError)
        assert not err.retryable

    def test_429_returns_rate_limit(self):
        err = classify_api_error(429, "Too many requests", "elevenlabs")
        assert isinstance(err, RateLimitError)
        assert err.retryable
        assert "Rate limited" in err.user_message

    def test_500_returns_server_error(self):
        err = classify_api_error(500, "Internal server error", "openai")
        assert isinstance(err, ServerError)
        assert err.retryable

    def test_503_returns_server_error(self):
        err = classify_api_error(503, "Service unavailable", "sargam")
        assert isinstance(err, ServerError)
        assert err.retryable

    def test_400_returns_base_error(self):
        err = classify_api_error(400, "Bad request", "openai")
        assert isinstance(err, ScribeAPIError)
        assert not isinstance(err, AuthenticationError)
        assert not err.retryable

    def test_long_body_truncated(self):
        body = "x" * 500
        err = classify_api_error(400, body, "openai")
        assert len(str(err)) < 500


class TestWithRetry:
    def test_success_on_first_try(self):
        fn = MagicMock(return_value="ok")
        decorated = with_retry(max_retries=3)(fn)
        assert decorated() == "ok"
        assert fn.call_count == 1

    @patch("anyscribe.core.errors.time.sleep")
    def test_retries_on_server_error(self, mock_sleep):
        fn = MagicMock(
            side_effect=[
                ServerError("fail", status_code=500, provider="openai"),
                ServerError("fail again", status_code=500, provider="openai"),
                "ok",
            ]
        )
        decorated = with_retry(max_retries=3, base_delay=0.01)(fn)
        assert decorated() == "ok"
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("anyscribe.core.errors.time.sleep")
    def test_no_retry_on_auth_error(self, mock_sleep):
        fn = MagicMock(
            side_effect=AuthenticationError("bad key", status_code=401, provider="openai")
        )
        decorated = with_retry(max_retries=3)(fn)
        with pytest.raises(AuthenticationError):
            decorated()
        assert fn.call_count == 1
        mock_sleep.assert_not_called()

    @patch("anyscribe.core.errors.time.sleep")
    def test_exhausts_retries(self, mock_sleep):
        fn = MagicMock(side_effect=RateLimitError("limited", status_code=429, provider="openai"))
        decorated = with_retry(max_retries=2, base_delay=0.01)(fn)
        with pytest.raises(RateLimitError):
            decorated()
        assert fn.call_count == 3  # 1 initial + 2 retries


# OpenAI's real answer for an account with no credit (HTTP 429).
OPENAI_NO_CREDIT_BODY = (
    '{"error": {"message": "You exceeded your current quota, please check your plan and '
    'billing details.", "type": "insufficient_quota", "param": null, '
    '"code": "insufficient_quota"}}'
)

S1_OPENAI = (
    "Your OpenAI account has no credit. OpenAI is prepaid: add credit at "
    "https://platform.openai.com/settings/organization/billing and try again, or use the "
    "free option instead (in the dashboard: Settings, then Run setup wizard, then On this "
    "computer)."
)


class TestNoCredit:
    @patch("anyscribe.core.errors.time.sleep")
    def test_openai_insufficient_quota_is_not_retried_and_says_no_credit(self, mock_sleep):
        fn = MagicMock(side_effect=classify_api_error(429, OPENAI_NO_CREDIT_BODY, "openai"))
        with pytest.raises(NoCreditError) as exc:
            with_retry(max_retries=3, base_delay=0.01)(fn)()
        assert type(exc.value) is NoCreditError
        assert exc.value.user_message == S1_OPENAI
        assert str(exc.value) == S1_OPENAI  # the dashboard shows str(e)
        assert exc.value.retryable is False
        assert fn.call_count == 1
        mock_sleep.assert_not_called()

    @patch("anyscribe.core.errors.time.sleep")
    def test_plain_429_is_still_rate_limited_and_retried(self, mock_sleep):
        body = '{"error": {"message": "Rate limit reached", "type": "requests", "code": "rate_limit_exceeded"}}'
        fn = MagicMock(side_effect=classify_api_error(429, body, "openai"))
        with pytest.raises(RateLimitError) as exc:
            with_retry(max_retries=2, base_delay=0.01)(fn)()
        assert type(exc.value) is RateLimitError
        assert exc.value.user_message.startswith("Rate limited by openai.")
        assert fn.call_count == 3  # 1 + 2 retries
        assert mock_sleep.call_count == 2

    def test_openrouter_402_says_no_credit_without_the_openai_billing_link(self):
        body = '{"error": {"message": "Insufficient credits", "code": 402}}'
        err = classify_api_error(402, body, "openrouter")
        assert type(err) is NoCreditError
        assert err.user_message == (
            "Your OpenRouter account has no credit. OpenRouter is prepaid: add credit and try "
            "again, or use the free option instead (in the dashboard: Settings, then Run setup "
            "wizard, then On this computer)."
        )
        assert not err.retryable

    def test_groq_insufficient_quota_uses_its_display_name(self):
        err = classify_api_error(429, '{"error": {"code": "insufficient_quota"}}', "groq")
        assert type(err) is NoCreditError
        assert err.user_message == (
            "Your Groq account has no credit. Add credit or check your plan, then try again, "
            "or use the free option instead (in the dashboard: Settings, then Run setup "
            "wizard, then On this computer)."
        )

    @pytest.mark.parametrize("provider", ["groq", "deepgram", "elevenlabs", "sargam"])
    def test_only_openai_and_openrouter_are_called_prepaid(self, provider):
        msg = classify_api_error(402, "", provider).user_message
        assert "prepaid" not in msg
        assert "Add credit or check your plan" in msg
