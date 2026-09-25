"""Yapay zekâ çağrılarının biçimi (gerçek API yok): önbellek anahtarı, düşünme seviyesi, token sınırları, kullanım."""

from types import SimpleNamespace

from apps.news_studio.ai import clients
from apps.news_studio.config import CLAUDE_MODEL
from apps.news_studio.models.news import HeadlineOutput, NewsOutput
from apps.news_studio.prompts.news import HEADLINE_SYSTEM_PROMPT, SYSTEM_PROMPT

NEWS = NewsOutput(baslik1="a", baslik2="b", icerik="c", tts_plani=["x"], tts="d")


class FakeOpenAI:
    def __init__(self, parsed, reject_cache_key=False):
        self.calls, self.parsed, self.reject = [], parsed, reject_cache_key
        self.responses = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.reject and "prompt_cache_key" in kwargs:
            raise TypeError("prompt_cache_key")
        usage = SimpleNamespace(input_tokens=100, output_tokens=20, input_tokens_details=SimpleNamespace(cached_tokens=80),
                                output_tokens_details=SimpleNamespace(reasoning_tokens=5))
        return SimpleNamespace(output_parsed=self.parsed, usage=usage)


class FakeClaude:
    def __init__(self, parsed):
        self.calls, self.parsed = [], parsed
        self.messages = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        usage = SimpleNamespace(input_tokens=90, output_tokens=10, cache_read_input_tokens=70, cache_creation_input_tokens=3)
        return SimpleNamespace(parsed_output=self.parsed, usage=usage)


def test_openai_news_call_uses_cache_key_and_effort():
    fake = FakeOpenAI(NEWS)
    result, usage = clients.generate(fake, None, "OpenAI", "GPT-5.6 Luna", "haber", "Orta")
    call = fake.calls[0]
    assert result is NEWS and call["instructions"] == SYSTEM_PROMPT and call["text_format"] is NewsOutput
    assert call["reasoning"] == {"effort": "medium"} and call["max_output_tokens"] == 2600
    assert call["prompt_cache_key"] == "axion-haber-studio-v7" and call["model"] == "gpt-5.6-luna"
    assert usage == {"input_tokens": 100, "output_tokens": 20, "cached_input_tokens": 80, "cache_creation_input_tokens": 0,
                     "reasoning_tokens": 5, "requests": 1, "provider": "OpenAI", "model": "gpt-5.6-luna"}


def test_openai_falls_back_without_cache_key_on_old_sdk():
    fake = FakeOpenAI(NEWS, reject_cache_key=True)
    clients.generate(fake, None, "OpenAI", "GPT-5.6 Luna", "haber", "Kapalı (Tasarruflu)", 1800)
    assert len(fake.calls) == 2 and "prompt_cache_key" not in fake.calls[1] and fake.calls[1]["max_output_tokens"] == 1800


def test_claude_news_call_caches_system_prompt_and_maps_thinking():
    fake = FakeClaude(NEWS)
    _, usage = clients.generate(None, fake, "Claude", "", "haber", "Kapalı (Tasarruflu)")
    call = fake.calls[0]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"} and call["thinking"] == {"type": "disabled"}
    assert "output_config" not in call and call["model"] == CLAUDE_MODEL
    clients.generate(None, fake, "Claude", "", "haber", "Yüksek")
    assert fake.calls[1]["output_config"] == {"effort": "high"} and "thinking" not in fake.calls[1]
    assert usage["cached_input_tokens"] == 70 and usage["cache_creation_input_tokens"] == 3 and usage["provider"] == "Claude"


def test_headlines_are_small_calls_and_turkish_uppercase():
    fake = FakeOpenAI(HeadlineOutput(baslik1=" ığdır'da kaza ", baslik2="şoför yaralandı"))
    output, usage = clients.regenerate_headlines(fake, None, "OpenAI", "GPT-5.6 Luna", "içerik")
    call = fake.calls[0]
    assert (output.baslik1, output.baslik2) == ("IĞDIR'DA KAZA", "ŞOFÖR YARALANDI")
    assert call["instructions"] == HEADLINE_SYSTEM_PROMPT and call["max_output_tokens"] == 450
    assert call["reasoning"] == {"effort": "none"} and call["prompt_cache_key"] == "axion-haber-headline-v7"
    assert "<HABER_ICERIGI>\niçerik\n</HABER_ICERIGI>" in call["input"] and usage["requests"] == 1
    claude = FakeClaude(HeadlineOutput(baslik1="a", baslik2="b"))
    clients.regenerate_headlines(None, claude, "Claude", "", "içerik")
    assert claude.calls[0]["max_tokens"] == 500 and claude.calls[0]["thinking"] == {"type": "disabled"}
