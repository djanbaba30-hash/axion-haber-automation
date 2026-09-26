"""Faz 4 (v3.6, editör kararı): sahneleri Luna seçer; kurallar yalnız yedek.

Haber başına tek, görüntüsüz Luna çağrısı: haberin anlatımı (paylaşım metninin başı), seslendirme sahneleri
(duraklamalarda kesilmiş, söylenen metinle) ve analizdeki pencereler (kaynak zamanı, çekim, tür, açıklama, mekân,
karedeki yazı; v4.0'dan beri fotoğraflar da) gider. Luna önce olay örgüsünü yazar, her sahneye aşama verir (olay anı, müdahale, sonuç…), sonra
sahneye bir pencere ve o penceredeki başlangıç anını seçer (v3.7: "haberin konusunu bilerek kurgu"). Kesme zamanları, kadraj (bulanık dolgu yok, dikeyde sabit), kaynak sesli kesitler ve aynı
anın iki kez kullanılmaması kurallarla kalır (`rough_cut.plan_rough_cut(picks=...)`). Luna'ya ulaşılamazsa ya da
anahtar yoksa kurallı kurgu kullanılır.

Plan `kurgu_plani.json`'a yazılır: girdiler (imza) değişmedikçe "Videoyu yeniden oluştur" yeni çağrı yapmaz;
"Sahneleri yeniden seç" önceki seçimi "editör beğenmedi" notuyla gönderip yeni plan ister.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, create_model

from shared.media_models import EditorialRole

from .rough_cut import Prepared, _generic, plan_rough_cut, prepare
from .soundbites import Soundbite
from .visual_analysis import LUNA_MODEL, calculate_cost, get_reasoning_tokens, get_usage_value

PLAN_FILENAME = "kurgu_plani.json"
REASONING_EFFORT = "low"  # editör: "elden geldiğince verimli"; kurgu kararı kısa bir akıl yürütme
MAX_OUTPUT_TOKENS = 6000  # düşünme dahil
TIMEOUT_SECONDS = 120

STAGES = ("olay_oncesi", "olay_ani", "olay_yeri", "mudahale", "sonuc", "aciklama", "genel")
SYSTEM_PROMPT = """Haber videosu kurgucususun. Haberi anlayarak seslendirmenin her sahnesine bir görüntü penceresi seç.

Girdi: başlıklar; haberin kendisi (olayın tam anlatımı); seslendirme sahneleri (sıra no, süre, o sırada söylenen);
görüntü pencereleri (id, video/çekim, kaynak zamanı, tür/rol, kısa açıklama, özne, mekân, karede okunan yazı).
Pencereler kaynaktaki sırasıyladır; aynı çekimin pencereleri tek kesintisiz çekimin ardışık parçalarıdır.
"fotoğraf" pencereleri hareketsiz karedir (videoda yavaş yakınlaşmayla gösterilir): videolar gibi seçilebilir, her
fotoğraf en fazla bir kez; kaynak_bas 0.
Görüntü açıklamaları kısadır: haberle bağını tür, mekân ve karedeki yazıdan kur (ör. "OLAY YERİ İNCELEME" yazılı
araç = soruşturma/olay yeri; ambulans = müdahale; hasarlı araç = olayın sonucu).

Önce olay_orgusu: haberin akışını en fazla 2 cümleyle yaz (ne oldu → kim müdahale etti → sonuç). Sonra her sahne
için asama: seslendirmenin o an anlattığı aşama (olay_oncesi, olay_ani, olay_yeri, mudahale, sonuc, aciklama,
genel). Pencereyi bu aşamayı en iyi gösterenlerden seç.

Kurallar (önem sırasıyla):
1. Olay örgüsü: görüntüler olayın akışını izlesin; sahnenin aşamasına uyan pencere gelsin. Olay anının görüntüsü
   varsa olay anlatılırken o kullanılsın.
2. Tekrar yok: bir pencereyi yalnız bir kez seç. Malzeme gerçekten yetmiyorsa aynı pencerenin kullanılmamış bir anını
   seç (farklı kaynak_bas). Aynı çekimden alınan parçalar videoda kaynaktaki sırasıyla gelsin.
3. İlk sahne videonun kapağıdır: başlıktaki olayı en net gösteren, öznesi belli pencere; manzara, grafik, genel
   görüntü ya da konuşan kişi (röportaj) değil.
4. Konuşan kişi (portre/röportaj) görüntüsünü ancak seslendirme o kişiden söz ediyorsa ya da başka seçenek yoksa seç.
5. Öznesi olmayan genel görüntüler (boş yol, ağaçlık, genel trafik) yalnız başka seçenek yoksa. KESİT diye
   işaretli pencereleri seçme (başka yerde kaynak sesiyle kullanılıyor).
6. kaynak_bas: sahnenin kaynaktaki başlangıç anı (saniye, pencerenin içinde). Sahne süresi kadar görüntü kalacak
   şekilde seç; "görülen an" açıklamanın kesin doğru olduğu andır.

Her sahne için tam bir satır döndür: parca (sahne no), asama, pencere (id), kaynak_bas."""
STAGE_LABELS = {"olay_oncesi": "olay öncesi", "olay_ani": "olay anı", "olay_yeri": "olay yeri", "mudahale": "müdahale",
                "sonuc": "sonuç", "aciklama": "açıklama", "genel": "genel"}
STORY_CHARS = 900  # haberin anlatımı (paylaşım metninin başı): olay örgüsü için yeterli, token az

RETRY_NOTE = ("Editör aşağıdaki önceki kurguyu beğenmedi. Kurallara uyarak farklı bir seçim yap; aynı sahnelere aynı "
              "pencereleri koyma (malzeme yetmiyorsa sırayı ve anları değiştir).")


def window_ids(prep: Prepared) -> list[str]:
    return [f"P{index + 1}" for index in range(len(prep.candidates))]


def build_prompt(prep: Prepared) -> str:
    """Luna'ya giden metin (önceki kurgu notu hariç: imza bundan hesaplanır)."""
    news = prep.project.news
    videos: dict[str, int] = {}
    photos: dict[str, int] = {}
    shots: dict[tuple[str, str], int] = {}
    rows: list[list[Any]] = []  # [ilk id, son id, konum, başlangıç, bitiş, açıklama, notlar, pencere sayısı]
    for pid, c in zip(window_ids(prep), prep.candidates):
        if c.photo:
            place = f"fotoğraf {photos.setdefault(c.asset_id, len(photos) + 1)}"
        else:
            video = videos.setdefault(c.asset_id, len(videos) + 1)
            shot = shots.setdefault((c.asset_id, c.shot_id), sum(1 for asset, _ in shots if asset == c.asset_id) + 1)
            place = f"video {video} çekim {shot}"
        notes = []
        if c.role is not EditorialRole.UNKNOWN:
            notes.append(f"{c.visual_type.value}/{c.role.value}")
        notes.append("genel görüntü" if _generic(c) else "özne var")
        if c.people:
            notes.append("insan var")
        if c.location and c.location != "unknown":
            notes.append(f"mekân: {c.location}")
        text = "; ".join(part.strip() for part in c.visible_text.split(";") if part.strip() and part.strip().upper() != "DHA")
        if text:
            notes.append(f"yazı: {text[:60]}")
        if any(a == c.asset_id and s < c.end and c.start < e for a, s, e in prep.blocked):
            notes.append("KESİT")
        last = rows[-1] if rows else None
        if last and last[2] == place and last[5] == c.description and last[6] == notes:
            last[1], last[4], last[7] = pid, c.end, last[7] + 1  # aynı çekimde aynı görünen ardışık pencereler: tek satır
            continue
        rows.append([pid, pid, place, c.start, c.end, c.description, notes, 1,
                     f"görülen an {c.seen:.1f}" if c.seen is not None else ""])
    lines = []
    for first, last, place, start, end, description, notes, count, seen in rows:
        ids = first if count == 1 else f"{first}–{last} ({count} ardışık pencere, hepsi aynı görünüyor)"
        extra = [*notes, seen] if count == 1 and seen else notes
        span = "hareketsiz" if place.startswith("fotoğraf") else f"{start:.1f}–{end:.1f} sn"
        lines.append(f"{ids} | {place} | {span} | {description or '-'} | " + " · ".join(extra))
    slots = []
    for number, (start, end, text) in enumerate(prep.slots(), 1):
        mark = " (kapak)" if number == 1 else ""
        slots.append(f"{number}{mark} | {end - start:.1f} sn | {text or '(sessiz, görüntü devam)'}")
    story = " ".join(news.caption.replace("Kaynak: DHA", "").split())
    story = story if len(story) <= STORY_CHARS else story[:STORY_CHARS].rsplit(" ", 1)[0] + " …"
    return (f"<basliklar>{news.headline_1} / {news.headline_2}</basliklar>\n"
            f"<haber>{story}</haber>\n"
            f"<sahneler>\n" + "\n".join(slots) + "\n</sahneler>\n"
            "<pencereler>\n" + "\n".join(lines) + "\n</pencereler>")


def signature(prompt: str) -> str:
    return hashlib.sha256(f"{LUNA_MODEL}\n{SYSTEM_PROMPT}\n{prompt}".encode()).hexdigest()[:16]


def _response_model(ids: list[str]) -> type[BaseModel]:
    # Alan sırası düşünme sırasıdır: önce olay örgüsü, sonra sahne başına aşama, sonra pencere.
    scene = create_model("LunaSahne", parca=(int, ...), asama=(Literal[STAGES], ...),
                         pencere=(Literal[tuple(ids)], ...), kaynak_bas=(float, ...))
    return create_model("LunaKurgu", olay_orgusu=(str, ...), sahneler=(list[scene], ...))


def request(prompt: str, ids: list[str], api_key: str, client: Any = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tek Luna çağrısı → {"olay_orgusu", "sahneler": [{"parca", "asama", "pencere", "kaynak_bas"}]}, kullanım."""
    client = client or OpenAI(api_key=api_key, timeout=TIMEOUT_SECONDS)
    response = client.responses.parse(
        model=LUNA_MODEL,
        input=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        text_format=_response_model(ids),
        reasoning={"effort": REASONING_EFFORT},
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Luna kurgu planı döndürmedi.")
    usage = getattr(response, "usage", None)
    input_tokens, output_tokens = get_usage_value(usage, "input_tokens"), get_usage_value(usage, "output_tokens")
    return parsed.model_dump(), {
        "model": LUNA_MODEL, "input_tokens": input_tokens, "output_tokens": output_tokens,
        "reasoning_tokens": get_reasoning_tokens(usage) if usage is not None else 0,
        "estimated_cost_usd": calculate_cost(input_tokens, output_tokens), "api_calls": 1,
    }


def to_picks(scenes: list[dict[str, Any]], prep: Prepared) -> dict[int, tuple[int, float | None]]:
    """Luna'nın satırları → {sahne sırası (0'dan): (aday no, kaynak başlangıcı)}; geçersiz satır atlanır."""
    ids = {pid: index for index, pid in enumerate(window_ids(prep))}
    count = len(prep.slots())
    picks: dict[int, tuple[int, float | None]] = {}
    for scene in scenes:
        slot, index = int(scene.get("parca", 0)) - 1, ids.get(str(scene.get("pencere")))
        if not 0 <= slot < count or index is None or slot in picks:
            continue
        candidate = prep.candidates[index]
        start = scene.get("kaynak_bas")
        valid = isinstance(start, (int, float)) and candidate.start - 0.05 <= float(start) < candidate.end
        picks[slot] = (index, float(start) if valid else None)
    return picks


def _read(folder: Path | None) -> dict[str, Any] | None:
    try:
        return json.loads((folder / PLAN_FILENAME).read_text(encoding="utf-8")) if folder else None
    except (OSError, ValueError):
        return None


def plan(edit_project: dict[str, Any], media_library: dict[str, Any], soundbites: list[Soundbite] | None,
         api_key: str, folder: Path | None, replan: bool = False, client: Any = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Kurgu planı: kayıtlı Luna planı (girdiler aynıysa), yoksa yeni Luna çağrısı, olmazsa kurallar.
    Döndürür: (EditProject sözlüğü, bilgi {"kaynak": "luna"|"kayitli"|"kural", "not", "kullanim"})."""
    prep = prepare(edit_project, media_library, soundbites)
    prompt = build_prompt(prep)
    sig = signature(prompt)
    stored = _read(folder)
    if stored and stored.get("imza") == sig and not replan:
        picks = to_picks(stored.get("sahneler", []), prep)
        return plan_rough_cut(edit_project, media_library, soundbites, picks=picks), {
            "kaynak": "kayitli", "not": "", "kullanim": stored.get("kullanim", {}), "secilen": len(picks)}
    if not api_key:
        return plan_rough_cut(edit_project, media_library, soundbites), {
            "kaynak": "kural", "not": "OPENAI_API_KEY yok; sahneler kurallarla seçildi.", "kullanim": {}}
    full = prompt
    if replan and stored and stored.get("sahneler"):
        previous = "\n".join(f"{s['parca']}: {s['pencere']} @ {s['kaynak_bas']:.1f}" for s in stored["sahneler"])
        full += f"\n<onceki_kurgu>\n{RETRY_NOTE}\n{previous}\n</onceki_kurgu>"
    try:
        answer, usage = request(full, window_ids(prep), api_key, client)
    except Exception as error:  # noqa: BLE001 — ağ, kota, şema: video yine çıksın
        return plan_rough_cut(edit_project, media_library, soundbites), {
            "kaynak": "kural", "not": f"Luna'ya ulaşılamadı, sahneler kurallarla seçildi: {str(error)[:200]}", "kullanim": {}}
    scenes = answer.get("sahneler", [])
    picks = to_picks(scenes, prep)
    if folder is not None:
        (folder / PLAN_FILENAME).write_text(json.dumps({
            "imza": sig, "tarih": datetime.now(timezone.utc).isoformat(timespec="seconds"), "yeniden": replan,
            "olay_orgusu": answer.get("olay_orgusu", ""), "sahneler": scenes, "kullanim": usage},
            ensure_ascii=False, indent=1), encoding="utf-8")
    missing = len(prep.slots()) - len(picks)
    note = f"Luna {missing} sahneyi boş bıraktı; onlar kurallarla seçildi." if missing else ""
    return plan_rough_cut(edit_project, media_library, soundbites, picks=picks), {
        "kaynak": "luna", "not": note, "kullanim": usage, "secilen": len(picks)}


def plan_summary(plan: dict[str, Any] | None) -> list[str]:
    """Geliştirici bilgileri için: Luna'nın olay örgüsü ve sahne başına aşama/pencere."""
    if not plan:
        return []
    lines = [f"Olay örgüsü (Luna): {plan['olay_orgusu']}"] if plan.get("olay_orgusu") else []
    scenes = [f"{s.get('parca')}. {STAGE_LABELS.get(s.get('asama'), s.get('asama') or '?')} → {s.get('pencere')}"
              for s in plan.get("sahneler", [])]
    if scenes:
        lines.append("Sahneler: " + " · ".join(scenes))
    return lines
