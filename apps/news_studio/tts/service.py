from elevenlabs import VoiceSettings


def synthesize(client, text, voice_id, speed, stability, similarity, style, boost):
    chunks = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_turbo_v2_5",
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity,
            style=style,
            use_speaker_boost=boost,
            speed=speed,
        ),
    )
    return b"".join(chunks)
