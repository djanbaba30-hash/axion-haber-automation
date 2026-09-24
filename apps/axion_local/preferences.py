"""Editörün son kullandığı ayarlar (üslup, model, spiker, ses ince ayarları): data/ayarlar.json."""

from __future__ import annotations

import json
from typing import Any

from .store import data_dir

PREFERENCES_FILENAME = "ayarlar.json"


def preferences_path():
    return data_dir() / PREFERENCES_FILENAME


def load_preferences() -> dict[str, Any]:
    try:
        data = json.loads(preferences_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_preferences(preferences: dict[str, Any]) -> None:
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(preferences, ensure_ascii=False, indent=2), encoding="utf-8")


def remember(session_state, defaults: dict[str, Any], choices: dict[str, list] | None = None) -> None:
    """Widget anahtarlarını kayıtlı ayarlarla (yoksa varsayılanla) başlatır; geçersiz seçimleri düzeltir."""
    saved = load_preferences()
    choices = choices or {}
    for key, default in defaults.items():
        value = session_state.get(key, saved.get(key, default))
        if key in choices and value not in choices[key]:
            value = default
        session_state[key] = value


def persist(session_state, keys) -> None:
    """Ayarlar değiştiyse diske yazar."""
    current = {key: session_state[key] for key in keys if key in session_state}
    if current != session_state.get("_saved_preferences"):
        save_preferences({**load_preferences(), **current})
        session_state["_saved_preferences"] = current
