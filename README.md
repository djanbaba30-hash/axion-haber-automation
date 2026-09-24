# Axion Haber Automation

Temiz başlangıç repo yapısı: **Axion Haber İçerik Stüdyosu** ve **Axion Video Studio** birbirinden ayrıdır; ortak veri sözleşmesi `shared/news_package.py` içindedir.

## Mimari

```text
axion-haber-automation/
├── apps/
│   ├── news_studio/
│   │   ├── app.py
│   │   ├── ai/
│   │   ├── models/
│   │   ├── prompts/
│   │   ├── validation/
│   │   ├── tts/
│   │   └── integration/
│   └── video_studio/
│       ├── app.py
│       └── modules/
├── shared/
│   └── news_package.py
├── tests/
├── data/
├── requirements.txt
└── packages.txt
```

## Uygulamaların sorumlulukları

### Haber Stüdyosu
- OpenAI / Claude seçimi
- Structured output
- Editoryal kalite kontrolü ve yalnızca gerekli olduğunda correction çağrısı
- TTS süre tahmini ve gerçek MP3 süresiyle kalibrasyon
- TTS MP3'ünün session state içinde tutulması; rerun sonrası kaybolmaması
- ElevenLabs ses seçiminin korunması
- NewsPackage JSON dışa aktarımı
- Basit SQLite üretim geçmişi

### Video Studio
- Video/görsel yükleme
- FFprobe metadata
- FFmpeg proxy
- Shot detection
- Representative frame sampling
- GPT-5.6 Luna ile görsel asset indeksleme
- Media Library
- TTS + haber metni ile EditProject başlangıcı
- NewsPackage JSON içe aktarımı

Video akışında Claude kullanılmaz.

## Kurulum

```bash
pip install -r requirements.txt
```

FFmpeg sistem paketidir ve `packages.txt` ile Streamlit Cloud üzerinde kurulabilir.

## Streamlit Cloud

Aynı repo içinden iki ayrı uygulama deploy edebilirsin:

- Haber: `apps/news_studio/app.py`
- Video: `apps/video_studio/app.py`

Secrets için `.streamlit/secrets.toml.example` dosyasını referans al; gerçek `secrets.toml` dosyasını repoya koyma.

## Çalıştırma

```bash
streamlit run apps/news_studio/app.py
```

veya

```bash
streamlit run apps/video_studio/app.py
```

## NewsPackage bağlantısı

Haber Stüdyosu bir `axion_news_package.json` üretir. Video Studio bu JSON'u doğrudan içe alabilir. TTS MP3 ayrı yüklenir.

Bu ayrım bilinçli: iki uygulamanın deploy yaşam döngüsünü birbirine bağlamadan veri sözleşmesini ortaklaştırır.

## Test

```bash
python -m unittest discover -s tests -v
```

## Notlar

- `data/` Streamlit Cloud üzerinde kalıcı disk değildir. TTS kalibrasyonu ve SQLite geçmişi yerel/ephemeral depolamadır. Kalıcı üretim geçmişi gerektiğinde harici bir storage katmanı eklenmelidir.
- AI ve TTS çağrılarında transient hata için sınırlı exponential backoff vardır; editoryal validation hataları otomatik retry edilmez.
- Caption'ın bilgi yoğunluğu korunur; optimizasyon haber bilgisini kısaltmak için yapılmamıştır.
