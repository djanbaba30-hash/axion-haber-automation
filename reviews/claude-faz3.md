# Claude Faz 3 Kod İncelemesi ve Düzeltmeler

- **Kapsam:** tüm repo (`axion_local.py`, `apps/`, `shared/`, `windows/`, `tests/`).
- **Girdiler:** GPT'nin raporu (`reviews/gpt-faz3.md`) ve editörün "Luna'da yüksek düşünme gerekli mi?" sorusu.
- **Sonuç:** düzeltmeler v2.4.0 olarak `main`'de.
- **Doğrulama:** `make test` bu ortamda gerçek FFmpeg ile çalıştı: 178 test geçti (önce 163). Gerçek Luna çağrısı ve Windows E2E testi editörde.

## GPT bulgularına kararlar

| # | GPT bulgusu | Karar | Ne yapıldı |
|---|---|---|---|
| 1 | Otomatik silmede hata görünmüyor (`rmtree(ignore_errors=True)`) | **Kabul** | Silinemeyen klasör `data/axion.log`'a yazılıyor. "Silindi" yalnızca klasör gerçekten yoksa sayılıyor. Ertesi gün yeniden deneniyor. Test eklendi. |
| 2 | Silme geri alınamaz (çöp klasörü, yedek) | **Kısmen** | Açılıştaki temizlik artık çökerse uygulamayı durdurmuyor ve her silme günlüğe yazılıyor. Çöp klasörü eklenmedi: editör "3 günden fazlasını istemiyorum" dedi, çöp klasörü bu kararı fiilen uzatırdı. Yalnızca `YYYYMMDD-HHMMSS_` adlı proje klasörlerine dokunuluyor, kaynak videolara hiç dokunulmuyor. |
| 3 | Render'da bulanık dolgu (FIT_BLUR) yolu duruyor | **Kabul** | Render tek kadraj yoluna indirildi (planlayıcının alanı ya da ortadan tam dolu). `boxblur`/`overlay` kodu yok. Eski kayıtta `fit_blur` olsa bile bulanık dolgu üretilmediği testle doğrulanıyor. |
| 4 | Yüksek yoğunlukta kare/token üst sınırı yok | **Kabul** | Video başına en fazla 40 kare. Aşılırsa pencere başına kare sayısı düşürülüyor; ekonomik modda her pencerenin 1 karesi kalıyor. Test eklendi. |
| 5 | Kareler base64 ile belleğe alınıyor | **Reddedildi** | 640 px JPEG'ler 30–60 KB; 40 kare en fazla ~2–3 MB. Ölçülebilir bir sorun değil. |
| 6 | Tarayıcı yüklemesinde yalnız boyutla eşleşme | **Kabul** | Boyut ön eleme, eşleşme SHA-256 ile doğrulanıyor. Aynı ad ve boyutta farklı içerik ayrı dosya olarak kaydediliyor. Test eklendi. |
| 7 | Kalıcı medya adı hash tabanlı olsun | **Reddedildi** | #6 doğruluk sorununu çözdü. Okunabilir dosya adı editörün klasörde dosyayı tanıması için daha değerli. |
| 8 | Kesit video süresini aşabilir | **Kabul** | Başlangıç video sonrasındaysa açık hata ("kesiti kaldırıp yeniden seç"). Video sonunu aşan kısım kırpılıyor. Test eklendi. |
| 9 | Windows'a özgü dosya adları | **Reddedildi** | Tarayıcıdan gelen ad zaten bir dosya sisteminden geliyor ve `Path(...).name` ile klasör dışına çıkması engelli. Gerçek bir hata senaryosu bulunamadı. |
| 10 | Proxy her analizde yeniden üretiliyor | **Başka yoldan çözüldü** | Önbellek yerine proxy ucuzlatıldı (bkz. C1). Yeniden analiz nadir. |
| 11 | Windows sınır durumları için test eksik | **Kısmen** | Eklenen testler: aynı ad ve boyutta farklı içerik, kilitli dosya silme, AMD → x264 geçişi, yarıda kalan kare çıkarma, kesit sınırları. FFmpeg zaman aşımı zaten `ffmpeg_runner`'da testli. Türkçe yol testi Windows E2E'ye bırakıldı. |
| 12 | Tarayıcıya özgü davranış için E2E yok | **Kısmen** | Aşağıya elle yapılacak kısa bir tarayıcı kontrol listesi eklendi. Playwright katmanı eklenmedi; test ortamındaki tarayıcı H.264 oynatamıyor, bakımı da maliyetli. |
| 13 | OpenAI/Claude istemci kodunda tekrar | **Reddedildi (şimdilik)** | Çalışıyor ve küçük. Faz 4'te Luna planlayıcı çağrısı eklenirken ortak yardımcı düşünülecek. |
| 14 | Dosya yaşam döngüsü dokümanı | **Kabul** | `AGENTS.md`'ye "Dosya yaşam döngüsü" bölümü eklendi. |
| 15 | Deterministik hata gereksiz düzeltme çağrısı tetikliyor | **Reddedildi** | Çağrıyı tetikleyen hataların hepsi metni yeniden yazmayı gerektiriyor: boş alan, 9 kelimeyi aşan başlık, 2200 karakteri aşan metin, hedefin %60'ının altında ya da belirgin üstünde seslendirme. Kodla kısaltmak haberi bozar. Küçük sapmalar zaten yalnızca uyarı. |
| 16 | Açılıştaki temizlik yavaşlatabilir | **Kabul (küçük)** | Günde bir kez çalışıyor (`cache_resource`), hatası açılışı engellemiyor. 3 gün saklamayla klasör sayısı küçük. |

## Claude'un kendi bulguları

| # | Önem | Tür | Yer | Sorun | Düzeltme |
|---|---|---|---|---|---|
| C1 | orta | performans | `video_ingestion.create_proxy` | Proxy 960 px, sesli ve "veryfast" üretiliyordu. Ses hiç kullanılmıyor, Luna kareleri zaten 640 px. | 640 px, sessiz (`-an`), `ultrafast`. Sahne tespiti ve kare çıkarma aynı. |
| C2 | orta | hata | `shot_detection.detect_scene_changes` | FFmpeg hata verirse video sessizce tek sahne sayılıyordu. | Hata kodu kontrol ediliyor; açık hata gösteriliyor. |
| C3 | orta | hata | `rough_cut._source_range` | Kesit olarak ayrılan aralık, aynı sahnenin komşu penceresinden uzayan dolgu klibiyle yine görüntüye girebiliyordu. İmleç tam aralık başına denk gelirse klip aralığın içinden de başlayabiliyordu. | Ayrılan aralığın içinden başlanmıyor, aralığa taşılmıyor. Üç konumla test edildi. |
| C4 | orta | maliyet | `visual_analysis` | Luna'nın düşünme seviyesi verilmemişti (model varsayılanı), zaman aşımı yoktu. | `reasoning.effort = "low"` (editörün önerisi; aynı parametreyi Haber Stüdyosu kullanıyor), 180 sn zaman aşımı. |
| C5 | düşük | hata | `media_pipeline`, `representative_sampling` | Analiz yarıda kalırsa proxy ve çıkarılmış kareler geçici klasörde kalıyordu. | Hata durumunda siliniyor. Test eklendi. |
| C6 | düşük | sadeleştirme | `rough_cut`, `render` | `framing_mode`/`mode` parametreleri artık hiçbir şey yapmıyordu; render'da üç kadraj yolu vardı. | Parametreler kaldırıldı, render tek yola indi. |
| C7 | düşük | sadeleştirme | `edit_plan`, `shared/news_package`, `config` | Kullanılmayan `validate_edit_project`, `add_timeline_item`, `add_news_segment`, `build_news_package`, `save_news_package` vardı; `RETRY_ATTEMPTS` tanımlıydı ama kullanılmıyordu. | Ölü kod silindi, sabit `retry_transient`'e bağlandı. |
| C8 | düşük | hata | `rough_cut` | Kesit kırpılırsa toplam süre hesabı kırpılmamış süreyi kullanıyordu. | Kesitler önce oluşturuluyor, gerçek süreleriyle hesaplanıyor. |
| C9 | düşük | doküman | `rough_cut.py` | `PAN_SPEED` satırındaki yorum aslında `EDGE_SECONDS`'a aitti. | Düzeltildi. |

## Tarayıcıda elle kontrol listesi (AppTest'in göremediği davranışlar)

1. Haber Stüdyosu: seslendirme metnini düzenle, kutunun dışına tıkla → metin korunmalı. Video Stüdyosu'na gidip dön → metin hâlâ orada olmalı.
2. Video Stüdyosu'nda kesit önizlemesi oynamalı; kaydırıcıyı değiştirince oynatıcı o aralığa gitmeli.
3. Axion'u kapatıp aç → Video ve Tasarım stüdyosunda haber seçili gelmemeli.
