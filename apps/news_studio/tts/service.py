import base64
import logging

from elevenlabs import VoiceSettings

from apps.news_studio.tts import pronunciation
from shared.news_package import TTSAlignment

logger = logging.getLogger(__name__)

TTS_MODEL_ID = "eleven_turbo_v2_5"


def alignment_from_response(alignment, text: str) -> TTSAlignment | None:
    """ElevenLabs karakter zamanlarını sözleşmeye çevirir; metinle birebir eşleşmezse None."""
    if alignment is None:
        return None
    characters = list(alignment.characters or [])
    if "".join(characters) != text:
        logger.warning("TTS alignment metinle eşleşmedi; zaman bilgisi kaydedilmeyecek.")
        return None
    try:
        return TTSAlignment(
            characters=characters,
            start_seconds=list(alignment.character_start_times_seconds),
            end_seconds=list(alignment.character_end_times_seconds),
        )
    except ValueError as error:
        logger.warning("TTS alignment geçersiz: %s", error)
        return None


def synthesize(client, text, voice_id, speed, stability, similarity, style, boost,
               lexicon: dict[str, str] | None = None) -> tuple[bytes, TTSAlignment | None, str]:
    """MP3 sesi ve karakter zamanlarını tek çağrıda üretir (ek API maliyeti yok). Okunuş sözlüğü yalnız ElevenLabs'a
    giden metne uygulanır; zamanlar `text`'e göre döner. Üçüncü değer okunan metin (harcanan karakter onun uzunluğu)."""
    spoken, spans = pronunciation.apply(text, lexicon or {})
    response = client.text_to_speech.convert_with_timestamps(
        text=spoken,
        voice_id=voice_id,
        model_id=TTS_MODEL_ID,
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity,
            style=style,
            use_speaker_boost=boost,
            speed=speed,
        ),
    )
    alignment = alignment_from_response(response.alignment, spoken)
    if alignment is not None and spans:
        alignment = pronunciation.remap(alignment, text, spans)
    return base64.b64decode(response.audio_base_64), alignment, spoken


# ElevenLabs anahtar izinleri (API anahtarı → izinler); hata metnindeki adla gelir.
PERMISSIONS = {"user_read": "User → Read", "text_to_speech": "Text to Speech", "voices_read": "Voices → Read"}


def error_message(error: Exception) -> str:
    """ElevenLabs hatasını editörün anlayacağı kısa cümleye çevirir. SDK hatasının metni başlıklarla (headers)
    başlar; kesilince asıl neden hiç görünmüyordu."""
    status = getattr(error, "status_code", None)
    body = getattr(error, "body", None)
    detail = body.get("detail", body) if isinstance(body, dict) else body
    code = str(detail.get("status", "")) if isinstance(detail, dict) else ""
    message = str(detail.get("message", "")) if isinstance(detail, dict) else str(detail or "")
    if code == "missing_permissions" or "missing the permission" in message:
        name = next((label for key, label in PERMISSIONS.items() if key in message), message[:80])
        return (f"API anahtarında \"{name}\" izni yok (ElevenLabs sitesi → Developers → API Keys → anahtarı "
                "düzenle → izni aç)")
    if code == "quota_exceeded":
        return "karakter kotası bitti (yenilenme gününü bekle ya da paketi büyüt)"
    if code in {"invalid_api_key", "api_key_invalid"} or status == 401:
        return "API anahtarı geçersiz (windows\\anahtarlar.bat ile yeniden gir)"
    if status == 429:
        return "ElevenLabs çok yoğun ya da istek sınırı doldu; biraz sonra yeniden dene"
    if status is not None:
        return f"ElevenLabs hatası {status}: {message[:120] or code or 'ayrıntı yok'}"
    if error.__class__.__module__.startswith("httpx"):
        return "ElevenLabs'a ulaşılamadı (internet bağlantısını kontrol et)"
    return str(error)[:160]
