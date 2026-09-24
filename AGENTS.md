# AGENTS.md — Yapay zekâ geliştiricileri için proje rehberi

Bu dosya, bu repoda çalışan her yapay zekâ geliştiricisi (GPT/Codex, Claude vb.) için ana başlangıç noktasıdır.
Önce bu dosyayı, sonra `ROADMAP.md`'yi oku.

## Proje nedir

Axion Haber Automation, bir haber editörünün **evdeki Windows bilgisayarında** çalışan yerel bir uygulamadır.
Ham haber + DHA videolarından sosyal medyaya hazır haber videosu üretmeyi otomatikleştirir.
Tek uygulama (Streamlit), üç sayfa: **Haber Stüdyosu**, **Video Stüdyosu**, **Tasarım Stüdyosu**. Bulut/hosting yok.

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
9. Kullanıcı Türkçe konuşur; arayüz metinleri ve kullanıcıya yönelik dokümanlar Türkçedir. Arayüzde İngilizce terim
   kullanma: "seslendirme metni" (TTS değil), "paylaşım metni" (caption değil), "sahne" (shot değil), "Video Stüdyosu".
10. **Arayüz sade kalır:** editörün görmesi gerekmeyen bilgi (token, maliyet, sahne tablosu, JSON, dosya yolları)
    sadece "Geliştirici bilgileri" altında; nadir değişen ayarlar kapalı bölümlerde. Sık kullanılan ayarlar
    (üslup, süre, yapay zekâ, model, düşünme seviyesi, spiker) kenar çubuğunda hep görünür ve hatırlanır.
    Video Stüdyosu adım adım ilerler: her adım bir expander; biten adım "✅ …" özet satırına daralır.

## Kod haritası

```text
axion_local.py                 Ana giriş: menü, isteğe bağlı şifre, stil (CSS), "Axion'u kapat" (sadece localhost)
.streamlit/config.toml         Port 8501, headless, 4 GB yükleme sınırı, beyaz Axion teması (lacivert #123249)
assets/                        axion_mark.png (tarayıcı sekmesi ikonu); windows/axion_x.ico aynı X işareti (masaüstü).
                               Uygulama içinde logo gösterilmez (editör kararı).
.streamlit/secrets.toml        API anahtarları (git'te yok; örnek: secrets.toml.example)

apps/axion_local/
  settings.py                  secret(), require_secrets(): anahtar okuma
  preferences.py               Son kullanılan ayarlar (üslup, model, spiker, ses ince ayarları) → data/ayarlar.json
  store.py                     Proje klasörü (data/projects/...), 02:00 iş günü, 3 gün saklama, gelen kutusu (İndirilenler)
  project_picker.py            Video/Tasarım stüdyosunun ortak haber seçicisi (taze açılışta boş, "Önceki günler")

apps/news_studio/              HABER STÜDYOSU
  page.py                      Sayfa: ham haber → başlıklar/paylaşım metni/seslendirme metni → ses → "Kaydet ve Video Stüdyosu'na geç"
  prompts/news.py              Sistem prompt'u (viral Türkçe sosyal medya kuralları)
  validation/news.py           Deterministik kontroller: tekrar, plaka temizleme, uzunluk
  validation/speakable.py      Seslendirmede saat/tarih/sayı → okunuş ("18.00'de" → "akşam 6'da")
  ai/clients.py, ai/retry.py   OpenAI/Claude çağrıları (tek retry katmanı; SDK retry kapalı)
  tts/service.py, calibration.py  ElevenLabs sesi, karakter/saniye kalibrasyonu
  integration/history.py       SQLite üretim geçmişi (data/history.sqlite3)

apps/video_studio/             VIDEO STÜDYOSU
  page.py                      Sayfa: 1. Haber → 2. Görüntüler (analiz) → 3. Kaynak sesli kesitler → 4. Video (kurgu + render)
  modules/media_pipeline.py    ingestion → proxy → shot tespiti → temsilci kare → Luna → Media Library
  modules/ffmpeg_runner.py     Tüm FFmpeg/FFprobe çağrıları (işleme göre timeout)
  modules/visual_analysis.py   Luna (gpt-5.6-luna) görsel analiz çağrısı
  modules/edit_plan.py         Deterministic EditProject 2.1 builder; shared/edit_models.py sözleşmesini üretir
  modules/rough_cut.py         Faz 3 kural tabanlı kurgu: TTS duraklamalarında kesme (2–5 sn sahneler) → sahne penceresi (API yok)
  modules/framing.py           Akıllı kadraj: bulanık/siyah kenar tespiti (analiz karelerinden, numpy/Pillow, API yok)
  modules/soundbites.py        Kaynak sesli kesitler (önce/sonra, kesitler.json) ve 360p önizleme (onizleme/)
  modules/render.py            EditProject → tek FFmpeg komutu → kaba_kurgu.mp4 (h264_amf varsa, yoksa x264)

apps/design_studio/page.py    TASARIM STÜDYOSU: video + kopyalanacak başlık/paylaşım metni; Faz 5'te Axion şablonu (Canva yerine)

shared/                        Modüller arası sözleşmeler (Pydantic)
  news_package.py              NewsPackage 1.1 (+1.0 migration), TTSAlignment
  media_models.py              MediaLibrary / VideoAsset / Shot / AnalysisWindow (hedef 2.1 modelleri)
  edit_models.py               EditProject / Timeline / Track / Clip (hedef 2.1 modelleri)
  axion_template.py            Editörün Canva şablonu: video alanı (kurgu ölçüsü), başlık/slogan/logo konum ve zamanları (Faz 5)

windows/                       kurulum.bat, axion_baslat.vbs (konsolsuz başlatıcı), guncelle.bat,
                               anahtarlar.bat, sorun_giderme.bat, kisayol.ps1, axion_x.ico
tests/                         pytest; tests/test_axion_local_app.py uygulamayı AppTest ile uçtan uca sürer
```

## Veri akışı

```text
Haber Stüdyosu ──"Kaydet"──► data/projects/<zaman>_<başlık>/
                               news_package.json  (NewsPackage; ses sha256'sı metadata'da)
                               tts.mp3
Video Stüdyosu ──analiz────►   media_library.json (shared MediaLibrary; tekrar açınca yeniden analiz yok)
                               browser upload ise proje içindeki media/ kaynakları kullanır
               ──hazırla───►   edit_project.json (shared EditProject 2.1; video izi rough_cut ile dolu)
               ──kesit─────►   kesitler.json (kaynak sesli kesitler) + onizleme/*.mp4 (360p, kesit seçmek için)
               ──oluştur───►   kaba_kurgu.mp4 (960x1226 = Canva şablonunun video alanı, TTS + kesit sesleriyle)
Tasarım Stüdyosu ◄──────────   kaba_kurgu.mp4 + başlıklar (Faz 5: 1080x1920 şablon)
```

- Aynı ham haber yeniden kaydedilirse aynı proje güncellenir (medya analizi korunur, eski edit_project silinir).
- Ses üretildikten sonra TTS metni değişirse kaydetme engellenir.
- Local inbox dosyaları yerinde okunur (`LocalMediaFile`); browser upload dosyaları aktif proje altındaki `media/` klasörüne kalıcı yazılır. Proxy ve analiz kareleri analizden sonra silinir.


## Nerede kaldık (2026-09-24) — Faz 3 tamamlandı, kod incelemesi aşaması

Faz 0–3 bitti ve editör her birini gerçek Windows'ta, gerçek DHA haberleriyle doğruladı (Bayrampaşa, Manavgat,
Kayseri, İnegöl, Kars). Sürüm ayrıntıları `CHANGELOG.md`'de (v1.7.1 → v2.3.0).

### Şu an çalışan akış
1. **Haber Stüdyosu:** ham haber → GPT/Claude (tek çağrı + gerekirse tek düzeltme çağrısı) → başlıklar, paylaşım
   metni, seslendirme metni → deterministik doğrulama (tekrar, plaka, uzunluk, saat/sayı okunuşu) → ElevenLabs
   `convert_with_timestamps` (ses + karakter zamanları tek çağrıda) → proje klasörüne kayıt.
2. **Video Stüdyosu** (adım adım, biten adım daralır):
   - Görüntüler: proxy → FFmpeg sahne tespiti → ≤10 sn pencereler → 640 px kare → **tek Luna çağrısı** (enum'lu şema:
     tür, rol, açıklama, özne kutusu, `side_bars`) + yerel bulanık/siyah kenar tespiti (`framing.py`). Tipik maliyet
     ~3–4k girdi token, ~$0.002/haber.
   - Kaynak sesli kesitler (isteğe bağlı): önce/sonra, 360p önizleme, kendi sesiyle, `loudnorm`.
   - Kurgu (API yok, `rough_cut.py`): kesmeler seslendirme duraklamalarında, sahneler 2–5 sn; sahne seçimi kelime
     eşleşmesi + kavram grupları + rol; kadraj hep tam dolu (bulanık dolgu yok), özneye göre; özne büyükse yavaş
     kaydırma (dikey çekimde yalnız yukarı/aşağı). Video en az 20 sn.
   - Render: tek FFmpeg komutu, 960x1226 (Canva şablonundaki video alanı), önce AMD `h264_amf`, olmazsa x264.
3. **Tasarım Stüdyosu:** video + kopyalanacak başlıklar/paylaşım metni (Faz 5'te Canva'nın yerini alacak).
4. **Veri:** haberler 3 iş günü saklanır; liste her gün 02:00'de sıfırlanır; taze açılışta haber seçili gelmez.

### Editör kararları (değiştirme; ayrıntı ROADMAP → Ürün kararları)
Doğrudan `main`; token tasarrufu; arayüz Türkçe ve sade; uygulamada logo yok; hiçbir sahnede bulanık dolgu yok;
seslendirmede saat/sayı okunuşuyla; şablon zamanları sabit (9/13/16. sn), video en az 20 sn; haberler 3 gün.

### Şimdiki aşama: Faz 3 sonu kod incelemesi
Claude ve GPT tüm repoyu **ayrı ayrı** inceler; ikisi de bulgularını `reviews/` altına yazar (GPT:
`reviews/gpt-faz3.md`, Claude: `reviews/claude-faz3.md`). İnceleme sırasında kod değiştirilmez. Editör iki raporu
karşılaştırır, onaylanan düzeltmeler tek seferde yapılır, sonra **Faz 4** (Luna Edit Planner: TTS segmentleri +
sahne açıklamaları → tek metin çağrısı → kurgu planı; `rough_cut` yedek kalır). Plaka/yüz bulanıklaştırma Faz 6.

### Bilinen borçlar
- Kaba kurgu tekil görselleri (fotoğraf) kullanmıyor; yalnızca video sahneleri.
- ElevenLabs çağrısı retry edilmez; karakter kotası iki kez tüketilmesin diye bilinçli.
- `edit_plan.py` ve `media_library.py` isimleri tarihsel (Faz 2 öncesi); davranışları shared 2.1 sözleşmesine uyar.
- Arayüz testleri AppTest ile; tarayıcıya özgü davranışlar (ör. v2.2.0'daki metin kutusu hatası) AppTest'te görünmeyebilir.

## Komutlar

```bash
pip install -r requirements-dev.txt   # geliştirme bağımlılıkları (pytest dahil)
make test                             # tüm testler
make run                              # uygulamayı başlat: http://localhost:8501
```

Test ortamında FFmpeg yoksa `tests/test_media_pipeline.py` atlanır.
