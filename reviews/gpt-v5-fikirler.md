# GPT fikirleri — Axion v4.0.0 sonrası

Tarih: 2026-09-26

`git pull`: `Already up to date.` Başlangıç commit'i: `2757f5360d1f51cfb234e5dae9f877e764ff6407` (`main`).

AGENTS.md, ROADMAP.md'nin ürün kararları / 3.x özeti / “Sonra” bölümleri ve CHANGELOG.md'nin v4.0.0 özeti okundu. ROADMAP'teki **istenmeyenler** burada tekrar önerilmiyor. Dört yerel veri dosyası yalnızca sayım ve uzunluk istatistikleri için okundu; haber, kişi adı, kaynak dosya adı veya proje kimliği bu rapora alınmadı.

Kod değiştirilmedi; editörün bu dokümantasyon commit'i için test kapısını geçersiz kılma talimatı doğrultusunda test çalıştırılmadı. Axion başlatılmadı, ücretli API çağrısı yapılmadı; `.streamlit/secrets.toml` ve `data/tarayici/` açılmadı.

## Gerçek kullanımdan görülenler

### Adım süreleri

`data/olcumler.jsonl` içinde 75 ölçüm var. Medyan süreye göre yavaş adımlar:

| Adım | Ölçüm | Medyan | P90 | En uzun |
|---|---:|---:|---:|---:|
| Görüntü analizi | 11 | 14,2 sn | 27,7 sn | 44,8 sn |
| Haber yazımı | 12 | 9,4 sn | 21,1 sn | 25,3 sn |
| Sahne seçimi | 8 | 9,2 sn | 11,6 sn | 11,6 sn |
| Tasarım son videosu | 4 | 6,4 sn | 9,0 sn | 9,0 sn |
| Son video | 13 | 4,3 sn | 6,7 sn | 8,3 sn |
| Kurgu | 13 | 2,3 sn | 4,0 sn | 5,1 sn |
| Seslendirme | 14 | 1,1 sn | 1,5 sn | 2,4 sn |

Ölçüm satırlarında `hata` alanı dolu kayıt yok. “Görüntü analizi” zamanlayıcısı tüm medya hazırlama ve Luna analiz akışını kapsadığı için bu süre tek başına model beklemesini göstermiyor.

### Düzeltme örüntüleri

`data/duzeltmeler.jsonl` içinde 10 kayıt var: 2 haber, 7 kesit, 1 sahne. Haber örneği sayısı istem değişikliği kararı vermek için çok küçük.

- 1. başlık iki haberin ikisinde değişmiş: biri daha uzun, biri aynı kelime sayısında yeniden ifade edilmiş. Kısaltma örüntüsü görünmüyor.
- 2. başlık bir haberde değişmiş ve kelime sayısı artmış.
- Seslendirme iki haberin ikisinde değişmiş; ikisinde de model metninden daha uzun (ortalama +1,5 kelime). Bu, kendi başına belirli bir dil kuralının tekrar ettiğini kanıtlamıyor.
- Paylaşım metni bir kez değişmiş ve yaklaşık 4 kelime kısalmış.
- Yedi kesit kaydının tamamında seçilen başlangıç, önerilen başlangıçtan daha ileri: ortanca fark +14,6 sn; her seçim öneriden 0,25 sn'den fazla ayrılıyor. Küçük örneklemde, olay anı varsayılanının editörün aradığı alıntı başlangıcını sık sık bulamadığını düşündürüyor.

### Hata ve maliyet görünümü

- `data/axion.log` mevcut görüntüsünde 7 satır var; hata, uyarı veya traceback işareti yok. Süre ölçümlerinde de hata kaydı yok. Bu kısa günlük, geçmişte hata yaşanmadığını kanıtlamaz.
- `data/maliyet.jsonl` içinde 17 kayıt; tahmini toplam **$0,01941**. Bunun dağılımı: görüntü analizi **$0,00726 (%37,4)**, sahne seçimi **$0,00621 (%32,0)**, haber üretimi **$0,00535 (%27,6)**, başlık yenileme **$0,00060 (%3,1)**.
- ElevenLabs maliyeti dolar olarak değil karakterle kaydedilmiş: 2 ses üretiminde toplam **671 karakter**. Bu yüzden $0,01941 ses maliyetini içermez.
- Bu sayılar tek ve küçük bir yerel kullanım kesiti; uzun dönem maliyet ya da düzenleme eğilimi olarak genellenmemeli.

## Hedef önerileri

| # | Hedef ve editöre kazancı | API/token | İş | Risk | Dayanak |
|---|---|---|---|---|---|
| 1 | **Görüntü analizi süresini parçalara ayırıp en yavaş bölümü hızlandır.** Ölçümlerdeki en uzun medyanı hedefler; beklemenin Luna'dan mı, proxy/kare hazırlamadan mı geldiği netleşir. | Ölçüm için sıfır; hızlandırma mevcut model çağrılarını azaltmaya odaklansın. | Küçük ölçüm, ardından orta optimizasyon | Yanlış alt adım optimize edilirse kazanım çıkmaz; ölçüme dosya adı/haber metni eklenmemeli. | 11 ölçüm; medyan 14,2 sn, P90 27,7 sn, en uzun 44,8 sn. Mevcut adım birden çok işi kapsıyor. |
| 2 | **DHA'daki tırnaklı alıntıyı yerel dökümle eşleştirip kesit adayı göster.** Elle zaman arama ve kesit başlangıcını düzeltme azalır; editör yine dinleyerek onaylar. | Sıfır; yerel yazıya döküm + indirilen DHA metni üzerinde eşleştirme. | Orta | Whisper özel ad/kelime atlayabilir, DHA metni sesle birebir olmayabilir. Güven eşiği düşükse öneri göstermeyip elle seçime dönmeli; otomatik kesit eklememeli. | 7/7 kesitte başlangıç öneriden ileri taşınmış; ortanca +14,6 sn. |
| 3 | **Düzeltme kaydı yeterince birikince istem/kuralı sıkıştırarak iyileştir.** Tekrarlanan editör düzeltmeleri daha az manuel düzeltme ve daha tutarlı çıktı sağlayabilir. | Ek çağrı yok; mevcut istemdeki bir kuralı sadeleştir/değiştir. | Küçük–orta | Şu an yalnız 2 haber var; genelleme tek örneğe aşırı uyum sağlar ve editoryal anlamı bozabilir. | Başlık 1 ve seslendirme 2/2 kayıtta değişmiş, ancak ortak bir metin kuralı çıkarmak için örnek az. |
| 4 | **Editör onaylı telaffuz sözlüğünü yalnız seslendirme girdisine uygula.** Tekrarlanan özel adların daha tutarlı okunmasını sağlayabilir; ekranda görünen metin korunur. | Ek model çağrısı yok; aynı ses üretimi çağrısı. Dönüşmüş karakter sayısı maliyet kaydına yansıtılmalı. | Küçük–orta | Yanlış okunuş eşlemesi TTS'i ve karakter maliyetini artırabilir; görünür haber metnine fonetik yazım sızmamalı. Önce editörün doğruladığı birkaç adla deneme gerekir. | Güncel iki haber düzeltmesi okunuş hatasını kanıtlamıyor; bu nedenle veriyle desteklenen acil iş değil, koşullu aday. |
| 5 | **Altyazıyı şimdilik ertele; ileride istenirse yalnız kaynak sesli kesitte, isteğe bağlı dene.** Röportajı sessiz izleyen kişinin sözü takip etmesine yardım edebilir. | Sıfır API; mevcut yerel döküm. | Orta–büyük | Yanlış kelime, özel ad ve zamanlama güveni düşürür; şablon alanı ve okunabilirlik ayrıca denenmeli. Editörün açık ürün kararı olmadan başlamamalı. | ROADMAP “altyazı şimdilik yok” diyor; kullanım verisinde altyazı talebi veya doğruluk düzeltmesi ölçülmüyor. |
| 6 | **Streamlit yükseltme planı ve küçük uyumluluk kontrol listesi hazırla; yükseltmeyi ancak gereksinim varsa yap.** Gelecekte güvenlik/bakım güncellemesini tablet akışını bozmadan değerlendirmeyi sağlar. | Sıfır API/token. | Orta | `st.App`, oturum yöneticisi, medya yöneticisi ve components v2 gibi iç API'ler değişebilir; gerçek tablet akışı etkilenebilir. Her sürüm artışında yerel test ve tablet smoke-check gerekir. | Bağımlılık `streamlit==1.64.0` olarak sabit; AGENTS iç API'leri ve tablet davranışını özellikle risk olarak işaretliyor. |

## Claude'un önerileri

| Öneri | Karar | Neden |
|---|---|---|
| (a) Düzeltme kaydına göre istemi büyütmeden iyileştirmek | **Katılıyorum, fakat şimdi genel istemi değiştirmem.** | Bu, ROADMAP kararıyla uyumlu. Yalnız iki haber kaydı var; tekrar eden örüntü oluşunca mevcut kuralı sadeleştirerek değiştir, token sayısını önce/sonra ölç ve gerçek örnekle regresyon testi ekle. |
| (b) DHA tırnaklı alıntısını yazıya dökümle eşleştirip kesit önermek | **Güçlü biçimde katılıyorum.** | Yedi kesitin tamamında seçilen başlangıç öneriden ileri alınmış. Yerel eşleştirme/API'siz öneri zaman kazandırabilir; düşük güven durumunda insanın dinleyip seçmesi devam etmeli. |
| (c) Seslendirmede okunuş sözlüğü (ör. Heimlich) | **Koşullu katılıyorum.** | Önce editörün gerçekten yanlış duyduğunu doğruladığı adlar eklenmeli. Sözlük TTS girdisiyle sınırlı kalmalı; haber metnini değiştirmemeli ve ayrı ücretli çağrı yapmamalı. Mevcut düzeltme kaydı bu sorunu göstermiyor. |
| (d) Yalnız kaynak sesli kesitlerde isteğe bağlı altyazı | **Şimdi hayır; ileride editör isterse sınırlı pilot.** | Ürün kararı şu an altyazı istemiyor ve kullanım verisi de ihtiyaç göstermiyor. İleride onaylanırsa yalnız seçilen kaynak sesli kesitte, kapalı varsayılanla ve düzenlenebilir metinle denenebilir. |
| (e) Adım süreleriyle en yavaş adımı hızlandırmak | **Katılıyorum.** | Görüntü analizi medyanı 14,2 sn ile en yüksek. Önce mevcut kapsayıcı ölçümü proxy, kare çıkarımı ve model isteği gibi alt adımlara ayır; sonra verinin gösterdiği bölümü optimize et. |
| (f) Streamlit sürüm yükseltme planı | **Katılıyorum; yükseltmeyi hemen önermiyorum.** | Sürüm sabit ve uygulama iç API kullanıyor. Plan; hedef sürüm için yerel testler, ASGI açılışı, medya sunucusu, components v2 ve gerçek tablet kontrolünü kapsamalı. ROADMAP'teki istenmeyen Windows otomasyon/CI'sini önermiyorum. |

## Öncelik sırası

1. Görüntü analizi iç adımlarını ölç; en uzun bölümü hızlandır.
2. Tırnaklı alıntı–yerel döküm eşleştirmesiyle kesit adayı sun; dinleyerek editör onayı iste.
3. Düzeltme kayıtlarını biriktir; tekrar eden kuralı ancak yeterli örnekten sonra istemi büyütmeden değiştir.
4. Telaffuz sözlüğünü yalnız doğrulanmış ihtiyaçta dene; altyazıyı editör kararı gelene kadar beklet.
5. Streamlit yükseltmesini ihtiyaç doğarsa uyumluluk planıyla ele al.
