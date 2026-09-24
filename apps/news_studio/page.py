"""Haber Stüdyosu: ham haber → başlıklar, caption, TTS metni ve sesi → Axion projesi."""

from __future__ import annotations

import io

import streamlit as st
from mutagen.mp3 import MP3
from elevenlabs.client import ElevenLabs

from apps.news_studio.ai.clients import make_anthropic, make_openai, generate, regenerate_headlines
from apps.news_studio.config import *
from apps.news_studio.integration.history import log_run
from apps.news_studio.prompts.news import build_news_prompt, build_correction_prompt
from apps.news_studio.tts.calibration import load as load_calibration, estimate, update as update_calibration
from apps.news_studio.tts.service import synthesize
from apps.news_studio.validation.news import validate_news_output, find_censorship_warnings
from apps.axion_local.settings import require_secrets, secret
from apps.axion_local.store import get_news_project, save_news_project
from shared.news_package import NewsPackage

VIDEO_PAGE = "apps/video_studio/page.py"

st.set_page_config(page_title="Haber Stüdyosu · Axion", page_icon="📰", layout="wide")

DEFAULT_EXAMPLES = {"Standart (Ana Haber) Dili":"","Tepkili Haber Dili":"","Eleştirel Haber Dili":"","Son Dakika Dili":"","Mizahi Haber Dili":""}
AUDIO_STATE = {"last_audio_bytes":None,"last_audio_duration":None,"last_audio_text":None,"last_audio_alignment":None,"last_audio_filename":"axion_haber_ses.mp3"}


def init_state():
    defaults={
        "baslik1":"","baslik2":"","icerik":"","tts_metni":"","raw_text":"",
        "examples":DEFAULT_EXAMPLES.copy(),"last_usage":None,"last_validation":[],"last_warnings":[],
        "last_correction_reason":"","tts_calibration":load_calibration(),"last_headline_usage":None,**AUDIO_STATE
    }
    for k,v in defaults.items(): st.session_state.setdefault(k,v)


@st.cache_resource
def openai_client(): return make_openai(secret("OPENAI_API_KEY"))
@st.cache_resource
def anthropic_client(): return make_anthropic(secret("ANTHROPIC_API_KEY"))
@st.cache_resource
def elevenlabs_client(): return ElevenLabs(api_key=secret("ELEVENLABS_API_KEY"), timeout=TTS_TIMEOUT_SECONDS)


@st.cache_data(ttl=3600)
def fetch_voices():
    response=elevenlabs_client().voices.get_all()
    return [(v.name,v.voice_id) for v in response.voices]


def accumulate(a,b):
    out=(a or {}).copy()
    for k in ("input_tokens","output_tokens","cached_input_tokens","cache_creation_input_tokens","reasoning_tokens","requests"):
        out[k]=out.get(k,0)+b.get(k,0)
    out["provider"]=b.get("provider",out.get("provider","-")); out["model"]=b.get("model",out.get("model","-"))
    return out


def reset_state():
    keep={"examples","tts_calibration","voice_name","ai_provider","openai_model"}
    for k in list(st.session_state.keys()):
        if k not in keep: del st.session_state[k]
    st.session_state.update(AUDIO_STATE)


require_secrets("OPENAI_API_KEY","ANTHROPIC_API_KEY","ELEVENLABS_API_KEY"); init_state()

# =================================================
# KENAR ÇUBUĞU: AYARLAR
# =================================================
with st.sidebar:
    style=st.selectbox("Üslup",list(DEFAULT_EXAMPLES),index=0)
    duration_label=st.selectbox("Seslendirme süresi",list(TTS_DURATION_PRESETS),index=2)
    duration_range=TTS_DURATION_PRESETS[duration_label]
    try:
        voices=fetch_voices(); names=[x[0] for x in voices]
        default=next((i for i,n in enumerate(names) if "Cavit" in n and "Presenter" in n), next((i for i,n in enumerate(names) if "Cavit" in n),0))
        saved=st.session_state.get("voice_name"); idx=names.index(saved) if saved in names else default
        voice_name=st.selectbox("Spiker",names,index=idx); st.session_state.voice_name=voice_name
        voice_id=dict(voices)[voice_name]
    except Exception:
        st.warning("ElevenLabs sesleri alınamadı. API anahtarını kontrol et.")
        voice_name=voice_id=""
    with st.expander("Gelişmiş ayarlar"):
        provider=st.radio("Yapay zekâ",["OpenAI","Claude"],horizontal=True,key="ai_provider")
        openai_model=st.selectbox("OpenAI modeli",list(OPENAI_MODELS),key="openai_model") if provider=="OpenAI" else "GPT-5.6 Luna"
        if provider=="Claude": st.caption(f"Claude modeli: `{CLAUDE_MODEL}`")
        thinking=st.selectbox("Düşünme seviyesi",["Kapalı (Tasarruflu)","Düşük","Orta","Yüksek"],index=0,help="Yüksek seviye daha pahalıdır.")
        speed=st.slider("Hız",0.7,1.2,1.11,0.01)
        stability=st.slider("Stabilite",0.0,1.0,0.50,0.01)
        similarity=st.slider("Benzerlik",0.0,1.0,0.65,0.01)
        style_strength=st.slider("Stil",0.0,1.0,0.10,0.01)
        boost=st.toggle("Speaker Boost",value=True)
    with st.expander("Üslup örnekleri"):
        st.caption("İsteğe bağlı: seçilen üslup için örnek bir haber metni. Model yalnızca tonu örnek alır.")
        for name in list(st.session_state.examples):
            st.session_state.examples[name]=st.text_area(name,value=st.session_state.examples[name],height=90,key="ex_"+name)
    tts_min,tts_target,tts_max,cps=estimate(st.session_state.tts_calibration,voice_id or "default",speed,duration_range)
    if st.button("Yeni haber",use_container_width=True,help="Ekrandaki haberi temizler; kayıtlı projeler silinmez."): reset_state(); st.rerun()

# =================================================
# HAM HABER
# =================================================
st.title("📰 Haber Stüdyosu")
st.session_state.raw_text=st.text_area("Ham haber",value=st.session_state.raw_text,height=200,placeholder="DHA'dan gelen ham haber metnini buraya yapıştır.")
raw=st.session_state.raw_text.strip()
if len(raw)>7000: st.warning(f"Ham haber {len(raw):,} karakter. Çok uzun metinler maliyeti artırır.")

if st.button("Haberi işle",type="primary",use_container_width=True):
    if not raw: st.error("Önce ham haber metnini yapıştır.")
    else:
        prompt=build_news_prompt(style,duration_label,duration_range,tts_min,tts_target,tts_max,raw,speed,st.session_state.examples)
        with st.spinner("Haber hazırlanıyor..."):
            try:
                result,usage=generate(openai_client(),anthropic_client(),provider,openai_model,prompt,thinking)
                check=validate_news_output(result,raw,tts_min,tts_max)
                total=accumulate(None,{**usage,"provider":provider})
                correction_reason=""
                if check.errors:
                    correction_reason=" | ".join(check.errors)
                    cp=build_correction_prompt(style,duration_label,tts_min,tts_target,tts_max,raw,result,check.errors)
                    try:
                        corrected,cusage=generate(openai_client(),anthropic_client(),provider,openai_model,cp,"Düşük",CORRECTION_MAX_TOKENS)
                        total=accumulate(total,cusage)
                        corrected_check=validate_news_output(corrected,raw,tts_min,tts_max)
                        if len(corrected_check.errors)<len(check.errors): result,check=corrected,corrected_check
                    except Exception as exc: st.warning(f"Kalite düzeltme çağrısı başarısız; ilk sonuç korunuyor: {exc}")
                if st.session_state.get("active_news_source")!=raw: st.session_state.pop("active_news_project",None)
                st.session_state.baslik1=result.baslik1; st.session_state.baslik2=result.baslik2; st.session_state.icerik=result.icerik; st.session_state.tts_metni=result.tts
                st.session_state.last_usage=total; st.session_state.last_validation=check.errors; st.session_state.last_warnings=check.warnings+find_censorship_warnings(result.tts+"\n"+result.icerik); st.session_state.last_correction_reason=correction_reason; st.session_state.last_headline_usage=None
                log_run(HISTORY_DB_PATH,raw_text=raw,result=result,usage=total,style=style,provider=provider,model=total.get("model",""),validation=check.errors)
                st.rerun()
            except Exception as exc: st.error(f"Haber işlenemedi ({provider}): {exc}")

if st.session_state.icerik:
    usage=st.session_state.last_usage or {}
    notes=st.session_state.last_validation+st.session_state.last_warnings
    if notes: st.warning("**Kontrol et:**\n\n"+"\n".join(f"- {n}" for n in notes))

    # =================================================
    # BAŞLIKLAR + CAPTION
    # =================================================
    st.subheader("Başlıklar")
    h1,h2=st.columns(2)
    st.session_state.baslik1=h1.text_input("1. başlık",value=st.session_state.baslik1)
    st.session_state.baslik2=h2.text_input("2. başlık",value=st.session_state.baslik2)
    if st.button("↻ Başlıkları yeniden üret",help="Sadece başlıklar için küçük bir yapay zekâ çağrısı yapar."):
        try:
            h,u=regenerate_headlines(openai_client(),anthropic_client(),provider,openai_model,st.session_state.icerik)
            st.session_state.baslik1=h.baslik1; st.session_state.baslik2=h.baslik2; st.session_state.last_headline_usage=u; st.rerun()
        except Exception as e: st.error(f"Başlıklar üretilemedi: {e}")

    st.subheader("Paylaşım metni")
    st.session_state.icerik=st.text_area("Caption",value=st.session_state.icerik,height=260,label_visibility="collapsed")
    st.caption(f"{len(st.session_state.icerik)}/2200 karakter")
    with st.expander("Kopyalamaya hazır tam metin"):
        st.code(f"{st.session_state.baslik1}\n\n{st.session_state.baslik2}\n\n{st.session_state.icerik}",language="text")

    # =================================================
    # SESLENDİRME
    # =================================================
    st.subheader("Seslendirme")
    st.session_state.tts_metni=st.text_area("TTS metni",value=st.session_state.tts_metni,height=150,label_visibility="collapsed")
    st.caption(f"{len(st.session_state.tts_metni)} karakter · hedef {tts_min}–{tts_max} ({duration_label})")
    if st.button("🎙️ Seslendir",type="primary",use_container_width=True):
        tts_text=st.session_state.tts_metni.strip()
        if not voice_id: st.error("Spiker seçilemedi; ElevenLabs anahtarını kontrol et.")
        elif not tts_text: st.error("TTS metni boş.")
        else:
            try:
                with st.spinner("Ses üretiliyor..."):
                    audio,alignment=synthesize(elevenlabs_client(),tts_text,voice_id,speed,stability,similarity,style_strength,boost)
                try: duration=float(MP3(io.BytesIO(audio)).info.length)
                except Exception: duration=None
                st.session_state.tts_metni=tts_text
                st.session_state.update({"last_audio_bytes":audio,"last_audio_text":tts_text,"last_audio_alignment":alignment,"last_audio_duration":duration})
                if duration: st.session_state.tts_calibration=update_calibration(st.session_state.tts_calibration,voice_id,speed,len(tts_text),duration)
                st.rerun()
            except Exception as e: st.error(f"Ses üretilemedi: {e}")

    audio_stale=bool(st.session_state.last_audio_bytes) and st.session_state.get("last_audio_text")!=st.session_state.tts_metni
    if st.session_state.last_audio_bytes:
        player,download=st.columns([4,1])
        player.audio(st.session_state.last_audio_bytes,format="audio/mp3")
        download.download_button("MP3 indir",data=st.session_state.last_audio_bytes,file_name=st.session_state.last_audio_filename,mime="audio/mp3",use_container_width=True)
        if st.session_state.last_audio_duration: st.caption(f"Ses süresi {st.session_state.last_audio_duration:.1f} sn · hedef {duration_range[0]:g}–{duration_range[1]:g} sn")

    # =================================================
    # PROJEYE KAYDET
    # =================================================
    st.divider()
    active=get_news_project(st.session_state.active_news_project) if st.session_state.get("active_news_project") else None
    if audio_stale:
        st.warning("TTS metni ses üretildikten sonra değişti. Kaydetmeden önce yeniden **Seslendir**.")
    else:
        if not st.session_state.last_audio_bytes: st.caption("Henüz ses yok. Video kurgusu için önce seslendir.")
        package=NewsPackage(headline_1=st.session_state.baslik1,headline_2=st.session_state.baslik2,caption=st.session_state.icerik,tts_text=st.session_state.tts_metni,source_text=raw,provider=usage.get("provider",""),model=usage.get("model",""),tts_duration_target=duration_label,tts_actual_duration_seconds=st.session_state.last_audio_duration,tts_voice_id=voice_id or "",tts_speed=speed,tts_alignment=st.session_state.last_audio_alignment if st.session_state.last_audio_bytes else None,metadata={"style":style,"usage":usage})
        go_col,save_col=st.columns([3,1])
        go=go_col.button("Kaydet ve Video Studio'ya geç",type="primary",use_container_width=True)
        save_only=save_col.button("Sadece kaydet",use_container_width=True)
        if go or save_only:
            try:
                folder=save_news_project(package,st.session_state.last_audio_bytes,folder=active.folder if active else None)
                st.session_state.active_news_project=folder.name; st.session_state.active_news_source=raw
                st.session_state.pop("loaded_news_project",None)
                if go: st.switch_page(VIDEO_PAGE)
                st.success("Proje kaydedildi.")
            except Exception as e: st.error(f"Proje kaydedilemedi: {e}")

    # =================================================
    # GELİŞTİRİCİ BİLGİLERİ
    # =================================================
    with st.expander("Geliştirici bilgileri"):
        c=st.columns(4); c[0].metric("Motor",usage.get("provider","-")); c[1].metric("Input",f"{usage.get('input_tokens',0):,}"); c[2].metric("Output",f"{usage.get('output_tokens',0):,}"); c[3].metric("API çağrısı",usage.get("requests",0))
        st.caption(f"Model: {usage.get('model','-')} · Önbellek: {usage.get('cached_input_tokens',0):,} · Reasoning: {usage.get('reasoning_tokens',0):,}")
        if st.session_state.last_correction_reason: st.caption(f"Düzeltme çağrısı nedeni: {st.session_state.last_correction_reason}")
        if st.session_state.last_audio_bytes:
            alignment=st.session_state.last_audio_alignment
            st.caption("TTS zaman bilgisi: " + (f"var ({len(alignment.characters)} karakter, {alignment.duration_seconds():.1f} sn)" if alignment else "yok"))
        if active: st.caption(f"Proje klasörü: {active.folder}")
