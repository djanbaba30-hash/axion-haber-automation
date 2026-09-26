"""Kural tabanlı kaba kurgu (Faz 3): TTS cümlelerine sahne penceresi seçer. API çağrısı yok.

Kesmeler seslendirmedeki duraklamalara (cümle sonu, virgül, nefes arası) konur; her sahne MIN–MAX_CLIP_SECONDS.
Her kesit için o sırada söylenen kelimeler, Luna açıklaması, rol ve kullanım geçmişine göre en iyi pencere seçilir.
v3.6'dan beri seçimi Luna yapar (`luna_edit.py`); bu modül ortak hazırlık, yedek ve Luna'nın bıraktığını doldurma.
Fotoğraflar (v4.0) da adaydır: hareketsiz kare, yavaş yakınlaşmayla (alan tam dolu, bulanık dolgu yok).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.axion_template import VIDEO_HEIGHT, VIDEO_WIDTH, video_seconds
from shared.edit_models import Clip, ClipOrigin, EditProject, Framing, FramingMode, TrackKind
from shared.media_models import EditorialRole, FocusPoint, ImageAsset, MediaLibrary, Region, VideoAsset, VisualType

from .soundbites import PLACEMENT_LABELS, Soundbite, ordered
from .video_asset import image_geometry

# Sahne süresi: çok hızlı geçiş olmasın (editör: "yarım saniyede bir sahne değişmesin"),
# 5 sn'den uzun kesintisiz konuşmada araya sahne girebilir.
MIN_CLIP_SECONDS = 2.0
IDEAL_CLIP_SECONDS = 3.0
MAX_CLIP_SECONDS = 5.0
SENTENCE_END = set(".!?…")
PAUSE_PUNCTUATION = set(".!?…,;:\"”'’»)")
EDGE_SECONDS = 0.2  # Shot geçişindeki karışık karelerden kaçın.
# Özne kaydırması: özne kadrajdan bu oranda büyükse kaydır; hız saniyede kare genişliğinin %3'ü (editör ayarı).
PAN_MIN_RATIO = 1.15
PAN_SPEED = 0.03
# Fotoğraf: kaynakta süresi yok; sahneye yetecek sanal bir "çekim" (en uzun sahne + kenar payları). Yakınlaşma
# saniyede %3 (5 sn'de 1,15x); öznenin tamamı hep kadrajda kalır.
PHOTO_SECONDS = MAX_CLIP_SECONDS + 2 * EDGE_SECONDS
PHOTO_ZOOM = 0.03

# Röportaj (konuşan kişi) sessiz dolgu olarak kötü durur; başka seçenek yoksa kullanılır.
ROLE_BONUS = {
    EditorialRole.PORTRAIT: -6.0,
    EditorialRole.GENERIC_BROLL: -0.5,
}
# İlk sahne aynı zamanda sosyal medyada videonun kapağı (editör): olayı net gösteren, başlıkla eşleşen sahne öne geçer.
OPENING_ROLES = {EditorialRole.ESTABLISHING, EditorialRole.ACTION}
OPENING_TYPES = {VisualType.EVENT}
WEAK_COVER_ROLES = {EditorialRole.GENERIC_BROLL, EditorialRole.PORTRAIT}
WEAK_COVER_TYPES = {VisualType.GRAPHIC, VisualType.DOCUMENT, VisualType.SCREEN, VisualType.LANDSCAPE}

# Haber cümlesindeki kavram → görüntüde karşılığı (kök başları; Türkçe ekler yüzünden önek eşleşmesi).
CONCEPTS = [
    ({"yaral", "hastane", "sağlık", "ambulans", "tedavi"}, {"ambulans", "sağlık", "sedye", "acil"}),
    ({"polis", "gözalt", "güvenlik", "emniyet", "jandarma"}, {"polis", "jandarma", "ekip", "şerit"}),
    ({"itfaiye", "yangın", "sönd", "alev"}, {"itfaiye", "yangın", "alev", "duman"}),
    ({"çarp", "kaza", "savrul", "hasar", "devril"}, {"hasar", "enkaz", "parça", "kırı", "çarp"}),
]
STOPWORDS = {"olarak", "sonra", "ardından", "sırasında", "belirtildi", "alındı", "yerinde", "arasında", "bulunan", "bulunduğu"}
PLATE = re.compile(r"\b\d{2}\s?[A-ZÇĞİÖŞÜ]{1,3}\s?\d{2,4}\b")


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.replace("I", "ı").replace("İ", "i").lower())


def _has(tokens: list[str], stems: set[str]) -> bool:
    return any(token.startswith(stem) for token in tokens for stem in stems)


@dataclass
class Candidate:
    asset_id: str
    shot_id: str
    shot_start: float
    shot_end: float
    start: float
    end: float
    order: int
    tokens: list[str]
    role: EditorialRole
    visual_type: VisualType
    confidence: float
    plate: bool
    description: str
    content_region: Region | None = None
    focus: FocusPoint | None = None
    subject: Region | None = None
    frame_aspect: float = 16 / 9  # kaynak genişlik / yükseklik (ekranda görünen)
    # Dikey (yanları dolgulu) çekimde tüm video boyunca sabit kadraj yüksekliği (özne merkezlerinin ortalaması).
    anchor_y: float | None = None
    seen: float | None = None  # Luna'nın bu pencerede gördüğü karelerin ortalama zamanı (açıklama o an için doğru)
    shot_count: int = 1  # aynı videodaki çekim sayısı (tek uzun çekimde anlatım sırası)
    # Luna'nın sahne seçimine ipucu (v3.7): görünen mekân, karede okunan yazı (ör. "OLAY YERİ İNCELEME"), insan var mı.
    location: str = ""
    visible_text: str = ""
    people: bool | None = None
    photo: bool = False  # hareketsiz kare (v4.0): kaynak aralığı sanal, render yakınlaşmayla gösterir


@dataclass
class _Usage:
    # Çekim başına kullanılan kaynak aralıkları: aynı an iki kez gösterilmez; bir pencere seçilince görüntü o
    # pencereden gelir (v3.4: çekim başına tek imleç, geç bir pencereden sonra öncekileri "tekrar" sayıyordu).
    used: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    count: dict[str, int] = field(default_factory=dict)
    window_count: dict[tuple[str, float], int] = field(default_factory=dict)
    # Kaynak sesli kesit olarak kullanılan aralıklar (asset_id, başlangıç, bitiş): dolgu görüntüsünde tekrar etmesin.
    blocked: list[tuple[str, float, float]] = field(default_factory=list)


def _candidates(library: MediaLibrary) -> list[Candidate]:
    items: list[Candidate] = []
    for asset in library.assets:
        if isinstance(asset, ImageAsset):
            photo = _photo_candidate(asset, len(items))
            if photo:
                items.append(photo)
            continue
        for shot in asset.shots:
            windows = shot.analysis_windows or []
            spans = [(w.start_seconds, w.end_seconds, w.visual or shot.visual,
                      [f.timestamp_seconds for f in w.frames]) for w in windows]
            if not spans:
                spans = [(shot.start_seconds, shot.end_seconds, shot.visual, [])]
            for start, end, visual, seen in spans:
                description = visual.description if visual else ""
                items.append(
                    Candidate(
                        asset_id=asset.asset_id,
                        shot_id=shot.shot_id,
                        shot_start=shot.start_seconds,
                        shot_end=shot.end_seconds,
                        start=start,
                        end=end,
                        order=len(items),
                        tokens=_tokens(f"{description} {visual.location if visual else ''}"),
                        role=visual.editorial_role if visual else EditorialRole.UNKNOWN,
                        visual_type=visual.visual_type if visual else VisualType.UNKNOWN,
                        confidence=visual.confidence if visual else 0.0,
                        plate=bool(visual and PLATE.search(visual.visible_text.upper())),
                        description=description,
                        content_region=shot.content_region,
                        focus=visual.focus_point if visual else None,
                        subject=visual.subject_region if visual else None,
                        frame_aspect=asset.geometry.display.width / asset.geometry.display.height,
                        shot_count=len(asset.shots),
                        seen=sum(seen) / len(seen) if seen else None,
                        location=visual.location if visual else "",
                        visible_text=visual.visible_text if visual else "",
                        people=visual.visible_people if visual else None,
                    )
                )
    for asset_id in {c.asset_id for c in items}:
        own = [c for c in items if c.asset_id == asset_id]
        centers = [c.subject.y + c.subject.height / 2 for c in own if c.subject and not _generic(c)]
        anchor = sum(centers) / len(centers) if centers else 0.5
        for c in own:
            if c.content_region is not None:
                c.anchor_y = anchor
    return items


def _photo_candidate(asset: ImageAsset, order: int) -> Candidate | None:
    geometry = asset.geometry
    if geometry is None:  # v4.0 öncesi analiz: boyut kayıtlı değil, dosyadan okunur
        try:
            geometry = image_geometry(Path(asset.source.original_path))
        except (OSError, ValueError):
            return None  # dosya yok/bozuk: render da yapamaz
    visual = asset.visual
    description = visual.description if visual else ""
    return Candidate(
        asset_id=asset.asset_id, shot_id=asset.asset_id, shot_start=0.0, shot_end=PHOTO_SECONDS, start=0.0,
        end=PHOTO_SECONDS, order=order, tokens=_tokens(f"{description} {visual.location if visual else ''}"),
        role=visual.editorial_role if visual else EditorialRole.UNKNOWN,
        visual_type=visual.visual_type if visual else VisualType.UNKNOWN,
        confidence=visual.confidence if visual else 0.0,
        plate=bool(visual and PLATE.search(visual.visible_text.upper())), description=description,
        focus=visual.focus_point if visual else None, subject=visual.subject_region if visual else None,
        frame_aspect=geometry.width / geometry.height, location=visual.location if visual else "",
        visible_text=visual.visible_text if visual else "", people=visual.visible_people if visual else None,
        photo=True,
    )


def _generic(candidate: Candidate) -> bool:
    """Luna belirli bir özne göstermemiş (kutu asıl görüntünün neredeyse tamamı: ağaçlık, boş yol, genel trafik)."""
    s = candidate.subject
    if s is None:
        return True
    c = candidate.content_region or Region(x=0, y=0, width=1, height=1)
    overlap_w = max(0.0, min(s.x + s.width, c.x + c.width) - max(s.x, c.x))
    overlap_h = max(0.0, min(s.y + s.height, c.y + c.height) - max(s.y, c.y))
    return overlap_w * overlap_h >= 0.7 * c.width * c.height


def _source_range(candidate: Candidate, usage: _Usage, need: float,
                  prefer: float | None = None) -> tuple[float, float, bool]:
    """Pencereden kullanılabilir kaynak aralığı: (başlangıç, kullanılabilir süre, tekrar mı). Başlangıç her zaman
    pencerenin içindedir (görüntü seçilen pencereden gelir; klip sonraki pencereye taşabilir). `prefer`: Luna'nın
    istediği an (v3.6); kullanılmışsa ya da yetmiyorsa her zamanki sıraya düşülür."""
    lead = EDGE_SECONDS if candidate.start <= candidate.shot_start else 0.0
    shot_limit = candidate.shot_end - EDGE_SECONDS
    blocked = [(start, end) for asset, start, end in usage.blocked if asset == candidate.asset_id]
    taken = sorted(blocked + usage.used.get(candidate.shot_id, []))

    def first_free(begin: float, intervals: list[tuple[float, float]]) -> float:
        moved = True
        while moved:
            moved = False
            for start, end in intervals:
                if start - 1e-6 <= begin < end:
                    begin, moved = end, True
        return begin

    def limit_from(begin: float, intervals: list[tuple[float, float]]) -> float:
        return min([shot_limit, *(start for start, _ in intervals if begin < start < shot_limit)])

    begin = candidate.start + lead
    window_end = min(candidate.end, shot_limit)
    # Önce Luna'nın gördüğü karenin çevresi: elde çekimde kamera pencere içinde başka yere dönebilir (editörün
    # midibüs videosu); açıklama yalnız o an için kesin.
    starts = [begin]
    if candidate.seen is not None:
        starts.insert(0, min(max(begin, candidate.seen - min(need, MAX_CLIP_SECONDS) / 2), window_end - 0.5))
    if prefer is not None:
        # Çekimin sonuna yakın istenen an sahneye yetmiyorsa biraz önceden başlanır; yoksa kalan yarım saniye başka bir
        # sahneyle dolup göz kırpması gibi görünüyordu (editörün Sultangazi videosu, v3.6.2).
        prefer = min(prefer, shot_limit - min(need, MAX_CLIP_SECONDS))
        starts.insert(0, min(max(begin, prefer), window_end - 0.5))
    for start in starts:
        fresh = first_free(start, taken)
        if fresh < window_end - 0.5 and limit_from(fresh, taken) - fresh >= min(need, MIN_CLIP_SECONDS):
            return fresh, limit_from(fresh, taken) - fresh, False
    again = first_free(begin, blocked)
    return again, max(0.0, limit_from(again, blocked) - again), True


def _score(candidate: Candidate, segment_tokens: list[str], opening: bool, previous_shot: str | None, usage: _Usage,
           need: float, story: float | None = None) -> float:
    words = {t[:5] for t in segment_tokens if len(t) >= 5 and t not in STOPWORDS}
    score = 2.0 * sum(1 for stem in words if _has(candidate.tokens, {stem}))
    for news_stems, visual_stems in CONCEPTS:
        if _has(segment_tokens, news_stems) and _has(candidate.tokens, visual_stems):
            score += 3.0
    score += ROLE_BONUS.get(candidate.role, 0.0)
    if any(asset == candidate.asset_id and start < candidate.end and candidate.start < end for asset, start, end in usage.blocked):
        score -= 10.0
    if opening:
        if candidate.role in OPENING_ROLES or candidate.visual_type in OPENING_TYPES:
            score += 3.0
        if candidate.subject is not None:  # kapakta seçilebilir bir özne
            score += 1.0
        if candidate.role in WEAK_COVER_ROLES or candidate.visual_type in WEAK_COVER_TYPES:
            score -= 3.0
    if candidate.plate:
        score -= 1.0
    score += candidate.confidence * 0.5
    if candidate.shot_count > 1 or candidate.photo:  # birden çok çekim varsa çeşitlilik (tek çekimde hepsi aynı)
        score -= 3.0 * usage.count.get(candidate.shot_id, 0)
        if candidate.shot_id == previous_shot:
            score -= 8.0
    score -= 2.0 * usage.window_count.get((candidate.shot_id, candidate.start), 0)
    if _generic(candidate):
        score -= 5.0  # belirli bir özne yok (ağaçlık, boş yol): haberi anlatmaz
    if story is not None and candidate.shot_count <= 2 and not candidate.photo:
        # Tek uzun çekim (cep telefonu): olay kaynakta akışıyla anlatılır; seslendirmenin başı çekimin başına,
        # sonu sonuna yakın pencereden (editör: "olay örgüsü orada yazıyor").
        length = max(1e-6, candidate.shot_end - candidate.shot_start)
        position = ((candidate.start + candidate.end) / 2 - candidate.shot_start) / length
        score -= 4.0 * abs(position - story)
    _, available, repeated = _source_range(candidate, usage, need)
    if repeated:
        score -= 2.0
    if available < need:
        score -= 4.0  # Sahne kesit süresine yetmiyorsa kesme duraklama dışına düşer; tercih etme.
    if available < MIN_CLIP_SECONDS / 2:
        score -= 50.0
    return score


def _view_regions(candidate: Candidate, slot_aspect: float, seconds: float, direction: int) -> tuple[Region, Region | None]:
    """Kaynakta gösterilecek alan (0–1) ve varsa kaydırma sonu. Hesap piksel oranında (yükseklik = 1 birim).

    Video alanı HER ZAMAN tam dolar (bulanık dolgu yok, editör kararı): alan, asıl görüntünün (bulanık/siyah kenar
    hariç) içindeki en büyük video-alanı oranlı dikdörtgendir; hiçbir zaman bundan fazla yakınlaştırılmaz. Dikey
    (yanları dolgulu) çekimde sabittir; tam karede öznenin ortasına gelir, özne bu alandan belirgin genişse (ör.
    yandan otobüs) klip boyunca öznenin üzerinde yavaşça kayar.
    """
    a = candidate.frame_aspect
    c = candidate.content_region or Region(x=0, y=0, width=1, height=1)
    cx, cy, cw, ch = c.x * a, c.y, c.width * a, c.height
    view_w, view_h = (ch * slot_aspect, ch) if cw / ch > slot_aspect else (cw, cw / slot_aspect)
    if candidate.subject:
        s = candidate.subject
        sx0, sx1 = max(cx, s.x * a), min(cx + cw, (s.x + s.width) * a)
        sy0, sy1 = max(cy, s.y), min(cy + ch, s.y + s.height)
    else:
        focus = candidate.focus or FocusPoint()
        sx0 = sx1 = focus.x * a
        sy0 = sy1 = focus.y
    center_x, center_y = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    distance = PAN_SPEED * a * seconds  # kaynak piksel oranında, her iki eksende aynı hız
    if candidate.content_region is not None:
        # Editör kuralı (v3.4): yanları dolgulu dikey çekimde hiç kaydırma yok; ne klip içinde ne klipten klibe.
        # Net şeridin tam genişliği, tüm video boyunca aynı yükseklikte (özne merkezlerinin ortalaması).
        center_x = cx + cw / 2
        center_y = candidate.anchor_y if candidate.anchor_y is not None else cy + ch / 2
        pan_x = pan_y = 0.0
    else:  # tam kare (yatay) çekim: alana sığan en geniş alan; özne alandan genişse yavaşça kayar
        pan_x = min(sx1 - sx0 - view_w, distance) if sx1 - sx0 > view_w * PAN_MIN_RATIO else 0.0
        pan_y = min(sy1 - sy0 - view_h, distance) if sy1 - sy0 > view_h * PAN_MIN_RATIO else 0.0
    floor = lambda v: math.floor(v * 10_000) / 10_000  # noqa: E731 — x + width 1'i aşmasın

    def region(mid_x: float, mid_y: float) -> Region:
        x = min(max(mid_x - view_w / 2, cx), cx + cw - view_w)
        y = min(max(mid_y - view_h / 2, cy), cy + ch - view_h)
        return Region(x=floor(x / a), y=floor(y), width=floor(view_w / a), height=floor(view_h))

    if pan_x <= 0 and pan_y <= 0:
        return region(center_x, center_y), None
    first = region(center_x - direction * pan_x / 2, center_y - direction * pan_y / 2)
    last = region(center_x + direction * pan_x / 2, center_y + direction * pan_y / 2)
    return (first, last) if first != last else (first, None)


def _photo_zoom(candidate: Candidate, view: Region, seconds: float) -> Region | None:
    """Fotoğrafta yavaş yakınlaşmanın son alanı: `view`in içinde, öznenin (yoksa odağın) ortasına doğru, aynı oranda.
    Öznenin tamamı kadrajda kalır; özne alanı zaten dolduruyorsa yakınlaşma yok."""
    zoom = 1 + PHOTO_ZOOM * seconds
    s = candidate.subject
    if s:
        zoom = min(zoom, view.width / max(s.width, 1e-6), view.height / max(s.height, 1e-6))
        center_x, center_y = s.x + s.width / 2, s.y + s.height / 2
    else:
        focus = candidate.focus or FocusPoint()
        center_x, center_y = focus.x, focus.y
    if zoom < 1.02:
        return None
    width, height = view.width / zoom, view.height / zoom
    x, y = center_x - width / 2, center_y - height / 2
    if s:  # özne kutusu yakınlaşmada da kesilmesin
        x = min(max(x, s.x + s.width - width), s.x)
        y = min(max(y, s.y + s.height - height), s.y)
    x = min(max(x, view.x), view.x + view.width - width)
    y = min(max(y, view.y), view.y + view.height - height)
    floor = lambda v: math.floor(v * 10_000) / 10_000  # noqa: E731
    return Region(x=floor(x), y=floor(y), width=floor(width), height=floor(height))


def clip_framing(candidate: Candidate, slot_aspect: float = VIDEO_WIDTH / VIDEO_HEIGHT,
                 seconds: float = 3.0, direction: int = 1) -> Framing:
    """Kaynaktaki gösterilecek alan (+ kaydırma). Kadraj her zaman tam dolu (editör kararı)."""
    fx, fy = (candidate.focus.x, candidate.focus.y) if candidate.focus else (0.5, 0.5)
    region = candidate.content_region
    if region:
        fx = (fx - region.x) / region.width
        fy = (fy - region.y) / region.height
    view, view_end = _view_regions(candidate, slot_aspect, seconds, direction)
    if candidate.photo and view_end is None:
        view_end = _photo_zoom(candidate, view, seconds)
        if view_end and direction < 0:  # sahneden sahneye bir yakınlaş, bir uzaklaş
            view, view_end = view_end, view
    return Framing(
        mode=FramingMode.FILL_CROP,
        focus_x=round(min(1.0, max(0.0, fx)), 3),
        focus_y=round(min(1.0, max(0.0, fy)), 3),
        content_region=region,
        view_region=view,
        view_region_end=view_end,
    )


def segment_times(project: EditProject) -> list[tuple[str, float, float]]:
    """(segment_id, başlangıç, bitiş) — boşluksuz; ilk segment 0'da, son segment ses sonunda biter."""
    segments = sorted(project.edit_plan.segments, key=lambda s: s.order)
    duration = project.audio.duration_seconds
    char_starts, _ = _char_times(project)
    starts = [char_starts[s.char_start] if s.char_start < len(char_starts) else duration for s in segments]
    if starts:
        starts[0] = 0.0
    ends = starts[1:] + [duration]
    return [(s.segment_id, start, end) for s, start, end in zip(segments, starts, ends) if end > start]


def _char_times(project: EditProject) -> tuple[list[float], list[float]]:
    """Her karakterin konuşulma zamanı: alignment'tan; yoksa ses süresine eşit dağıtılır."""
    alignment = project.news.tts_alignment
    if alignment and len(alignment.start_seconds) == len(project.news.tts_text):
        return list(alignment.start_seconds), list(alignment.end_seconds)
    size = max(1, len(project.news.tts_text))
    step = project.audio.duration_seconds / size
    return [i * step for i in range(size)], [(i + 1) * step for i in range(size)]


def cut_points(project: EditProject) -> list[tuple[float, float]]:
    """Sahne değişebilecek anlar: kelime aralarındaki duraklamanın ortası ve gücü.

    Güç: cümle sonu > virgül/iki nokta > düz kelime arası; duraklama uzadıkça artar (nefes payı).
    """
    text = project.news.tts_text
    starts, ends = _char_times(project)
    points = []
    for index, char in enumerate(text):
        if char != " " or index == 0 or index + 1 >= len(text):
            continue
        first = index
        while first > 0 and text[first - 1] in PAUSE_PUNCTUATION:
            first -= 1
        pause_start, pause_end = starts[first], ends[index]
        before = text[index - 1]
        strength = 0.5 + 4.0 * max(0.0, pause_end - pause_start)
        if before in SENTENCE_END:
            strength += 3.0
        elif before in PAUSE_PUNCTUATION:
            strength += 1.5
        points.append(((pause_start + pause_end) / 2, strength))
    return points


def _cut_times(project: EditProject, total: float) -> list[float]:
    """Kurgu kesme zamanları [0, ..., total]: her sahne MIN–MAX sn, kesmeler duraklamalarda."""
    points = cut_points(project)
    tts_end = project.audio.duration_seconds
    if total - tts_end >= MIN_CLIP_SECONDS:
        points.append((tts_end, 3.0))  # Seslendirme bitti; sessiz uzatma ayrı sahne olabilir.
    cuts = [0.0]
    while total - cuts[-1] > MAX_CLIP_SECONDS:
        now = cuts[-1]
        window = [
            (time, strength) for time, strength in points
            if now + MIN_CLIP_SECONDS <= time <= now + MAX_CLIP_SECONDS and total - time >= MIN_CLIP_SECONDS
        ]
        if window:
            cuts.append(max(window, key=lambda p: p[1] - 0.4 * abs(p[0] - now - IDEAL_CLIP_SECONDS))[0])
        else:  # Kelime arası bile yok (çok uzun kelime/sessizlik): ideal sürede kes.
            cuts.append(now + IDEAL_CLIP_SECONDS)
    return cuts + [total]


def _spoken_text(project: EditProject, start: float, end: float) -> str:
    starts, _ = _char_times(project)
    return "".join(char for char, at in zip(project.news.tts_text, starts) if start <= at < end)


def _segment_at(project: EditProject, time: float) -> str:
    timed = segment_times(project)
    for segment_id, start, end in timed:
        if start <= time < end:
            return segment_id
    return timed[-1][0]


def _soundbite_clip(bite: Soundbite, clip_id: str, start_f: int, fps: int, library: MediaLibrary,
                    candidates: list[Candidate]) -> Clip:
    asset = next(
        (a for a in library.assets if isinstance(a, VideoAsset) and a.source.original_path == bite.path), None
    ) or next((a for a in library.assets if isinstance(a, VideoAsset) and a.source.filename == bite.filename), None)
    if asset is None:
        raise ValueError(f"Kesitin videosu analiz edilmedi: {bite.filename}. Görüntüleri analiz ederken bu videoyu da seç.")
    length = asset.source.duration_seconds or 0.0
    if length and bite.start_s >= length - 0.1:
        raise ValueError(f"Kesit ({bite.filename}, {bite.start_s:.1f} sn) videonun süresini ({length:.1f} sn) aşıyor; kesiti kaldırıp yeniden seç.")
    # Kadraj: kesitin başladığı sahne penceresinin öznesi ve kenar bilgisi.
    frame = next(
        (c for c in candidates if c.asset_id == asset.asset_id and c.start <= bite.start_s < c.end),
        None,
    )
    if frame is None:
        frame = Candidate(
            asset_id=asset.asset_id, shot_id="", shot_start=0, shot_end=0, start=0, end=0, order=0, tokens=[],
            role=EditorialRole.UNKNOWN, visual_type=VisualType.UNKNOWN, confidence=0, plate=False, description="",
            frame_aspect=asset.geometry.display.width / asset.geometry.display.height,
        )
    end_s = min(bite.end_s, length) if length else bite.end_s  # Video sonrasına taşan kısım kırpılır.
    duration_f = max(1, round((end_s - bite.start_s) * fps))
    return Clip(
        id=clip_id,
        asset_id=asset.asset_id,
        shot_id=frame.shot_id or None,
        source_in_s=round(bite.start_s, 3),
        source_out_s=round(bite.start_s + duration_f / fps, 3),
        start_f=start_f,
        duration_f=duration_f,
        framing=clip_framing(frame, seconds=duration_f / fps),
        use_source_audio=True,
        origin=ClipOrigin.USER,
        reason=f"Kaynak sesli kesit ({PLACEMENT_LABELS[bite.placement].lower()})",
    )


@dataclass
class Prepared:
    """Kurgunun sabit kısmı: kesitler, seslendirme sahnelerinin zamanları (duraklamalarda) ve aday pencereler.
    Kurallı seçim ve Luna seçimi (luna_edit.py) aynı sahne zamanlarını kullanır."""
    project: EditProject
    library: MediaLibrary
    candidates: list[Candidate]
    fps: int
    before: list[Clip]
    after: list[Clip]
    blocked: list[tuple[str, float, float]]
    intro_end_f: int
    broll_s: float
    broll_end_f: int
    cuts: list[float]

    def slots(self) -> list[tuple[float, float, str]]:
        """Seslendirme sahneleri: (başlangıç, bitiş, o sırada söylenen) — seslendirmenin başına göre saniye."""
        return [(start, end, _spoken_text(self.project, start, end).strip()) for start, end in zip(self.cuts, self.cuts[1:])]


def prepare(edit_project: dict[str, Any], media_library: dict[str, Any],
            soundbites: list[Soundbite] | None = None) -> Prepared:
    project = EditProject.model_validate(edit_project)
    library = MediaLibrary.model_validate(media_library)
    candidates = _candidates(library)
    if not candidates:
        raise ValueError("Kurgu için analiz edilmiş görüntü (video ya da fotoğraf) yok.")
    fps = project.edit_plan.timeline.fps
    blocked: list[tuple[str, float, float]] = []

    def soundbite_clips(placement: str) -> list[Clip]:
        result = []
        for bite in ordered(soundbites or [], placement):
            clip = _soundbite_clip(bite, "", 0, fps, library, candidates)
            result.append(clip)
            blocked.append((clip.asset_id, bite.start_s, bite.end_s))
        return result

    # Önce kesitler hazırlanır: süreleri toplamı belirler, aralıkları dolgu görüntüsünde tekrar edilmez.
    before, after = soundbite_clips("before"), soundbite_clips("after")
    intro_end_f = sum(c.duration_f for c in before)
    intro_s, outro_s = intro_end_f / fps, sum(c.duration_f for c in after) / fps
    # Seslendirme kısmı; video toplamda şablonun en kısa süresinden kısa kalmasın (sessiz uzatma).
    tts_s = project.audio.duration_seconds
    broll_s = max(tts_s, video_seconds(tts_s, intro_s + outro_s) - intro_s - outro_s)
    return Prepared(project, library, candidates, fps, before, after, blocked, intro_end_f, broll_s,
                    intro_end_f + round(broll_s * fps), _cut_times(project, broll_s))


def plan_rough_cut(
    edit_project: dict[str, Any],
    media_library: dict[str, Any],
    soundbites: list[Soundbite] | None = None,
    picks: dict[int, tuple[int, float | None]] | None = None,
) -> dict[str, Any]:
    """EditProject'in video_main izini doldurur.

    Sıra: seslendirme öncesi kesitler → seslendirme (dolgu görüntüleriyle) → seslendirme sonrası kesitler.
    `picks`: Luna'nın seçimi (v3.6, Faz 4) {sahne no: (aday no, kaynak başlangıcı)}; verilmeyen sahne ve pencere
    yetmezse kalan süre kurallarla seçilir.
    """
    prep = prepare(edit_project, media_library, soundbites)
    project, candidates, fps = prep.project, prep.candidates, prep.fps
    usage = _Usage(blocked=list(prep.blocked))
    clips: list[Clip] = []
    before, after = prep.before, prep.after
    intro_end_f, broll_s, broll_end_f = prep.intro_end_f, prep.broll_s, prep.broll_end_f
    picks = dict(picks or {})  # kopyası: seçilen sahneler sırayla düşülür

    previous_shot: str | None = None
    previous_tokens: list[str] = []
    headline_tokens = _tokens(f"{project.news.headline_1} {project.news.headline_2}")
    cuts = prep.cuts
    carried_f: int | None = None  # önceki sahne erken bittiyse bu sahne oradan başlar (kısa artık sahne olmasın)
    last_slot = len(cuts) - 2
    for slot, (start, end) in enumerate(zip(cuts, cuts[1:])):
        # Sahne, o sırada söylenen kelimelere göre seçilir (sessiz uzatmada son söylenenlere göre).
        tokens = _tokens(_spoken_text(project, start, end)) or previous_tokens
        previous_tokens = tokens
        segment_id = _segment_at(project, start)
        cursor_f = carried_f if carried_f is not None else intro_end_f + round(start * fps)
        carried_f = None
        end_f = broll_end_f if end >= broll_s else intro_end_f + round(end * fps)
        while cursor_f < end_f:
            need = (end_f - cursor_f) / fps
            opening = cursor_f == 0
            wanted = tokens + headline_tokens if opening else tokens  # kapak: haberin bütününü (başlıkları) anlatsın
            # Anlatımdaki yer (bu parçanın ortası, 0–1): tek uzun çekimde kaynaktaki yere eşlenir.
            story = (cursor_f + min(end_f - cursor_f, IDEAL_CLIP_SECONDS * fps) / 2 - intro_end_f) / max(1, broll_end_f - intro_end_f)
            pick = picks.pop(slot, None)  # Luna'nın seçimi sahnenin başında bir kez; yetmezse kalanı kurallar
            if pick is not None and 0 <= pick[0] < len(candidates):
                best, prefer, origin = candidates[pick[0]], pick[1], ClipOrigin.LLM
            else:
                best = max(candidates, key=lambda c: (_score(c, wanted, opening, previous_shot, usage, need, story), -c.order))
                prefer, origin = None, ClipOrigin.RULE
            source_in, available, _ = _source_range(best, usage, need, prefer)
            # Sahne yetmezse (kısa shot) kalan süre bir sonraki en iyi sahneyle doldurulur. Kalan MIN_CLIP_SECONDS'tan
            # kısaysa ayrı sahne olmaz (editörün Eymen videosu, v3.7.2: 1 sn'lik ara sahne): bu sahne erken biter,
            # sonraki sahne o kadar erken başlar (kesme duraklamadan biraz kayar).
            duration_f = max(1, min(end_f - cursor_f, math.floor(available * fps)))
            short_rest = 0 < (end_f - cursor_f - duration_f) < MIN_CLIP_SECONDS * fps
            if short_rest and slot < last_slot and duration_f >= MIN_CLIP_SECONDS * fps:
                end_f = cursor_f + duration_f
                carried_f = end_f
            source_out = source_in + duration_f / fps
            clips.append(
                Clip(
                    id=f"video_{len(clips) + 1:03d}",
                    asset_id=best.asset_id,
                    shot_id=best.shot_id,
                    segment_id=segment_id,
                    source_in_s=round(source_in, 3),
                    source_out_s=round(source_out, 3),
                    start_f=cursor_f,
                    duration_f=duration_f,
                    framing=clip_framing(best, seconds=duration_f / fps, direction=1 if len(clips) % 2 else -1),
                    origin=origin,
                    reason=best.description,
                )
            )
            # Fotoğrafın sanal aralığının tamamı kullanılmış sayılır: aynı kare ikinci kez gelirse tekrardır.
            usage.used.setdefault(best.shot_id, []).append((0.0, PHOTO_SECONDS) if best.photo else (source_in, source_out))
            usage.window_count[(best.shot_id, best.start)] = usage.window_count.get((best.shot_id, best.start), 0) + 1
            usage.count[best.shot_id] = usage.count.get(best.shot_id, 0) + 1
            previous_shot = best.shot_id
            cursor_f += duration_f

    _chronological(clips, candidates, usage.blocked)

    cursor_f = 0
    for clip in before:
        clip.start_f, cursor_f = cursor_f, cursor_f + clip.duration_f
    cursor_f = broll_end_f
    for clip in after:
        clip.start_f, cursor_f = cursor_f, cursor_f + clip.duration_f
    clips = sorted([*before, *clips, *after], key=lambda c: c.start_f)
    for number, clip in enumerate(clips, 1):
        clip.id = f"video_{number:03d}"

    for track in project.edit_plan.timeline.tracks:
        if track.kind == TrackKind.VIDEO:
            track.clips = clips
        elif track.kind == TrackKind.AUDIO:
            for clip in track.clips:
                if clip.asset_id == project.audio.asset_id:
                    clip.start_f = intro_end_f  # Seslendirme, öncesindeki kesitler bitince başlar.
    return EditProject.model_validate(project.model_dump(mode="json")).model_dump(mode="json")


def _chronological(clips: list[Clip], candidates: list[Candidate], blocked: list[tuple[str, float, float]]) -> None:
    """Aynı çekimden alınan parçalar videoda kaynaktaki sırasıyla oynar (editör, v3.3: tek uzun cep telefonu çekiminde
    parçalar 46. sn → 4. sn → 50. sn diye atlıyor, olay anlaşılmıyordu). Hangi anların seçildiği değişmez; her parça
    kadrajını yanında taşır, süreler videodaki yerlerinde kalır. Sığmazsa (sahne sonu, kesit aralığı) o çekim eski
    sırasında bırakılır."""
    shot_end = {c.shot_id: c.shot_end for c in candidates}
    by_shot: dict[str, list[Clip]] = {}
    for clip in clips:
        by_shot.setdefault(clip.shot_id, []).append(clip)
    for shot_id, group in by_shot.items():
        if len(group) < 2:
            continue
        slots = sorted(group, key=lambda c: c.start_f)  # videodaki yerler (süreleriyle)
        pieces = sorted(((c.source_in_s, c.framing, c.reason, c.origin) for c in group), key=lambda p: p[0])
        limit = shot_end.get(shot_id, math.inf) - EDGE_SECONDS
        plan, previous_out = [], 0.0
        for slot, (source_in, framing, reason, origin) in zip(slots, pieces):
            start = max(source_in, previous_out)
            out = start + (slot.source_out_s - slot.source_in_s)
            if out > limit + 1e-6 or any(a == slot.asset_id and s < out and start < e for a, s, e in blocked):
                break
            plan.append((slot, start, out, framing, reason, origin))
            previous_out = out
        else:
            for slot, start, out, framing, reason, origin in plan:
                slot.source_in_s, slot.source_out_s = round(start, 3), round(out, 3)
                slot.framing, slot.reason, slot.origin = framing, reason, origin


def has_rough_cut(edit_project: dict[str, Any] | None) -> bool:
    tracks = ((edit_project or {}).get("edit_plan") or {}).get("timeline", {}).get("tracks", [])
    return any(track.get("kind") == "video" and track.get("clips") for track in tracks)


def matches_template(edit_project: dict[str, Any]) -> bool:
    """Kurgu, şablonun güncel video alanı ölçüsünde mi (eski 1080x1440 projeler yeniden kurulur)?"""
    timeline = edit_project["edit_plan"]["timeline"]
    return (timeline.get("width"), timeline.get("height")) == (VIDEO_WIDTH, VIDEO_HEIGHT)


def clip_rows(edit_project: dict[str, Any]) -> list[dict[str, Any]]:
    """Geliştirici tablosu: hangi TTS cümlesine hangi sahne kesiti kondu."""
    fps = edit_project["edit_plan"]["timeline"]["fps"]
    rows = []
    for track in edit_project["edit_plan"]["timeline"]["tracks"]:
        if track["kind"] != "video":
            continue
        for clip in track["clips"]:
            rows.append(
                {
                    "Zaman (sn)": round(clip["start_f"] / fps, 2),
                    "Süre (sn)": round(clip["duration_f"] / fps, 2),
                    "Cümle": clip["segment_id"],
                    "Sahne": clip["shot_id"] or "",
                    "Ses": "kaynak" if clip.get("use_source_audio") else "",
                    "Kaynak (sn)": f"{clip['source_in_s']:.1f}-{clip['source_out_s']:.1f}",
                    "Odak": f"{clip['framing']['focus_x']:.2f}, {clip['framing']['focus_y']:.2f}",
                    "Kenar kırpma": "var" if clip["framing"].get("content_region") else "",
                    "Görüntü": clip["reason"],
                }
            )
    return rows
