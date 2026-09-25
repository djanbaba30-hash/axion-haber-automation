# Claude 3.0.0 öncesi repo incelemesi (2026-09-25)

Editörün isteği: 2.x'i kapatmadan önce tüm repoyu kontrol et; optimize et, geliştir, toparla; hayat kalitesini artır;
DHA girişini bir kez kaydedip sonra otomatik doldur; Faz 4 ROADMAP'te ihtiyaç halinde dönülecek biçimde kalsın.

Yöntem: ruff (pyflakes, bugbear, pylint seçmeleri) ve vulture ile tarama, bulguların elle doğrulanması; incelenmemiş
kalan dosyaların (Haber Stüdyosu, Video Stüdyosu sayfası, store, Windows betikleri, README) satır satır okunması;
her düzeltme için test. Biçim önerileri (tırnaklı tip ipuçları, `zip(strict=)` vb.) davranış değiştirmediği için
toplu olarak uygulanmadı.

## Bulgular ve yapılanlar

| # | Önem | Tür | Yer | Sorun | Yapılan |
|---|---|---|---|---|---|
| 1 | yüksek | hata | `design_studio/design.py` `load_design` | Haber Stüdyosu'nda başlık değişip proje yeniden kaydedilince Tasarım Stüdyosu ve son video **eski başlıkları** kullanıyordu (başlık `tasarim.json`'a ilk açılışta yazılıyor, sonra hiç güncellenmiyordu). Kenar çubuğundaki metin de oturumda eski kalıyordu. | `news_headlines`: tasarım hangi haber başlıklarından türediğini tutar; haber değişince başlıklar yenilenir, yalnız Tasarım Stüdyosu'nda yapılmış düzenlemeler (satır kırma, sansür) haber değişmedikçe korunur. İmzaya girmez. Test. |
| 2 | orta | hata | `axion_local/store.py` `save_news_project` | Haber yeniden kaydedilince kurgu silinip **eski son video** kalıyordu. | Son video da silinir. Test. |
| 3 | orta | hata | `news_studio/page.py` | "Başlıkları yeniden üret" çağrısının token kullanımı hiçbir yere eklenmiyordu (`last_headline_usage` yazılıp okunmuyordu). | Toplam kullanıma eklenir (Geliştirici bilgileri). Test. |
| 4 | orta | performans | `video_studio/page.py` | "Son videoyu indir" düğmesi 10–25 MB'lık videoyu her etkileşimde belleğe okuyordu (Tasarım Stüdyosu'nda v2.8'de düzeltilmişti). | Yalnız tıklanınca okunur. |
| 5 | düşük | performans | `video_studio/page.py` kesit adımı | FFprobe her etkileşimde çalışıyordu. | Dosya başına bir kez (önbellek). |
| 6 | orta | hata (Windows) | `axion_local.py` "Axion'u kapat", `windows/guncelle.bat` | Axion zorla kapanınca Tarayıcı sayfasının görünmez Brave'i arkada kalabilir, profili kilitleyip sonraki açılışta tarayıcıyı başlatamaz. | Kapatırken tarayıcı düzgün kapatılır; güncellemede Axion profiliyle kalan süreçler kapatılır (normal Brave'e dokunmaz); başlatma kilitten düşerse artık süreci kapatıp bir kez yeniden dener. **Windows'ta denenmedi.** |
| 7 | orta | kullanım (tablet) | `video_studio/page.py` | "Videoyu oluştur" sayfayı dakikalarca kilitliyordu; tabletin ekranı kapanır ya da bağlantı koparsa üretim yarıda kalabilirdi. | Arka plan işi (`video_studio/jobs.py`): kurgu → son video; durum saniyede bir yenilenir; aynı haberin tasarım üretimi önce durdurulur. Testler (başarı, hata ve yeniden deneme, iptal). |
| 8 | orta | sadeleştirme | `news_studio/ai/clients.py` | OpenAI ve Claude çağrıları haber ve başlık için iki kez yazılmıştı (sıkıştırılmış satırlar). | Tek `_parse_openai` / `_parse_claude`; davranış aynı (çağrı biçimi testleri: önbellek anahtarı, düşünme seviyesi, token sınırı, kullanım). |
| 9 | düşük | sadeleştirme | `news_studio/page.py` | Yıldızlı import (`from config import *`), noktalı virgülle sıkıştırılmış satırlar, ölü `last_headline_usage`. | Okunur biçimde yeniden yazıldı, davranış aynı. |
| 10 | düşük | kullanım | `news_studio/page.py` | "Üslup örnekleri" her açılışta sıfırlanıyordu. | `data/ayarlar.json`'da hatırlanır. Test. |
| 11 | düşük | bakım | tüm sayfalar | Streamlit'in eskiyen `use_container_width` parametresi. | `width="stretch"`. |
| 12 | düşük | ölü kod | `template.preview_image`, `validation/news.py` döngü değişkeni, `calibration.py` import, testlerde kullanılmayan importlar, `blur.py` döngü kapanışı (B023) | — | Kaldırıldı / düzeltildi. |
| 13 | — | istek | Tarayıcı | DHA girişi her seferinde elle. | Giriş kaydı + otomatik doldurma (aşağıda). |
| 14 | — | kullanım | Tarayıcı → Video Stüdyosu | İnen videoyu Video Stüdyosu'nda listeden bulmak gerekiyordu. | "🎬 Video Stüdyosu'nda kullan": video 2. adımda seçili gelir. |

### DHA giriş kaydı (13)
- Editör giriş formunu gönderirken (Giriş düğmesi ya da Enter) kullanıcı adı + şifre bilgisayardaki tarayıcıda okunur;
  şifre yazılıyken başka bir yere dokunmak kaydı açmaz (yalnız düğme/bağlantı).
- Tablette "girişi kaydedilsin mi?" → Kaydet / Hayır. "Hayır" denen aynı bilgi yeniden sorulmaz; şifre değişirse sorulur.
- Kayıtlı sitenin giriş sayfası yüklenince kutular kendiliğinden dolar (React/Vue sayfaları için gerçek yazma olayları);
  editör yalnız Giriş'e dokunur. Otomatik gönderme yok: yanlış şifreyle hesap kilitlenmesin.
- Şifre `data/tarayici_girisler.json`'da Windows DPAPI ile (yalnız aynı Windows kullanıcısı çözebilir); tablete hiç
  gitmez (testte doğrulandı). Kenar çubuğunda liste ve "Sil".

## Bilinçli olarak yapılmayanlar
- Tip ipuçlarındaki tırnaklar, `zip(strict=)`, `try` içindeki döngüler (ruff UP/B905/PERF): davranış değişmez.
- `shared/axion_template.HEADLINE_BOX` kullanılmıyor ama Canva ölçümünün belgesi; kaldı.
- Faz 4 (Luna Edit Planner): editör kararıyla ertelendi, ROADMAP'te planıyla duruyor.
- Başlık yenileme istemi ("en fazla 9 kelime") değiştirilmedi: sistem istemi zaten 44 karakter kuralını içeriyor;
  gerçek modelle denenmeden haber üretim mantığına dokunulmadı (AGENTS kural 5).

## Doğrulama
- `make test` geçti. Tarayıcı testleri gerçek Chromium ile (giriş formu, kaydetme, otomatik doldurma, şifre değişimi,
  "Hayır", indirme, yeni sekme); arka plan video işi AppTest ile; yeni testler kararlı (giriş testi 6 kez üst üste).
- Headless Chromium'da tablet boyutunda: giriş → kaydet → yeniden girişte kutuların dolması → indirme → "Video
  Stüdyosu'nda kullan".
- Windows'ta, gerçek DHA'da ve AMD kodlayıcıyla denenmedi.

## Editör için Windows deneme listesi (3.0.0)
1. `guncelle.bat` → Axion açılıyor mu? (Playwright paketi kurulur.)
2. Tabletten **🌐 Tarayıcı** → DHA'ya giriş yap → "kaydedilsin mi?" → **Kaydet**. Çıkış yapıp yeniden gir: kutular
   doluyor mu? Bir haber videosunu indir → **🎬 Video Stüdyosu'nda kullan** → video seçili mi?
3. Video Stüdyosu'nda **Videoyu oluştur** → tableti kilitle, bir dakika sonra aç: video hazır mı? Kenar çubuğunda /
   Geliştirici bilgilerinde kodlayıcı "AMD donanım" mı?
4. Haber Stüdyosu'nda bir başlığı değiştir → **Sadece kaydet** → Video Stüdyosu'nda yeniden oluştur → son videoda yeni
   başlık mı?
5. Tasarım Stüdyosu: 3–6 blur (biri kenarda, biri dönen, bir mozaik) → **Yeniden oluştur** süresi; oluşturma sürerken
   bir şey değiştirip **🔁 Değişikliklerle yeniden başlat**.
6. Axion'u kapat → Görev Yöneticisi'nde arkada `brave.exe` kalmış mı (normal Brave açık değilken)?

## GPT'nin yerel gözlemleri (editörün Windows bilgisayarı, v3.0.0) ve kararlar

| # | Gözlem | Karar |
|---|---|---|
| G1 | `design_jobs.cancel` 60 sn beklemede döner, iş sürüyorsa Video Stüdyosu yine de son videoyu yazar: çakışma. | Doğru. `cancel` durup durmadığını döndürür; durmadıysa son video yazılmaz. Ayrıca tersi (video üretilirken Tasarım Stüdyosu'nun üretim başlatması) da kapatıldı. v3.0.1, testli. |
| G2 | "Axion'u kapat" (`os._exit`) arka plan üretimini yarıda keser. | Bilinen borç; yarım dosya `.yaziliyor.mp4` olarak kalır, son videonun yerine geçmez. Ayrı işçi süreci bu ölçekte fazla; kapatma onayına "üretim sürüyor" uyarısı eklendi. |
| G3 | Windows'ta `make` yok; `make test` çalışmıyor. | `windows/testler.bat` eklendi, README'de not. GPT'nin `.venv` bulamaması (Python yolunu görememesi) GPT'nin kendi korumalı ortamından; Axion'un kendisi aynı `.venv` ile çalışıyor. |
| G4 | (2. tur) Tasarım sayfasındaki "video üretiliyor mu" kontrolü ile `jobs.start` ayrı adımlar; iki stüdyonun kilitleri de ayrı. | Doğru. Tek başlatma kilidi (`design_studio/jobs.START_LOCK`, Video Stüdyosu da kullanır); kontrol `start` içinde. Test. |
| G5 | (2. tur) Kapatma uyarısının testi yok. | Eklendi (üretim varken / yokken). |
