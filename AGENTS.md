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
10. **Arayüz sade kalır:** editörün görmesi gerekmeyen bilgi (token, maliyet, sahne tablosu, JSON, dosya yolları)
    sadece "Geliştirici bilgileri" altında; nadir değişen ayarlar kapalı bölümlerde. Sık kullanılan ayarlar
    (üslup, süre, yapay zekâ, model, düşünme seviyesi, spiker) kenar çubuğunda hep görünür ve hatırlanır.

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
  modules/edit_plan.py         Deterministic EditProject 2.1 builder; shared/edit_models.py sözleşmesini üretir

shared/                        Modüller arası sözleşmeler (Pydantic)
  news_package.py              NewsPackage 1.1 (+1.0 migration), TTSAlignment
  media_models.py              MediaLibrary / VideoAsset / Shot / AnalysisWindow (hedef 2.1 modelleri)
  edit_models.py               EditProject / Timeline / Track / Clip (hedef 2.1 modelleri)

windows/                       kurulum.bat, axion_baslat.vbs (konsolsuz başlatıcı), guncelle.bat,
                               anahtarlar.bat, sorun_giderme.bat, kisayol.ps1, axion_x.ico
tests/                         pytest; tests/test_axion_local_app.py uygulamayı AppTest ile uçtan uca sürer
```

## Veri akışı

```text
Haber Stüdyosu ──"Kaydet"──► data/projects/<zaman>_<başlık>/
                               news_package.json  (NewsPackage; ses sha256'sı metadata'da)
                               tts.mp3
Video Studio   ──analiz────►   media_library.json (shared MediaLibrary; tekrar açınca yeniden analiz yok)
                               browser upload ise proje içindeki media/ kaynakları kullanır
               ──hazırla───►   edit_project.json (shared EditProject 2.1)
```

- Aynı ham haber yeniden kaydedilirse aynı proje güncellenir (medya analizi korunur, eski edit_project silinir).
- Ses üretildikten sonra TTS metni değişirse kaydetme engellenir.
- Local inbox dosyaları yerinde okunur (`LocalMediaFile`); browser upload dosyaları aktif proje altındaki `media/` klasörüne kalıcı yazılır. Proxy ve analiz kareleri analizden sonra silinir.


## Nerede kaldık (2026-09-24)

### Tamamlanan
- Faz 0: yerel tek uygulama ve Windows çalışma zinciri gerçek Windows kurulumunda doğrulandı.
- Faz 1: zaman bilgili TTS ve TTSAlignment tamamlandı.
- v1.6.x arayüz sadeleştirmeleri tamamlandı.
- Faz 2 medya sözleşmesi: media_pipeline artık shared.media_models MediaLibrary 2.1 üretir; kaynak SHA-256, VideoGeometry, AudioTechnicalInfo, Shot → AnalysisWindow → AnalysisFrame ve enum tabanlı VisualType/EditorialRole kullanır.
- Faz 2 EditProject: edit_plan artık shared.edit_models EditProject 2.1 üretir; TTS metni NewsSegment'lere ayrılır, alignment doğrulanır ve TTS sesi ortak timeline sözleşmesine bağlanır.
- Eski 1.1 edit_project.json dosyaları kullanılmaz; 2.1 değilse yeniden oluşturulur.
- Browser upload medya kaynakları aktif proje altında media/ klasöründe saklanır; local inbox dosyaları yerinde okunur.
- TTS audio metadata'sına gerçek SHA-256 eklendi.
- Faz 2 için ortak sözleşme regresyon testi eklendi.

- v1.7.1 (Claude): Luna sonuçlarının `unknown`/boş gelmesinin kök nedeni bulundu ve düzeltildi. Sorun Luna'da değil
  eşleme kodundaydı: `description` `subjects` listesine yazılıp okunmuyordu; Luna serbest Türkçe kategori ("olay yeri")
  döndürdüğü için enum'a düşmüyordu. Artık şema enum'lu (Luna sabit kategoriden seçmek zorunda, `unknown` seçeneği yok),
  tüm alanlar `VisualMetadata`'ya birebir aktarılıyor.
- v1.7.1: uzun shot windowing: shot'lar en fazla 10 sn'lik eşit pencerelere bölünür (`representative_sampling.WINDOW_SECONDS`),
  "kare sayısı" pencere başınadır, tüm pencereler yine tek Luna çağrısında gider. 71,6 sn röportaj → 8 pencere.
  Her `AnalysisWindow`'un kendi `visual`'ı var; `Shot.visual` ilk pencerenin özeti.
- Eski/eksik analizler (`is_current_media_library`: 2.1 şemasına uymayan veya `LUNA_PROMPT_VERSION` farklı) yüklenmez;
  editöre "yeniden analiz et" bilgisi gösterilir. Luna prompt/şemasını değiştirirsen `LUNA_PROMPT_VERSION`'ı artır.

### Şu anki durum / sonraki adım
- Faz 2 kodda tamam. **Editörün Windows'ta doğrulaması bekleniyor:** `guncelle.bat` → aynı haberin görüntülerini yeniden
  analiz et → Geliştirici bilgileri tablosunda Görüntü/Rol/Açıklama dolu mu, uzun shot pencerelere bölünmüş mü?
- Sonra Faz 3: API çağrısı olmadan TTS segmentlerini shot pencereleriyle eşleştirip FFmpeg ile 1080x1440 kaba kurgu MP4
  üretmek. AMD `h264_amf` mevcutsa render adımında tercih edilecek.

### Bilinen borçlar
- Tanık sesi ve klip kaynak sesi için çalışma zamanı modeli henüz tamamlanmadı.
- ElevenLabs çağrısı retry edilmez; karakter kotası iki kez tüketilmesin diye bilinçli.
- `make test` çalıştırmadan push etme: v1.7.0 3 kırık testle push edilmişti (eski formatta kayıtlı analiz sayfayı
  çökertiyordu, tarayıcıdan yüklenen görsel analiz sonrası silinip okunmaya çalışılıyordu). v1.7.1'de düzeltildi.

## Komutlar

```bash
pip install -r requirements-dev.txt   # geliştirme bağımlılıkları (pytest dahil)
make test                             # tüm testler
make run                              # uygulamayı başlat: http://localhost:8501
```

Test ortamında FFmpeg yoksa `tests/test_media_pipeline.py` atlanır.
