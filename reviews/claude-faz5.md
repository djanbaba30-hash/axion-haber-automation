# Claude Faz 5 optimizasyonu (2026-09-25) — ölçümler, GPT önerilerine kararlar, v2.9.0

Editör "bu sabah optimizasyonlarla devam" dedi ve GPT'ye de danıştı (`reviews/gpt-faz5.md`). Claude önce Tasarım
Stüdyosu'nu ölçtü, sonra GPT önerilerini kodla karşılaştırdı. Editör şu sırayı onayladı: (1) son video hızı,
(2) son video doğrulaması, (3) eski işi durdurma + üst çubukta durum, (4) efekt parametreleri tek kaynak.

## Ölçümler (v2.8.0, bu ortam: 4 çekirdek Xeon, x264 veryfast; 18,2 sn'lik gerçek haber)

| Ölçüm | Süre |
|---|---|
| Sayfa: ilk açılış (slogan/logo PNG 0,75 sn, arka plan JPEG 0,4 sn, sahne 0,3 sn) | ~1,5 sn |
| Sayfa: sonraki her yeniden çalıştırma (sahne + atlaslar + PNG'ler) | ~0,1 sn |
| Son video: 6 blur + kovalayan çerçeve (katmanlar 4,9 + FFmpeg 53,8) | ~59 sn |
| Son video: blursuz / blursuz + sabit çerçeve | ~24 / ~19,5 sn |
| FFmpeg ayrıntısı (blursuz): filtreler 15,3 sn, x264 kodlama ~5 sn, kurgu çözme 0,5 sn | |

Darboğaz kodlama değil filtre zinciriydi (Windows'ta AMF kodlama hızlı olsa da süre düşmezdi):
- `-loop 1 -i zemin.png`: 1080x1920 PNG **her karede yeniden çözülüyordu** (yalnız bu ~6 sn).
- Grafik/çerçeve katmanları `fps` ile çoğaltıldıktan sonra RGBA→YUV çevriliyordu (her çıkış karesinde tam kare dönüşüm).
- Her blur **tüm kareyi** her an bulanıklaştırıp maskeyle bindiriyordu: 6 blur ≈ +34 sn.

## Yapılanlar (v2.9.0)

| # | İş | Sonuç |
|---|---|---|
| 1 | Zemin bir kez okunur (`loop` filtresi), katmanlar `fps`'den önce YUV'a çevrilir; blur/mozaik yalnızca kutunun tüm süredeki bölgesinde (+ bulanıklık payı) ve görünür olduğu sürede işlenir; hiç görünmeyen blur atlanır | Standart şablon 25,7 → **8,8 sn**; 6 blur + kovalayan 53,5 → **18,8 sn**. Standart şablon eskisiyle bit bit aynı; blurlu videoda PSNR ≥ 44,8 dB (gözle fark yok, yan yana bakıldı) |
| 2 | Son video FFprobe ile denetlenir (açılıyor mu, 1080x1920, süre ±0,25 sn, kurguda ses varsa ses); AMF bozuk video üretirse x264 ile yeniden | Sahte FFprobe çıktılarıyla test edildi; **gerçek FFprobe ile denenmedi** (bu ortamda yok, Windows kurulumunda var) |
| 3 | Üretim sürerken tasarım değişirse "🔁 Değişikliklerle yeniden başlat": eski FFmpeg öldürülür, yeni iş onun bitmesini bekleyip başlar; üst çubukta "Son video güncel / işlenmedi / oluşturuluyor" | AppTest (iptal edilen işin tasarımı hiç yazılmaz) + gerçek FFmpeg'in <5 sn'de durdurulması + Chromium'da rozet akışı |
| 4 | Efekt süre/mesafeleri `effects.json`'da (Python ve JS aynı dosyayı okur) + `tests/test_effects_parity.py`: JS formülleri Node'da çalıştırılıp Python'la 0,01 sn adımla karşılaştırılır | Test ilk çalıştırmada gerçek bir fark buldu: eski TV sloganında renk kayması yarım piksellerde farklı yuvarlanıyordu (düzeltildi) |

Neden yalnızca JSON değil: GPT'nin A seçeneği (parametreler tek dosyada) sabitlerin ayrışmasını önler ama formüllerin
ayrışmasını önlemez; asıl risk formüllerdeydi. Eşlik testi ikisini de yakalar. Çerçeve çizimi (numpy ↔ canvas) testte
değil: piksel düzeyinde aynı olamaz, parametreleri JSON'dan gelir.

## GPT önerilerine kararlar

| # | Öneri | Karar | Gerekçe |
|---|---|---|---|
| 1 | Değişiklik zinciri / ortak imza sistemi | **Ertelendi** | Parçaları zaten var: Video Stüdyosu haber/görüntü değişince kurguyu ve son videoyu siler, Tasarım imzası güncel olmayanı gösterir. `st_mtime` yalnızca kurgu yeniden üretilince değişir; o zaman son videonun yeniden üretilmesi zaten doğru. Büyük yeniden yapılanma, bugün hissedilen bir sorunu çözmüyor |
| 2 | Efekt mantığı tek kaynak | **Yapıldı** (JSON + eşlik testi) | Yukarıda |
| 3 | Kaydedildi ≠ son videoya işlendi | **Yapıldı** | Üst çubukta ayrı rozet (kenar çubuğunda zaten vardı) |
| 4 | Eski render'ı durdurma | **Yapıldı** | Yeniden başlatınca eski FFmpeg öldürülür |
| 5 | Sayfa yeniden çalışmasında önbellek | **Katılmadım** | Ölçüldü: yeniden çalıştırma ~0,1 sn. Kaydırıcı hareketleri Python'a gitmiyor (editör tasarımı tarayıcıda tutar, 400 ms gecikmeyle tek gönderim) |
| 6 | Luna kare bütçesi | **Zaten var** | `media_pipeline.MAX_FRAMES_PER_VIDEO = 40`; pencere başına kare bu tavana göre seyreltilir |
| 7 | Proxy önbelleği | **Katılmadım** | Proxy yalnızca analiz sırasında üretilir; analiz `media_library.json`'da saklanır, tekrar açınca proxy de analiz de yapılmaz. Proxy'yi saklamak disk kullanır (AGENTS: geçici klasörde, analiz bitince silinir) |
| 8 | Media Library parmak izi | **Ertelendi** | Görüntüler değişince Video Stüdyosu analizi zaten geçersiz sayıyor; yeniden analiz yalnızca editörün düğmesiyle. Kazanç küçük |
| 9 | Ortak varlık kimliği (SHA256) | **Ertelendi** | 7–8'e bağlı; tek başına kazancı yok |
| 10 | Son video doğrulaması | **Yapıldı** | fps ayrıca denetlenmiyor (süre + boyut + ses yeterli; fps kurgudan gelir) |
| 11 | Önizleme / final ayrımı | **Zaten var** | Üst çubukta "🎨 Düzenle / 🎬 Son video" geçişi; tuval canlı önizleme, "Son video" gerçek MP4 |
| 12 | Tasarım geçmişi (adlandırılmış) | **Ertelendi** | 60 adımlık geri al/yinele v2.8.0'da geldi, editör henüz denemedi |
| 13 | Tablet dokunmatik testleri | **Faz 6'da** | ROADMAP Faz 6 |
| 14 | İş akışı durum çizgisi | **Ertelendi** | Video Stüdyosu adımları zaten "✅ …" özetine daralıyor; editör isterse küçük bir iş |
| 15 | "Neden yeniden oluşturuyoruz" | **Kısmen** | Tasarımda: rozet + "Son değişikliklerin bu videoda yok". Zincirin geri kalanı 1'e bağlı |

## Doğrulanmadı / editörün Windows'ta bakması gerekenler
- AMD `h264_amf` ile yeni süre (bu ortamda yalnız x264 ölçüldü; filtreler hızlandığı için AMF'de oran daha da iyi olmalı).
- Gerçek FFprobe ile son video kontrolü (Windows kurulumu FFprobe'u zaten içerir; Video Stüdyosu da kullanır).
- "🔁 Değişikliklerle yeniden başlat" düğmesi: bir başlık değiştirip "Yeniden oluştur"a bas, bitmeden başka bir şey
  değiştir, düğmeye bas.

## GPT revizyonu (v2.9.0 incelemesi) ve v2.9.1

GPT v2.9.0'ı statik inceledi (editör cevabı sohbete yapıştırdı). Claude'un "Katılmadım / Ertelendi / Zaten var"
kararlarının hiçbirine itiraz etmedi. Bulguları çoğunlukla "gerçek FFmpeg / Windows ile doğrulanmadı" uyarısıydı.

| GPT bulgusu | Karar | Ne yapıldı |
|---|---|---|
| 1, 7 (test): kenara taşan + dönen + yumuşak kenarlı blur gerçek FFmpeg'le doğrulanmamış | **Yapıldı** | `test_cropped_blur_matches_full_frame_blur_at_edges_and_rotation`: aynı blurlar bir kez kırpılmış bölgede, bir kez tüm karede gerçek FFmpeg ile üretilip karşılaştırılır; en kötü kare PSNR 52 dB (fark yalnız sıkıştırma gürültüsü) |
| 2: `blur_region` her kareyi Python'da tarıyor | **Değiştirilmedi** | Ölçüldü: 3 blur × 546 kare < 0,01 sn (maske yazımıyla birlikte hareketli 3 blur 2,2 sn) |
| 3, 4: kısa/uzun kurgu, zemin döngüsünün kare sayısı | **Yapıldı** | `test_final_video_has_exact_frames_when_rough_cut_is_shorter_or_longer`: 2 ve 4 sn'lik kurgu, 3 sn'lik tasarım → tam 90 kare, süre 3,0 sn, ses var |
| 5: FFprobe yoksa kontrol sessizce atlanıyor | **Yapıldı** | Atlanınca `data/axion.log`'a uyarı yazılır; editöre hata gösterilmez |
| 6: fps denetlenmiyor | Kabul (GPT de kabul etti) | — |
| 8, 10: Windows'ta kill/communicate süresi; yeni iş eskisini bekliyor | **Windows'ta denenecek** | Bu ortamda gerçek FFmpeg <5 sn'de durduruluyor (test). Kenar çubuğundaki yeni "Son oluşturma N sn · kodlayıcı" satırı süreyi gösterir |
| 9, 11, 12 | Hata yok (GPT) | — |
| Sıradaki 1: Windows render doğrulama paketi | **Kısmen** | Kenar çubuğunda son oluşturmanın süresi ve kodlayıcısı görünür (AMD çalıştı mı, kaç sn sürdü). Aşağıda editör için deneme listesi |
| Sıradaki 2: durum dilini birleştirmek | **Yapıldı** | Üst çubuk: "✓ Kaydedildi", "✓ Son video hazır", "⚠ Son videoya işlenmedi", "⏳ Son video oluşturuluyor" |
| Sıradaki 3: blur sayısı/boyutuna göre ölçüm | **Yapıldı** | Aşağıdaki tablo |

**Claude'un bu turda bulduğu hata (v2.8.0'dan beri):** sayfa ve arka plandaki üretim `tasarim.json`'a kilitsiz
yazıyordu. Sayfanın elindeki eski kopya, biten üretimin imzasını ezebiliyordu ("işlenmedi" yanlış görünür). Nadiren
üretim de editörün o anki değişikliğini ezebiliyordu. Bir test bir kez bu yüzden kırıldı. Düzeltme: tek kilit;
sayfa `rendered`'a hiç dokunmaz, imzayı yalnızca `pipeline.mark_rendered` yazar. Regresyon testi eklendi.

### Blur maliyeti (18,2 sn haber, sabit çerçeve, x264, bu ortam)

| Blurlar | Son video |
|---|---|
| 0 | 9,8 sn |
| 1 küçük (%15 × %10, sabit) | 9,4 sn |
| 3 küçük | 12,4 sn |
| 6 küçük | 15,6 sn |
| 10 küçük | 20,0 sn |
| 6 küçük mozaik | 12,5 sn |
| 3 orta (%33 × %25) | 13,4 sn |
| 3 büyük (%80 × %50) | 15,4 sn |
| 3 küçük, tüm kareyi çaprazlama gezip 180° dönen | 22,9 sn |

Maliyet kutunun **tüm süre boyunca taradığı alanla** büyür: çok gezen blurda bölge neredeyse tüm kare olur. Ölçüldü:
bu durumda sürenin çoğu Gauss bulanıklığında (maske yazımı ~2 sn). Yarım çözünürlükte bulanıklaştırmak kazandırmadı.
Olası sonraki adım: bölgeyi zamana bölmek (her saniye kendi küçük bölgesi). Canlı takipte kutu bu kadar gezmediği ve
editör Windows'ta yavaşlık görmediği sürece yapılmayacak.

### Editör için Windows deneme listesi
1. Blursuz bir haberde **🎬 Yeniden oluştur** → kenar çubuğunda "Son oluşturma N sn · AMD donanım (h264_amf)" mı yazıyor?
   (x264 yazıyorsa AMD kodlayıcı çalışmamış demektir.) N'yi not et.
2. 3–6 blur (biri kenara taşan, biri döndürülmüş, bir mozaik) ekle, yeniden oluştur, videoyu izle ve süreyi not et.
3. Oluşturma sürerken başlığı değiştir → **🔁 Değişikliklerle yeniden başlat** → yeni üretim hemen başlıyor mu?
4. Son videoyu indirip telefonda aç: ses, süre ve görüntü tamam mı?
