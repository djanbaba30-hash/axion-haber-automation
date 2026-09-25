# AGENTS.md — Yapay zekâ geliştiricileri için proje rehberi

Bu dosya, bu repoda çalışan her yapay zekâ geliştiricisi (GPT/Codex, Claude vb.) için ana başlangıç noktasıdır.
Önce bu dosyayı, sonra `ROADMAP.md`'yi oku.

## Proje nedir

Axion Haber Automation, bir haber editörünün **evdeki Windows bilgisayarında** çalışan yerel bir uygulamadır.
Ham haber + DHA videolarından sosyal medyaya hazır haber videosu üretmeyi otomatikleştirir.
Tek uygulama (Streamlit): **Haber Stüdyosu**, **Video Stüdyosu**, **Tasarım Stüdyosu** ve tabletten DHA'ya girmek için
**Tarayıcı** (evdeki bilgisayarın görünmez Brave'i). Bulut/hosting yok.

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
11. **Kullanım limitini ve bağlamı idareli kullan; iş yarım kalmasın.** Büyük dosyaları bütün okuma, gereken kısmı oku;
    uzun çıktıları kısalt. Uzun işleri küçük, testleri geçen commit'lere böl. Limit ya da bağlam dolmak üzereyse yeni
    işe başlama: yapılanı commit'le, kalanı "Nerede kaldık"a yaz ve editöre "sonraki oturumda devam" de.

## Kod haritası

```text
axion_app.py                   Başlatma noktası (`streamlit run axion_app.py`): st.App(axion_local.py) + Tarayıcı akış kanalı
axion_local.py                 Uygulama: menü, isteğe bağlı şifre, stil (CSS), "Axion'u kapat" (sadece localhost),
                               "✅ … videosu hazır" bildirimi (her sayfada); testler (AppTest) bunu çalıştırır
.streamlit/config.toml         Port 8501, headless, 4 GB yükleme sınırı, beyaz Axion teması (lacivert #123249)
assets/                        axion_mark.png (tarayıcı sekmesi ikonu); windows/axion_x.ico aynı X işareti (masaüstü).
  sablon/                      Faz 5 şablon dosyaları (arka planlar, logo kutusu, örnek Canva videosu; README)
                               Uygulama içinde logo gösterilmez (editör kararı).
.streamlit/secrets.toml        API anahtarları (git'te yok; örnek: secrets.toml.example)

apps/axion_local/
  settings.py                  secret(), require_secrets(): anahtar okuma
  media.py                     media_url(): dosya/görseli tarayıcıya Streamlit medya sunucusuyla verir (Tasarım, Tarayıcı)
  copy_button.py               📋 Paylaşım metnini kopyala (components v2; http'de pano API'si yoksa execCommand yedeği)
  presence.py                  Aynı haber iki cihazda açık mı (oturum → haber; bağlı mı: Streamlit oturum yöneticisi)
  metrics.py                   Adım süreleri → data/olcumler.jsonl (geliştirici için; `timed(...)`)
  update_check.py              🟢/🔴 güncelleme göstergesi: git HEAD ↔ `ls-remote origin main` (arka planda, 30 dk'da bir)
  preferences.py               Son kullanılan ayarlar (üslup, model, spiker, ses ince ayarları) → data/ayarlar.json
  store.py                     Proje klasörü (data/projects/...), 02:00 iş günü, 3 gün saklama, gelen kutusu (İndirilenler),
                               İndirilenler'deki TXT'ler (DHA "TXT indir" → Haber Stüdyosu)
  project_picker.py            Video/Tasarım stüdyosunun ortak haber seçicisi (taze açılışta boş, "Önceki günler")

apps/news_studio/              HABER STÜDYOSU
  page.py                      Sayfa: ham haber → başlıklar/paylaşım metni/seslendirme metni → ses → "Kaydet ve Video Stüdyosu'na geç"
  prompts/news.py              Sistem prompt'u (viral Türkçe sosyal medya kuralları)
  validation/news.py           Deterministik kontroller: tekrar, plaka temizleme, uzunluk
  validation/speakable.py      Seslendirmede saat/tarih/sayı → okunuş ("18.00'de" → "akşam 6'da")
  validation/source_check.py   🟡 Kaynakta yok: çıktıda olup ham haberde geçmeyen sayı/isim (API yok)
  validation/diff.py           Düzeltme çağrısı neyi değiştirdi (kelime farkı)
  read_along.py                Seslendirmeyi okuyarak dinleme (karakter zamanlarından kelime vurgusu; components v2)
  ai/clients.py, ai/retry.py   OpenAI/Claude çağrıları (tek retry katmanı; SDK retry kapalı); yalnız başlık hatalıysa
                               tam düzeltme yerine küçük başlık çağrısı
  ai/cost.py                   Tarihli fiyat tablosu, haber başına tahmini maliyet, önbellek sayacı (data/onbellek.json)
  tts/service.py, calibration.py  ElevenLabs sesi, karakter/saniye kalibrasyonu
  integration/history.py       SQLite üretim geçmişi (data/history.sqlite3)

apps/video_studio/             VIDEO STÜDYOSU
  page.py                      Sayfa: 1. Haber → 2. Görüntüler (analiz) → 3. Kaynak sesli kesitler → 4. Video (kurgu + render)
  modules/media_pipeline.py    ingestion → proxy → shot tespiti → temsilci kare → Luna → Media Library
  modules/ffmpeg_runner.py     Tüm FFmpeg/FFprobe çağrıları (işleme göre timeout)
  modules/visual_analysis.py   Luna (gpt-5.6-luna) görsel analiz çağrısı; kareler 512 px, aynı görünen kareler elenir
  modules/edit_plan.py         Deterministic EditProject 2.1 builder; shared/edit_models.py sözleşmesini üretir
  modules/rough_cut.py         Faz 3 kural tabanlı kurgu: TTS duraklamalarında kesme (2–5 sn sahneler) → sahne penceresi (API yok);
                               aynı çekim kaynak sırasıyla, tek uzun çekimde anlatım sırası, dikeyde sabit kadraj
  modules/framing.py           Akıllı kadraj: bulanık/siyah kenar tespiti (önce DHA'nın sınır çizgisi çifti; analiz karelerinden,
                               numpy/Pillow, API yok)
  modules/soundbites.py        Kaynak sesli kesitler (önce/sonra, kesitler.json) ve 360p önizleme (onizleme/)
  modules/moment.py            Kesitin varsayılan aralığı = olay anı (ani hareket/ses + Luna "action"; API yok)
  modules/render.py            EditProject → tek FFmpeg komutu → kaba_kurgu.mp4 (h264_amf varsa, yoksa x264); ses: parça
                               başına ölçülmüş sabit kazanç (TTS -18, kesit -20 LUFS), kenar yumuşatma, -2 dBFS sınırlayıcı
  jobs.py                      Videoyu arka planda üretme: kaba kurgu → son video (aynı haberin tasarım üretimi önce
                               durdurulur); sayfa saniyede bir durumu yeniler, tablet kapansa da sürer

apps/design_studio/            TASARIM STÜDYOSU (Faz 5, sade Canva; API yok)
  page.py                      Sayfa: kenar çubuğunda durum, Yeniden oluştur/İndir, başlık metinleri, varlık ekleme;
                               ana alanda tek editör bileşeni (tasarımın geri kalanı orada)
  design.py                    tasarim.json v2 (Pydantic): başlık stili, başlıklar+efektler, yazı katmanları, slogan/logo,
                               çerçeve, arka plan, blurlar; v1 (v2.5.0) otomatik yükseltilir
  effects.py, effects.json     Efekt kütüphanesi: yazı giriş/çıkış, slogan, logo, çerçeve stilleri (numpy alanı);
                               süre/mesafeler effects.json'da (editor.js de okur; eşlik: tests/test_effects_parity.py)
  template.py                  Katmanlar (Pillow): kelime sprite'ları (parıltı, sansür çizgisi), sahne zaman çizelgesi,
                               yalnız farklı kareler PNG (paralel), FFmpeg concat listeleri
  blur.py                      Elle blur/mozaik: doğrulama, anahtar kareler (konum, boyut, açı), yumuşak kenarlı maske,
                               kutunun tüm süredeki bölgesi (FFmpeg yalnız orayı işler)
  render.py                    Tek FFmpeg komutu: kurgu → blur/mozaik → arka plan/çerçeve/grafik → son_video.mp4;
                               FFprobe kontrolü (boyut, süre, ses), bozuksa x264 ile yeniden; iptal edilebilir
  pipeline.py                  Projenin son videosu: tasarımı oku, üret, imzayı kaydet (Video Stüdyosu da çağırır);
                               tasarim.json yazmaları kilitli, `rendered` imzasını yalnız `mark_rendered` yazar
  jobs.py                      Son videoyu arka planda üretme (proje başına tek iş; bitince yalnız `rendered` imzası yazılır;
                               yeniden başlatılınca eski iş durdurulur)
  assets.py                    Arka plan sırası (02:00), uygulamadan varlık ekleme (data/varliklar) + GitHub contents API
  editor.py, editor.js         Canva benzeri tarayıcı editörü (components v2): üst araç çubuğu (yazı stili, sansür),
                               sol panel (animasyon kartları, blur), tuval, sağ panel (arka plan, çerçeve), katmanlı
                               zaman çizelgesi; tasarımı kendisi tutar, her değişiklikte `edits` ile Python'a gönderir

apps/remote_browser/           TARAYICI (Faz 6; API yok): tabletten evdeki bilgisayarın görünmez tarayıcısını kullanma
  service.py                   Playwright (async, kendi iş parçacığında) ile Brave/Chrome'u sürer (Edge kasıtlı yok); 1024x768
                               CSS, 1,5x çözünürlük (tablette net yazı), JPEG 70;
                               ekran CDP screencast ile (yalnız değişen kare; yoksa ekran görüntüsü), sekme listesi/seçme;
                               Axion'un kendi profili data/tarayici; indirmeleri Axion yapar (httpx + tarayıcı çerezleri; Brave
                               indirmede çöküyordu) → İndirilenler (.iniyor → ad); 20 dk boşta kapanır;
                               giriş formu gönderilirken bilgileri okur ("kaydedilsin mi?"), kayıtlı sitede kutuları doldurur;
                               profil kilitliyse (Axion zorla kapatılmış) artık süreci kapatıp yeniden dener
  stream.py                    Doğrudan akış (WebSocket, axion_app.py ekler): kareler anında, dokunuşlar anında; oturum jetonlu;
                               ack ile en fazla 2 kare yolda (yavaş internette gecikme birikmez); yoksa fragment yolu
  logins.py                    Kayıtlı girişler data/tarayici_girisler.json (şifre Windows DPAPI ile; tablete gitmez)
  viewer.py, viewer.js         Tabletteki görünüm (components v2, iki bileşen tek JS): ekran + sağda yazı paneli ve indirilenler
                               (dokun=tıkla, sürükle=kaydır, giriş kaydı çubuğu, 🔑, 🎬 Videoda kullan / 📰 Habere aktar) ve
                               kenar çubuğu paneli (◀ ▶ ⟳ ⌂, adres, sekmeler); önce akış kanalına bağlanır;
                               `apply_events` olayları doğrular
  page.py                      Sayfa: ⌂ = DHA abone paneli; iki fragment: ekran 0,25 sn (işlemden sonra taze kare bekler),
                               kenar çubuğu paneli 1 sn

shared/                        Modüller arası sözleşmeler (Pydantic)
  news_package.py              NewsPackage 1.1 (+1.0 migration), TTSAlignment
  media_models.py              MediaLibrary / VideoAsset / Shot / AnalysisWindow (hedef 2.1 modelleri)
  edit_models.py               EditProject / Timeline / Track / Clip (hedef 2.1 modelleri)
  axion_template.py            Axion şablonu: video alanı (kurgu ölçüsü), başlık/slogan/logo konum ve zamanları (Canva örneğinden ölçüldü)
  fonts.py                     Yazı tipi kaydı (repo + data/varliklar/fontlar; değişken fontların kalınlıkları)
  text_layout.py               Başlık yerleşimi ve "2 satıra sığıyor mu" ölçümü (Haber + Tasarım stüdyosu ortak), ~~sansür~~

windows/                       kurulum.bat, axion_baslat.vbs (konsolsuz başlatıcı) → axion_calistir.ps1 (bekçi: çökerse
                               5 sn sonra yeniden başlatır; kod 0 = Axion'u kapat, -1 = Stop-Process/güncelleme), guncelle.bat,
                               anahtarlar.bat, sorun_giderme.bat, testler.bat (make'siz test), kisayol.ps1, axion_x.ico
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
               ──oluştur───►   son_video.mp4 da hemen (standart şablon; design_studio/pipeline.py)
Tasarım Stüdyosu ──düzenle──►   tasarim.json v2 (başlıklar, stil, yazılar, efektler, çerçeve, arka plan, blur/mozaik)
                                 + onizleme/tasarim_onizleme.mp4 (tuval için hafif kopya)
                 ──oluştur───►   son_video.mp4 (1080x1920, sesiyle); imza tasarim.json'da ("güncel mi")
Varlıklar ──────────────────►   data/varliklar/{fontlar,arka_planlar} (+ GITHUB_TOKEN varsa repoya assets/sablon/)
Tarayıcı ──indir────────────►   İndirilenler/<dosya> (Video Stüdyosu'nun gelen kutusu; "kullan" ile 2. adımda seçili)
         ──giriş────────────►   data/tarayici (oturum, çerezler), data/tarayici_girisler.json (kayıtlı girişler, şifreli)
```

- Aynı ham haber yeniden kaydedilirse aynı proje güncellenir (medya analizi korunur, eski edit_project, kurgu ve son
  video silinir). Başlıklar değiştiyse tasarım yeni başlıkları alır (`tasarim.json` `news_headlines`); yalnız Tasarım
  Stüdyosu'nda yapılmış başlık düzenlemeleri haber değişmedikçe korunur.
- Ses üretildikten sonra TTS metni değişirse kaydetme engellenir.

### Dosya yaşam döngüsü

| Dosya | Nerede | Ne zaman silinir |
|---|---|---|
| DHA kaynak videosu | İndirilenler (yerinde okunur, kopyalanmaz) | Axion hiç dokunmaz |
| Tarayıcıdan yüklenen video/görsel | `<proje>/media/` (SHA-256 ile tekrar yazılmaz) | Proje ile (3 gün) |
| Proxy (640 px, sessiz) ve analiz kareleri | Sistem geçici klasörü | Analiz bitince veya hata olunca (`media_pipeline`) |
| Şablon katmanları ve blur maskeleri (PNG + concat listesi) | Sistem geçici klasörü | Son video bitince veya hata olunca (`design_studio/render.py`) |
| `news_package.json`, `tts.mp3`, `media_library.json`, `kesitler.json`, `edit_project.json`, `kaba_kurgu.mp4`, `onizleme/`, `tasarim.json`, `son_video.mp4` | `data/projects/<zaman>_<başlık>/` | 3 iş günü sonra (`store.delete_old_projects`); `edit_project`/MP4 ayrıca haber veya görüntü değişince |
| Üretim geçmişi | `data/history.sqlite3` | 3 iş günü sonra satır satır |
| Ayarlar, seslendirme hız kalibrasyonu, günlük | `data/ayarlar.json`, `data/*.json`, `data/axion.log` | Silinmez |
| Uygulamadan eklenen yazı tipi ve arka planlar | `data/varliklar/` (+ `GITHUB_TOKEN` varsa repoda `assets/sablon/`) | Silinmez |
| Tarayıcı profili (DHA oturumu, çerezler) | `data/tarayici/` | Silinmez (silinirse DHA'ya yeniden giriş) |
| Kayıtlı girişler (şifre DPAPI ile şifreli) | `data/tarayici_girisler.json` | Kenar çubuğundan "Sil" ile |
| Tarayıcıyla indirilen videolar | İndirilenler (yarımken `.iniyor` uzantılı) | Axion silmez |


## Nerede kaldık (2026-09-25) — Sürüm 3.4.1

**3.4.1:** kenar çubuğunda güncelleme göstergesi (editör isteği; `apps/axion_local/update_check.py`).

**3.4.0:** "Sıradaki: v3.4.0" planı yapıldı (aşağıdaki bölüm; ayrıntı CHANGELOG). Kurgu olay örgüsü (aralık bazlı
kullanım, tek uzun çekimde anlatım sırası, Luna'nın gördüğü kare çevresi, öznesiz pencere geride), kenar tespiti sınır
çizgisi çiftiyle (`framing._edge_pair`), dikeyde sabit kadraj, Luna'ya net şerit, indirmeler sayfa betiğiyle
(`service.DOWNLOAD_HOOK` + `axionIndir` bağlaması; Brave'in indirme yöneticisi kullanılmaz).
**Editör doğruladı (Windows, 2026-09-25):** "Tüm Materyali İndir" tek seferde sorunsuz; midibüs videosu "çok daha
başarılı" (olay sırasıyla, net şeridin tamamı). Gerçek kullanım: Haber Stüdyosu 2 çağrı (haber + elle başlık yenileme)
2.688 girdi (%66'sı önbellekten) / 482 çıktı ≈ $0.0008; görüntü analizi 6 kare (net şerit) 1.995 girdi / 754 çıktı
≈ $0.0013. Haber başına toplam ~$0.002.
Tailscale kuruldu: evdeki bilgisayar + telefon (mobil veriyle) Axion'u açtı. **Sıradaki:** editör yarın dükkânda
tabletten tam akışı deneyecek (haber → ses → Tarayıcı'dan DHA → video); sonra dükkân notları + ROADMAP "Sıradaki
işler" 8 (editör yalnız günlük/aylık maliyeti seçti; diğer QoL önerileri istenmedi) yapılır, ardından sürüm 4.0.
Yeni oturum AGENTS.md + ROADMAP'ten başlar.

**3.3.2:** Brave DHA indirmelerinde çöküyordu (editörün günlüğü); indirmeleri artık Axion yapar (`service.fetch_file`:
httpx, tarayıcının çerezleri; `blob:` hâlâ tarayıcıyla). Kurgu: aynı çekimin parçaları kaynak sırasıyla
(`rough_cut._chronological`). Açık: "kadın polis midibüs" videosu 640x480, asıl görüntü ~239 px şerit → ~4x büyütme
bulanık (DHA'da daha yüksek çözünürlüklü dosya var mı, editör bakacak); özne kutusu 9 sn'lik pencere başına tek (elde
çekimde kayabilir) — editörün projesindeki media_library.json/edit_project.json ile doğrulanacak; dar şeritte üst/alt
kırpma yerine koyu kenarlı "tam göster" seçeneği editöre soruldu (bulanık dolgu yasak).

**3.3.1:** Tarayıcı indirirken "yeniden başlatılıyor"da kalma düzeltildi (tek hata çökme sayılmaz, gerçek çökmede
ekran kendiliğinden yeni tarayıcı açar ve sayfaya döner; eşzamanlı aynı adlı indirmeler). Windows'ta tetikleyici
(Brave + DHA İndir) doğrulanmadı; olursa `data\axion.log`.

**3.3.0** (editörün 3.2.0 denemesi + GPT'nin v3.2 incelemesi; ayrıntı `CHANGELOG.md`): kesitin varsayılan aralığı olay
anı (`moment.py`, API yok); yalnız başlık hatalıysa küçük başlık çağrısı, 50 px'e kadar küçülerek sığan başlık uyarı;
başlık görsel önizlemesi kalktı; önbellek sayacı (kenar çubuğu) + tahmini maliyet (Geliştirici bilgileri); Claude
önbelleği 1 saat; Luna'ya kareler 512 px ve aynı görünen kareler elenir (editörün videosunda görüntü token'ı ~7.500 →
~3.000); GPT bulguları G6–G8 (`reviews/claude-v3.md`).

Doğrulananlar (2026-09-25, SDK tanımları + platform.claude.com; developers.openai.com bu ortamdan açılmadı, fiyatlar
ikincil kaynaklardan): GPT-5.6 önbelleği `prompt_cache_options.ttl` = "30m" (tek değer, en az süre), 24 saat yok;
görsel 32 px parça × 1,2 token, "auto"da sınır yok; `detail: "low"`un 5.6'daki etkisi doğrulanamadı (kullanılmadı).
Claude Sonnet 5: en az 1.024 token önbelleklenir (haber komutu ~1.700), 1 saatlik yazma 2x, okuma 0,1x.

**Editörün denemesi beklenenler:** gerçek haberde önbellek sayacı ve maliyet (Luna/Claude), başlık küçük çağrısının
kalitesi, kesit aralığı gerçek DHA videolarında (özellikle güvenlik kamerası), 512 px analizde sahne/kadraj isabeti
(özne kutusu, yan dolgu), bekçi + `guncelle.bat` (çift tıkla). **Açık karar:** sistem komutunu kısaltmak (plan 5. adım)
— önbellek tuttuğu için kazanç küçük; editör isterse gerçek haberle önce/sonra karşılaştırılarak yapılır.

### v3.4.0 kurgu ve kadraj planı (editörle konuşuldu, 2026-09-25; yapıldı)
Örnek: "kadın polis arızalı midibüsü tek başına itti" (DHA 1524464.mp4: 640x480, ortada dikey telefon şeridi ~%37,
yanları DHA'nın bulanık dolgusu; tek, 55 sn'lik gece elde çekimi). GPT editörün projesini okudu
(`data/projects/20260925-215857_kadin-polis-...`): Luna 6 pencere (ekonomik, pencere başına 1 kare) — 0–37 sn beyaz
araç ve "aracın yanındaki kişi" (özne kutusu ortada), 37–55 sn ağaçlık/boş yol (kutu tüm kare). Kurgu YALNIZ
46,3–55,4 sn'yi kullandı; kırpma genişliği karenin %27,7'si (net şerit ~%37). Editör: "boşuna haber oluşturmuyoruz,
olay örgüsü orada yazıyor; saçma sapan kurgu yapmasın". Yapılacaklar (editörün geri bildirimi gelince, tek seferde):
1. **Kurgu olay örgüsünü izlesin:** `rough_cut` çekim başına tek `cursor` tutuyor → geç bir pencere bir kez seçilince
   aynı çekimin önceki pencereleri "tekrar" sayılıp puan kaybediyor, hep aynı pencere seçiliyor (bu videonun hatası).
   Kullanımı pencere/aralık bazında tut. Seslendirmenin anlattığı sırayla (olay → sonuç) kaynak zamanı eşleşsin;
   öznesi olmayan pencereler (kutu tüm kare, ağaçlık/boş yol) geride kalsın; aynı çekimde kaynak sırası (v3.3.2
   `_chronological`) korunur. Regresyon testi bu videonun Luna tablosuyla (GPT'nin tablosu yukarıda) yazılsın.
2. **Yanları bulanık video:** kırpma TAM bulanıklığın bittiği yerden; net görüntüden yandan hiç kesilmez, fazladan
   yakınlaştırma yok. `framing.detect_content_region` bu videoda editörün bilgisayarında dar çıktı (%27,7 vs ~%37;
   sandbox'ta .3133/.3733 bulundu — farkın nedeni araştırılacak: pencere/kare seçimi, karanlık gece karesi). Dikey şerit
   (9:16) 960x1226 alana enine sığar, üst+alttan ~%28 kesilir (editör: seçenek a; koyu kenarla "tamamı" değil).
3. **Dikey görüntüde hiç kaydırma yok:** ne klip içinde ne klipten klibe (sabit kadraj, tüm video boyunca aynı dikey
   konum; özne kutularının ortalamasına göre bir kez). Kaydırma yalnız yatay (geniş) videoda, özne alandan genişse.
4. **Yatay normal video:** alana sığan en geniş alan (tüm yükseklik); özneye göre gereksiz yakınlaştırma yok.
5. **Luna'ya yalnız net şerit:** yanları bulanık videoda analiz karesini bulanıklığın bittiği yerden kırp (özne ~1,3x
   büyük görünür, kare başı ~231 → ~154 token). Luna bu videoda kişiyi gördü; sorun kurgudaydı, bu ek iyileştirme.
6. Çözünürlük: 640x480 kaynakta şerit ~239 px → ~4x büyütme bulanık; editör "Tüm Materyali İndir"deki video daha
   büyük mü bakacak (kodla çözülmez).
Editörün bu testi v3.3.2 ile: indirmeyi Axion yapıyor (Brave çöküyordu), aynı çekim kaynak sırasıyla.

### 3.2.0

**3.2.0:** ROADMAP'teki "Sıradaki işler"in hepsi yapıldı (editörün Windows testinden sonraya bıraktıkları dahil):
Axion çökerse kendini yeniden başlatır (bekçi betiği), kalite kontrolü araçları (kaynakta yok, başlık önizlemesi,
okuyarak dinleme, düzeltme farkı, dosya adı = başlık, "video hazır" bildirimi), adım süresi ölçümü
(`data/olcumler.jsonl`), aynı haber iki cihazda uyarısı. Tarayıcı doğrudan akış kanalıyla (st.App + WebSocket):
sandbox'ta ~19 kare/sn ve 0,15 sn (v3.1: ~4 kare/sn, 0,27 sn); indirilenler sağ panele taşındı. Ölü kod/verimsizlik
temizliği. Windows'ta denenmedi: bekçi betiği, akış kanalı (Tailscale üzerinden), yeni başlatma noktası.

### 3.1.0

**3.1.0:** editör bir günün 4 haberini baştan sona Axion'la yaptı (Windows + tablet); geri bildiriminin hepsi bu
sürümde (`CHANGELOG.md`): çökme düzeltmesi, ses dengesi/sınırlayıcı, istem (başlıkta yer adı yok, spiker dili, röportajda
isim açık), kapak sahnesi, dakika:saniye, kalın çerçeveler ve font, 250 px kenar çubuğu, Tarayıcı'nın yeni düzeni ve
hızı, paylaşım metni kopyalama, TXT'den haber. Editörün yeniden denemesi bekleniyor; özellikle gerçek modelle istem,
gerçek videolarda ses ve Tailscale üzerinden Tarayıcı hızı. Editörün notu: son oluşturma 8 sn (AMD donanım) — v2.9
hızlandırması Windows'ta doğrulandı.

### 3.0.1 ve öncesi

Faz 0–3 bitti ve editör her birini gerçek Windows'ta, gerçek DHA haberleriyle doğruladı (Bayrampaşa, Manavgat,
Kayseri, İnegöl, Kars). Faz 5 (Tasarım Stüdyosu) v2.5–v2.9'da yapıldı; editör v2.7.0'ı denedi ("sorunsuz çalıştı").
Faz 6'nın temel akışı (tabletten DHA → video) v2.10–v3.0'da hazır. Faz 4 ertelendi (aşağıda). Sürüm ayrıntıları
`CHANGELOG.md`'de.

3.0.0 öncesi Claude tüm repoyu inceledi (`reviews/claude-v3.md`: bulgular ve yapılanlar). GPT artık editörün
bilgisayarında yerel çalışıyor (Windows dosyaları + repo); ilk gözlemleri ve kararlar aynı dosyanın sonunda (v3.0.1).
Windows'ta test: `windows\testler.bat` (`make` yok). Windows'ta henüz denenmeyenler: v2.8–v3.0 (geri al/yinele,
~3 kat hızlı son video, FFprobe kontrolü, yeniden başlatma, Tarayıcı + gerçek DHA, giriş kaydı, arka planda video).
Editör için deneme listesi `reviews/claude-v3.md` sonunda. Editörün isteği: arayüz, kullanım kolaylığı, optimizasyon.

### Şu an çalışan akış
1. **Haber Stüdyosu:** ham haber → GPT/Claude (tek çağrı + gerekirse tek düzeltme çağrısı) → başlıklar, paylaşım
   metni, seslendirme metni → deterministik doğrulama (tekrar, plaka, uzunluk, saat/sayı okunuşu) → ElevenLabs
   `convert_with_timestamps` (ses + karakter zamanları tek çağrıda) → proje klasörüne kayıt.
2. **Video Stüdyosu** (adım adım, biten adım daralır):
   - Görüntüler: proxy → FFmpeg sahne tespiti → ≤10 sn pencereler → 640 px kare (Luna'ya 512) → **tek Luna çağrısı** (enum'lu şema:
     tür, rol, açıklama, özne kutusu, `side_bars`) + yerel bulanık/siyah kenar tespiti (`framing.py`). Kareler Luna'ya
     512 px (v3.3); dikey videoda kare başı ~173 token.
   - Kaynak sesli kesitler (isteğe bağlı): önce/sonra, 360p önizleme, kendi sesiyle, `loudnorm`.
   - Kurgu (API yok, `rough_cut.py`): kesmeler seslendirme duraklamalarında, sahneler 2–5 sn; sahne seçimi kelime
     eşleşmesi + kavram grupları + rol; kadraj hep tam dolu (bulanık dolgu yok); dikey çekimde sabit (kaydırma yok),
     tam karede özneye göre, özne büyükse yavaş kaydırma. Video en az 20 sn.
   - Render: tek FFmpeg komutu, 960x1226 (Canva şablonundaki video alanı), önce AMD `h264_amf`, olmazsa x264; ardından
     son video. İkisi de arka planda (`jobs.py`): sayfa beklemez, tablet kapansa da sürer.
3. **Tasarım Stüdyosu (v2.7.0, sade Canva):** Video Stüdyosu kurguyla birlikte standart şablonlu `son_video.mp4`'ü de
   üretir. Editör isterse değiştirir: başlık metni/stili/animasyonu, ~~sansür~~, eklenen yazılar (sürükleyerek konum),
   slogan/logo efektleri (kapatılabilir), çerçeve (sabit, kovalayan ışıklar, nefes, renk akışı, yok), arka plan,
   blur/mozaik (şekil, açı, yumuşak kenar, anahtar kare, canlı takip). Canlı önizleme (tuval) son videonun aynısını
   gösterir (efektlerin JS eşi `editor.js`). Yazı tipleri Pillow ile çizilir; Google Sans Bold (OFL) varsayılan.
4. **Veri:** haberler 3 iş günü saklanır; liste her gün 02:00'de sıfırlanır; taze açılışta haber seçili gelmez.

### Editör kararları (değiştirme; ayrıntı ROADMAP → Ürün kararları)
Doğrudan `main`; token tasarrufu; arayüz Türkçe ve sade; uygulamada logo yok; hiçbir sahnede bulanık dolgu yok;
seslendirmede saat/sayı okunuşuyla; şablon zamanları sabit (9/13/16. sn), video en az 20 sn; haberler 3 gün.

### Faz 3 kod incelemesi tamamlandı (v2.4.0)
GPT (`reviews/gpt-faz3.md`) ve Claude (`reviews/claude-faz3.md`) ayrı ayrı inceledi; kararlar ve yapılan düzeltmeler
Claude raporundaki tablolarda. Luna görsel analizi artık `reasoning.effort="low"`.

### Faz 4 ertelendi (editör kararı, token tasarrufu; ihtiyaç halinde geri dönülecek)
Luna Edit Planner 3.0'da da yok. Sahne seçimi şikâyetleri önce `rough_cut` kurallarıyla (API'siz) çözülür; kurallar
yetmezse yalnızca editörün bastığı "Sahneleri Luna ile düzenle" düğmesiyle, haber başına tek metin çağrısı olarak
yapılır (her haberde otomatik değil). Plan ROADMAP'teki Faz 4 satırında.

### Başlık 2 satır kuralı (v2.6.0, editörün temel kuralı)
`shared/text_layout.check_headline` başlığı videodaki yazıyla ölçer. Prompt'lar "EN FAZLA 44 KARAKTER" der;
doğrulama sığmayan başlığı hata sayar (mevcut tek düzeltme çağrısı somut "x karakter kısalt" hedefiyle gider).
Gerçek model çağrısıyla editörün denemesi bekleniyor (AGENTS kural 5).

### Faz 6: tabletten kullanım (v2.10.0–v3.0.0)
Editörün durumu: dükkân başka ilçede, interneti yavaş (45/13 Mbps), tablet orada; bilgisayarı uzak masaüstüyle
kullanmak (iki monitör, gizli görev çubuğu) pratik değil; tabletten yükleme olmaz. Çözüm: Axion içinde uzak tarayıcı.
Brave (editör Edge sevmiyor; Firefox Playwright ile sürülemiyor), Axion'un kendi profili, DHA'da captcha yok, arada
şifre istiyor → giriş bilgileri bir kez kaydedilir, sonra kutular kendiliğinden dolar (v3.0.0; `DHA_SIFRE` eski yol,
hâlâ çalışır). Gerçek DHA paneliyle henüz denenmedi (sandbox'ta yerel test siteleriyle denendi). Video üretimi arka
planda (tablet kapansa da sürer).

### v3.3.0 planı (yapıldı; 5. adım editörün kararında)
Plan ve GPT'nin plan notları bu sürümde uygulandı (CHANGELOG v3.3.0). Sapmalar: başlık "küçülerek sığıyor" sınırı
planın 42 px'i yerine 50 px (42 px videoda zayıf); `detail: "low"` doğrulanamadığı için yerine 512 px sınırı;
kontak sayfası gerekmedi; açık güncelleme sinyali `guncelle.bat`'ın `git pull` öncesine dokunmayı gerektirdiği için
yapılmadı (G6). Önbellek sayacı kenar çubuğunda (editörün açık isteği, sade tek satır), maliyet ve ayrıntılı
önbellek sayıları Geliştirici bilgileri'nde (kural 10, GPT notu).

Editörün bilgisayar ayarı (yapıldı/önerildi): uyku kapalı (`powercfg /change standby-timeout-ac 0`,
`hibernate-timeout-ac 0`), ekran 30 dk (`monitor-timeout-ac 30`). `guncelle.bat` artık Axion'u açmaz (masaüstü simgesi).
Windows açılışında otomatik başlatma istenmiyor. Uyku/ekran ayarını çalıştırmadan önce mevcut AC değerlerini doğrula;
uyku kapalı olmalı, ekranın kapanması uygulamanın çalışmasını engellememeli.

### Bilinen borçlar
- Kaba kurgu tekil görselleri (fotoğraf) kullanmıyor; yalnızca video sahneleri.
- ElevenLabs çağrısı retry edilmez; karakter kotası iki kez tüketilmesin diye bilinçli.
- `edit_plan.py` ve `media_library.py` isimleri tarihsel (Faz 2 öncesi); davranışları shared 2.1 sözleşmesine uyar.
- Arayüz testleri AppTest ile; tarayıcıya özgü davranışlar (ör. v2.2.0'daki metin kutusu hatası) AppTest'te görünmeyebilir.
  Tasarım editörü (JS) AppTest'te çalışmaz; Playwright/Chromium ile elle denendi (test paketinde değil). Efekt
  formülleri `effects.py` ile `editor.js`'te iki kez yazılı (parametreler tek: `effects.json`); birini değiştiren
  ötekini de değiştirmeli, `tests/test_effects_parity.py` farkı yakalar (Node gerekir; çerçeve çizimi kapsamda değil).
- Editör tasarımı tarayıcıda tutar (başlık metinleri hariç: kenar çubuğu); Python yalnızca haber değişince yükler.
  Yazı stili/metni değişince atlas PNG'leri Python'da yeniden çizilir (tek yeniden çalıştırma gecikmesi).
- Tarayıcı akış kanalı `st.App` (Streamlit'in resmi ASGI yolu) ile eklenir; Axion `axion_app.py` ile başlatılmazsa
  (eski kısayol) ekran fragment yoluna düşer (~4 kare/sn). Akış jetonu süreç başına; yalnız Axion'a girmiş sayfa alır.
- Aynı haber iki cihazda uyarısı ve akış kanalı Streamlit iç API'lerine dayanır (`_session_mgr`, `media_file_mgr` gibi);
  streamlit sürümü sabit, yükseltmede kontrol et.
- Tasarım önizlemesi ve Tarayıcı ekranı Streamlit'in medya sunucusuyla verilir (`runtime.media_file_mgr`, iç API;
  streamlit sürümü sabit; `apps/axion_local/media.py`). Olmazsa gömülü veriye (data URL) düşer.
- Arka plan işleri (tasarım ve video üretimi) Streamlit sürecinin iş parçacıklarıdır: Axion kapanırsa yarıda kalır
  (yarım dosya `.yaziliyor.mp4` adıyla yazılır, yerine konmaz).
- `.streamlit/config.toml` `fileWatcherType = "none"`: kod değişince Axion yeniden başlatılmalı (guncelle.bat yapar).

## Komutlar

```bash
pip install -r requirements-dev.txt   # geliştirme bağımlılıkları (pytest dahil)
make test                             # tüm testler
make run                              # uygulamayı başlat (axion_app.py): http://localhost:8501
```

Test ortamında FFmpeg yoksa `tests/test_media_pipeline.py` atlanır.
