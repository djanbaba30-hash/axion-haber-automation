import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def log_run(db_path: Path, *, raw_text, result, usage, style, provider, model, validation):
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS news_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                provider TEXT, model TEXT, style TEXT,
                source_chars INTEGER, caption_chars INTEGER, tts_chars INTEGER,
                usage_json TEXT, validation_json TEXT,
                headline1 TEXT, headline2 TEXT, caption TEXT, tts TEXT
            )""")
            con.execute("INSERT INTO news_runs(provider,model,style,source_chars,caption_chars,tts_chars,usage_json,validation_json,headline1,headline2,caption,tts) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(
                provider,model,style,len(raw_text),len(result.icerik),len(result.tts),json.dumps(usage,ensure_ascii=False),json.dumps(validation,ensure_ascii=False),result.baslik1,result.baslik2,result.icerik,result.tts))
    except Exception as exc:
        logger.warning("News history log yazılamadı: %s", exc, exc_info=True)


def delete_runs_before(db_path: Path, cutoff: datetime) -> int:
    """Saklama süresi dolan üretim kayıtlarını siler. `cutoff` yerel saattir; tablo UTC tutar."""
    if not db_path.exists():
        return 0
    utc = cutoff.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(db_path) as con:
            return con.execute("DELETE FROM news_runs WHERE created_at < ?", (utc,)).rowcount
    except sqlite3.Error as exc:
        logger.warning("Eski üretim kayıtları silinemedi: %s", exc)
        return 0
