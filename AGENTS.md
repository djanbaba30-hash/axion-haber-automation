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
- Editörün denemesini bekleyenler: `DENENECEKLER.md` (yeni ön sürümde ekle; editör denediğinde sil, sonucu CHANGELOG'a)
- Araştırma raporları (kod yok, editör karar verir): `arastirma/`

## Çalışma kuralları

1. **Doğrudan `main`'e commit ve push et.** Branch/PR açma (repo sahibinin açık talimatı).
2. **Push etmeden önce `make test` çalıştır ve tamamen geçtiğinden emin ol** (`pip install -r requirements-dev.txt`).
   Yalnız belge (`*.md`) değişen commit'te gerekmez; CHANGELOG'un ilk başlığı değişiyorsa gerekir (sürümü testler okur).
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
    (süre, yapay zekâ, model, düşünme seviyesi, spiker) kenar çubuğunda hep görünür ve hatırlanır. Editörün haber
    talimatı (v4.2) "Haberi işle"nin yanında; her yeni haberde boş gelir.
    Video Stüdyosu adım adım ilerler: her adım bir expander; biten adım "✅ …" özet satırına daralır.
11. **Kullanım limitini ve bağlamı idareli kullan; iş yarım kalmasın.** Büyük dosyaları bütün okuma, gereken kısmı oku;
    uzun çıktıları kısalt. Uzun işleri küçük, testleri geçen commit'lere böl. Limit ya da bağlam dolmak üzereyse yeni
    işe başlama: yapılanı commit'le, kalanı "Nerede kaldık"a yaz ve editöre "sonraki oturumda devam" de.
12. **Editörün kalıcı ilkesi (2026-09-26; her işte geçerli, editör tekrarlamak zorunda kalmasın):** adım adım ve
    planlı git; her adımda **bir şeyi** ve ondan etkilenebilecek her şeyi (çağıranlar, testler, belgeler) birlikte
    düzenle. **Arkada çöp bırakma** (ölü kod, kullanılmayan dosya/sabit/oturum anahtarı, eski açıklama). Optimizasyon
    ve verimlilik önceliklidir: API kullanılsa bile verimli (gereksiz çağrı/token yok) ama **kaliteden ödün vermeden**.
    Büyük işte önce plan editöre onaylatılır ("tamam / devam / iptal").
13. **Repoya not az ve öz (editör, 2026-09-26):** repoya yalnız (a) kod değişince, (b) editör bir kararı kesinleştirince
    (mümkünse o kararın ilk kod commit'iyle birlikte), (c) oturum biterken "Nerede kaldık" için yazılır. Beyin fırtınası,
    seçenekler, taslaklar sohbette kalır. Her push editörde "güncelleme var" gösterir: belge için ayrı push'u biriktir.
    GPT yalnız büyük işlerden önce (fikir) ve uzun serilerin sonunda (kontrol, hata) okur; ona sürekli not yazılmaz.

## Kod haritası

```text
axion_app.py                   Başlatma noktası (`streamlit run axion_app.py`): st.App(axion_local.py) + Tarayıcı akış kanalı
axion_local.py                 Uygulama: menü, isteğe bağlı şifre, stil (CSS), "Axion'u kapat" (sadece localhost),
                               "✅ … videosu hazır" bildirimi (her sayfada); testler (AppTest) bunu çalıştırır
.streamlit/config.toml         Port 8501, headless, 4 GB yükleme sınırı, beyaz Axion teması (lacivert #123249)
assets/                        axion_mark.png (tarayıcı sekmesi ikonu); windows/axion_x.ico aynı X işareti (masaüstü).
  sablon/                      Faz 5 şablon dosyaları (arka planlar, logo kutusu, örnek Canva videosu; README)
  muzik/                       Müzik altlıkları (v4.0; uret.py ile sentezlendi, telif yok; README)
                               Uygulama içinde logo gösterilmez (editör kararı).
.streamlit/secrets.toml        API anahtarları (git'te yok; örnek: secrets.toml.example)

apps/axion_local/
  settings.py                  secret(), require_secrets(): anahtar okuma
  media.py                     media_url(): dosya/görseli tarayıcıya Streamlit medya sunucusuyla verir (Tasarım, Tarayıcı)
  copy_button.py               📋 Paylaşım metnini kopyala (components v2; http'de pano API'si yoksa execCommand yedeği)
  presence.py                  Aynı haber iki cihazda açık mı (oturum → haber; bağlı mı: Streamlit oturum yöneticisi)
  metrics.py                   Adım süreleri → data/olcumler.jsonl (geliştirici için; `timed(...)`, alt adım `step(...)`,
                               son ölçüm `last(...)`; teşhis dosyasında da gider)
  update_check.py              🟢/🔴 güncelleme göstergesi: git HEAD ↔ `ls-remote origin main` (arka planda, 2 dk'da bir;
                               satır fragment, 2 dk'da kendiliğinden yenilenir);
                               uygulamadan güncelleme (`git pull`, çıkış kodu 3 → bekçi pip + yeniden başlatır);
                               önceki sürüm data/guncelleme_onceki.txt, geri dönüş uyarısı; sürüm = CHANGELOG ilk başlığı
  self_check.py                Açılış kontrolü (bekçi güncellemeden sonra çalıştırır): derle, içe aktar, 3 sayfayı AppTest
                               ile çiz (boş veri klasörü); geçmezse bekçi önceki sürüme döner
  corrections.py               Düzeltmelerden öğrenme kaydı (v4.0): model çıktısı ↔ editörün son hâli, sahne/kesit
                               değişiklikleri → data/duzeltmeler.jsonl (silinmez; Geliştirici bilgileri'nden indirilir)
  status.py, ledger.py         Durum paneli (disk, ElevenLabs kalan karakter [arka planda, 10 dk] + Axion'un bugün/bu ay
                               harcadığı karakter, okunamazsa neden; FFmpeg) ve maliyet
                               defteri data/maliyet.jsonl (günlük/aylık; v4.0; Geliştirici bilgileri)
  diagnostics.py               Teşhis dosyası: projenin kurgu JSON'ları + günlüğün sonu tek JSON (Video Stüdyosu → Geliştirici
                               bilgileri → İndir; internete gönderilmez, editör sohbette yollar)
  preferences.py               Son kullanılan ayarlar (süre, model, spiker, ses ince ayarları) → data/ayarlar.json
  store.py                     Proje klasörü (data/projects/...), 02:00 iş günü, 3 gün saklama, gelen kutusu (İndirilenler),
                               İndirilenler'deki TXT'ler (DHA "TXT indir" → Haber Stüdyosu)
  project_picker.py            Video/Tasarım stüdyosunun ortak haber seçicisi (taze açılışta boş, "Önceki günler")

apps/news_studio/              HABER STÜDYOSU
  page.py                      Sayfa: ham haber (+ editörün talimatı, v4.2) → başlıklar/paylaşım metni/seslendirme metni → ses
                               → "Kaydet ve Video Stüdyosu'na geç"
  prompts/news.py              Sistem prompt'u (viral Türkçe sosyal medya kuralları; varsayılan objektif haber sunucusu);
                               `instruction_block`: editörün talimatı kullanıcı istemine (boşsa hiç yok)
  validation/news.py           Deterministik kontroller: tekrar, plaka temizleme, uzunluk
  validation/speakable.py      Seslendirmede saat/tarih/sayı → okunuş ("18.00'de" → "akşam 6'da")
  validation/source_check.py   🟡 Kaynakta yok: çıktıda olup ham haberde geçmeyen sayı/isim (API yok)
  validation/diff.py           Düzeltme çağrısı neyi değiştirdi (kelime farkı)
  read_along.py                Seslendirmeyi okuyarak dinleme (karakter zamanlarından kelime vurgusu; components v2)
  ai/clients.py, ai/retry.py   OpenAI/Claude çağrıları (tek retry katmanı; SDK retry kapalı); yalnız başlık hatalıysa
                               tam düzeltme yerine küçük başlık çağrısı
  ai/cost.py                   Tarihli fiyat tablosu, haber başına tahmini maliyet, önbellek sayacı (data/onbellek.json)
  tts/service.py, calibration.py  ElevenLabs sesi, karakter/saniye kalibrasyonu; `error_message` (ElevenLabs hatasının
                               açık nedeni: izin eksik, anahtar geçersiz, kota, internet)
  tts/pronunciation.py         Okunuş sözlüğü (v4.1) data/okunus.json: yalnız ElevenLabs'a giden metne uygulanır,
                               karakter zamanları ekrandaki metne geri taşınır (`remap`)
  integration/history.py       SQLite üretim geçmişi (data/history.sqlite3)

apps/video_studio/             VIDEO STÜDYOSU
  page.py                      Sayfa: 1. Haber → 2. Görüntüler (analiz) → 3. Kaynak sesli kesitler → 4. Video (kurgu + render)
  modules/media_pipeline.py    ingestion → proxy → shot tespiti → temsilci kare → Luna → Media Library; alt adım süreleri
                               (v4.1, `STEP_LABELS`) "goruntu_analizi" ölçüm satırının `adimlar` alanına
  modules/ffmpeg_runner.py     Tüm FFmpeg/FFprobe çağrıları (işleme göre timeout)
  modules/visual_analysis.py   Luna (gpt-5.6-luna) görsel analiz çağrısı; kareler 512 px, aynı görünen kareler elenir;
                               haberin başlık + seslendirmesi bağlam olarak gider (v3.7; "görmediğini yazma")
  modules/edit_plan.py         Deterministic EditProject 2.1 builder; shared/edit_models.py sözleşmesini üretir
  modules/luna_edit.py         Faz 4 (v3.6–3.7): sahneleri Luna seçer — tek görüntüsüz çağrı (haberin anlatımı + sahneler +
                               pencereler [mekân, karedeki yazı, insan] → olay_orgusu, sahne başına asama + pencere +
                               başlangıç anı, enum'lu şema); plan kurgu_plani.json (imza aynıysa yeniden çağrı yok;
                               "yeniden seç" önceki kurguyu "beğenilmedi" diye gönderir); olmazsa kurallar
  modules/rough_cut.py         Faz 3 kural tabanlı kurgu (v3.6'dan beri yedek + Luna'nın bıraktığını doldurma; `prepare` ortak
                               hazırlık, `plan_rough_cut(picks=, user=)`): TTS duraklamalarında kesme (2–5 sn sahneler) → sahne penceresi
                               (v4.0: fotoğraflar da aday, yakınlaşmalı kadraj);
                               aynı çekim kaynak sırasıyla, tek uzun çekimde anlatım sırası, dikeyde sabit kadraj
  modules/scene_swap.py        Kurguda sahne değiştirme (v4.0, API yok): sahne başına küçük kare, kurallı 4 seçenek,
                               editörün seçimi kurgu_plani.json `editor` (Luna planının üstüne; girdiler değişince düşer)
  modules/framing.py           Akıllı kadraj: bulanık/siyah kenar tespiti (önce DHA'nın sınır çizgisi çifti; analiz karelerinden,
                               numpy/Pillow, API yok); sabit kamerada hareket bölgesi (v4.0, `motion_regions`, proxy tek geçiş)
  modules/soundbites.py        Kaynak sesli kesitler (önce/sonra, kesitler.json) ve 360p önizleme (onizleme/)
  modules/transcribe.py        Yerel yazıya dökme (v4.0; faster-whisper, API yok): kesit cümleden seçilir; model data/modeller
  modules/speech.py            Seste konuşma var mı (kepstrum, API yok): müzik altlığı konuşmalı kesitte kısılır (v4.0)
  modules/moment.py            Kesitin varsayılan aralığı = olay anı (ani hareket/ses + Luna "action"; API yok)
  modules/quotes.py            Haberdeki tırnaklı alıntı ↔ yazıya döküm (v4.1; kelime kökleri, sıralı eşleşme, API yok):
                               "📍 Haberdeki alıntı" önerisi; güven düşükse öneri yok, kesit kendiliğinden eklenmez
  modules/render.py            EditProject → tek FFmpeg komutu → kaba_kurgu.mp4 (h264_amf varsa, yoksa x264); fotoğraf:
                               EXIF yönü + yavaş yakınlaşma (zoompan, v4.0); ilk kare kapak sahnesi (v4.0); ses: parça
                               başına ölçülmüş sabit kazanç (TTS -18, kesit -20 LUFS), kenar yumuşatma, -2 dBFS sınırlayıcı
  range_player.py              Kesit oynatıcısı (v4.0, components v2): yalnız seçili aralık oynar, dışarı sarılmaz
  jobs.py                      Videoyu arka planda üretme: sahne seçimi (Luna, PlanRequest) → kaba kurgu → son video (aynı haberin tasarım üretimi önce
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
  music.py                     Müzik altlığı (v4.0): assets/muzik hazır parçalar + editörün müziği (yalnız yerel),
                               son videoda döngü; konuşmada -45, arada -27 LUFS (`speech_spans`, `mix_filters`)
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
                               5 sn sonra yeniden başlatır; kod 0 = Axion'u kapat, -1 = Stop-Process/güncelleme, 3 = uygulamadan
                               güncellendi → pip + açılış kontrolü + yeniden başlat; kontrol geçmezse ya da 3 dk içinde çökerse
                               `git reset --keep` ile önceki sürüm; AXION_BEKCI=1 koyar), guncelle.bat,
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
                               + yazi/*.json (yerel yazıya döküm, v4.0; cümleye dokunarak kesit)
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
| `news_package.json`, `tts.mp3`, `media_library.json`, `kesitler.json`, `kurgu_plani.json`, `edit_project.json`, `kaba_kurgu.mp4`, `onizleme/`, `yazi/`, `tasarim.json`, `son_video.mp4` | `data/projects/<zaman>_<başlık>/` | 3 iş günü sonra (`store.delete_old_projects`); `edit_project`/MP4 ayrıca haber veya görüntü değişince |
| Üretim geçmişi | `data/history.sqlite3` | 3 iş günü sonra satır satır |
| Ayarlar, seslendirme hız kalibrasyonu, okunuş sözlüğü (v4.1), günlük | `data/ayarlar.json`, `data/*.json` (`okunus.json`), `data/axion.log` | Silinmez |
| Yazıya dökme modeli (v4.0, ~1,6 GB) | `data/modeller/` | Silinmez (ilk kullanımda bir kez iner) |
| Düzeltme kaydı (v4.0) | `data/duzeltmeler.jsonl` | Silinmez (internete gitmez; editör indirip yollar) |
| Maliyet defteri (v4.0) | `data/maliyet.jsonl` | Silinmez (çağrı başına ~100 bayt) |
| Uygulamadan eklenen yazı tipi ve arka planlar | `data/varliklar/` (+ `GITHUB_TOKEN` varsa repoda `assets/sablon/`) | Silinmez |
| Tarayıcı profili (DHA oturumu, çerezler) | `data/tarayici/` | Silinmez (silinirse DHA'ya yeniden giriş) |
| Kayıtlı girişler (şifre DPAPI ile şifreli) | `data/tarayici_girisler.json` | Kenar çubuğundan "Sil" ile |
| Tarayıcıyla indirilen videolar | İndirilenler (yarımken `.iniyor` uzantılı) | Axion silmez |


## Nerede kaldık (2026-09-26) — v4.2.0 FINAL (Streamlit). New work happens in the `axion-studio` repository.

**YENİ OTURUM BURADAN BAŞLAR.** This repository is frozen at **v4.2.0**: only bug fixes and small patches (the editor
still uses it daily until Axion Studio is ready). Do not add features here.

**Editor decisions (2026-09-26, final):**
- **Axion Studio (v5)** is a **separate, clean project** in a new **private** repository `djanbaba30-hash/axion-studio`:
  FastAPI backend + React/Tailwind web UI (built files committed; no Node on the editor's PC). Built from scratch;
  useful code from this repo is **copied and cleaned**, never imported or shared. Own data folder, own address and
  desktop icon; the only shared thing is the Downloads inbox (read-only). At switch-over the editor's settings
  (pronunciation dictionary, voice settings, calibration) are copied once.
- **Tablet first** (Samsung Galaxy Tab S9+; phone Galaxy S21 FE; home PC last). Axion navy, light, modern; sliding
  panels, collapsible sections, bottom sheets, live progress, toasts. Approved prototype:
  https://claude.ai/artifact/XvUBo5oBDthGd4GixB7A9E
- **English** in the new repository (code, docs, terms); the UI stays Turkish; chat with the editor in Turkish.
- Private repo: the editor's PC signs in to GitHub once (Git Credential Manager) so clone/pull/update work.
- Plan: ROADMAP "v5.0 planı" (prototype ✓ → infrastructure → News → Video → Browser → Design → switch-over).

**Last Streamlit features (waiting for the editor's real-news test, `DENENECEKLER.md`):** pronunciation dictionary +
ElevenLabs status, quote-based soundbite suggestion, editor instruction box, image-analysis sub-step timings.

### Çalışma biçimi (editör kararları, 2026-09-26)
- Büyük özellikler parça parça ön sürüm: CHANGELOG başlığı `# vX.Y.Z-alpha.N — <özellik> — <tarih>` (ilk başlık =
  kenar çubuğundaki sürüm; `update_check.version` ön sürümü de okur). Editör tabletten "Güncelle" ile alır, dener.
- Editörün kullanım limiti sınırlı: oturum başına bir parça, küçük testli commit'ler; bitince bu bölüme yaz.
- Sorun bildiriminde önce **teşhis dosyasını** iste (Video Stüdyosu → Geliştirici bilgileri → "📦 Teşhis dosyasını
  indir": projenin JSON'ları + yazıya dökümler + günlüğün sonu). Hiçbir şey internete gönderilmez (repo herkese açık).
- **Düzeltme kaydı** (`data/duzeltmeler.jsonl`, Geliştirici bilgileri → "📝 Düzeltme kaydını indir"): editör yollayınca
  değişen alanlara bak (tekrar tekrar düzeltilen başlık kuralı, seslendirme, Luna'nın değiştirilen sahneleri, kesit
  aralıkları), istemi/kuralları düzelt, gerçek örnekle regresyon testi ekle (kural 5). **Kayıt token harcamaz ve istem
  büyümez:** yeni kural eski/uzun bir kuralı sadeleştirerek eklenir, öncesi/sonrası token sayılır.
- İncelemeler `reviews/` (biçim `reviews/README.md`): GPT editörün bilgisayarında yerel çalışır (Windows + repo +
  gerçek proje verisi, yalnız okur), raporu `reviews/gpt-*.md`; Claude her bulguyu ölçerek yanıtlar
  (`reviews/claude-*.md`), editör onaylar. Son: `gpt-v4.md` / `claude-v4.md`.

### Editörün bilgisayarı
- Windows, AMD işlemci + ekran kartı (`h264_amf`; son video ~5–8 sn), 32 GB RAM, 1000 Mbps. FFmpeg winget
  `Gyan.FFmpeg` = **en yeni sürüm**: FFmpeg'e dokunan değişikliği sandbox'ta yeni sürümle de dene (GitHub BtbN
  `ffmpeg-master-latest-linux64-gpl`, PATH'in başına; v4.0'da fotoğraf yönü hatası yalnız yenide çıktı).
- Test: `windows\testler.bat` (`make` yok). Windows'ta metin dosyası yazan testte `encoding="utf-8"`; satır sonu CRLF.
- Axion masaüstü simgesiyle açılır (Windows açılışında değil); bekçi çökmede yeniden başlatır, bozuk güncellemede önceki
  sürüme döner (etkin). `guncelle.bat` Axion'u açmaz. Uyku kapalı, ekran 30 dk (`powercfg`; değiştirmeden önce mevcut
  AC değerlerini doğrula). Tailscale: bilgisayar + tablet + telefon.
- Yazıya dökme modeli `data/modeller` (faster-whisper large-v3-turbo; 71 sn ses ~12 sn'de).

### Gerçek maliyet (editörün haberleri)
Haber başına ~$0,002–0,013 (seslendirme hariç): haber metni 1–4 çağrı (~$0,001–0,004, istem önbellekte), görüntü
analizi (~$0,002, uzun haberde 40 kare), Luna sahne seçimi (~$0,001). 4.0'da yeni model çağrısı yok.

### Şu an çalışan akış
1. **Haber Stüdyosu:** ham haber (ya da DHA "TXT indir") → GPT/Claude (tek çağrı + gerekirse tek düzeltme; yalnız
   başlık hatalıysa küçük başlık çağrısı) → başlıklar, paylaşım metni, seslendirme metni → deterministik doğrulama
   (tekrar, plaka, uzunluk, saat/sayı okunuşu, isim kuralı, kaynakta yok) → ElevenLabs `convert_with_timestamps` →
   proje klasörüne kayıt.
2. **Video Stüdyosu** (adım adım, biten adım daralır):
   - Görüntüler: proxy → sahne tespiti → ≤10 sn pencereler → kareler (Luna'ya 512 px, aynı görünenler elenir) → **tek
     Luna çağrısı** (enum'lu şema; haberin başlık + seslendirmesi bağlam) + yerel kenar tespiti ve sabit kamerada
     hareket bölgesi (`framing.py`, API yok). Fotoğraflar da (EXIF yönü).
   - Kaynak sesli kesitler: 360p önizleme, olay anı varsayılan aralık, yalnız aralığı oynatan oynatıcı; yazıya dökümden
     cümleye dokunarak seçim ("önceki/sonraki cümleyi de ekle").
   - Kurgu: **Luna sahne seçimi** (görüntüsüz tek çağrı; olay örgüsü → sahne aşaması → pencere; plan
     `kurgu_plani.json`, girdiler aynıysa yeniden çağrı yok) + kurallar (kesmeler seslendirme duraklamalarında, aynı an
     iki kez yok, aynı çekim kaynak sırasıyla, kadraj hep tam dolu). Editör sahneyi elle değiştirebilir (API yok).
   - Render (arka planda, tablet kapansa da sürer): 960x1226, `h264_amf` ya da x264; ilk kare kapak; ardından son video.
3. **Tasarım Stüdyosu** (sade Canva): standart şablonlu son video hazır gelir; editör başlık, yazı, efekt, çerçeve, arka
   plan, müzik, blur/mozaik değiştirir. Canlı önizleme son videonun aynısı (`editor.js`).
4. **Tarayıcı:** tabletten evdeki görünmez Brave ile DHA; indirmeleri Axion yapar, kayıtlı girişler.
5. **Veri:** haberler 3 iş günü; liste 02:00'de sıfırlanır; taze açılışta haber seçili gelmez.

### Editör kararları (değiştirme; ayrıntı ROADMAP → Ürün kararları)
Doğrudan `main`; token tasarrufu; arayüz Türkçe ve sade; uygulamada logo yok; hiçbir sahnede bulanık dolgu yok;
dikey çekimde kaydırma yok; seslendirmede saat/sayı okunuşuyla; başlık videoda 2 satıra sığar (`shared/text_layout`,
istem "EN FAZLA 44 KARAKTER"); isim kuralı "A.K."; şablon zamanları sabit (9/13/16. sn), video en az 20 sn; haberler 3
gün; blur tamamen elle. İstenmeyenler ROADMAP "3.x özeti"nde (yeniden önerme).

### 4.0 teknik notlar (kod ipuçları; ayrıntı CHANGELOG)
- **Fotoğraf:** `Candidate(photo=True)`, sanal aralık `PHOTO_SECONDS`; kadraj `_photo_zoom` (view_region ↔
  view_region_end farklı boyut = yakınlaşma); render `_photo_input` (zoompan 4x büyütülmüş karede; `-noautorotate` +
  `EXIF_TURN` + **Display Matrix etiketi silinir**, yoksa yeni FFmpeg videoyu yan gösterir).
- **Sahne değiştirme:** `modules/scene_swap.py`; `Clip.scene`; seçim `kurgu_plani.json` `editor` (Luna planı yoksa
  `temel`), `luna_edit.plan` üstüne koyar (`plan_rough_cut(user=, pick_origin=)`); girdiler değişince düşer.
  Sayfada tam genişlikte düğmeyle açılır (anahtar tablette açılmıyordu).
- **Kapak:** `template.Scene.items` 0. kare = 1. başlık giriş sonu hâli (`editor.js` `visibleItems` aynısı); önde kesit
  varsa ilk kare `scene == 0` klibinden (`render.build_render_command`).
- **Müzik:** `design_studio/music.py` (`speech_spans` + `duck_expression`: seslendirme ve konuşmalı kesit -45 LUFS,
  arada -27), konuşma tespiti `video_studio/modules/speech.py` (kepstrum); parçalar `assets/muzik` (`uret.py`, telifsiz
  sentez; repo herkese açık, lisanslı müzik konmaz), editörün müziği yalnız yerel.
- **Kayıtlar:** `corrections.py` (haber/sahne/kesit), `ledger.py` (yeni ücretli çağrı eklerken `ledger.add` de çağır),
  `status.py` (ElevenLabs arka planda, 10 dk önbellek).
- **Yazıya dökme:** `transcribe.py`: VAD, kelime zamanları; cümle = noktalama / 1,2 sn sessizlik / **büyük harfle
  başlayan kelime** (Whisper noktasız ama büyük harfli yazıyor; haberdeki özel adlar hariç); tek kelime ya da 1 sn'den
  kısa öncekine katılır; 8 sn'den uzun fiil sonunda (`VERB_END`) bölünür; parça sonu sesle uzar (`levels`,
  `_voiced`); özel ad yazımı `fix_names` (okunuş karşılaştırması; hotwords kullanılmıyor); uydurma altyazı kalıpları
  atılır; döküm `VERSION` (biçim değişince artır), ham `bolumler` saklanır. İş kilitli (`_JOBS_LOCK`). Sayfa
  `transcript_picker`; kaydırıcı cümle seçilince yeni anahtarla (`kesit_slider`; Session State'e yazmak uyarı verir).
  Regresyon: `test_artvin_interview_splits_where_the_editor_did`.
- **Kesit oynatıcısı:** `range_player.py` (components v2): yalnız aralık, her oynatma baştan, aralık değişince durur.
- **Hareket kadrajı:** `framing.motion_regions` (proxy tek geçiş) → `AnalysisWindow.motion_region`; alana sığıyorsa
  kadraj onun ortasına (`rough_cut._view_regions`). Yalnız yeni analizlerde.

### Bilinen borçlar
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
- Arka plan işleri (tasarım ve video üretimi, yazıya dökme) Streamlit sürecinin iş parçacıklarıdır: Axion kapanırsa
  yarıda kalır (yarım dosya `.yaziliyor.mp4` adıyla yazılır, yerine konmaz).
- Tarayıcı bileşenleri (components v2: kesit oynatıcısı, okuyarak dinleme, Tarayıcı görünümü) pytest'te çalışmaz;
  Playwright/Chromium ile elle denenir (Chromium H.264 oynatmaz: test için VP9-in-MP4 önizleme).
- Luna planının imzası sistem istemini içerir: istem değişince eski haberin planı bir kez yeniden çağrılır (bilinçli;
  `reviews/claude-v4.md` V4-G1). `transcribe.levels` tüm sesi belleğe alır (DHA videoları kısa; saatlik videoda ~330 MB).
- `.streamlit/config.toml` `fileWatcherType = "none"`: kod değişince Axion yeniden başlatılmalı (guncelle.bat yapar).

## Komutlar

```bash
pip install -r requirements-dev.txt   # geliştirme bağımlılıkları (pytest dahil)
make test                             # tüm testler
make run                              # uygulamayı başlat (axion_app.py): http://localhost:8501
```

Test ortamında FFmpeg yoksa `tests/test_media_pipeline.py` atlanır.
