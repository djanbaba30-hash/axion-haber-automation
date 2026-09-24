from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mutagen.mp3 import MP3
from elevenlabs.client import ElevenLabs

from apps.news_studio.ai.clients import make_anthropic, make_openai, generate, regenerate_headlines
from apps.news_studio.config import *
from apps.news_studio.integration.history import log_run
from apps.news_studio.models.news import NewsOutput
from apps.news_studio.prompts.news import build_news_prompt, build_correction_prompt
from apps.news_studio.tts.calibration import load as load_calibration, estimate, update as update_calibration
from apps.news_studio.tts.service import synthesize
from apps.news_studio.validation.news import validate_news_output, find_censorship_warnings
from shared.news_package import NewsPackage
from apps.axion_local.store import is_local_mode, save_news_project


st.set_page_config(page_title="Axion Haber İçerik Stüdyosu", layout="wide")

DEFAULT_EXAMPLES = {"Standart (Ana Haber) Dili":"","Tepkili Haber Dili":"","Eleştirel Haber Dili":"","Son Dakika Dili":"","Mizahi Haber Dili":""}


def secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value).strip() if value else None


def require_secrets():
    required=("OPENAI_API_KEY","ANTHROPIC_API_KEY","ELEVENLABS_API_KEY") if is_local_mode() else ("APP_PASSWORD","OPENAI_API_KEY","ANTHROPIC_API_KEY","ELEVENLABS_API_KEY")
    missing=[x for x in required if not secret(x)]
    if missing:
        st.error("Eksik Streamlit secret: " + ", ".join(missing))
        st.code("APP_PASSWORD = \"...\"\nOPENAI_API_KEY = \"...\"\nANTHROPIC_API_KEY = \"...\"\nELEVENLABS_API_KEY = \"...\"")
        st.stop()


def init_state():
    defaults={
        "password_correct":False,"baslik1":"","baslik2":"","icerik":"","tts_metni":"","raw_text":"",
        "examples":DEFAULT_EXAMPLES.copy(),"last_usage":None,"last_validation":[],"last_warnings":[],
        "last_correction_reason":"","tts_calibration":load_calibration(),"last_audio_duration":None,
        "last_audio_bytes":None,"last_audio_filename":"axion_haber_ses.mp3","last_headline_usage":None,
        "news_package_json":""
    }
    for k,v in defaults.items(): st.session_state.setdefault(k,v)


def check_password():
    expected=secret("APP_PASSWORD")
    if not expected:
        st.error("APP_PASSWORD secret tanımlı değil.")
        return False
    if st.session_state.get("password_correct"):
        return True
    def entered():
        st.session_state.password_correct=(st.session_state.get("password","")==expected)
        st.session_state.pop("password",None)
    st.text_input("Şifre", type="password", key="password", on_change=entered)
    if st.session_state.get("password_correct") is False and "password" not in st.session_state:
        st.error("Şifre yanlış.")
    return False


@st.cache_resource
def openai_client(): return make_openai(secret("OPENAI_API_KEY"))
@st.cache_resource
def anthropic_client(): return make_anthropic(secret("ANTHROPIC_API_KEY"))
@st.cache_resource
def elevenlabs_client():
    key=secret("ELEVENLABS_API_KEY")
    try:return ElevenLabs(api_key=key, timeout=TTS_TIMEOUT_SECONDS)
    except TypeError:return ElevenLabs(api_key=key)


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
    keep={"examples","tts_calibration"}
    for k in list(st.session_state.keys()):
        if k not in keep: del st.session_state[k]
    st.session_state.update({"password_correct":True,"last_audio_bytes":None,"last_audio_duration":None,"last_audio_filename":"axion_haber_ses.mp3"})


require_secrets(); init_state()
if not is_local_mode() and not check_password(): st.stop()

st.title("Axion Haber İçerik Stüdyosu")

with st.sidebar:
    st.header("1. Yapay Zekâ Motoru")
    provider=st.radio("Haber üretim motoru",["OpenAI","Claude"],horizontal=True,key="ai_provider")
    openai_model=st.selectbox("OpenAI Modeli",list(OPENAI_MODELS),key="openai_model") if provider=="OpenAI" else "GPT-5.6 Luna"
    if provider=="Claude": st.caption(f"Claude modeli: `{CLAUDE_MODEL}`")
    thinking=st.selectbox("Düşünme / Reasoning",["Kapalı (Tasarruflu)","Düşük","Orta","Yüksek"],index=0)
    st.divider(); st.header("2. Haber Ayarları")
    style=st.selectbox("Haberin Üslubu",list(DEFAULT_EXAMPLES),index=0)
    duration_label=st.selectbox("TTS Süre Hedefi",list(TTS_DURATION_PRESETS),index=2)
    duration_range=TTS_DURATION_PRESETS[duration_label]
    st.divider(); st.header("3. Ses Ayarları")
    try:
        voices=fetch_voices(); names=[x[0] for x in voices]
        default=next((i for i,n in enumerate(names) if "Cavit" in n and "Presenter" in n), next((i for i,n in enumerate(names) if "Cavit" in n),0))
        saved=st.session_state.get("voice_name"); idx=names.index(saved) if saved in names else default
        voice_name=st.selectbox("Spiker Seçimi",names,index=idx); st.session_state.voice_name=voice_name
        voice_id=dict(voices)[voice_name]
    except Exception as e:
        st.warning("ElevenLabs sesleri alınamadı. API anahtarını ve hesabı kontrol edin.")
        voice_name=voice_id=""
    speed=st.slider("Speed",0.7,1.2,1.11,0.01)
    stability=st.slider("Stability",0.0,1.0,0.50,0.01)
    similarity=st.slider("Similarity",0.0,1.0,0.65,0.01)
    style_strength=st.slider("Style",0.0,1.0,0.10,0.01)
    boost=st.toggle("Speaker Boost",value=True)
    tts_min,tts_target,tts_max,cps=estimate(st.session_state.tts_calibration,voice_id or "default",speed,duration_range)
    st.info(f"**Tahmini TTS:** {duration_range[0]:g}–{duration_range[1]:g} sn\n\nKarakter: **{tts_min}–{tts_max}** · merkez **{tts_target}**")
    st.divider()
    if st.button("Sistemi Sıfırla / Temizle",use_container_width=True): reset_state(); st.rerun()

with st.expander("Üslup Referans Örnekleri Ekle (İsteğe Bağlı)"):
    for name in list(st.session_state.examples):
        st.session_state.examples[name]=st.text_area(name,value=st.session_state.examples[name],height=90,key="ex_"+name)

st.markdown("### 📰 Ham Haber")
st.session_state.raw_text=st.text_area("Ham Haber Metni",value=st.session_state.raw_text,height=220)
raw=st.session_state.raw_text.strip()
if len(raw)>7000: st.warning(f"Ham haber {len(raw):,} karakter. Çok uzun girişler token kullanımını ve editoryal kontrolü artırabilir.")

if st.button("Haberi İşle",type="primary",use_container_width=True):
    if not raw: st.error("Lütfen önce ham haber metnini girin.")
    else:
        prompt=build_news_prompt(style,duration_label,duration_range,tts_min,tts_target,tts_max,raw,speed,st.session_state.examples)
        with st.spinner(f"{provider} haberi işliyor..."):
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
                st.session_state.baslik1=result.baslik1; st.session_state.baslik2=result.baslik2; st.session_state.icerik=result.icerik; st.session_state.tts_metni=result.tts
                st.session_state.last_usage=total; st.session_state.last_validation=check.errors; st.session_state.last_warnings=check.warnings+find_censorship_warnings(result.tts+"\n"+result.icerik); st.session_state.last_correction_reason=correction_reason; st.session_state.last_headline_usage=None
                log_run(HISTORY_DB_PATH,raw_text=raw,result=result,usage=total,style=style,provider=provider,model=total.get("model",""),validation=check.errors)
                st.rerun()
            except Exception as exc: st.error(f"{provider} API Hatası: {exc}")

if st.session_state.icerik:
    usage=st.session_state.last_usage or {}
    st.success(f"Haber işlendi — {usage.get('provider',provider)}")
    if usage:
        with st.expander("Son API Kullanımı"):
            c=st.columns(4); c[0].metric("AI Motoru",usage.get("provider","-")); c[1].metric("Input",f"{usage.get('input_tokens',0):,}"); c[2].metric("Output",f"{usage.get('output_tokens',0):,}"); c[3].metric("API Çağrısı",usage.get("requests",1))
            st.caption(f"Model: {usage.get('model','-')} · Cached: {usage.get('cached_input_tokens',0):,} · Reasoning: {usage.get('reasoning_tokens',0):,}")
    if st.session_state.last_validation: st.warning("Kalan kalite kontrolü: " + " | ".join(st.session_state.last_validation))
    if st.session_state.last_warnings:
        st.info("Editoryal uyarı: " + " | ".join(st.session_state.last_warnings))
    st.markdown("### 📝 Haber Başlıkları")
    st.session_state.baslik1=st.text_input("1. Başlık",value=st.session_state.baslik1)
    st.session_state.baslik2=st.text_input("2. Başlık",value=st.session_state.baslik2)
    if st.button("Sadece Başlıkları Yeniden Üret"):
        try:
            h,u=regenerate_headlines(openai_client(),anthropic_client(),provider,openai_model,st.session_state.icerik)
            st.session_state.baslik1=h.baslik1; st.session_state.baslik2=h.baslik2; st.session_state.last_headline_usage=u; st.rerun()
        except Exception as e: st.error(f"Başlık üretim hatası: {e}")
    st.markdown("### 📱 Sosyal Medya İçeriği")
    st.caption(f"Karakter: {len(st.session_state.icerik)}/2200")
    st.session_state.icerik=st.text_area("Caption",value=st.session_state.icerik,height=280)
    with st.expander("Kopyalamaya Hazır Tam Metin"):
        st.code(f"{st.session_state.baslik1}\n\n{st.session_state.baslik2}\n\n{st.session_state.icerik}",language="text")
    st.markdown("### 🎙️ Seslendirme")
    st.info(f"Hedef: {duration_label} · {tts_min}–{tts_max} karakter · merkez {tts_target}")
    st.session_state.tts_metni=st.text_area("TTS Metni",value=st.session_state.tts_metni,height=160)
    if st.button("Yukarıdaki Metni Seslendir (MP3 Üret)",type="primary",use_container_width=True):
        if not voice_id: st.error("Lütfen bir spiker seçin.")
        elif not st.session_state.tts_metni.strip(): st.error("TTS metni boş.")
        else:
            try:
                with st.spinner("ElevenLabs ses sentezi yapılıyor..."):
                    audio=synthesize(elevenlabs_client(),st.session_state.tts_metni,voice_id,speed,stability,similarity,style_strength,boost)
                st.session_state.last_audio_bytes=audio
                st.session_state.last_audio_text=st.session_state.tts_metni
                st.session_state.last_audio_filename="axion_haber_ses.mp3"
                try:
                    duration=float(MP3(io.BytesIO(audio)).info.length)
                except Exception: duration=None
                st.session_state.last_audio_duration=duration
                if duration: st.session_state.tts_calibration=update_calibration(st.session_state.tts_calibration,voice_id,speed,len(st.session_state.tts_metni),duration)
                st.rerun()
            except Exception as e: st.error(f"Seslendirme hatası: {e}")
    if st.session_state.last_audio_bytes:
        st.audio(st.session_state.last_audio_bytes,format="audio/mp3")
        if st.session_state.last_audio_duration: st.success(f"Gerçek ses süresi: {st.session_state.last_audio_duration:.1f} sn · Hedef {duration_range[0]:g}–{duration_range[1]:g} sn")
        st.download_button("MP3 Olarak İndir",data=st.session_state.last_audio_bytes,file_name=st.session_state.last_audio_filename,mime="audio/mp3")

    st.divider(); st.markdown("### 🔗 Video Studio Paketi")
    package=NewsPackage(headline_1=st.session_state.baslik1,headline_2=st.session_state.baslik2,caption=st.session_state.icerik,tts_text=st.session_state.tts_metni,source_text=raw,provider=usage.get("provider",""),model=usage.get("model",""),tts_duration_target=duration_label,tts_actual_duration_seconds=st.session_state.last_audio_duration,tts_voice_id=voice_id or "",tts_speed=speed,metadata={"style":style,"usage":usage})
    package_json=package.model_dump_json(indent=2)
    st.download_button("NewsPackage JSON indir",data=package_json,file_name="axion_news_package.json",mime="application/json")
    if is_local_mode():
        audio_stale=bool(st.session_state.last_audio_bytes) and st.session_state.get("last_audio_text")!=st.session_state.tts_metni
        if audio_stale:
            st.warning("TTS metni ses üretildikten sonra değişti. Projeye kaydetmeden önce sesi yeniden üret.")
        elif st.button("Projeye kaydet (Video Studio'da kullan)",use_container_width=True):
            try:
                folder=save_news_project(package,st.session_state.last_audio_bytes)
                st.success(f"Proje kaydedildi: {folder.name}" + ("" if st.session_state.last_audio_bytes else " (ses henüz yok)"))
            except Exception as e: st.error(f"Proje kaydedilemedi: {e}")
    elif st.session_state.last_audio_bytes:
        st.caption("Video Studio için JSON ve MP3 dosyasını birlikte kullanabilirsin.")
