# Axion Haber Automation

Ham haber ve DHA videolarından sosyal medyaya hazır haber videosu üretimini otomatikleştiren,
editörün **kendi Windows bilgisayarında** çalışan yerel uygulama.

Tek uygulama, dört sayfa (sürüm 3.0):

- **📰 Haber Stüdyosu:** Ham haber → iki başlık, paylaşım metni, seslendirme metni → ElevenLabs sesi.
  "Kaydet ve Video Stüdyosu'na geç" ile haber, projesiyle birlikte Video Stüdyosu'na aktarılır.
- **🎬 Video Stüdyosu:** Haber projesi + bilgisayardaki videolar → sahne tespiti → GPT-5.6 Luna görsel analizi →
  isteğe bağlı kaynak sesli kesitler → kural tabanlı kaba kurgu → Canva şablonunun video alanı ölçüsünde MP4.
- **🎨 Tasarım Stüdyosu:** Canva'nın yerine Axion şablonu (arka plan, başlık animasyonları, sloganlar, logo kutusu),
  canlı önizleme, yazılar, sansür, çerçeve efektleri ve elle blur/mozaik (sürükleyerek takip) → 1080×1920 son video.
- **🌐 Tarayıcı:** tabletten evdeki bilgisayarın görünmez Brave'iyle DHA'ya girip videoyu doğrudan bilgisayara indirme
  (giriş bilgileri bir kez kaydedilir, sonra kendiliğinden dolar).

Uzaktan (telefon/tablet) erişim Tailscale ile; iş hep evdeki bilgisayarda yapılır, internete açık port yok.

Her haber `data/projects/` altında bir proje klasörüdür; haber, ses, görüntü analizi, kesitler, kurgu ve video orada durur.

## Belgeler

| Dosya | İçerik |
|---|---|
| [KURULUM.md](KURULUM.md) | Windows kurulumu, günlük kullanım, telefon/tabletten erişim |
| [ROADMAP.md](ROADMAP.md) | Ürün hedefi, editör kararları, fazlar |
| [AGENTS.md](AGENTS.md) | Geliştirici (yapay zekâ) kuralları, kod haritası, **nerede kaldık** |
| [CHANGELOG.md](CHANGELOG.md) | Sürüm geçmişi |

## Hızlı başlangıç (Windows)

1. `winget install -e --id Git.Git`
2. `git clone https://github.com/djanbaba30-hash/axion-haber-automation.git C:\Axion`
3. `C:\Axion\windows\kurulum.bat` → API anahtarlarını gir → masaüstündeki **Axion Local** ikonu.

Ayrıntılar: [KURULUM.md](KURULUM.md).

## Geliştirme

```bash
pip install -r requirements-dev.txt
make test    # pytest
make run     # http://localhost:8501 (streamlit run axion_app.py)
```

Windows'ta `make` yok: testler için `windows\testler.bat` (ya da `.venv\Scripts\python.exe -m pytest`).

Sistem gereksinimi: Python 3.12, FFmpeg; Tarayıcı sayfası için Brave (ya da Chrome).
