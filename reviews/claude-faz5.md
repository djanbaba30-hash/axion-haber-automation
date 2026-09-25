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
