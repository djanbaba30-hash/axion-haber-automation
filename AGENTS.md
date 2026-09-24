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
  store.py                     Proje klasörü (data/projects/...), gelen kutusu (İndirilenler) listesi

apps/news_studio/              HABER STÜDYOSU
  page.py                      Sayfa: ham haber → başlık/caption/TTS → ses → "Kaydet ve Video Studio'ya geç"
  prompts/news.py              Sistem prompt'u (viral Türkçe sosyal medya kuralları)
  validation/news.py           Deterministik kontroller: tekrar, plaka temizleme, uzunluk
  ai/clients.py, ai/retry.py   OpenAI/Claude çağrıları (tek retry katmanı; SDK retry kapalı)
  tts/service.py, calibration.py  ElevenLabs sesi, karakter/saniye kalibrasyonu
  integration/history.py       SQLite üretim geçmişi (data/history.sqlite3)

apps/video_studio/             VIDEO STUDIO
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
Video Studio   ──analiz────►   media_library.json (shared MediaLibrary; tekrar açınca yeniden analiz yok)
                               browser upload ise proje içindeki media/ kaynakları kullanır
               ──hazırla───►   edit_project.json (shared EditProject 2.1; video izi rough_cut ile dolu)
               ──kesit─────►   kesitler.json (kaynak sesli kesitler) + onizleme/*.mp4 (360p, kesit seçmek için)
               ──oluştur───►   kaba_kurgu.mp4 (960x1226 = Canva şablonunun video alanı, TTS + kesit sesleriyle)
Tasarım Stüdyosu ◄──────────   kaba_kurgu.mp4 + başlıklar (Faz 5: 1080x1920 şablon)
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
- Faz 2 Windows'ta doğrulandı (v1.7.1, Bayrampaşa videosu): 15 shot'ın hepsinde visual_type/editorial_role/açıklama
  dolu ve doğru; 71,6 sn röportaj 8 pencereye bölündü (hepsi person/portrait). 22 kare, tek çağrı, $0.0057.
  Not: Luna plakayı `visible_text`'te okuyor ("34 FPR 116"); Faz 6 blur önerisi bu alanı kullanabilir.
- Faz 3 (v1.8.0, Claude) kodda tamam, **editörün Windows'ta denemesi bekleniyor**:
  - `rough_cut.plan_rough_cut`: segment zamanları alignment'tan (yoksa karakter oranı); her segment ≤3 sn kesitlere bölünür.
    Puan: açıklama/konum kelime eşleşmesi + kavram grupları (yaralı→ambulans, gözaltı→polis, yangın→itfaiye, kaza→hasar)
    + açılışta establishing/action/event + güven. Cezalar: röportaj (portrait) sessiz dolgu olarak, plaka görünen kare,
    aynı shot'ı tekrar veya art arda kullanma. Aynı shot'tan ikinci kesit kaldığı yerden devam eder. Boşluk bırakmaz.
  - Klipler `origin="rule"` (sözleşmeye eklendi). Kadraj (Akıllı=fill_crop / Tüm kare=fit_blur) editör seçer, hatırlanır.
  - `render.render_rough_cut`: her klip ayrı `-ss/-t` girdisi, filtrede tam kare sayısına kırpılır (ses senkronu), concat + TTS.
    Önce `h264_amf` (AMD), hata verirse x264. Dosya önce `.yaziliyor.mp4` adına yazılır.
- Faz 3 Windows'ta doğrulandı: Bayrampaşa videosu hızlıca render edildi, AMD `h264_amf` kullanıldı, editör kaliteden memnun.
- v1.9.0 akıllı kadraj (Claude, editör isteği: "nereden kırpılacağını anlasın"):
  - `framing.detect_content_region`: DHA dikey çekimleri 16:9 içinde iki yanı bulanık verir. Analiz karelerinin
    sütun/satır keskinlik profili (70. yüzdelik; logo etkilemez) → merkezden dışa yürü → sınır çizgisine otur →
    simetri ve kenar medyanı kontrolü → %1,2 güvenlik payı. Siyah bantlar da yakalanır. Sonuç `Shot.content_region`.
  - Luna artık `focus_x/focus_y` (ana öznenin merkezi) döndürüyor → `VisualMetadata.focus_point`. `LUNA_PROMPT_VERSION`
    v2.3 (eski analizler yeniden analiz ister).
  - `Framing.content_region` + odak (content'e göre). Render önce asıl alanı kırpar; Doldur'da kadrajı odağa ortalar,
    Bulanık kenar'da arka planı asıl görüntüden üretir.
- v1.9.1: kurgu çıktısı 1080x1440 yerine şablonun video alanı 960x1226 (`shared/axion_template.py`; editör Canva'da
  ikinci kez kırpmasın). Eski ölçüdeki edit_project'ler açılışta yeniden kurulur. Şablonun tamamı ROADMAP'te (Faz 5).
- v1.9.2: video en az 20 sn (`axion_template.video_seconds`); TTS daha kısaysa son sahne sessiz uzar (`apad`).
  EditProject kuralı artık "timeline ≤ max(TTS, 20 sn)".
- v1.9.3 (editörün Manavgat testi, yatay video + araya konmuş bulanık kenarlı dikey sahneler):
  - Bulanık kenar tespiti gerçek DHA'da dışa taşıyordu (%31,7 yerine ~%42 genişlik → kenarda bulanık şerit).
    `framing._snap_to_vertical_aspect`: yanları bulanık alan en yakın küçük standart orana (9:16, 1:1, 4:3) daraltılır;
    hata hep "fazla yakınlaştır" yönünde.
  - Kesmeler artık sabit 3 sn değil: `rough_cut.cut_points` alignment'tan kelime arası duraklamaları puanlar
    (cümle sonu > virgül > nefes arası, duraklama uzunluğu), `_cut_times` her sahneyi 2–5 sn tutar. Sahne, o aralıkta
    söylenen kelimelere göre seçilir.
  - `edit_plan._segment_ranges`: "17.00" gibi sayılardaki nokta artık cümle sonu sayılmıyor (0,8 sn'lik sahne bunun içindi).
- v1.9.4 (editör: "aşırı zoom yapıp bir cismin yarısını göstermeyelim; kadraja olabildiğince çok şey sığsın"):
  - Luna odak noktası yerine ana öznenin kutusunu verir (`subject_left/right/top/bottom` → `VisualMetadata.subject_region`),
    prompt v2.4. `rough_cut._view_region`: video alanını dolduran en büyük alan (en az zoom), özneyi içerecek şekilde
    kaydırılır; özne daha genişse alan özne kadar genişler, üst/alt bulanık dolgu. `Framing.view_region` → render
    bu alanı kırpıp FIT_BLUR ile yerleştirir.
  - Bulanık kenar oturtması merkezde (DHA hep ortalar; tek yanda şerit kalıyordu), güvenlik payı %2.
  - Token: Luna kareleri 640 px genişlikte (önce 960) → girdi token'ı yaklaşık yarıya inmeli; editör doğrulayacak.
- v2.0.0 (editör isteği, kapsamlı arayüz güncellemesi):
  - Kaynak sesli kesitler: `soundbites.Soundbite` (path, start_s, end_s, placement before/after), proje klasöründe
    `kesitler.json`. Analizden önce de seçilir (2. adımda seçilen videolardan). `plan_rough_cut(..., soundbites)`:
    [öncesi kesitler] → [seslendirme + dolgu] → [sonrası kesitler]; kesit klipleri `use_source_audio=True`,
    TTS ses klibi `start_f` öncesi kesitler kadar kayar; kesit aralıkları dolgu görüntüsünde kullanılmaz (−10 puan).
    Render sesi parça parça kurar (kesit sesi / TTS+apad / kesit sesi), her parça `loudnorm` ile eşitlenir.
    EditProject kuralı: timeline ≤ max(TTS + kesitler, 20 sn).
  - Video Stüdyosu adım adım: biten adım daralır; ayarlar `st.popover`'da (expander iç içe olamaz).
  - Yeni sayfa `apps/design_studio/page.py` (Tasarım Stüdyosu): Canva'nın yerini alacak araçlar burada olacak.
  - Arayüz terimleri Türkçeleştirildi (Video Stüdyosu, seslendirme/paylaşım metni, sahne, girdi/çıktı token).
- v2.1.0 (editörün Kayseri testi: token 17.5k → 4.1k girdi, $0.0022; kesit ses geçişi ve sahne temposu iyi):
  - Bulanık dolgu tamamen kaldırıldı (editör: "videonun hiçbir yanında bulanıklaştırma istemiyorum"). Luna'nın özne
    kutusu genelde tüm kareyi kaplıyordu → v1.9.4'te neredeyse her sahne dolgulu çıkıyordu. `_view_regions`: hep video
    alanı oranında en büyük alan, öznenin ortasına; özne %15'ten fazla genişse kadraj klip boyunca kayar
    (`Framing.view_region_end`, hız karenin %4'ü/sn). Render `crop` x/y ifadesinde `t` kullanır. Kadraj seçimi arayüzden kalktı.
  - `news_studio/validation/speakable.py`: seslendirme metninde saat/tarih/binlik/ondalık → okunuş ("18.00'de" →
    "akşam 6'da", ek uyumlu). Doğrulamada ve "Seslendir"de uygulanır; çevrilemeyen sayı için uyarı. Prompt'a 2 satır kural.
- v2.2.0 (editörün Kayseri + İnegöl testleri; kaydırma kadrajı beğenildi; video analizi ~2,9k girdi token, $0.0017):
  - Kaydırma hızı %4 → %2,5/sn (`rough_cut.PAN_SPEED`).
  - Haber Stüdyosu metin kutuları (ham haber, başlıklar, paylaşım/seslendirme metni) `bound_text` ile anahtarlı:
    anahtarsız kutuya her çalıştırmada `value=` vermek tarayıcıda düzenlemenin kutu dışına tıklayınca kaybolmasına
    yol açıyordu. Widget anahtarı `_w_<alan>`, değer `session_state[<alan>]`; sayfa değişince de kaybolmaz.
  - `axion_local/project_picker.py`: Video/Tasarım stüdyosunda taze açılışta haber seçili gelmez; liste her gün 02:00'de
    (bilgisayar saati) sıfırlanır (`store.work_day_start`), "Önceki günler" ile eskiler görünür.
- v2.2.1: haberler en fazla 3 iş günü saklanır (`store.KEEP_DAYS`, editör kararı). `axion_local.clean_up_for_day`
  her iş günü bir kez eski proje klasörlerini (`store.delete_old_projects`, yalnızca YYYYMMDD-HHMMSS_ adlı klasörler)
  ve `history.sqlite3` kayıtlarını (`delete_runs_before`) siler. İndirilenler'deki kaynak videolara dokunulmaz.
- v2.3.0 (editörün Kars yangını testi: dumanlı/gece dikey çekimde bulanık kenar kadraja girdi):
  - Kök neden: keskinlik tespiti (framing.py) duman/gece/yumuşak görüntüde kaçırdı → sahne tam 16:9 sanıldı → yatay
    kaydırma bulanık kenara girdi. Yedek: Luna `side_bars` (dikey çekim, yanlar dolgulu) → `VisualMetadata.side_bars`;
    tespit yoksa ve Luna "evet" derse `video_asset` ortadaki 9:16 alanı (`framing.standard_vertical_region`) kullanır.
    Prompt v2.5 (yeniden analiz).
  - Kaydırma kuralı (editör): içerik alanı olan (dikey) sahnede yalnızca yukarı/aşağı; tam karede her yön (x ve y
    ayrı ayrı, çapraz olabilir). Hız %3/sn.
- **Faz 3 sonu:** editör bu sürümü test edecek, ardından Claude ve GPT tüm kodu ayrı ayrı gözden geçirecek
  (hata, optimizasyon, sadeleştirme); düzeltmelerden sonra Faz 4'e geçilir (Luna Edit Planner: tek metin çağrısı,
  rough_cut yedek kalır). Plaka/yüz bulanıklaştırma ROADMAP'te Faz 6.

### Bilinen borçlar
- Kaba kurgu tekil görselleri (fotoğraf) kullanmıyor; yalnızca video sahneleri.
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
