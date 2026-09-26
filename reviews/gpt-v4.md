# GPT incelemesi — v4.0.0 öncesi

İnceleme tarihi: 2026-09-26

Dal/başlangıç commit'i: `main` / `e3be6fd1e59fb23ae9fc5debd0bee2a5de663877`

`git pull`: `Already up to date.`

Kapsam: `8365e2b..HEAD`; gerçek fark 53 dosya, 3.497 ekleme ve 99 silme. Başlangıçta çalışma ağacı temizdi.

## Doğrulama

- Çalıştırılan tam komut: `.venv\Scripts\python.exe -m pytest -p no:cacheprovider`
- Sonuç satırı: `4 failed, 389 passed, 1 warning in 94.70s`.
- Atlanan test yok. Başarısızlar:
  - `tests/test_photos.py::test_render_photo_cut_to_mp4_upright_and_full_frame`: EXIF yönü 6 olan fotoğrafın çıktısı `(1226, 960)`; beklenen `(960, 1226)`. FFmpeg sürümünü doğrudan okuyamadım (`ffmpeg` mevcut komut ortamında bulunamadı); kök neden doğrulanmadı.
  - `tests/test_corrections.py::test_empty_log_and_write_errors_do_not_break_work` ve `tests/test_status.py::test_ledger_write_error_does_not_break_work`: ürün fonksiyonu çağrılmadan önce test kurulumu `write_text("klasör değil")` sırasında Windows'un varsayılan cp1252 kodlamasında `ğ` karakteri için `UnicodeEncodeError` veriyor.
  - `tests/test_axion_local_app.py::test_diagnostics_file_for_the_developer`: günlük sonu `SON SATIR\r\n`; test `SON SATIR\n` bekliyor. Windows metin kipinde satır sonu dönüşümünden kaynaklanan test beklentisi.
- Uyarı: `tests/test_remote_browser.py:24` geçersiz kaçış dizisi `\u` için `SyntaxWarning`.
- Windows betikleri kural 8'e göre kontrol edildi: 8 betiğin tümü ASCII ve CRLF. `make` kurulu olmadığından `make test` çalıştırılamadı; tam pytest komutu yukarıdaki gibi çalıştırıldı.
- `data/projects/` altındaki izin verilen proje JSON'ları yalnızca yerel inceleme için okundu; içerikleri bu rapora veya repoya alınmadı.
- Axion başlatılmadı/durdurulmadı; `guncelle.bat` çalıştırılmadı; paket kurulmadı; ücretli API çağrısı yapılmadı. Tarayıcı/tablet ve gerçek AMD kodlayıcı akışı çalıştırılmadı.

## Bulgular

### V4-G1 — Orta

- **Tür:** maliyet (token)
- **Yer:** `apps/video_studio/modules/luna_edit.py:38-43,129-130,203-225`
- **Sorun:** Fotoğraf desteği için `SYSTEM_PROMPT`'a bir yönerge eklendi; `signature()` imzaya tüm sistem istemini katıyor. v3.7.2'de kaydedilmiş Luna planlarının imzası bu yüzden fotoğraf içermeyen projelerde de değişiyor. Bu projede video yeniden oluşturma/planlama çalıştığında kayıtlı plan geçersiz sayılıp Luna'ya yeni çağrı yapılabilir; editörün 4.0 için “gereksiz yeni model çağrısı olmasın” kararı bozulur. Yeni statik yönerge yaklaşık 30–35 token; fotoğraflı girdide her fotoğraf için ayrıca bir satır eklenir. Bu tahmindir, model tokenizer'ı ile sayılmadı. Haber istemleri değişmemiştir.
- **Öneri:** Fotoğraf yönergesini ve imza değişimini yalnız fotoğraf içeren planlara uygula veya eski video planlarını fotoğrafsız girdilerde geçerli kabul et. Eski imzalı, fotoğrafsız plan için istemcinin çağrılmadığını doğrulayan test ekle.
- **Kanıt:** İmza ve plan seçimi kodundan doğrulandı; ücretli çağrı özellikle yapılmadı.

### V4-G2 — Orta

- **Tür:** hata / eşzamanlılık
- **Yer:** `apps/video_studio/modules/transcribe.py:282-300`
- **Sorun:** `start()` içinde `_JOBS.get`, yeni `Job` oluşturma ve sözlüğe koyma kilitsiz. Aynı haber iki cihazda açıkken iki Streamlit oturumu aynı anda “yazıya dök” başlatırsa ikisi de boş kayıt görüp iki iş parçacığı başlatabilir. `_LOCK` model çağrılarını sıraya koyuyor; ikinci dökümü engellemiyor. Aynı videonun CPU işi ve dosya yazımı iki kez yapılabilir.
- **Öneri:** İş sözlüğü için ayrı kilitle kontrol + kayıt + thread başlatma işlemini atomik yap; varsa aynı işi döndür. İki oturumun eşzamanlı başlatma testi ekle.
- **Kanıt:** Kilit kapsamı statik incelemede doğrulandı; yarışı eşzamanlı çalıştırarak üretmedim.

### V4-G3 — Düşük

- **Tür:** hata / önbellek
- **Yer:** `apps/video_studio/modules/transcribe.py:88-95`
- **Sorun:** Döküm anahtarı kaynak dosyanın yalnız adı, boyutu ve saniyeye yuvarlanmış `mtime` değerini kullanıyor. Aynı adlı dosya aynı boyutta aynı saniye içinde değiştirilirse (veya alt-saniye farkıyla kaydedilirse) `load()` eski dökümü yeni videoya aitmiş gibi bulabilir.
- **Öneri:** Anahtara `resolve()` edilmiş yol ve `st_mtime_ns` ekle; aynı boyut/zaman olasılığı için içerikten küçük bir parmak izi veya tam içerik özeti kullan. Aynı boyutlu, aynı saniyedeki değiştirme senaryosunu test et.
- **Kanıt:** Anahtar bileşenleri koddan doğrulandı; dosya değiştirme senaryosunu yerel veri üzerinde denemedim.

### V4-G4 — Orta, şüpheli kök neden

- **Tür:** hata (fotoğraf yönü / Windows FFmpeg)
- **Yer:** `apps/video_studio/modules/render.py:120-129`; test: `tests/test_photos.py:131-145`
- **Sorun:** EXIF 6'lı fotoğraf entegrasyon testi Windows koşusunda videodan alınan kareyi yatay `(1226, 960)` buldu; video alanı dikey `(960, 1226)` olmalı. Bu durum fotoğraf sahnesinin yönünü bozabilir ve son tasarım render'ında görüntünün beklenmedik biçimde ölçeklenmesine yol açabilir.
- **Öneri:** Windows'taki FFmpeg build'iyle üretilen komutu ve `ffprobe` boyut/döndürme bilgisini incele; EXIF dönüşümünden sonra piksel boyutunu açıkça dikey video alanına sabitle. En azından EXIF 2–8 yönleri için gerçek render testi çalıştır.
- **Kanıt:** Testteki boyut uyuşmazlığı doğrulandı. Kullanılan FFmpeg sürümü ve hatanın `-noautorotate`/filtre/çıktı metadata'sından hangisine bağlı olduğu doğrulanmadı.

## Verimlilik/optimizasyon

- **Düşük — `apps/axion_local/media.py:9-19`, `apps/video_studio/range_player.py:64-71`, `apps/video_studio/page.py:450`:** Her sayfa yeniden çalışmasında `media_url(Path)` Streamlit'in medya yöneticisine tekrar yol veriyor; mevcut Streamlit depolaması her çağrıda dosyayı okuyup kimlik/hash çıkarıyor. Slider veya cümle seçimi uzun MP4'ü tekrar tekrar diskten okuyabilir. Yol + boyut + `mtime_ns` ile URL/kimlik önbelleği kullanmayı veya dosya okumasını erteleyen bir medya yolu seçmeyi değerlendirin. Kod akışı ve kurulu Streamlit uygulaması doğrulandı; gerçek dosya boyutunda süre ölçülmedi.
- **Düşük — `apps/video_studio/modules/media_pipeline.py:85-89`, `apps/video_studio/modules/framing.py:195-208`:** Her analiz penceresi için ayrı FFmpeg süreci başlatılıyor. Uzun videolarda pencere sayısı kadar süreç başlangıcı ek gecikme getirir. Proxy'yi tek geçişte 5 fps çözerek kareleri pencere aralıklarına bölmek değerlendirilebilir. Süre etkisi ölçülmedi.
- **Düşük — `apps/video_studio/modules/transcribe.py:179-193`:** `levels()` tüm videonun sesini `capture_output` ile belleğe alıyor; 16 kHz mono PCM'de ham çıktı yaklaşık 32 KB/sn, ardından float32 örnek dizisi de tutuluyor. Bir saatlik kaynakta bu iki dizi birlikte yaklaşık 330 MiB yapar. Tipik kısa haber videoları için sorun görmedim; çok uzun kaynaklarda akışlı/chunk'lı ölçüm belleği sınırlar.

## Sadeleştirme (ölü kod)

- `apps/video_studio/modules/speech.py` ölü değil; `apps/design_studio/music.py:speech_spans()` içinde kullanılıyor. `hotwords` yalnız eski davranışı açıklayan yorum/test metninde geçiyor; çalıştırılan hotword parametresi yok. `yazi_anchor` için kodda etkin kullanım bulmadım. Güvenle silinebilecek yeni ölü fonksiyon/sabit saptamadım.

## Test

- İki test, senaryo kurulumunda `write_text("klasör değil")` için açık `encoding="utf-8"` kullanmadığından Windows cp1252'de ürün koduna ulaşmadan düşüyor (`tests/test_corrections.py:54`, `tests/test_status.py:34`). Test metinlerine UTF-8 belirtin.
- Teşhis testi günlükteki Windows `CRLF` sonunu birebir `LF` olarak bekliyor (`tests/test_axion_local_app.py:1180-1188`). Satır sonunu normalize ederek içerik sonunu doğrulayın.
- Fotoğraf yönü testi gerçek FFmpeg çağrısı yapıyor ve bu ortamda başarısız; Windows FFmpeg sürümünü CI/yerel test raporuna eklemek kök nedeni ayırmaya yardımcı olur.
- Transkripsiyon testleri sezgileri sahte kelime/örneklerle kapsıyor; eşzamanlı job başlatma ve aynı boyut-zaman cache çakışması test edilmiyor.
- `tests/test_remote_browser.py:24` içindeki `\u` için raw string veya çift ters eğik çizgi kullanmak uyarıyı kaldırır.

## Özet tablosu

| Kimlik | Önem | Yer | Özet | Önerilen iş |
|---|---|---|---|---|
| V4-G1 | Orta | `luna_edit.py:38-43,129-130,203-225` | Yeni sistem istemi eski fotoğrafsız Luna planlarının önbelleğini de geçersiz kılıyor. | küçük |
| V4-G2 | Orta | `transcribe.py:282-300` | Eşzamanlı iki oturum aynı dökümü iki kez başlatabilir. | küçük |
| V4-G3 | Düşük | `transcribe.py:88-95` | Alt-saniye/same-size kaynak değişimi eski döküm anahtarına çarpabilir. | küçük |
| V4-G4 | Orta, şüpheli kök neden | `render.py:120-129` | EXIF 6 fotoğraf Windows testinde yatay boyutlu kare üretti. | orta |
| V4-T1 | Düşük | `test_corrections.py:54`, `test_status.py:34` | İki test kurulumunda Windows varsayılan kodlaması Türkçe karakteri yazamıyor. | küçük |
| V4-T2 | Düşük | `test_axion_local_app.py:1180-1188` | Teşhis testi LF beklerken Windows günlük satırı CRLF ile bitiyor. | küçük |
