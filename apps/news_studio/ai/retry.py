import time

try:
    from openai import APIConnectionError as OpenAIAPIConnectionError
    from openai import APITimeoutError as OpenAIAPITimeoutError
    from openai import InternalServerError as OpenAIInternalServerError
    from openai import RateLimitError as OpenAIRateLimitError
except ImportError:
    OpenAIAPIConnectionError = OpenAIAPITimeoutError = OpenAIInternalServerError = OpenAIRateLimitError = ()

try:
    from anthropic import APIConnectionError as AnthropicAPIConnectionError
    from anthropic import APITimeoutError as AnthropicAPITimeoutError
    from anthropic import InternalServerError as AnthropicInternalServerError
    from anthropic import RateLimitError as AnthropicRateLimitError
except ImportError:
    AnthropicAPIConnectionError = AnthropicAPITimeoutError = AnthropicInternalServerError = AnthropicRateLimitError = ()

TRANSIENT_EXCEPTIONS = tuple(
    item
    for item in (
        OpenAIRateLimitError,
        OpenAIAPITimeoutError,
        OpenAIAPIConnectionError,
        OpenAIInternalServerError,
        AnthropicRateLimitError,
        AnthropicAPITimeoutError,
        AnthropicAPIConnectionError,
        AnthropicInternalServerError,
    )
    if isinstance(item, type)
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
