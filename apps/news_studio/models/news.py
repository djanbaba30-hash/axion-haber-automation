from pydantic import BaseModel


class NewsOutput(BaseModel):
    baslik1: str
    baslik2: str
    icerik: str
    tts_plani: list[str]
    tts: str


class HeadlineOutput(BaseModel):
    baslik1: str
    baslik2: str


class TtsOutput(BaseModel):
    """Yalnız seslendirme metni ("↻ Seslendirme metnini yeniden üret", v3.6.3)."""
    tts_plani: list[str]
    tts: str
