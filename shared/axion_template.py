"""Axion Haber Canva şablonu (1080x1920), editörün verdiği ölçü ve zamanlamalarla.

Faz 3 kaba kurguyu doğrudan video alanının ölçüsünde üretir (Canva'da ikinci kez kırpma olmasın).
Faz 5 (Canva'nın yerini alma) bu tanımı kullanacak. Konumlar 1080x1920 kanvasın sol üst köşesine göre piksel.
"""

from __future__ import annotations

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# Şablondaki video alanı: 960x1225, x=60, y=453. H.264 çift sayı ister → video 960x1226 üretilir
# (1 px fark; Canva'da alana yerleştirince görünmez).
VIDEO_SLOT = {"x": 60, "y": 453, "width": 960, "height": 1225}
VIDEO_WIDTH = 960
VIDEO_HEIGHT = 1226

# Zamanlar video uzunluğundan bağımsız, sabittir. Video en az 20 sn; daha uzunsa yalnızca arka plan ve
# 2. başlık videonun sonuna kadar uzar. Seslendirme 20 sn'den kısaysa görüntü sessiz devam eder.
MIN_VIDEO_SECONDS = 20.0


def video_seconds(tts_seconds: float, soundbite_seconds: float = 0.0) -> float:
    """Kurgu/video süresi: seslendirme + kaynak sesli kesitler, en az MIN_VIDEO_SECONDS."""
    return max(float(tts_seconds) + float(soundbite_seconds), MIN_VIDEO_SECONDS)


# Başlıklar: Binate Bold, 45 pt, "glow" efekti (yoğunluk 100). İkisi de aynı kutuda: 960x155, x=60, y=260.
HEADLINE_BOX = {"x": 60, "y": 260, "width": 960, "height": 155}
HEADLINE_FONT = {"family": "Binate Bold", "size": 45, "glow_intensity": 100}
HEADLINE_1 = {"start_s": 0.0, "end_s": 9.0, "enter": None, "exit": "merge"}      # girişte animasyon yok
# Videonun başına kaynak sesli kesit (TTS öncesi) eklense de 1. başlık 0. saniyeden itibaren ekrandadır (editör).
HEADLINE_2 = {"start_s": 13.0, "end_s": None, "enter": "merge", "exit": None}    # sona kadar kalır

# Başlıklar arasındaki "reklamvari" yazılar (Canva Text Studio), başlık kutusunun ortasında, her biri 2 sn,
# giriş/çıkış "old tv" animasyonu.
SLOGANS = [
    {"text": "TARAFSIZ HABERCİLİĞİN ADRESİ", "start_s": 9.0, "end_s": 11.0, "animation": "old tv"},
    {"text": "BEĞEN, PAYLAŞ, TAKİP ET", "start_s": 11.0, "end_s": 13.0, "animation": "old tv"},
]

# Alttan yükselen yumuşak köşeli Axion Haber logo kutusu: 16. sn, "slow baseline" (alttan çıkıp geri iner),
# giriş-çıkış dahil ekranda 3 sn.
LOGO_BADGE = {"start_s": 16.0, "end_s": 19.0, "animation": "slow baseline"}

# 8 arka plan (1080x1920), her gün bir sonraki; aynı gün üretilen haberlerin hepsi aynı arka planı kullanır.
BACKGROUND_COUNT = 8
