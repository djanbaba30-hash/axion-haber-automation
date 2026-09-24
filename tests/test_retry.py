import pytest

from apps.news_studio.ai.retry import retry_transient


def test_retry_does_not_use_error_message_substring_matching():
    calls = 0

    def permanent_error():
        nonlocal calls
        calls += 1
        raise ValueError("accurate rate wording is not a transient API exception")

    with pytest.raises(ValueError):
        retry_transient(permanent_error, attempts=3, base_delay=0)
    assert calls == 1
