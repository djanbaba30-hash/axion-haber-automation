from pathlib import Path

CLAUDE_MODEL = "claude-sonnet-5"
OPENAI_MODELS = {
    "GPT-5.6 Luna": "gpt-5.6-luna",
    "GPT-5.6 Sol": "gpt-5.6-sol",
}

BASE_CPS = 320 / 21
BASE_SPEED = 1.11
TTS_TOLERANCE_CHARS = 30
TTS_HARD_MIN_RATIO = 0.6
CORRECTION_MAX_TOKENS = 1800
AI_TIMEOUT_SECONDS = 90.0
TTS_TIMEOUT_SECONDS = 90.0
RETRY_ATTEMPTS = 3

TTS_DURATION_PRESETS = {
    "20–22 saniye": (20.0, 22.0),
    "23–24 saniye": (23.0, 24.0),
    "25–26 saniye": (25.0, 26.0),
    "27–29 saniye": (27.0, 29.0),
    "30–32 saniye": (30.0, 32.0),
}

DATA_DIR = Path("data")
CALIBRATION_PATH = DATA_DIR / "tts_calibration.json"
HISTORY_DB_PATH = DATA_DIR / "history.sqlite3"
