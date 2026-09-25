"""Haber başına tahmini maliyet ve önbellek sayacı (v3.3; API yok)."""

from __future__ import annotations

import pytest

from apps.news_studio.ai import cost


def test_openai_cost_counts_cached_and_written_input_separately():
    # OpenAI: input_tokens önbellekten okunanı ve yazılanı içerir; düşünme çıktının içinde (iki kez sayılmaz).
    usage = {"provider": "OpenAI", "model": "gpt-5.6-luna", "input_tokens": 3000, "cached_input_tokens": 1800,
             "cache_creation_input_tokens": 0, "output_tokens": 1000, "reasoning_tokens": 300}
    assert cost.cost_usd(usage) == pytest.approx((1200 * 0.20 + 1800 * 0.02 + 1000 * 1.20) / 1e6)
    assert cost.cache_share(usage) == pytest.approx(0.6)


def test_claude_cost_uses_one_hour_write_price():
    usage = {"provider": "Claude", "model": "claude-sonnet-5", "input_tokens": 1200, "cached_input_tokens": 0,
             "cache_creation_input_tokens": 1800, "output_tokens": 1000}
    assert cost.cost_usd(usage) == pytest.approx((1200 * 2 + 1800 * 4 + 1000 * 10) / 1e6)
    assert cost.cache_share(usage) == 0
    assert cost.cost_usd({"model": "bilinmeyen"}) is None


def test_cache_counter_is_an_estimate_from_the_last_news(tmp_path):
    usage = {"provider": "OpenAI", "model": "gpt-5.6-luna", "cached_input_tokens": 0, "cache_creation_input_tokens": 0}
    cost.touch(tmp_path, usage, now=1000.0)  # önbellek tutmadı (ikisi de 0): sayaç başlamaz
    assert cost.minutes_left(tmp_path, "OpenAI", "gpt-5.6-luna", now=1000.0) == 0
    cost.touch(tmp_path, {**usage, "cache_creation_input_tokens": 1700}, now=1000.0)
    assert cost.minutes_left(tmp_path, "OpenAI", "gpt-5.6-luna", now=1000.0 + 10 * 60) == 20
    assert cost.minutes_left(tmp_path, "OpenAI", "gpt-5.6-luna", now=1000.0 + 31 * 60) == 0
    assert cost.minutes_left(tmp_path, "Claude", "claude-sonnet-5", now=1000.0) == 0  # model başına ayrı
