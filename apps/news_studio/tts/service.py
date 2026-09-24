import base64
import logging

from elevenlabs import VoiceSettings

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


def synthesize(client, text, voice_id, speed, stability, similarity, style, boost) -> tuple[bytes, TTSAlignment | None]:
    """MP3 sesi ve karakter zamanlarını tek çağrıda üretir (ek API maliyeti yok)."""
    response = client.text_to_speech.convert_with_timestamps(
        text=text,
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
    return base64.b64decode(response.audio_base_64), alignment_from_response(response.alignment, text)
