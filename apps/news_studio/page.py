"""Haber Stüdyosu: ham haber → başlıklar, paylaşım metni, seslendirme metni ve sesi → Axion projesi."""

from __future__ import annotations

import io
import time
from datetime import datetime

import streamlit as st
from elevenlabs.client import ElevenLabs
from mutagen.mp3 import MP3

from apps.axion_local import corrections, ledger, status
from apps.axion_local.metrics import record, timed
from apps.axion_local.preferences import load_preferences, persist, remember, save_preferences
from apps.axion_local.settings import require_secrets, secret
from apps.axion_local.store import (
    NEWS_IMPORT_KEY,
    data_dir,
    get_news_project,
    list_inbox_texts,
    read_text_file,
    save_news_project,
)
from apps.news_studio.ai import cost
from apps.news_studio.ai.clients import generate, make_anthropic, make_openai, regenerate_headlines, regenerate_tts
from apps.news_studio.config import (
    CLAUDE_MODEL,
    CORRECTION_MAX_TOKENS,
    HISTORY_DB_PATH,
    OPENAI_MODELS,
    TTS_DURATION_PRESETS,
    TTS_TIMEOUT_SECONDS,
)
from apps.news_studio.integration.history import log_run
from apps.news_studio.models.news import NewsOutput
from apps.news_studio.prompts.news import build_correction_prompt, build_news_prompt
from apps.news_studio.read_along import read_along
from apps.news_studio.tts.calibration import estimate
from apps.news_studio.tts.calibration import load as load_calibration
from apps.news_studio.tts.calibration import update as update_calibration
from apps.news_studio.tts.service import synthesize
from apps.news_studio.validation.diff import STYLE as DIFF_STYLE
from apps.news_studio.validation.diff import changed_fields, word_diff_html
from apps.news_studio.validation.news import find_censorship_warnings, validate_news_output
from apps.news_studio.validation.source_check import missing_numbers, unsupported
from apps.news_studio.validation.speakable import make_speakable
from shared.news_package import NewsPackage, TTSAlignment
from shared.text_layout import check_headline

VIDEO_PAGE = "apps/video_studio/page.py"

st.set_page_config(page_title="Haber Stüdyosu · Axion", page_icon="📰", layout="wide")

STYLES = ["Standart (Ana Haber) Dili", "Tepkili Haber Dili", "Eleştirel Haber Dili", "Son Dakika Dili", "Mizahi Haber Dili"]
EXAMPLES_KEY = "news_examples"  # üslup örnekleri de hatırlanır (data/ayarlar.json)
THINKING_LEVELS = ["Kapalı (Tasarruflu)", "Düşük", "Orta", "Yüksek"]
PROVIDERS = ["OpenAI", "Claude"]
PREFERENCES = {
    "news_style": STYLES[0], "duration_label": list(TTS_DURATION_PRESETS)[2],
    "ai_provider": "OpenAI", "openai_model": list(OPENAI_MODELS)[0], "thinking": THINKING_LEVELS[0], "voice_name": "",
    "speed": 1.11, "stability": 0.50, "similarity": 0.65, "style_strength": 0.10, "boost": True,
}
# Ses zamanları dict olarak tutulur: Streamlit modülü yeniden yüklerse eski sınıfın nesnesi NewsPackage'a girmez.
AUDIO_STATE = {"last_audio_bytes": None, "last_audio_duration": None, "last_audio_text": None,
               "last_audio_alignment": None, "last_audio_filename": "axion_haber_ses.mp3"}
USAGE_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_creation_input_tokens", "reasoning_tokens", "requests")

ss = st.session_state


def _sync_text(field: str) -> None:
    ss[field] = ss["_w_" + field]


def bound_text(widget, label: str, field: str, **kwargs) -> str:
    """Metin kutusu kendi anahtarıyla çizilir, değer ss[field]'da tutulur.

    Anahtarsız kutuya her çalıştırmada value= vermek, tarayıcıda kutu dışına tıklanınca düzenlemenin kaybolmasına
    yol açıyordu. Bu desenle düzenleme korunur, programın yazdığı değer (yeni haber, başlık yenileme) de kutuya gelir
    ve sayfa değiştirince metin kaybolmaz.
    """
    ss["_w_" + field] = ss[field]
    widget(label, key="_w_" + field, on_change=_sync_text, args=(field,), **kwargs)
    return ss[field]


def init_state() -> None:
    saved_examples = load_preferences().get(EXAMPLES_KEY)
    examples = {name: str((saved_examples or {}).get(name, "")) for name in STYLES}
    defaults = {
        "baslik1": "", "baslik2": "", "icerik": "", "tts_metni": "", "raw_text": "",
        "examples": examples, "last_usage": None, "last_validation": [], "last_warnings": [],
        "last_correction_reason": "", "last_correction_diff": {}, "tts_calibration": load_calibration(), **AUDIO_STATE,
    }
    for key, value in defaults.items():
        ss.setdefault(key, value)


@st.cache_resource
def openai_client():
    return make_openai(secret("OPENAI_API_KEY"))


@st.cache_resource
def anthropic_client():
    return make_anthropic(secret("ANTHROPIC_API_KEY"))


@st.cache_resource
def elevenlabs_client():
    return ElevenLabs(api_key=secret("ELEVENLABS_API_KEY"), timeout=TTS_TIMEOUT_SECONDS)


@st.cache_data(ttl=3600)
def fetch_voices() -> list[tuple[str, str]]:
    response = elevenlabs_client().voices.get_all()
    return [(voice.name, voice.voice_id) for voice in response.voices]


def accumulate(total: dict | None, usage: dict) -> dict:
    """Token kullanımını toplar (haber + düzeltme + başlık yenileme); Geliştirici bilgilerinde görünür."""
    out = (total or {}).copy()
    for key in USAGE_KEYS:
        out[key] = out.get(key, 0) + usage.get(key, 0)
    out["provider"] = usage.get("provider", out.get("provider", "-"))
    out["model"] = usage.get("model", out.get("model", "-"))
    return out


@st.fragment(run_every=120)  # dakika sayacı; 2 dk'da bir yeter (sayfa boşta sık yenilenmesin)
def cache_status(provider: str, model_id: str) -> None:
    """Sistem komutu önbellekte mi (tahmin: son haber + önbellek süresi). Sıcakken sistem komutu ~%10 fiyatına gider."""
    left = cost.minutes_left(data_dir(), provider, model_id)
    st.caption(f"🟢 Önbellek sıcak, ~{left} dk (tahmini)" if left else "⚪ Önbellek soğuk",
               help="İlk haberde yapay zekânın kuralları (sistem komutu) önbelleğe yazılır; süre dolmadan gelen haberde "
                    f"bu kısım ~%10 fiyatına okunur. Süre her haberde baştan başlar (Luna {cost.CACHE_MINUTES['OpenAI']} dk, "
                    f"Claude {cost.CACHE_MINUTES['Claude']} dk). Gerçek ölçüm: Geliştirici bilgileri.")


def reset_state() -> None:
    keep = {"examples", "tts_calibration", *PREFERENCES}
    for key in list(ss.keys()):
        if key not in keep:
            del ss[key]
    ss.update(AUDIO_STATE)


def source_note(container, items: list[str]) -> None:
    """Kaynakta (ham haberde) bulunmayan sayı/isimler: yapay zekâ uydurmuş ya da farklı yazmış olabilir, kontrol et."""
    if items:
        container.markdown("🟡 **Kaynakta yok:** " + " · ".join(f":orange-background[{item}]" for item in items[:12]),
                           help="Ham haberde geçmiyor. Yapay zekâ uydurmuş ya da farklı yazmış olabilir (ör. \"iki\" ↔ \"2\").")


def note_model_output(kind: str, **fields: str) -> None:
    """"Yeniden üret" sonrası modelin yeni çıktısı: editörün düzeltmesi bundan sayılır; kaç kez yeniden üretildiği de."""
    if ss.get("model_output"):
        ss.model_output = {**ss.model_output, **fields}
    counts = dict(ss.get("regenerations") or {})
    counts[kind] = counts.get(kind, 0) + 1
    ss.regenerations = counts


def start_from_text(text: str) -> None:
    """TXT'den yeni haber: ekrandaki haber temizlenir; önceki kayıtlı proje silinmez, üzerine de yazılmaz."""
    ss.update({"baslik1": "", "baslik2": "", "icerik": "", "tts_metni": "", "last_usage": None, "last_validation": [],
               "headline_history": [], "tts_notes": [], "last_warnings": [], "last_correction_reason": "", "last_correction_diff": {}, **AUDIO_STATE,
               "raw_text": text, "model_output": None, "regenerations": {}})
    for key in ("active_news_project", "loaded_news_project", "active_news_source"):
        ss.pop(key, None)


require_secrets("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY")
init_state()
if ss.get(NEWS_IMPORT_KEY) is not None:  # Tarayıcı'daki "📰 Haber Stüdyosu'na aktar"
    start_from_text(ss.pop(NEWS_IMPORT_KEY))

# =================================================
# KENAR ÇUBUĞU: AYARLAR (son kullanılan değerler hatırlanır)
# =================================================
remember(ss, PREFERENCES, {"news_style": STYLES, "duration_label": list(TTS_DURATION_PRESETS), "ai_provider": PROVIDERS,
                           "openai_model": list(OPENAI_MODELS), "thinking": THINKING_LEVELS})
try:
    voices = fetch_voices()
except Exception:  # noqa: BLE001 — anahtar/bağlantı sorunu: kenar çubuğunda uyarı
    voices = []
names = [name for name, _ in voices]
if names and ss.voice_name not in names:
    ss.voice_name = next((n for n in names if "Cavit" in n and "Presenter" in n), next((n for n in names if "Cavit" in n), names[0]))

with st.sidebar:
    style = st.selectbox("Üslup", STYLES, key="news_style", filter_mode=None)
    duration_label = st.selectbox("Seslendirme süresi", list(TTS_DURATION_PRESETS), key="duration_label",
                                  filter_mode=None)
    duration_range = TTS_DURATION_PRESETS[duration_label]
    provider = st.segmented_control("Yapay zekâ", PROVIDERS, key="ai_provider") or "OpenAI"
    if provider == "OpenAI":
        openai_model = st.selectbox("Model", list(OPENAI_MODELS), key="openai_model", filter_mode=None)
    else:
        openai_model = ss.openai_model
        st.caption(f"Claude modeli: `{CLAUDE_MODEL}`")
    model_id = OPENAI_MODELS.get(openai_model, "") if provider == "OpenAI" else CLAUDE_MODEL
    cache_status(provider, model_id)
    thinking = st.selectbox("Düşünme seviyesi", THINKING_LEVELS, key="thinking", help="Yüksek seviye daha pahalıdır.",
                            filter_mode=None)
    if names:
        voice_name = st.selectbox("Spiker", names, key="voice_name", filter_mode=None)
        voice_id = dict(voices)[voice_name]
    else:
        st.warning("ElevenLabs sesleri alınamadı. API anahtarını kontrol et.")
        voice_name = voice_id = ""
    with st.expander("Ses ince ayarları"):
        speed = st.slider("Hız", 0.7, 1.2, step=0.01, key="speed")
        stability = st.slider("Stabilite", 0.0, 1.0, step=0.01, key="stability")
        similarity = st.slider("Benzerlik", 0.0, 1.0, step=0.01, key="similarity")
        style_strength = st.slider("Stil", 0.0, 1.0, step=0.01, key="style_strength")
        boost = st.toggle("Ses netliği artırma", key="boost", help="ElevenLabs Speaker Boost: spikere benzerliği artırır, biraz yavaşlatır.")
    with st.expander("Üslup örnekleri"):
        st.caption("İsteğe bağlı: seçilen üslup için örnek bir haber metni. Model yalnızca tonu örnek alır. Hatırlanır.")
        for name in STYLES:
            ss.examples[name] = st.text_area(name, value=ss.examples[name], height=90, key="ex_" + name)
    if ss.examples != load_preferences().get(EXAMPLES_KEY, dict.fromkeys(STYLES, "")):
        save_preferences({**load_preferences(), EXAMPLES_KEY: ss.examples})
    tts_min, tts_target, tts_max, cps = estimate(ss.tts_calibration, voice_id or "default", speed, duration_range)
    if st.button("Yeni haber", width="stretch", help="Ekrandaki haberi temizler; kayıtlı projeler silinmez."):
        reset_state()
        st.rerun()
persist(ss, PREFERENCES)

# =================================================
# HAM HABER
# =================================================
st.title("Haber Stüdyosu")
texts = list_inbox_texts()
if texts:  # DHA'nın "TXT indir"i İndirilenler'e iner; "metni kopyala" uzaktan (tablette) çalışmayabilir
    pick_col, import_col = st.columns([4, 1], vertical_alignment="bottom")
    picked = pick_col.selectbox(
        "📄 İndirilenler'deki haber metni (TXT)", texts, key="txt_secim",
        format_func=lambda path: f"{path.name} · {datetime.fromtimestamp(path.stat().st_mtime):%d.%m %H:%M}",
        filter_mode=None,
    )
    if import_col.button("Aktar", width="stretch", help="Ekrandaki haberi temizler, TXT'yi ham habere yazar."):
        start_from_text(read_text_file(picked))
        st.rerun()
bound_text(st.text_area, "Ham haber", "raw_text", height=200, placeholder="DHA'dan gelen ham haber metnini buraya yapıştır.")
raw = ss.raw_text.strip()
if len(raw) > 7000:
    st.warning(f"Ham haber {len(raw):,} karakter. Çok uzun metinler maliyeti artırır.")

# Ekranda haber varken yeniden işlemek editörün düzeltmelerini siler: önce onay (editör, v3.6.3: tablette seslendirmeyi
# düzeltirken dokunuş bu düğmeye gelmiş, haber baştan üretilmişti).
process = st.button("Haberi işle", type="primary", width="stretch")
if process and ss.get("icerik") and not ss.get("confirm_reprocess"):
    ss.confirm_reprocess, process = True, False
if ss.get("confirm_reprocess"):
    st.warning("Ekrandaki başlıklar, paylaşım metni ve seslendirme metni silinip haber baştan üretilecek; yaptığın "
               "düzeltmeler kaybolur. Emin misin?")
    yes_col, no_col = st.columns(2)
    if yes_col.button("Evet, baştan üret", type="primary", width="stretch"):
        ss.confirm_reprocess, process = False, True
    if no_col.button("Vazgeç", width="stretch", key="reprocess_cancel"):
        ss.confirm_reprocess = False
        st.rerun()
if process:
    if not raw:
        st.error("Önce ham haber metnini yapıştır.")
    else:
        prompt = build_news_prompt(style, duration_label, duration_range, tts_min, tts_target, tts_max, raw, speed, ss.examples)
        with st.spinner("Haber hazırlanıyor..."):
            try:
                timer = time.monotonic()
                result, usage = generate(openai_client(), anthropic_client(), provider, openai_model, prompt, thinking)
                check = validate_news_output(result, raw, tts_min, tts_max)
                total = accumulate(None, {**usage, "provider": provider})
                correction_reason = ""
                fields = ("baslik1", "baslik2", "icerik", "tts")
                first = {name: getattr(result, name) for name in fields}
                if check.headlines_only:  # yalnız başlık hatalı: tam düzeltme yerine küçük başlık çağrısı (token ~1/5)
                    correction_reason = " | ".join(check.errors)
                    try:
                        headlines, headline_usage = regenerate_headlines(
                            openai_client(), anthropic_client(), provider, openai_model, result.icerik, correction_reason)
                        total = accumulate(total, headline_usage)
                        # Yalnız hatalı başlık değişir; geçerli başlık korunur. Tek deneme, döngü yok.
                        corrected = result.model_copy(update={
                            f"baslik{i}": getattr(headlines, f"baslik{i}") for i in check.headline_errors})
                        corrected_check = validate_news_output(corrected, raw, tts_min, tts_max)
                        if len(corrected_check.errors) < len(check.errors):
                            result, check = corrected, corrected_check
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"Başlık düzeltme çağrısı başarısız; ilk sonuç korunuyor: {exc}")
                elif check.errors:  # tek düzeltme çağrısı (düşük düşünme); daha az hatalıysa o alınır
                    correction_reason = " | ".join(check.errors)
                    correction = build_correction_prompt(style, duration_label, tts_min, tts_target, tts_max, raw, result, check.errors)
                    try:
                        corrected, correction_usage = generate(openai_client(), anthropic_client(), provider, openai_model,
                                                               correction, "Düşük", CORRECTION_MAX_TOKENS)
                        total = accumulate(total, correction_usage)
                        corrected_check = validate_news_output(corrected, raw, tts_min, tts_max)
                        if len(corrected_check.errors) < len(check.errors):
                            result, check = corrected, corrected_check
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"Kalite düzeltme çağrısı başarısız; ilk sonuç korunuyor: {exc}")
                if ss.get("active_news_source") != raw:
                    ss.pop("active_news_project", None)
                ss.baslik1, ss.baslik2, ss.icerik, ss.tts_metni = result.baslik1, result.baslik2, result.icerik, result.tts
                # Düzeltmelerden öğrenme (v4.0): kaydederken modelin son çıktısı editörün son hâliyle karşılaştırılır.
                ss.model_output = {"baslik1": result.baslik1, "baslik2": result.baslik2, "icerik": result.icerik,
                                   "tts": result.tts}
                ss.regenerations = {}
                ss.last_usage = total
                ledger.add("haber", cost.cost_usd(total))  # günlük/aylık toplam (düzeltme çağrısı dahil)
                cost.touch(data_dir(), total)
                ss.last_validation = check.errors
                ss.last_warnings = check.warnings + find_censorship_warnings(result.tts + "\n" + result.icerik)
                ss.last_correction_reason = correction_reason
                ss.headline_history = []  # yeni haber: "yeniden üret" geçmişi baştan
                ss.tts_notes = []
                ss.last_correction_diff = changed_fields(first, {name: getattr(result, name) for name in fields})
                record("haber_yazimi", time.monotonic() - timer, model=total.get("model"), duzeltme=bool(correction_reason),
                       cagri=total.get("requests"))
                log_run(HISTORY_DB_PATH, raw_text=raw, result=result, usage=total, style=style, provider=provider,
                        model=total.get("model", ""), validation=check.errors)
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Haber işlenemedi ({provider}): {exc}")

if ss.icerik:
    usage = ss.last_usage or {}
    notes = ss.last_validation + ss.last_warnings
    if notes:
        st.warning("**Kontrol et:**\n\n" + "\n".join(f"- {note}" for note in notes))
    if ss.last_correction_diff:  # kalite kontrolü: ikinci (düzeltme) çağrısının yaptığı değişiklik
        with st.expander("🔁 Düzeltme çağrısı neyi değiştirdi"):
            labels = {"baslik1": "1. başlık", "baslik2": "2. başlık", "icerik": "Paylaşım metni", "tts": "Seslendirme"}
            st.html(DIFF_STYLE + "".join(f"<p><b>{labels[name]}</b></p>{word_diff_html(old, new)}"
                                         for name, (old, new) in ss.last_correction_diff.items()))

    # =================================================
    # BAŞLIKLAR + PAYLAŞIM METNİ
    # =================================================
    st.subheader("Başlıklar")
    h1, h2 = st.columns(2)
    bound_text(h1.text_input, "1. başlık", "baslik1")
    bound_text(h2.text_input, "2. başlık", "baslik2")
    for col, key in ((h1, "baslik1"), (h2, "baslik2")):
        text = ss.get(key, "").strip()
        if text:  # Videodaki yazıyla ölçülür: editör başlığı düzeltirken sığıp sığmadığını hemen görür.
            fit = check_headline(text)
            prefix = ("✅ Videoda: " if fit.fits else f"✅ Videoda (küçültülmüş yazı, {fit.size} px): " if fit.shrinks
                      else f"⚠️ Videoda 2 satıra sığmıyor, ~{fit.over_chars} karakter kısalt: ")
            col.caption(prefix + " / ".join(fit.lines))
            source_note(col, missing_numbers(text, raw))
    if st.button("↻ Başlıkları yeniden üret", help="Sadece başlıklar için küçük bir yapay zekâ çağrısı yapar. "
                 "Önceki başlıklardan farklı bir açıdan yazar."):
        try:
            # Bu haberde gösterilen başlıklar (en çok son 4 çift): yeni başlık farklı bir açıdan yazılsın.
            shown = [pair for pair in ss.get("headline_history", []) if pair != (ss.baslik1, ss.baslik2)]
            shown = (shown + [(ss.baslik1, ss.baslik2)])[-4:]
            headlines, headline_usage = regenerate_headlines(openai_client(), anthropic_client(), provider, openai_model,
                                                             ss.icerik, previous=shown)
            ss.headline_history = shown
            ss.baslik1, ss.baslik2 = headlines.baslik1, headlines.baslik2
            note_model_output("baslik", baslik1=headlines.baslik1, baslik2=headlines.baslik2)
            ss.last_usage = accumulate(ss.last_usage, headline_usage)
            ledger.add("baslik", cost.cost_usd({**headline_usage, "provider": provider}))
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Başlıklar üretilemedi: {exc}")

    st.subheader("Paylaşım metni")
    bound_text(st.text_area, "Paylaşım metni", "icerik", height=260, label_visibility="collapsed")
    st.caption(f"{len(ss.icerik)}/2200 karakter")
    source_note(st, unsupported(ss.icerik, raw))
    with st.expander("Kopyalamaya hazır tam metin"):
        st.code(f"{ss.baslik1}\n\n{ss.baslik2}\n\n{ss.icerik}", language="text")

    # =================================================
    # SESLENDİRME
    # =================================================
    title_col, retry_col = st.columns([3, 1], vertical_alignment="bottom")
    title_col.subheader("Seslendirme")
    if retry_col.button("↻ Yeniden üret", width="stretch", key="tts_yeniden",
                        help="Yalnız seslendirme metnini yeniden yazar (başlıklar ve paylaşım metni kalır). Bir yapay zekâ "
                        "çağrısı; önceki metin \"beğenilmedi\" diye gider."):
        try:
            with st.spinner("Seslendirme metni yeniden yazılıyor..."):
                prompt = build_news_prompt(style, duration_label, duration_range, tts_min, tts_target, tts_max, raw, speed,
                                           ss.examples)
                output, tts_usage = regenerate_tts(openai_client(), anthropic_client(), provider, openai_model, prompt,
                                                   thinking, ss.tts_metni)
            # Aynı temizlik ve kontroller (okunuş, plaka, sivil isim, uzunluk); yalnız seslendirmeyle ilgili notlar gösterilir.
            composed = NewsOutput(baslik1=ss.baslik1, baslik2=ss.baslik2, icerik=ss.icerik, tts_plani=output.tts_plani,
                                  tts=output.tts)
            check = validate_news_output(composed, raw, tts_min, tts_max)
            ss.tts_metni = composed.tts
            note_model_output("seslendirme", tts=composed.tts)
            ss.tts_notes = [n for n in check.errors + check.warnings if "eslendirme" in n or "tts" in n.lower()]
            ss.last_usage = accumulate(ss.last_usage, {**tts_usage, "provider": provider})
            ledger.add("seslendirme_metni", cost.cost_usd({**tts_usage, "provider": provider}))
            cost.touch(data_dir(), tts_usage)
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Seslendirme metni üretilemedi: {exc}")
    bound_text(st.text_area, "Seslendirme metni", "tts_metni", height=150, label_visibility="collapsed")
    if ss.get("tts_notes"):
        st.warning("**Kontrol et:**\n\n" + "\n".join(f"- {note}" for note in ss.tts_notes))
    st.caption(f"{len(ss.tts_metni)} karakter · hedef {tts_min}–{tts_max} ({duration_label})")
    source_note(st, unsupported(ss.tts_metni, raw))
    if st.button("🎙️ Seslendir", type="primary", width="stretch"):
        tts_text = make_speakable(ss.tts_metni.strip())  # "18.00'de" → "akşam 6'da" (spiker okuyabilsin)
        if not voice_id:
            st.error("Spiker seçilemedi; ElevenLabs anahtarını kontrol et.")
        elif not tts_text:
            st.error("Seslendirme metni boş.")
        else:
            try:
                with st.spinner("Ses üretiliyor..."), timed("seslendirme", karakter=len(tts_text)):
                    audio, alignment = synthesize(elevenlabs_client(), tts_text, voice_id, speed, stability, similarity,
                                                  style_strength, boost)
                ledger.add("ses", 0.0, characters=len(tts_text))  # abonelik: karakter sayılır
                try:
                    duration = float(MP3(io.BytesIO(audio)).info.length)
                except Exception:  # noqa: BLE001
                    duration = None
                ss.tts_metni = tts_text
                ss.update({"last_audio_bytes": audio, "last_audio_text": tts_text, "last_audio_alignment": alignment.model_dump() if alignment else None,
                           "last_audio_duration": duration})
                if duration:
                    ss.tts_calibration = update_calibration(ss.tts_calibration, voice_id, speed, len(tts_text), duration)
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Ses üretilemedi: {exc}")

    audio_stale = bool(ss.last_audio_bytes) and ss.get("last_audio_text") != ss.tts_metni
    if ss.last_audio_bytes:
        player, download = st.columns([4, 1])
        with player:
            if ss.last_audio_alignment and not audio_stale:  # çalan kelime vurgulanır, kelimeye dokununca oradan çalar
                read_along(ss.last_audio_bytes, ss.last_audio_alignment, key="okuyarak_dinle")
            else:
                st.audio(ss.last_audio_bytes, format="audio/mp3")
        download.download_button("MP3 indir", data=ss.last_audio_bytes, file_name=ss.last_audio_filename, mime="audio/mp3",
                                 width="stretch")
        if ss.last_audio_duration:
            st.caption(f"Ses süresi {ss.last_audio_duration:.1f} sn · hedef {duration_range[0]:g}–{duration_range[1]:g} sn")

    # =================================================
    # PROJEYE KAYDET
    # =================================================
    st.divider()
    active = get_news_project(ss.active_news_project) if ss.get("active_news_project") else None
    if audio_stale:
        st.warning("Seslendirme metni ses üretildikten sonra değişti. Kaydetmeden önce yeniden **Seslendir**.")
    else:
        if not ss.last_audio_bytes:
            st.caption("Henüz ses yok. Video kurgusu için önce seslendir.")
        package = NewsPackage(
            headline_1=ss.baslik1, headline_2=ss.baslik2, caption=ss.icerik, tts_text=ss.tts_metni, source_text=raw,
            provider=usage.get("provider", ""), model=usage.get("model", ""), tts_duration_target=duration_label,
            tts_actual_duration_seconds=ss.last_audio_duration, tts_voice_id=voice_id or "", tts_speed=speed,
            tts_alignment=ss.last_audio_alignment if ss.last_audio_bytes else None, metadata={"style": style, "usage": {**usage, "estimated_cost_usd": cost.cost_usd(usage)} if usage else usage},
        )
        go_col, save_col = st.columns([3, 1])
        go = go_col.button("Kaydet ve Video Stüdyosu'na geç", type="primary", width="stretch")
        save_only = save_col.button("Sadece kaydet", width="stretch")
        if go or save_only:
            try:
                folder = save_news_project(package, ss.last_audio_bytes, folder=active.folder if active else None)
                final = {"baslik1": ss.baslik1, "baslik2": ss.baslik2, "icerik": ss.icerik, "tts": ss.tts_metni}
                rejected = [list(pair) for pair in ss.get("headline_history", []) if pair != (ss.baslik1, ss.baslik2)]
                corrections.news(folder.name, ss.get("model_output"), final, raw, {
                    "saglayici": usage.get("provider", ""), "model": usage.get("model", ""), "uslup": style,
                    "yeniden_uretim": ss.get("regenerations") or {}, "reddedilen_basliklar": rejected})
                ss.active_news_project = folder.name
                ss.active_news_source = raw
                ss.pop("loaded_news_project", None)
                if go:
                    st.switch_page(VIDEO_PAGE)
                st.success("Proje kaydedildi.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Proje kaydedilemedi: {exc}")

    # =================================================
    # GELİŞTİRİCİ BİLGİLERİ
    # =================================================
    with st.expander("Geliştirici bilgileri"):
        status.render(secret("ELEVENLABS_API_KEY"))
        corrections.download_button(st)
        cols = st.columns(4)
        cols[0].metric("Motor", usage.get("provider", "-"))
        cols[1].metric("Girdi token", f"{usage.get('input_tokens', 0):,}")
        cols[2].metric("Çıktı token", f"{usage.get('output_tokens', 0):,}")
        cols[3].metric("API çağrısı", usage.get("requests", 0))
        st.caption(f"Model: {usage.get('model', '-')} · Önbellekten: {usage.get('cached_input_tokens', 0):,} · "
                   f"Önbelleğe yazılan: {usage.get('cache_creation_input_tokens', 0):,} · "
                   f"Reasoning: {usage.get('reasoning_tokens', 0):,}")
        price = cost.cost_usd(usage) if usage else None
        if price is not None:
            st.caption(f"Bu haberin tahmini maliyeti: ${price:.4f} · girdinin %{cost.cache_share(usage) * 100:.0f}'i "
                       f"önbellekten (fiyatlar {cost.PRICES_CHECKED})")
        if ss.last_correction_reason:
            st.caption(f"Düzeltme çağrısı nedeni: {ss.last_correction_reason}")
        if ss.last_audio_bytes:
            alignment = TTSAlignment.model_validate(ss.last_audio_alignment) if ss.last_audio_alignment else None
            st.caption("Seslendirme zaman bilgisi: "
                       + (f"var ({len(alignment.characters)} karakter, {alignment.duration_seconds():.1f} sn)" if alignment else "yok"))
        if active:
            st.caption(f"Proje klasörü: {active.folder}")
