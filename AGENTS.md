# AGENTS.md — Yapay zekâ geliştiricileri için proje rehberi

Bu dosya, bu repoda çalışan her yapay zekâ geliştiricisi (GPT/Codex, Claude vb.) için ana başlangıç noktasıdır.
Önce bu dosyayı, sonra `ROADMAP.md`'yi oku.

## Proje nedir

Axion Haber Automation, bir haber editörünün **evdeki Windows bilgisayarında** çalışan yerel bir uygulamadır.
Ham haber + DHA videolarından sosyal medyaya hazır haber videosu üretmeyi otomatikleştirir.
Tek uygulama (Streamlit), iki sayfa: **Haber Stüdyosu** ve **Video Studio**. Bulut/hosting yok.

- Ürün hedefi, editörün kararları ve faz sırası: `ROADMAP.md`
- Kullanıcı için kurulum ve kullanım: `KURULUM.md`
- Sürüm geçmişi: `CHANGELOG.md`

## Çalışma kuralları

1. **Doğrudan `main`'e commit ve push et.** Branch/PR açma (repo sahibinin açık talimatı).
2. **Push etmeden önce `make test` çalıştır ve tamamen geçtiğinden emin ol** (`pip install -r requirements-dev.txt`).
3. **CHANGELOG'a yalnızca gerçekten yapılanı yaz.** Yapılmamış işi "yapıldı" diye listeleme.
4. **API/token maliyetini gözet.** Gereksiz ikinci model çağrısı ekleme; sistem prompt'u önbelleğe alınıyor, kısa ve yoğun tut.
5. **Editoryal kurallar editörün kararıdır** (ROADMAP → Ürün kararları). Haber üretim mantığını (prompt, doğrulama)
   değiştirirken gerçek bir haberle test et ve regresyon testi ekle (`tests/test_viral_tts_quality.py` örneği).
6. **Video tarafının yapay zekâ motoru GPT-5.6 Luna'dır.** Claude, Video Studio çalışma zamanında kullanılmaz.
7. **Modüller ayrı kalır.** Tek arayüz (`axion_local.py`) sayfaları birleştirir; iş mantığı `apps/*/` ve `shared/` içinde yaşar.
8. **Windows betikleri** (`windows/*.bat|.vbs|.ps1`) ASCII ve CRLF olmalı (Türkçe karakter yok; `.gitattributes` CRLF'yi korur).
9. Kullanıcı Türkçe konuşur; arayüz metinleri ve kullanıcıya yönelik dokümanlar Türkçedir.

## Kod haritası

```text
axion_local.py                 Ana giriş: isteğe bağlı şifre, iki sayfalı menü, "Axion'u kapat" (sadece localhost)
.streamlit/config.toml         Port 8501, headless, 4 GB yükleme sınırı, sade araç çubuğu
.streamlit/secrets.toml        API anahtarları (git'te yok; örnek: secrets.toml.example)

apps/axion_local/
  settings.py                  secret(), require_secrets(): anahtar okuma
  store.py                     Proje klasörü (data/projects/...), gelen kutusu (İndirilenler) listesi

apps/news_studio/              HABER STÜDYOSU
  page.py                      Sayfa: ham haber → başlık/caption/TTS → ses → "Kaydet ve Video Studio'ya geç"
  prompts/news.py              Sistem prompt'u (viral Türkçe sosyal medya kuralları)
  validation/news.py           Deterministik kontroller: tekrar, plaka temizleme, uzunluk
  ai/clients.py, ai/retry.py   OpenAI/Claude çağrıları (tek retry katmanı; SDK retry kapalı)
  tts/service.py, calibration.py  ElevenLabs sesi, karakter/saniye kalibrasyonu
  integration/history.py       SQLite üretim geçmişi (data/history.sqlite3)

apps/video_studio/             VIDEO STUDIO
  page.py                      Sayfa: 1. haber projesi → 2. medya analizi → 3. EditProject
  modules/media_pipeline.py    ingestion → proxy → shot tespiti → temsilci kare → Luna → Media Library
  modules/ffmpeg_runner.py     Tüm FFmpeg/FFprobe çağrıları (işleme göre timeout)
  modules/visual_analysis.py   Luna (gpt-5.6-luna) görsel analiz çağrısı
  modules/edit_plan.py         ESKİ taslak EditProject (1.1); hedef sözleşme shared/edit_models.py (2.1)

shared/                        Modüller arası sözleşmeler (Pydantic)
  news_package.py              NewsPackage 1.1 (+1.0 migration), TTSAlignment
  media_models.py              MediaLibrary / VideoAsset / Shot / AnalysisWindow (hedef 2.1 modelleri)
  edit_models.py               EditProject / Timeline / Track / Clip (hedef 2.1 modelleri)

windows/                       kurulum.bat, axion_baslat.vbs (konsolsuz başlatıcı), guncelle.bat,
                               anahtarlar.bat, sorun_giderme.bat, kisayol.ps1, axion.ico
tests/                         pytest; tests/test_axion_local_app.py uygulamayı AppTest ile uçtan uca sürer
```

## Veri akışı

```text
Haber Stüdyosu ──"Kaydet"──► data/projects/<zaman>_<başlık>/
                               news_package.json  (NewsPackage; ses sha256'sı metadata'da)
                               tts.mp3
Video Studio   ──analiz────►   media_library.json (Luna sonucu; tekrar açınca yeniden analiz yok)
               ──hazırla───►   edit_project.json
```

- Aynı ham haber yeniden kaydedilirse aynı proje güncellenir (medya analizi korunur, eski edit_project silinir).
- Ses üretildikten sonra TTS metni değişirse kaydetme engellenir.
- Videolar kopyalanmadan diskten okunur (`LocalMediaFile`); proxy ve kareler analizden sonra silinir.

## Nerede kaldık (2026-09-24)

Tamamlanan:
- Faz 0: yerel tek uygulama, proje klasörü, Windows kurulum/başlatıcı. Editör gerçek Windows'ta kurdu ve
  Bayrampaşa haberiyle baştan sona (haber → ses → video analizi → proje) hatasız çalıştırdı.
- Faz 1: zaman bilgili TTS. `tts/service.py` ElevenLabs `convert_with_timestamps` kullanır (tek çağrı, ek maliyet yok);
  karakter zamanları `TTSAlignment` olarak `news_package.json`'a kaydedilir. Metinle birebir eşleşmezse alignment
  kaydedilmez, ses yine kullanılır.
- Arayüz sadeleştirildi: kullanıcıya gerekmeyen ayarlar "Gelişmiş" altında, token/maliyet "Geliştirici bilgileri"
  altında. Video Studio'da EditProject otomatik oluşur (düğme yok).
- Haber Stüdyosu viral TTS kuralları (v1.2.0): tekrar yasağı, süre hedefi üst sınır, plaka temizleme.

**Sıradaki iş — Faz 2 (Video Studio'yu shared/ 2.1 modellerine taşıma), ardından Faz 3 (kaba kurgu MP4):**
1. `media_pipeline.py` çıktısını `shared.media_models.MediaLibrary` (VideoAsset/Shot) olarak üret; Luna yanıtını
   `VisualType`/`EditorialRole` enum'larına eşle (`visual_analysis.py` şemasını enum'lu yap). Eski `media_library.py`,
   `video_asset.py`, `edit_plan.py` kaldırılır; `media_library.json` eski formattaysa yeniden analiz iste.
2. `shared.edit_models.EditProject` üret: `NewsReference` (tts_alignment dahil), `AudioReference`, `NewsSegment`ler
   (TTS cümleleri; `char_start/char_end`, zamanlar alignment'tan).
3. Faz 3: kural tabanlı eşleştirme (API çağrısı yok) — her TTS cümlesine sırayla uygun shot; FFmpeg ile orijinal
   videodan kesip TTS ile birleştir, 1080×1440 MP4'ü proje klasörüne yaz. AMD donanım kodlayıcı (`h264_amf`) varsa kullan.

Sonrası (ROADMAP): Faz 4 Edit Planner (Luna, tek metin çağrısı) → Faz 5 Axion şablonu (1080×1920) → Faz 6 blur önerisi.

Maliyet notu: OpenAI Batch API (%50 indirim) etkileşimli akışa uygun değil (sonuç 24 saate kadar gecikir).
Tasarruf; prompt önbelleği, ekonomik Luna modu (shot başına 1 kare) ve API'siz kural tabanlı adımlarla sağlanır.

## Bilinen borçlar

- Video Studio hâlâ eski formatları üretiyor: EditProject 1.1 (`modules/edit_plan.py`), Media Library 1.0
  (`media_library.py`, `video_asset.py`; `*_formatted` alanları, serbest metin `visual_type`/`editorial_role`).
  Faz 2'de `shared/media_models.py` ve `shared/edit_models.py`'ye taşınacak.
- Luna shot başına en fazla 4 kare görüyor; 70 sn'lik röportaj gibi uzun shot'lar pencerelere bölünmüyor.
- Tanık sesi (başta/sonda/yok) ve klip kaynak sesi alanları sözleşmede yok; `EditProject` "timeline ≤ TTS süresi"
  kuralı tanık sesi gelince "TTS + tanık sesi" olarak güncellenmeli.
- ElevenLabs çağrısı retry edilmez (bilinçli: tekrar karakter kotası harcayabilir).
- Tarayıcıdan yüklenen videolar geçici klasörde kalır (yerel klasörden seçilenler kopyalanmaz).

## Komutlar

```bash
pip install -r requirements-dev.txt   # geliştirme bağımlılıkları (pytest dahil)
make test                             # tüm testler
make run                              # uygulamayı başlat: http://localhost:8501
```

Test ortamında FFmpeg yoksa `tests/test_media_pipeline.py` atlanır.
