"""Düzeltmelerden öğrenme kaydı (v4.0.0-alpha.5, editör kararı): sistemin önerdiği ↔ editörün son hâli.

Kaydedilenler: başlıklar, seslendirme ve paylaşım metni (modelin son çıktısı ↔ kaydedilen), elle değiştirilen sahneler,
kesit aralığı (önerilen olay anı ↔ seçilen). Tasarım ve kesit ekleme kaydedilmez (editör: önemsiz). Çalışma zamanında
ek model çağrısı yok: geliştirici (Claude/GPT) kaydı belli aralıklarla okuyup istemi ve kuralları düzeltir.

`data/duzeltmeler.jsonl`: projeler 3 günde silinse de silinmez. Aynı haber/sahne/kesit yeniden kaydedilince eski satır
yerine yazılır (son hâl). Repo herkese açık: kayıt internete gönderilmez, editör Geliştirici bilgileri'nden indirip
sohbette yollar.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any

from apps.axion_local.store import data_dir

FILENAME = "duzeltmeler.jsonl"
RAW_CHARS = 2000  # ham haberin başı: istemi düzeltirken bağlam yeter, dosya küçük kalır
NEWS_FIELDS = {"baslik1": "1. başlık", "baslik2": "2. başlık", "icerik": "paylaşım metni", "tts": "seslendirme"}
_LOCK = threading.Lock()


def _path():
    return data_dir() / FILENAME


def entries() -> list[dict[str, Any]]:
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except ValueError:
            continue  # yarım yazılmış satır: atla
    return result


def record(kind: str, project: str, key: str, data: dict[str, Any]) -> None:
    """Satırı yazar; aynı (tür, proje, anahtar) varsa yerine."""
    entry = {"tur": kind, "proje": project, "anahtar": key, "tarih": datetime.now().isoformat(timespec="seconds"), **data}
    with _LOCK:
        kept = [e for e in entries() if (e.get("tur"), e.get("proje"), e.get("anahtar")) != (kind, project, key)]
        path = _path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".yaziliyor")
            temporary.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in [*kept, entry]),
                                 encoding="utf-8")
            temporary.replace(path)
        except OSError:  # kayıt editörün işini hiçbir zaman durdurmaz
            logging.getLogger(__name__).exception("Düzeltme kaydı yazılamadı")


def news(project: str, model_output: dict[str, str] | None, final: dict[str, str], raw: str, meta: dict[str, Any]) -> None:
    """Haber Stüdyosu kaydedince: modelin son çıktısı ↔ editörün kaydettiği (değişen alanlar önce/sonra)."""
    if not model_output:
        return  # kayıtlı haber açılıp yeniden kaydedildi: modelin çıktısı bu oturumda yok
    changed = {name: {"model": model_output.get(name, ""), "editor": final.get(name, "")}
               for name in NEWS_FIELDS if model_output.get(name, "").strip() != final.get(name, "").strip()}
    record("haber", project, "", {**meta, "ham_haber": raw[:RAW_CHARS], "degisen": changed,
                                  "degismeyen": [name for name in NEWS_FIELDS if name not in changed]})


def scene(project: str, number: int, spoken: str, before: dict[str, Any], after: dict[str, Any]) -> None:
    """Editör kurguda bir sahneyi değiştirdi (sahne no 1'den; önceki/yeni: pencere, açıklama, kim seçmişti)."""
    record("sahne", project, str(number), {"sahne": number, "soylenen": spoken, "onceki": before, "yeni": after})


def soundbite(project: str, filename: str, suggested: tuple[float, float] | None, chosen: tuple[float, float],
              placement: str, quoted: list[tuple[float, float]] = ()) -> None:
    """Kesit eklendi: önerilen aralık (olay anı) ↔ editörün seçtiği; `quoted`: haberdeki alıntıların dökümdeki
    aralıkları (v4.1; öneri doğru muydu)."""
    record("kesit", project, f"{filename}@{chosen[0]:.1f}", {
        "video": filename, "yer": placement, "onerilen": list(suggested) if suggested else None,
        "secilen": list(chosen), "degisti": suggested is None or any(abs(a - b) > 0.25 for a, b in zip(suggested, chosen)),
        **({"alintilar": [list(span) for span in quoted]} if quoted else {})})


def summary() -> str:
    """Geliştirici bilgileri için tek satır."""
    rows = entries()
    if not rows:
        return "Düzeltme kaydı boş."
    news_rows = [e for e in rows if e.get("tur") == "haber"]
    changed = {name: sum(1 for e in news_rows if name in e.get("degisen", {})) for name in NEWS_FIELDS}
    parts = [f"{len(news_rows)} haber (" + ", ".join(f"{label} {changed[name]}" for name, label in NEWS_FIELDS.items())
             + " kez düzeltildi)"]
    parts.append(f"{sum(1 for e in rows if e.get('tur') == 'sahne')} sahne değişikliği")
    bites = [e for e in rows if e.get("tur") == "kesit"]
    parts.append(f"{len(bites)} kesit ({sum(1 for e in bites if e.get('degisti'))} aralığı değiştirildi)")
    return "Düzeltme kaydı: " + " · ".join(parts)


def export() -> bytes:
    try:
        return _path().read_bytes()
    except OSError:
        return b""


def download_button(container: Any) -> None:
    """Geliştirici bilgileri: özet + "📝 Düzeltme kaydını indir" (tüm haberler; editör sohbette geliştiriciye yollar)."""
    container.caption(summary())
    if _path().exists():
        container.download_button(
            "📝 Düzeltme kaydını indir", export, file_name=FILENAME, mime="application/x-ndjson", on_click="ignore",
            help="Başlık/seslendirme/paylaşım metni düzeltmelerin, sahne ve kesit değişikliklerin (tüm haberler). "
                 "İnternete gönderilmez; istemi iyileştirmek için Claude'a/GPT'ye sen yollarsın.")
