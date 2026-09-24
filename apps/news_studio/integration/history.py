import sqlite3
from pathlib import Path
import json


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
    except Exception:
        pass
