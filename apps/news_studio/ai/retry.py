import time

import anthropic
import openai

TRANSIENT_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.OverloadedError,
)


def retry_transient(fn, attempts=3, base_delay=1.0):
    last = None
    for n in range(attempts):
        try:
            return fn()
        except TRANSIENT_EXCEPTIONS as exc:
            last = exc
            if n == attempts - 1:
                raise
            time.sleep(base_delay * (2**n))
    raise last
