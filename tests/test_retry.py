import anthropic
import httpx
import openai
import pytest

from apps.news_studio.ai.clients import make_anthropic, make_openai
from apps.news_studio.ai.retry import retry_transient
from apps.news_studio.prompts.news import SYSTEM_PROMPT


def response(status):
    return httpx.Response(status, request=httpx.Request("POST", "https://example.invalid"))


def failing_then_ok(error, failures=1):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] <= failures:
            raise error
        return "ok"

    return fn, calls


def test_retry_does_not_use_error_message_substring_matching():
    calls = 0

    def permanent_error():
        nonlocal calls
        calls += 1
        raise ValueError("accurate rate wording is not a transient API exception")

    with pytest.raises(ValueError):
        retry_transient(permanent_error, attempts=3, base_delay=0)
    assert calls == 1


@pytest.mark.parametrize(
    "error",
    [
        anthropic.OverloadedError("overloaded", response=response(529), body=None),
        anthropic.RateLimitError("rate", response=response(429), body=None),
        openai.RateLimitError("rate", response=response(429), body=None),
        openai.InternalServerError("boom", response=response(503), body=None),
    ],
)
def test_transient_errors_are_retried(error):
    fn, calls = failing_then_ok(error)
    assert retry_transient(fn, attempts=3, base_delay=0) == "ok"
    assert calls["n"] == 2


def test_client_errors_are_not_retried():
    fn, calls = failing_then_ok(anthropic.BadRequestError("bad", response=response(400), body=None))
    with pytest.raises(anthropic.BadRequestError):
        retry_transient(fn, attempts=3, base_delay=0)
    assert calls["n"] == 1


def test_sdk_internal_retries_are_disabled():
    assert make_openai("test").max_retries == 0
    assert make_anthropic("test").max_retries == 0


def test_caption_source_instruction_is_complete():
    assert "kaynak bilgisini ekle." in SYSTEM_PROMPT
    assert "kaynak bilgisini ek.\n" not in SYSTEM_PROMPT
