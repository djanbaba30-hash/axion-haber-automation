"""Axion Haber şablonu (1080x1920): editörün Canva şablonunun ölçü ve zamanları.

Faz 3 kaba kurguyu doğrudan video alanının ölçüsünde üretir; Faz 5 (Tasarım Stüdyosu) bu tanımla son videoyu kurar.
Konumlar 1080x1920 kanvasın sol üst köşesine göre piksel. Zamanlar saniye; editörün Canva örneğinden
(assets/sablon/ornek_canva.mp4) kare kare ölçüldü.
"""

from __future__ import annotations

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# Şablondaki video alanı: 960x1225, x=60, y=453. H.264 çift sayı ister → kaba kurgu 960x1226 üretilir
# (son videoda alt 1 px kırpılır).
VIDEO_SLOT = {"x": 60, "y": 453, "width": 960, "height": 1225}
VIDEO_WIDTH = 960
VIDEO_HEIGHT = 1226
# Video alanının beyaz çerçevesi (alanın içine çizilir) ve yuvarlak köşeleri.
FRAME_BORDER = 6
FRAME_RADIUS = 22
FRAME_COLOR = (246, 246, 246)

# Zamanlar video uzunluğundan bağımsız, sabittir. Video en az 20 sn; daha uzunsa yalnızca arka plan ve
# 2. başlık videonun sonuna kadar uzar. Seslendirme 20 sn'den kısaysa görüntü sessiz devam eder.
MIN_VIDEO_SECONDS = 20.0


def video_seconds(tts_seconds: float, soundbite_seconds: float = 0.0) -> float:
    """Kurgu/video süresi: seslendirme + kaynak sesli kesitler, en az MIN_VIDEO_SECONDS."""
    return max(float(tts_seconds) + float(soundbite_seconds), MIN_VIDEO_SECONDS)


# Başlıklar: büyük harf, beyaz, hafif parıltı (glow); yazı tipi Google Sans Bold (OFL lisanslı, assets/sablon/fontlar).
# İkisi de aynı kutuda: 960x155, x=60, y=260. En fazla 2 satır (sığmazsa yazı küçülür).
HEADLINE_BOX = {"x": 60, "y": 260, "width": 960, "height": 155}
HEADLINE_FONT_SIZE = 58
HEADLINE_MIN_FONT_SIZE = 42
HEADLINE_LINE_PITCH = 83   # satır başlangıçları arası (örnekte ölçülen)
HEADLINE_MAX_WIDTH = 920
HEADLINE_CENTER_Y = 342    # yazı bloğunun (büyük harf yüksekliği) dikey ortası
# 1. başlık 0. sn'den itibaren ekranda (başa kaynak sesli kesit eklense de); çıkışı "merge": sola kayarak satır satır söner.
HEADLINE_1_EXIT = (8.77, 9.03)
# 2. başlık girişi "merge": 1. satırın kelimeleri sağdan, 2. satırınkiler soldan kelime kelime belirir; sona kadar kalır.
HEADLINE_2_ENTER_START = 13.13

# Başlıklar arasındaki sloganlar (editörün Canva görselleri: slogan_1.png, slogan_2.png), başlık kutusunun ortasında,
# "old tv" animasyonuyla: noktadan yatay çizgiye, çizgiden tam yazıya açılır; kapanırken tersi.
SLOGAN_SCALE = 0.78
SLOGANS = [
    {"file": "slogan_1.png", "text": "TARAFSIZ VE ŞEFFAF HABERCİLİK", "enter": (9.37, 9.93), "exit": (10.57, 10.80)},
    {"file": "slogan_2.png", "text": "BEĞEN, PAYLAŞ, TAKİP ET", "enter": (11.37, 11.93), "exit": (12.60, 12.85)},
]

# Alttan yükselen yumuşak köşeli beyaz logo kutusu ("slow baseline"): hızlı çıkar, yavaşlayarak yerine oturur,
# üzerinden ışık geçer, hızla aşağı iner. Örnekte ölçülen: 15.03 sn'de çıkar, 17.69 sn'de kaybolur.
LOGO_BOX = {"x": 440, "width": 200, "height": 200, "radius": 26, "rest_y": 1737, "logo_width": 160, "logo_top": 16}
LOGO_RISE_START = 15.03
LOGO_RISE_TAU = 0.34         # üstel yavaşlama sabiti (sn)
LOGO_GLINT = (17.15, 17.45)
LOGO_DROP_START = 17.47
LOGO_DROP_SECONDS = 0.215

# 8 arka plan (arka_plan_1..8.png), her iş günü (02:00'de) bir sonraki; aynı gün tüm haberler aynı arka planı kullanır.
BACKGROUND_COUNT = 8
