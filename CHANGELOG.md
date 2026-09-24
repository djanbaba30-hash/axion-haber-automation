# v2.4.0 — Faz 3 kod incelemesi düzeltmeleri — 2026-09-24

GPT ve Claude incelemesinin sonucu (`reviews/`). Kullanıcıya görünen davranış aynı; daha hızlı, daha ucuz, daha sağlam.

## Changed
- Luna görsel analizi düşük düşünme seviyesiyle (`low`) çalışır; 180 sn zaman aşımı.
- Analiz kopyası (proxy) 640 px, sessiz ve en hızlı ayarla üretilir: görüntü analizi daha kısa sürer.
- Video başına Luna'ya en fazla 40 kare gider (yüksek analiz yoğunluğunda maliyet tavanı).
- Render tek kadraj yoluna indirildi; bulanık dolgu kodu tamamen kaldırıldı.

## Fixed
- Otomatik silmede silinemeyen klasör artık sessizce "silindi" sayılmıyor; `data/axion.log`'a yazılır, ertesi gün
  yeniden denenir. Temizlik hatası uygulamanın açılmasını engellemez.
- Tarayıcıdan yüklenen dosya yalnızca ad+boyutla eşleştiriliyordu; artık SHA-256 ile.
- Kesit olarak seçilen aralık, aynı sahnenin komşu kısmından uzayan dolgu görüntüsüyle tekrar görünebiliyordu.
- Kesit videonun süresini aşıyorsa açık hata; sonu taşıyorsa kırpılır.
- FFmpeg sahne tespiti hata verirse video sessizce tek sahne sayılıyordu; artık hata gösterilir.
- Yarıda kalan analiz geçici klasörde proxy/kare bırakıyordu.

## Removed
- Kullanılmayan kod: `validate_edit_project`, `add_timeline_item`, `add_news_segment`, `build_news_package`,
  `save_news_package`, kadraj modu parametreleri.

## Verification
- `make test`: 178 test geçti (gerçek FFmpeg ile). Gerçek Luna çağrısı ve Windows E2E editörde.

# v2.3.0 — Dikey çekimlerde güvenli kaydırma — 2026-09-24

## Fixed
- Dumanlı, gece veya yumuşak görüntülü dikey çekimlerde (Kars yangını) bulanık kenar tespit edilemiyor, kadraj yatay
  kayarken DHA'nın bulanık kenarına giriyordu. Luna artık her sahne için "dikey çekim, yanları dolgulu" bilgisini de
  veriyor; tespit kaçırırsa görüntü ortadaki 9:16 alana kilitlenir.

## Changed
- Kaydırma kuralı: yanları dolgulu dikey çekimde yalnızca yukarı/aşağı; tam 16:9 görüntüde yatay, dikey veya çapraz.
- Kaydırma hızı saniyede kare genişliğinin %3'ü.
- Luna prompt v2.5: önceki analizler için yeniden analiz istenir.

## Verification
- `make test` geçti (Kars durumu ve kaydırma yönü regresyon testleri dahil). Windows testi bekleniyor.

# v2.2.1 — Haberler 3 gün saklanır — 2026-09-24

## Changed
- Haber projeleri en fazla 3 iş günü (bugün + önceki 2 gün) saklanır; daha eskileri her gün ilk açılışta otomatik
  silinir (ses, analiz, kesitler, kurgu, video ve önizlemeler dahil). Üretim geçmişindeki eski kayıtlar da silinir.
  İndirilenler'deki kaynak videolara dokunulmaz.

## Verification
- `make test` geçti (3 gün sınırı ve proje olmayan klasöre dokunulmaması testleri dahil).

# v2.2.0 — Her gün taze başlangıç, metin düzenleme düzeltmesi — 2026-09-24

## Fixed
- Haber Stüdyosu'nda metin kutusunu düzenleyip dışına tıklayınca değişikliğin kaybolup ilk hâline dönmesi
  (seslendirme metni, paylaşım metni, başlıklar, ham haber). Metinler sayfa değiştirince de korunur.

## Changed
- Video ve Tasarım stüdyosu açılışta haber seçili gelmez; Haber Stüdyosu'ndan geçince kaydedilen haber seçilidir.
- Haber listesi her gün 02:00'de (bilgisayar saati) sıfırlanır; "Önceki günler" ile eski haberler seçilebilir.
- Geniş özne kaydırması daha yavaş (saniyede kare genişliğinin %2,5'i).

## Verification
- `make test` geçti (taze açılış, 02:00 sınırı, düzenlenen metnin korunması testleri dahil). Windows testi bekleniyor.

# v2.1.0 — Bulanık dolgu yok, okunabilir saatler — 2026-09-24

## Changed
- Video alanı her sahnede tam dolu; hiçbir yanda bulanık dolgu yok. Kadraj haberin ana öznesine kayar; özne çok
  genişse (ör. yandan otobüs) kadraj sahne boyunca onun üzerinde yavaşça kayar. "Akıllı / Tüm kare" seçimi kaldırıldı.
- Seslendirme metninde saat, tarih, binlik ve ondalık sayılar okunuşuna çevrilir: "saat 18.00'de" → "akşam 6'da",
  "09.30'da" → "sabah 9 buçukta", "24.09.2026'da" → "24 Eylül'de", "1.500" → "1500", "2,5" → "2 buçuk".
  Haber üretiminde ve "Seslendir"de uygulanır; çevrilemeyen sayı için uyarı çıkar. Yönergeye kural eklendi.

## Verification
- `make test` geçti: tam dolu kadraj ve kaydırma (gerçek FFmpeg render), saat/tarih dönüşümü regresyon testleri
  (Kayseri haberi). Windows testi bekleniyor.

# v2.0.0 — Kaynak sesli kesitler, adım adım Video Stüdyosu, Tasarım Stüdyosu — 2026-09-24

## Added
- **Kaynak sesli kesitler:** videodan bir bölüm kendi sesiyle seslendirmenin önüne (dikkat çekici an) veya arkasına
  (röportaj) eklenir. Önizleme oynatıcısı + aralık kaydırıcısı; birden fazla kesit; analizden önce de seçilebilir.
  Kesit sesi ile seslendirme aynı ses yüksekliğine getirilir; kesit görüntüsü dolgu olarak tekrar kullanılmaz.
- **Tasarım Stüdyosu** sayfası: video ve kopyalamaya hazır başlıklar/paylaşım metni. Faz 5'te Canva'nın yerini alacak.
- Video Stüdyosu'ndan "Tasarım Stüdyosu'na geç".

## Changed
- Video Stüdyosu adım adım: 1. Haber → 2. Görüntüler → 3. Kaynak sesli kesitler → 4. Video. Biten adım tek satırlık
  özete daralır; ayarlar "⚙️ Ayarlar" düğmesinde.
- Arayüz terimleri Türkçe: "Video Studio" → "Video Stüdyosu", TTS → seslendirme metni, caption → paylaşım metni,
  shot → sahne, Speaker Boost → ses netliği artırma, Input/Output → girdi/çıktı token. Doğrulama uyarıları da Türkçe.
- Video en az 20 sn kuralı artık seslendirme + kesitlerin toplamına uygulanır.

## Verification
- `make test` geçti (163 test): kesit planı, kesit sesinin gerçekten duyulduğu render testi, kesit seçicinin uçtan uca
  arayüz testi, Tasarım Stüdyosu. Arayüz gerçek tarayıcıda ekran görüntüsüyle kontrol edildi. Windows testi bekleniyor.

# v1.9.4 — Özneyi kesmeyen kadraj, daha az token — 2026-09-24

## Changed
- Akıllı kadraj: Luna ana öznenin tamamını içeren kutuyu verir; kadraj özneyi asla kesmez ve olabildiğince az
  yakınlaştırır. Özne dikey alana sığmayacak kadar genişse (ör. yandan minibüs) üst/alt bulanık dolguyla tamamı gösterilir.
- Kadraj seçenekleri: "Akıllı" (önerilen) ve "Tüm kare" (önceki "Doldur"/"Bulanık kenar").
- Yanları bulanık dikey çekimlerde kadraj ortalanıyor ve güvenlik payı %2 (tek yanda ince bulanık şerit kalıyordu).
- Luna'ya gönderilen analiz kareleri 640 px genişlikte (önce 960): girdi token'ı azalır.
- Luna prompt v2.4: önceki analizler için yeniden analiz istenir.

## Verification
- `make test` geçti: geniş özne tam görünür, dar özne alanı tam doldurur (gerçek FFmpeg render testleri).
  Windows'ta yeni bir haberle doğrulanacak.

# v1.9.3 — Doğal kesmeler ve bulanık kenarın tamamen atılması — 2026-09-24

## Changed
- Sahne geçişleri seslendirmedeki duraklamalara konuyor (cümle sonu, virgül, nefes arası); her sahne 2–5 sn.
  Önceki sürüm sabit ≤3 sn parçalara bölüyordu, bazı geçişler 1 sn'nin altına düşüyordu.
- Sahne, o aralıkta söylenen kelimelere göre seçiliyor (cümlenin tamamına göre değil).
- Yanları bulanık dikey çekimlerde bulunan alan standart orana (9:16, 1:1, 4:3) daraltılıyor; gerçek DHA videosunda
  kenarda kalan bulanık şerit gideriliyor.

## Fixed
- "Saat 17.00" gibi saat/sayılardaki nokta cümle sonu sayılıyordu; ayrı ve çok kısa bir sahneye yol açıyordu.

## Verification
- `make test` geçti (Manavgat videosundaki gerçek tespit değerleriyle regresyon testi dahil). Windows testi bekleniyor.

# v1.9.2 — Video en az 20 saniye — 2026-09-24

## Changed
- Şablon videosu en az 20 sn: seslendirme daha kısaysa kurgu 20 sn'ye tamamlanır, son sahne sessiz devam eder.
  EditProject doğrulaması "timeline ≤ TTS" yerine "timeline ≤ max(TTS, 20 sn)".
- Şablon zamanları (9/13/16. sn) sabit olarak kaydedildi (editör onayı).

## Verification
- `make test` geçti (15 sn TTS → 20 sn kurgu ve 4 sn TTS → 20 sn MP4 render testleri dahil).

# v1.9.1 — Kurgu ölçüsü Canva şablonuna göre — 2026-09-24

## Changed
- Kaba kurgu 1080×1440 yerine Canva şablonundaki video alanının ölçüsünde üretiliyor: 960×1226 (alan 960×1225;
  H.264 çift sayı istediği için 1 px fazla). Canva'da ikinci kez kırpma gerekmez.
- Eski ölçüdeki kurgu projeleri açılışta yeniden kuruluyor.

## Added
- `shared/axion_template.py` ve ROADMAP'te Axion Canva şablonunun tam tanımı (Faz 5 için): başlık, slogan ve logo kutusu
  konum/zaman/animasyonları, yazı tipi, arka plan rotasyonu.

## Verification
- `make test` geçti.

# v1.9.0 — Akıllı kadraj — 2026-09-24

## Added
- Bulanık/siyah kenar tespiti: DHA'nın yatay formata bulanık kenarlarla koyduğu dikey çekimlerde asıl görüntü alanı
  analiz karelerinden bulunur (API yok). Kurgu bu alandan kadrajlanır; bulanık kenar videoya girmez.
- Odak noktası: Luna her pencere için ana öznenin konumunu verir (birkaç token). "Doldur" kadrajı bu noktaya ortalanır.
- "Bulanık kenar" modunda arka plan, DHA'nın bulanık kenarından değil asıl görüntüden üretilir.
- Geliştirici kurgu tablosunda odak ve kenar kırpma bilgisi.

## Changed
- Luna prompt sürümü v2.3: önceki analizler için "yeniden analiz et" bilgisi çıkar (yaklaşık yarım sent).

## Verification
- `make test` geçti; sentetik DHA tipi (bulanık kenar + logo), siyah bantlı, tam kare ve tek yanı düz videolarla
  tespit testleri ve iki kadraj modunda gerçek FFmpeg render testleri dahil. Gerçek DHA videolarıyla Windows testi bekleniyor.

# v1.8.0 — Faz 3: ilk otomatik kaba kurgu — 2026-09-24

## Added
- Video Studio "3. Video": TTS cümlelerine sahneleri kurallarla eşleştiren kaba kurgu (API çağrısı yok, ek maliyet yok).
  Kesitler en fazla 3 sn; röportaj görüntüsü sessiz dolgu olarak kullanılmaz, aynı sahne art arda gelmez.
- "Videoyu oluştur": FFmpeg ile 1080×1440 MP4 (`kaba_kurgu.mp4`, proje klasöründe), sayfada önizleme ve indirme.
  AMD donanım kodlayıcı (h264_amf) varsa kullanılır, yoksa x264.
- Kadraj seçimi: Doldur (kırp) / Bulanık kenar; son seçim hatırlanır.
- Geliştirici bilgilerinde kurgu tablosu (hangi cümleye hangi sahne kesiti).

## Changed
- `ClipOrigin` sözleşmesine `rule` eklendi.
- FFmpeg çıktısı UTF-8 okunuyor (Windows'ta Türkçe dosya adlarında çözme hatası riskine karşı).

## Verification
- `make test` geçti (Linux, gerçek FFmpeg ile iki kadraj modunda 1080×1440 render testi dahil).
- AMD kodlayıcı ve gerçek DHA videosuyla render editörün Windows testinde doğrulanacak.

# v1.7.1 — Luna sınıflandırma düzeltmesi ve uzun shot pencereleri — 2026-09-24

## Fixed
- Luna sonuçlarında `visual_type`/`editorial_role` `unknown`, `description` boş kalıyordu: açıklama yanlış alana
  yazılıyordu ve serbest metin kategoriler enum'a eşlenemiyordu. Luna şeması artık enum'lu; tüm alanlar aktarılıyor.
- Eski formatta kayıtlı `media_library.json` Video Studio'yu çökertiyordu; artık "yeniden analiz et" bilgisi gösteriliyor.
- Tarayıcıdan yüklenen görsel analizden sonra silinip ardından okunmaya çalışılıyordu (çökme); proje `media/` klasöründe kalıyor.
- Yüklenen dosya adları `hash()` ile (her açılışta farklı) üretiliyordu; aynı dosya yeniden yüklenince kopya birikmesi önlendi.
- v1.7.0 ile kırılan 3 test düzeltildi.

## Added
- Uzun shot'lar en fazla 10 sn'lik analiz pencerelerine bölünüyor (tek Luna çağrısı korunuyor); her pencerenin kendi görsel analizi var.

## Verification
- `make test` geçti (Linux). Gerçek Luna çağrısı ve Windows doğrulaması editör tarafından yapılacak.

# v1.7.0 — Faz 2 sözleşme geçişi — 2026-09-24

## Changed
- Video Studio medya çıktısı shared.media_models 2.1 sözleşmesine taşındı.
- Medya kaynaklarına gerçek SHA-256 kimliği eklendi.
- Luna görsel sınıfları ortak VisualType / EditorialRole enum değerlerine normalize ediliyor; ek API çağrısı eklenmedi.
- EditProject üretimi shared.edit_models 2.1'e taşındı.
- Eski 1.1 EditProject dosyaları açılışta kullanılmıyor; yeniden oluşturuluyor.
- Browser upload medya kaynakları aktif proje altında media/ klasöründe saklanıyor.
- TTS audio metadata'sında gerçek SHA-256 tutuluyor.
- Faz 2 için ortak sözleşme regresyon testi eklendi.
- Gerçek Windows testinde medya analizi ve EditProject üretimi doğrulandı: 157.28 sn video, 15 shot, 21.27 sn TTS timeline.
- EditProject TTSAlignment süre erişim hatası düzeltildi; syntax/import hataları giderildi.

## Verification
- Kod GitHub main üzerinde doğrudan güncellendi.
- Bu oturumda gerçek Windows/FFmpeg ortamında make test çalıştırılmadı; Windows uçtan uca doğrulama açık test adımıdır.

# v1.6.1 — 2026-09-24

## Changed
- Removed the logo from the sidebar and the password screen; the sidebar starts with the page links. The Axion X mark stays only as the browser tab icon and the desktop icon.
- The desktop icon file is renamed to `windows/axion_x.ico` so Windows' icon cache picks up the new X mark. `guncelle.bat` now recreates the desktop shortcut on every update.

# v1.6.0 — Axion branding, remembered settings, leaner Video Studio — 2026-09-24

## Changed
- White theme in the Axion logo colours (navy `#123249` primary, light blue and green accents). The logo is in the sidebar above custom page links; the X mark is the browser tab icon and the new `windows/axion.ico`.
- Haber Stüdyosu sidebar:
  - style, duration, AI provider, model, reasoning level and voice are always visible;
  - voice fine-tuning sits in a collapsed "Ses ince ayarları" section;
  - all of these settings are remembered across sessions in `data/ayarlar.json` (`apps/axion_local/preferences.py`).
- Video Studio:
  - the shot table moved to developer info;
  - the news text box was removed; the text comes from the project;
  - browser upload became a toggle under "Gelişmiş";
  - status is a single line.

# v1.5.0 — Timed TTS (Faz 1) and a simpler interface — 2026-09-24

## Added
- Faz 1: ElevenLabs `convert_with_timestamps` returns the audio and per-character timings in one call, at no extra cost. The timings are stored as `TTSAlignment` in `news_package.json`. An alignment that does not match the text exactly is dropped; the audio is still used. TTS text is trimmed before synthesis.

## Changed
- Haber Stüdyosu:
  - the sidebar shows only style, duration and voice; AI engine, reasoning level and voice sliders moved under "Gelişmiş ayarlar";
  - headlines sit side by side; validation notes are grouped in one "Kontrol et" box;
  - token usage moved to a collapsed "Geliştirici bilgileri" section;
  - "Sistemi Sıfırla" became "Yeni haber" and keeps the voice and engine choices.
- Video Studio:
  - the steps are "1. Haber" and "2. Görüntüler"; the news text sits in a collapsed section;
  - folder and analysis density moved under "Gelişmiş";
  - the EditProject is built and saved automatically when news, audio and media are ready (no button);
  - cost and the project folder moved to developer info.
- Axion red is the primary colour in both light and dark themes (the system theme is followed). Page top padding is tighter. "Axion'u kapat" sits at the bottom of the sidebar.

# v1.4.0 — Fully local, single linked app — 2026-09-24

## Changed
- Streamlit Cloud support removed. Axion runs only on the editor's PC:
  - no `AXION_LOCAL` mode switch;
  - no per-page passwords (the optional password lives only in `axion_local.py`);
  - no NewsPackage JSON download or upload, no TTS upload;
  - `packages.txt` and `REPO_MANIFEST.txt` deleted.
- Pages renamed to `apps/news_studio/page.py` and `apps/video_studio/page.py`; `axion_local.py` is the only entry point. Streamlit settings moved to `.streamlit/config.toml`.
- News → Video linking:
  - "Kaydet ve Video Studio'ya geç" saves the project and opens it in Video Studio;
  - re-saving the same raw news updates the same project instead of creating a new one;
  - the sidebar shows the active project.
- Video Studio page rewritten (1140 → about 230 lines) in the order 1. news project → 2. media → 3. project:
  - the media pipeline moved to `modules/media_pipeline.py`;
  - a time-coded shot table (usable for manual CapCut cuts) is shown;
  - media analysis and the EditProject are saved to the project folder and restored when the project is reopened, so Luna does not run again.
- Proxy videos and analysis frames are deleted after analysis; previously they piled up in the temp folder.
- News Studio data files use the fixed `data/` folder (`AXION_DATA_DIR`) regardless of the working directory.
- Axion no longer starts with Windows; it runs only when the desktop icon is clicked. `kisayol.ps1` removes the old Startup shortcut.

## Added
- `AGENTS.md`: shared guide for AI developers (rules, code map, where we left off, known debts). `CLAUDE.md` imports it. README rewritten; KURULUM.md covers phone access and full remote desktop.

# v1.3.1 — Axion Local polish — 2026-09-24

## Changed
- Password is optional in local mode: an empty `APP_PASSWORD` opens Axion directly. The apps no longer require `APP_PASSWORD` in local mode. Streamlit Cloud still requires it.
- Windows launcher `windows/axion_baslat.vbs` replaces the console `.bat`:
  - no console window; the log goes to `data/axion.log`;
  - if Axion is already running, it only opens the browser;
  - it waits up to 60 s and opens the log if startup fails.
- `kurulum.bat` creates a desktop shortcut with the Axion icon and a Startup shortcut that launches Axion in the background at login (`windows/kisayol.ps1`). The Streamlit "Deploy" toolbar is hidden.
- "Axion'u kapat" button in the sidebar, shown only when Axion is opened on the home PC itself (Host header is localhost), so it cannot be closed from the tablet by mistake.
- `windows/anahtarlar.bat` opens the API key file. `windows/sorun_giderme.bat` runs Axion in a visible console for troubleshooting. `guncelle.bat` stops, updates and restarts Axion.

## Fixed
- Video Studio's news text box no longer empties when switching between pages.

# v1.3.0 — Axion Local (Faz 0) — 2026-09-24

## Added
- `axion_local.py`: Haber Stüdyosu and Video Studio run as one Streamlit app with one password (`st.navigation`). The modules stay separate.
- `apps/axion_local/store.py`: persistent project folder (`data/projects/<time>_<headline>/news_package.json + tts.mp3`) and media inbox listing (default `~/Downloads`, overridable with `AXION_DATA_DIR` / `AXION_INBOX_DIR`).
- News Studio (local mode only): "Projeye kaydet" stores the package together with the audio and its sha256. Saving is blocked when the TTS text changed after the audio was generated.
- Video Studio (local mode only):
  - media can be picked from a local folder and is read in place, without upload or copy (`LocalMediaFile`);
  - saved news projects load caption and TTS audio directly; the audio hash is verified.
- Windows `windows/kurulum.bat`, `axion_baslat.bat`, `guncelle.bat` and the Turkish guide `KURULUM.md` (Tailscale access from the tablet).

## Unchanged
- News generation, prompts and validation. The Streamlit Cloud behaviour of both apps is unchanged outside local mode.

# v1.2.0 — Viral TTS quality — 2026-09-24

## Changed
- News prompt tuned for Turkish social media:
  - first TTS sentence carries the most striking event;
  - every sentence must add new information (restating an event or a number counts as repetition);
  - the duration target is an upper bound — add unused facts, otherwise finish short;
  - conversational tone without agency phrases, semicolons or street-level addresses;
  - no license plates or ID-type details;
  - witness guesses are attributed, not stated as fact;
  - the two headlines must not repeat each other or use verbs that are not in the source.
- Structured output gains `tts_plani` (one short line per TTS sentence, before `tts`), so the model plans distinct facts inside the same call. No extra API call.
- Validation:
  - TTS below the target is now a warning instead of an error, so it no longer triggers a correction call. Below 60% of the minimum is still an error; above the maximum still is too.
  - Heuristic repetition warning for TTS sentences (a shared number plus a shared word stem, or 3+ shared stems).
  - `NN ABC NNN plakalı` is removed automatically, with a warning.
  - TTS semicolons are split into sentences.

## Cost
- About +345 input tokens per request, mostly in the cached system prompt, and about +60 output tokens for the plan. Under-length TTS no longer costs a second request.

# v1.1.2 — Contract revision and fixes — 2026-09-24

## Fixed
- Video Studio: Luna image data URLs were sent as the literal text `{image_mime_type(...)}` (missing f-string), breaking visual analysis for every video. Frames and standalone images now both use the real MIME type from the file extension (`image_data_url`).
- Video Studio: every FFmpeg/FFprobe call goes through `modules/ffmpeg_runner.py`. Probe and frame extraction: 60 s. Proxy transcode (previously no timeout) and scene detection: 4× video duration, clamped to 300–3600 s. A timeout raises a readable `RuntimeError`, and temporary proxy/frame files are removed.
- Video Studio: wrong password now shows "Şifre yanlış."; password comparison uses `hmac.compare_digest`.
- News prompt: the caption source instruction was truncated ("ek." → "ekle.").
- News prompt: `build_correction_prompt` no longer uses a backslash inside an f-string expression (SyntaxError on Python < 3.12). Prompt output is unchanged.
- Retry: `anthropic.OverloadedError` (529) is now treated as transient. The OpenAI/Anthropic SDK internal retries are disabled (`max_retries=0`), so `retry_transient` is the only retry layer (previously up to 3×3 = 9 requests).

## Contract (shared/)
- NewsPackage: `parse_news_package` is the single entry point for every version. 1.0 files (flat, nested `news`, Turkish field names, `schema_version: null`) are migrated to 1.1. Unknown legacy fields are kept under `metadata.legacy_fields`.
- Video Studio's NewsPackage import now uses the shared contract instead of its own parser.
- NewsReference validates `tts_alignment` against `tts_text`.
- EditProject cross-validation:
  - segment text equals `tts_text[char_start:char_end]`;
  - segments are ordered, non-overlapping and cover the whole `tts_text` (whitespace excepted);
  - clip `asset_id` exists in `media` (audio clips: `audio.asset_id` or `media`) and clip `segment_id` exists;
  - timeline end does not exceed the TTS duration;
  - `media` has no duplicate asset ids.
- Timeline and track rules:
  - no overlapping clips within a track;
  - clip and track ids are unique;
  - transition in + out ≤ clip duration;
  - `cut`/`none` transitions have a duration of 0 and `fade` has a duration above 0;
  - segment `order` runs 1..n.
- Media:
  - Shot `start_seconds` ≥ 0;
  - AnalysisWindow must lie inside its Shot, and AnalysisFrame inside its window;
  - fractional rotation is rejected;
  - `exif_orientation` must be 1–8.
- `FramingMode.VERTICAL_CROP` merged into `FILL_CROP` (both are documented). The unused `EditPlan.snapshot_id` field was removed.

## Process
- Tests run with pytest: `make test` (80 tests; previously only 4 unittest tests ran). `pytest` moved to `requirements-dev.txt`.
- `.github/workflows/extract-repo.yml` removed. `.pytest_cache/` and `*.zip` added to `.gitignore`.

## Known / deferred
- Video Studio still builds its draft project with `apps/video_studio/modules/edit_plan.py` (format 1.1). The target contract is `shared/edit_models.py` (2.1); the switch happens when the Edit Planner is connected.
- ElevenLabs TTS calls are not retried, because a retry could consume character quota twice.

# Axion Repo Reset — 2026-09-24

## Included
- Clean monorepo layout for News Studio + Video Studio.
- News app split into AI, prompts, validation, TTS, integration, and models modules.
- Existing editorial prompt rules preserved as the baseline.
- Reset no longer removes authentication state.
- Generated TTS bytes persist in Streamlit session state across reruns.
- Real MP3 duration measured with Mutagen and calibration persisted locally.
- Selected ElevenLabs voice is remembered in session state.
- AI (OpenAI/Claude) transient retry and request timeouts added. ElevenLabs has a request timeout but no retry.
- Censorship terms are reported as validation warnings rather than silently rewritten.
- Simple SQLite production history log added.
- Shared `NewsPackage` contract added for News → Video handoff.
- Video Studio accepts NewsPackage JSON and continues to use GPT-5.6 Luna only for visual analysis.
- Basic unit tests included.

## Deliberately deferred
- AI Edit Planner: not implemented yet; objective media indexing remains separate from editorial selection.
- Final renderer/export pipeline: not implemented yet.
- Durable external database/object storage: not implemented; local SQLite/JSON is ephemeral on Streamlit Cloud.
