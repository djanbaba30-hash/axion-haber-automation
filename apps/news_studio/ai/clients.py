"""OpenAI ve Claude çağrıları: haber (tek çağrı + gerekirse tek düzeltme çağrısı; yalnız başlık hatalıysa küçük başlık
çağrısı) ve başlık yenileme.

SDK'ların kendi retry'ı kapalı; tek retry katmanı `retry_transient`. Sistem prompt'ları önbelleğe alınır
(OpenAI `prompt_cache_key`, GPT-5.6'da en az 30 dk; Claude `cache_control` 1 saat). Fiyat/süre: `cost.py`.
"""

from __future__ import annotations

from typing import Any

import anthropic
from openai import OpenAI

from ..config import AI_TIMEOUT_SECONDS, CLAUDE_MODEL, OPENAI_MODELS
from ..models.news import HeadlineOutput, NewsOutput
from ..prompts.news import HEADLINE_SYSTEM_PROMPT, SYSTEM_PROMPT
from ..validation.news import turkish_upper
from .retry import retry_transient

EFFORTS = {"Kapalı (Tasarruflu)": "none", "Düşük": "low", "Orta": "medium", "Yüksek": "high"}
NEWS_CACHE_KEY = "axion-haber-studio-v7"
HEADLINE_CACHE_KEY = "axion-haber-headline-v7"
NEWS_MAX_TOKENS = 2600
# Haberler arası 10–20 dk: 5 dk'lık önbellek her haberde yeniden yazılırdı (1,25x); 1 saatlik yazma 2x, sonra okuma 0,1x.
CLAUDE_CACHE = {"type": "ephemeral", "ttl": "1h"}
HEADLINE_MAX_TOKENS = {"OpenAI": 450, "Claude": 500}
HEADLINE_REQUEST = (
    "<HABER_ICERIGI>\n{content}\n</HABER_ICERIGI>\nİki YENİ başlık üret. Yeni bilgi ekleme. baslik1 olayın nasıl "
    "yaşandığını; baslik2 sonucu veya en önemli gelişmeyi anlatsın. İkisi de tamamen büyük harf ve en fazla 9 kelime olsun."
)


def _make(cls, api_key):
    return cls(api_key=api_key, timeout=AI_TIMEOUT_SECONDS, max_retries=0)


def make_openai(api_key):
    return _make(OpenAI, api_key)


def make_anthropic(api_key):
    return _make(anthropic.Anthropic, api_key)


def effort(level: str) -> str:
    return EFFORTS.get(level, "none")


def _usage_openai(response) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    details_in = getattr(usage, "input_tokens_details", None)
    details_out = getattr(usage, "output_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0), "output_tokens": getattr(usage, "output_tokens", 0),
        "cached_input_tokens": getattr(details_in, "cached_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(details_in, "cache_write_tokens", 0) or 0,
        "reasoning_tokens": getattr(details_out, "reasoning_tokens", 0), "requests": 1,
    }


def _usage_claude(response) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0), "output_tokens": getattr(usage, "output_tokens", 0),
        "cached_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "reasoning_tokens": 0, "requests": 1,
    }


def _parse_openai(client, model: str, system: str, prompt: str, schema, reasoning: str, max_tokens: int,
                  cache_key: str) -> tuple[Any, dict[str, Any]]:
    kwargs = {"model": model, "instructions": system, "input": prompt, "text_format": schema,
              "reasoning": {"effort": reasoning}, "max_output_tokens": max_tokens, "prompt_cache_key": cache_key}

    def call():
        try:
            return client.responses.parse(**kwargs)
        except TypeError:  # prompt_cache_key'i tanımayan SDK sürümü
            kwargs.pop("prompt_cache_key", None)
            return client.responses.parse(**kwargs)

    response = retry_transient(call)
    if response.output_parsed is None:
        raise ValueError("OpenAI yapılandırılmış çıktı üretmedi.")
    return response.output_parsed, {**_usage_openai(response), "provider": "OpenAI", "model": model}


def _parse_claude(client, system: str, prompt: str, schema, reasoning: str, max_tokens: int) -> tuple[Any, dict[str, Any]]:
    kwargs: dict[str, Any] = {
        "model": CLAUDE_MODEL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}],
        "output_format": schema, "system": [{"type": "text", "text": system, "cache_control": CLAUDE_CACHE}],
    }
    if reasoning == "none":
        kwargs["thinking"] = {"type": "disabled"}
    else:
        kwargs["output_config"] = {"effort": reasoning}
    response = retry_transient(lambda: client.messages.parse(**kwargs))
    if response.parsed_output is None:
        raise ValueError("Claude yapılandırılmış çıktı üretmedi.")
    return response.parsed_output, {**_usage_claude(response), "provider": "Claude", "model": CLAUDE_MODEL}


def generate(client_openai, client_claude, provider: str, model_name: str, prompt: str, thinking: str,
             max_tokens: int = NEWS_MAX_TOKENS) -> tuple[NewsOutput, dict[str, Any]]:
    """Haber (başlıklar, paylaşım metni, seslendirme metni) tek yapılandırılmış çağrıyla."""
    if provider == "OpenAI":
        return _parse_openai(client_openai, OPENAI_MODELS[model_name], SYSTEM_PROMPT, prompt, NewsOutput, effort(thinking),
                             max_tokens, NEWS_CACHE_KEY)
    return _parse_claude(client_claude, SYSTEM_PROMPT, prompt, NewsOutput, effort(thinking), max_tokens)


def regenerate_headlines(client_openai, client_claude, provider: str, model_name: str,
                         content: str, problems: str = "") -> tuple[HeadlineOutput, dict[str, Any]]:
    """Yalnız iki başlık (küçük, düşünmesiz çağrı); büyük harfe Türkçe kurallarıyla çevrilir. `problems`: önceki
    başlıkların hatası (haber işlenirken başlık sığmadıysa tam düzeltme yerine bu çağrı yapılır)."""
    prompt = HEADLINE_REQUEST.format(content=content)
    if problems:
        prompt += f"\nÖnceki başlıkların sorunu: {problems}"
    if provider == "OpenAI":
        output, usage = _parse_openai(client_openai, OPENAI_MODELS[model_name], HEADLINE_SYSTEM_PROMPT, prompt,
                                      HeadlineOutput, "none", HEADLINE_MAX_TOKENS["OpenAI"], HEADLINE_CACHE_KEY)
    else:
        output, usage = _parse_claude(client_claude, HEADLINE_SYSTEM_PROMPT, prompt, HeadlineOutput, "none",
                                      HEADLINE_MAX_TOKENS["Claude"])
    output.baslik1 = turkish_upper(output.baslik1.strip())
    output.baslik2 = turkish_upper(output.baslik2.strip())
    return output, usage
