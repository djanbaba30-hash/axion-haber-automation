# Axion Haber Automation — Yol Haritası

Bu dosya ürünün ana referansıdır. Güncel durum ve sıradaki iş: `AGENTS.md` → "Nerede kaldık". Her değişiklik şu soruyla değerlendirilir:
**"Bu, bizi güvenilir, otomatik ve editoryal olarak kullanılabilir haber videosu üretimine yaklaştırıyor mu?"**
Yaklaştırmıyorsa, sadece teknik olarak yapılabildiği için eklenmez.

## Amaç

Ham haber ve ilgili medyadan editoryal olarak doğru, sosyal medyada izlenebilir, doğal seslendirilmiş
bir haber videosunu mümkün olduğunca otomatik üretmek. Amaç editörü ortadan kaldırmak değil:
tekrar eden teknik işi otomatikleştirmek, son kararı editöre bırakmak.

```text
Ham haber + video ─► News Studio ─► NewsPackage + TTS ─┐
                     Video Studio ─► MediaLibrary ─────┼─► Edit Planner ─► EditProject ─► Renderer ─► MP4
```

## Mimari ilkeler

- News Studio haberin editoryal anlamını korur; Video Studio görüntüyü ve montajı yönetir.
- Video tarafındaki AI motoru GPT-5.6 Luna'dır; Claude Video Studio'da kullanılmaz.
- Modüller yalnızca ortak sözleşmeler üzerinden konuşur: `NewsPackage`, `MediaLibrary`, `EditProject` (`shared/`).
- API/token maliyeti her değişiklikte gözetilir; ikinci model çağrısı yalnızca gerçekten gerektiğinde yapılır.
- Doğrudan `main` üzerinde çalışılır.

## Çalışma ortamı kararı: yerel öncelikli

Sistem tamamen **evdeki Windows bilgisayarında** çalışır; bulut/hosting kullanılmaz.

- Büyük videolar internete yüklenmez; diskten okunur.
- Veriler (projeler, TTS kalibrasyonu, üretim geçmişi) kalıcıdır.
- Axion yalnızca editör ikona tıkladığında çalışır (Windows açılışında başlamaz). Şifre isteğe bağlıdır.
- Telefon/tabletten erişim, bilgisayar açıkken Tailscale ile sağlanır (internete açık port yok). DHA videoları tablete
  değil, Axion'un Tarayıcı sayfasıyla doğrudan bilgisayara indirilir.
- Tek uygulama: Haber Stüdyosu ve Video Studio aynı projede buluşur ("Kaydet ve Video Studio'ya geç"). JSON/MP3 indirip yükleme yok.

## Ürün kararları (editör)

**Haber metni ve TTS**
- Plaka, kimlik no ve benzeri teknik ayrıntılar hiçbir çıktıda yer almaz.
- İsim sansürü (editör, 2026-09-26): suç unsuru olan, reşit olmayan ve masumiyet karinesi/özel hayat gereği korunan
  kişilerin adı yalnız baş harfleriyle ("A.K."; DHA'nın "Abdullah K."sı da). Tanınmış kişiler ve röportaj veren
  kişilerin adı açık. TTS'te sivil isim ve baş harf kullanılmaz. (Kontrol: `validation/news.py`, API'siz.)
- TTS doğal ve konuşma dilindedir. Her cümle yeni bilgi verir; süreyi doldurmak için metin uzatılmaz.
- Viral potansiyeli olan yön öne çıkarılır, ama kaynakta olmayan fiil veya abartı kullanılmaz.
- **Başlıklar videoda 2 satıra sığmalı** (editörün temel kuralı): videodaki yazıyla (Google Sans Bold 58 px, 920 px
  genişlik) ölçülür. Modele "en fazla 44 karakter" denir; sığmayan başlık kalite kontrolünde düzeltme çağrısını
  tetikler (ek çağrı yalnızca gerekirse). Haber Stüdyosu başlık kutusunun altında canlı "sığıyor/sığmıyor" gösterir.

**Arayüz**
- Beyaz zeminli, Axion logosu renklerinde (lacivert, açık mavi, yeşil) sade arayüz; uygulama içinde logo yok.
- Editörün görmesi gerekmeyen bilgiler gizli (geliştirici bölümü); son kullanılan ayarlar hatırlanır.
- Tasarım Stüdyosu sade bir Canva'dır: her şey otomatik ve standart gelir (son video hazır), editör isterse değiştirir:
  başlık metni/yazı tipi/kalınlık/renk, sansür çizgisi, eklenen yazılar, efektleri seçme/kapatma, çerçeve animasyonu,
  arka plan, blur/mozaik. Yeni yazı tipi ve arka plan uygulamadan eklenir (yerel + GitHub). Alan kompakt kullanılır.
- Tasarım Stüdyosu düzeni (editör, v2.7.0): kenar çubuğunda durum, Yeniden oluştur, İndir ve başlık metinleri; ortada
  video; üstte Canva gibi yazı araç çubuğu (sansür = S̶ + kelimeye dokun); solda animasyon kartları / blur ayarları;
  sağda arka plan ve çerçeve; altta Canva gibi katmanlı zaman çizelgesi. Paylaşım metni ve Paylaş düğmesi burada yok.

**Video**
- Kurgu çıktısı şablondaki video alanının ölçüsünde: 960×1225 (H.264 için 960×1226). Axion şablonu ile son çıktı 1080×1920.
- Altyazı yok (şimdilik; 4.0'daki yazıya dökme ileride altyazıyı mümkün kılar, editör isterse).
- Tanık sesi editör kararıdır:
  - dikkat çekici söz → videonun başına, TTS'ten önce;
  - tamamlayıcı röportaj → TTS'ten sonra;
  - gerekmiyorsa → kullanılmaz.
  Video Stüdyosu'nda "Kaynak sesli kesitler" adımıyla yapılır (v2.0.0); birden fazla kesit seçilebilir.
- Haberler en fazla 3 gün saklanır (bugün + önceki 2 gün); eskiler otomatik silinir. Liste her gün 02:00'de sıfırlanır.
- Kaydırma: yanları dolgulu dikey çekimde hiç yok (tüm video boyunca sabit kadraj, v3.4); yalnız tam 16:9 görüntüde,
  özne alandan genişse yavaşça. Sabit kamerada (güvenlik kamerası) kadraj hareketin olduğu yere (v4.0).
- Video alanı hep tam dolu: hiçbir sahnede üst/alt/yan bulanık dolgu yok (editör, Kayseri testi).
- Seslendirmede saat/tarih/ondalık sayı okunuşuyla: "18.00'de" değil "akşam 6'da" (ElevenLabs okuyamıyor).
- Plaka ve reşit olmayanların yüzü bulanıklaştırılır. Blur tamamen elle: editör Tasarım Stüdyosu'nda blur kutusu ekler
  (şekil, boyut, güç, opaklık ayarlanır), videoda sürükleyerek takip ettirir. Otomatik tespit yok (editör kararı).
- Fotoğraflar da kurguya girer (yavaş yakınlaşma, alan tam dolu); ilk kare kapaktır (başlık tam görünür) (v4.0).
- Müzik altlığı varsayılan açık ("Gündem"): seslendirme ve konuşmalı kesitte varla yok arası, konuşmasız kesitte
  duyulur ama yüksek değil; editör Tasarım Stüdyosu'nda değiştirir ya da kapatır (v4.0).

**Kayıtlar ve maliyet (v4.0)**
- Editörün düzeltmeleri silinmeyen bir kayda yazılır; **token harcamaz, modele hiç gönderilmez, istemi büyütmez**.
  Geliştirici okuyup istemi/kuralları düzeltir (yeni kural eskisini sadeleştirerek; öncesi/sonrası token sayılır).
- Teşhis dosyası ve kayıtlar internete gönderilmez (repo herkese açık); editör indirip sohbette yollar.

## Fazlar

Sürüm 3.0.0 (2026-09-25): Faz 0–3 ve 5 tamam, Faz 6'nın temel akışı hazır. Sürüm 3.6.0: Faz 4. Sürüm 4.0.0
(2026-09-26): tüm fazlar tamam; editör gerçek haberlerde (tablet + ev) kullanıyor.

| Faz | İçerik | Sonuç |
|---|---|---|
| 0 ✅ | **Yerel çalışma:** tek uygulama (`axion_local.py`), kalıcı proje klasörü, videoyu diskten alma, ikonla konsolsuz başlatma, Tailscale ile uzaktan erişim | Yükleme sorunu biter |
| 1 ✅ | **News Studio:** zaman bilgili TTS (`convert_with_timestamps`), metin değişince sesin geçersiz sayılması, NewsPackage'da ses hash'i | TTS cümleleri zamanlanabilir |
| 2 ✅ | **Video Studio sözleşme geçişi:** `shared/` 2.1 modelleri, enum'lu Luna şeması, uzun shot pencereleri (Windows'ta doğrulandı) | Planner'a güvenilir veri |
| 3 ✅ | **Kaba kurgu:** kural tabanlı TTS ↔ shot eşleştirme + FFmpeg ile şablon video alanı ölçüsünde (960×1226) MP4 | **CapCut'a gerek kalmaz** |
| 4 ✅ (v3.6.0) | **Luna sahne seçimi (AI Edit Planner):** editör kararı (2026-09-26): "kurguyla sürekli uğraşmayalım, Luna yapsın, verimli olsun". Her videoda tek, görüntüsüz Luna metin çağrısı (`reasoning low`): seslendirme sahneleri (duraklamalarda kesilmiş, söylenen metinle) + analiz pencereleri (kaynak zamanı, çekim, tür, açıklama; aynı görünen ardışık pencereler tek satır) → her sahneye pencere + başlangıç anı. Kesme zamanları, kadraj, kesitler, aynı anın tekrar edilmemesi ve aynı çekimin kaynak sırası kurallarla kalır. Plan `kurgu_plani.json`'da; girdiler aynıysa yeniden çağrı yok; "🔀 Sahneleri yeniden seç" önceki kurguyu "beğenilmedi" notuyla gönderir. Luna'ya ulaşılamazsa kurallı kurgu (`rough_cut`, artık yalnız yedek ve kalan süreyi doldurma; kuralları ayrıca geliştirilmez). | Kurguyla uğraşmak biter |
| 5 ✅ (v2.5–v2.9; editör Windows'ta doğruladı) | **Tasarım Stüdyosu = sade Canva:** Axion şablonu otomatik (kurguyla birlikte son video hazır); canlı önizleme (tuval, efektler oynar); başlık/yazı stili, sansür, eklenen yazılar, seçilebilir animasyonlar, çerçeve animasyonları, arka plan seçimi, varlık ekleme; **elle blur/mozaik** (şekil, açı, yumuşak kenar, anahtar kare, canlı takip). Ayrıntı: aşağıda ve `shared/axion_template.py` | **Canva'ya gerek kalmaz** |
| 6 ✅ (v2.10–v3.4) | **Tabletten tam kullanım:** Axion tablette Tailscale ile açılır; iş bilgisayarda yapılır, tablete yalnızca önizleme ve son video (İndir) gelir. Dükkân başka ilçede, interneti yavaş (45/13 Mbps): büyük dosya tabletten yüklenmez, tablete de indirilmez. DHA videoları Axion'un **🌐 Tarayıcı** sayfasından indirilir (v2.10.0): evdeki bilgisayarda görünmez bir Brave (Axion'un kendi profili; editör Edge kullanmaz), tablete yalnızca ekran görüntüsü gelir, video evin internetiyle İndirilenler'e iner. Giriş bilgileri bir kez kaydedilir (Windows'ta şifreli), sonra kutular kendiliğinden dolar; inen video "🎬 Video Stüdyosu'nda kullan" ile seçili gelir (v3.0.0). Video ve son video arka planda üretilir: tablet kapansa da bilgisayarda sürer (v3.0.0). Uzak masaüstü yalnızca yedek (editör: iki monitör + gizli görev çubuğuyla pratik değil). Paylaş düğmesi ve APK yok (editör: işe yaramıyor). Editör doğruladı: gerçek DHA paneli (giriş kaydı, "Tüm Materyali İndir"), Tailscale üzerinden tablet ve telefon. | Evde olmadan haber → video |

## 3.x özeti (2026-09-25 – 2026-09-26; ayrıntı CHANGELOG)

Editörün ilk gerçek gün denemesinden (4 haber, v3.1) sonra: kendini yeniden başlatan bekçi ve güncellemede geri dönüş,
uygulamadan (tabletten) güncelleme, API'siz kalite kontrol araçları (kaynakta yok, okuyarak dinleme, düzeltme farkı,
"video hazır" bildirimi, paylaşım metnini kopyalama), TXT'den haber, adım süresi ölçümü, iki cihaz uyarısı, Tarayıcı
için doğrudan akış kanalı ve Axion'un kendi indirmesi, kurgunun olay örgüsünü izlemesi ve kadraj kuralları, isim
kuralı ("A.K."), teşhis dosyası, Faz 4 (Luna sahne seçimi, haberi bilerek).

**İstenmeyenler (editör kararı; yeniden önerme):** "bu haberle başla" düğmesi (haberin birden çok videosu olabilir),
günün haberleri panosu, arka planda otomatik analiz/video zinciri, düşük çözünürlük uyarısı, büyük düğmeler, "video
hazır" sesi, Tarayıcı'da DHA kısayolları, Axion'u Brave'de açmak, Windows açılışında otomatik başlatma, Windows'ta
otomatik test (GitHub Actions), güncellemeden sonra "Yenilikler", yatay/kare çıktı (yalnız Reels/Shorts), Paylaş
düğmesi ve APK, dosyaların repoya/internete otomatik yüklenmesi.

## Sürüm 4.0 (yapıldı, 2026-09-26)

Tema: Axion'u uzaktan güvenle kullanmak ve son kararı editöre hızlı verdirmek. Parça parça ön sürümler
(`v4.0.0-alpha.1` … `alpha.7.4`), sonra GPT incelemesi (`reviews/gpt-v4.md`, yanıt `reviews/claude-v4.md`) ve genel
tarama → `v4.0.0`. Hepsi API'siz (yazıya dökme de bilgisayarda):

1. **Fotoğraf desteği:** kurgu ve sahne değiştirmede fotoğraflar (yavaş yakınlaşma, EXIF yönü).
2. **Kurguda sahne değiştirme:** sahneye dokun → 4 alternatif → yalnız o parça değişir (Luna planının üstüne).
3. **Kapak = ilk kare:** başlık tam görünür.
4. **Müzik altlığı:** hazır sözsüz parçalar + editörün müziği; konuşmada kısılır.
5. **Düzeltmelerden öğrenme (kayıt):** token harcamaz; geliştirici okuyup istemi düzeltir.
6. **Durum paneli + günlük/aylık maliyet** (Geliştirici bilgileri).
7. **Yazıya dökme:** kesit cümleden seçilir (faster-whisper, bilgisayarda; editör Artvin haberiyle doğruladı).
   Ayrıca sabit kamerada kadraj hareketin olduğu yere (Artvin: Heimlich anı).

## v4.1 planı (editörle beyin fırtınası, 2026-09-26; GPT: `reviews/gpt-v5-fikirler.md`) — ONAYLANDI (editör, 2026-09-26)

Durum: 1. madde yapıldı (`v4.1.0-alpha.1`, editör denemesi bekleniyor); sıradaki **2. madde**. Biten maddeyi burada
"— YAPILDI (sürüm)" diye işaretle.

Sıra, bağımlılığa göre: önce altyapı kararını etkilemeyen küçük işler, sonra büyük kararlar için araştırma (kod yok),
sonra kararlara göre geliştirme. Her parça ayrı ön sürüm (`v4.1.0-alpha.N`); taşınma kararı çıkarsa o `v5.0`.
Her maddede AGENTS kural 12 (bir şey + etkilediği her şey, çöp yok, verimli, kaliteden ödün yok).

1. — YAPILDI (`v4.1.0-alpha.1`; göstergenin nedeni: SDK hata metni başlıklarla başlayıp kesiliyordu, asıl neden
   görünmüyordu; editör güncelleyince panelde yazan nedeni bildirir) **Okunuş sözlüğü + ElevenLabs kullanım
   göstergesi** (editör: "bazen yanlış okuyor, sırf o yüzden sesi yeniden
   üretiyorum"; "kullanılan kredi yazmıyordu"). Kalıcı, editörün doldurduğu küçük liste (`data/`; ör. Heimlich →
   Haymlih); yalnız ElevenLabs'a giden metne uygulanır, ekrandaki/paylaşım metni değişmez; okuyarak dinleme ve
   zamanlar bozulmaz. Göstergede önce neden bulunur (editörden Geliştirici bilgileri → 🩺 Durum ekran görüntüsü;
   olası neden: anahtarda kullanıcı okuma izni yok) → açık mesaj; ayrıca haber başına ve günlük/aylık harcanan
   karakter (defterde zaten var) görünür. API çağrısı eklenmez.
2. **Haberdeki alıntıdan kesit önerisi** (veri: 7/7 kesitte önerilen başlangıç ~15 sn ileri alındı). DHA metnindeki
   tırnaklı alıntı ↔ yazıya döküm eşleşmesi → "📍 Haberdeki alıntı: 00:54,5–01:01,9" önerisi; güven düşükse öneri yok,
   kendiliğinden eklenmez. API yok. Olay anı önerisi (güvenlik kamerası) kalır.
3. **Görüntü analizinin süre ölçümü** (medyan 14 sn, en uzun 45 sn): alt adımlar ayrı ölçülür (proxy, sahne tespiti,
   kareler, Luna, hareket); hızlandırma birkaç haberin verisiyle ayrıca kararlaştırılır.
4. **Araştırma A — altyapı/ön yüz (kod yok):** Streamlit'te kalmak (ve sürüm yükseltme planı, madde 6) mı, daha akıcı
   bir ön yüze taşınmak mı (ör. iş mantığı `apps/`+`shared/` aynen kalır, arayüz ayrı web uygulaması/PWA)? Rapor:
   seçenekler, tablette akıcılık/tasarım kazancı, taşıma işi ve riski, parça parça geçiş yolu, öneri. Editör karar
   verir; karar sonraki arayüz işlerinin (5, 7, altyazı) nerede yapılacağını belirler.
5. **Tarayıcı sayfası iyileştirmesi** (editör: tablette kaydırınca üst/altta beyazlık, çözünürlük). Editörden: tablet
   modeli + tarayıcı, sorunun ekran kaydı/görüntüsü. Düzen (tam ekran yüksekliği, kaydırma taşması) ve çözünürlüğün
   tabletin ekranına göre ayarlanması; akış hızı korunarak (yavaş internet).
6. **Streamlit sürüm yükseltme planı:** Araştırma A "kal" derse: uyum kontrol listesi (iç API'ler, `st.App`, medya
   sunucusu, components v2, tablet denemesi) ve denetimli yükseltme. "Taşın" derse gereksiz.
7. **Araştırma B — sosyal medyaya yükleme (kod yok):** yeni son sekmeden Instagram (Reels), YouTube (Shorts),
   Facebook, TikTok'a doğrudan yükleme mümkün mü: resmî API'ler, hesap türü şartları, onay/inceleme süreçleri, günlük
   sınırlar, maliyet, güvenlik (anahtarlar bilgisayarda). Not: istenmeyen "Paylaş düğmesi" tabletten dosya paylaşımıydı;
   bu, Axion'un bilgisayardan doğrudan yüklemesi (editörün yeni isteği). Rapor → editör karar verir.
8. **Sonra, veriyle:** düzeltme kaydı birikince (~10 haber) istem/kural iyileştirmesi (istem büyümez); görüntü analizi
   hızlandırması (3'ün verisiyle); **altyazı** yalnız editörün tarifinden sonra (nerede, nasıl; önce editöre sorulur).
   Blur/mozaik editör kullandıkça.

## Ortam

- Evdeki bilgisayar Windows; güçlü (AMD işlemci ve ekran kartı), 1000 Mbps internet, iş saatlerinde açık kalabilir.
- DHA videoları editör tarafından panelden normal yolla indirilir (evde doğrudan, dışarıda Axion'un Tarayıcı sayfasıyla);
  Video Studio indirilenler klasöründen okur. Otomatik DHA erişimi (kazıma, toplu indirme) hedef değil: editör kendisi
  gezer ve seçer.

## Axion şablonu (Faz 5; editörün Canva şablonu ve örnek videosundan)

Kanvas 1080×1920. Konumlar sol üst köşeye göre piksel; koddaki karşılığı `shared/axion_template.py`. Zamanlar
editörün Canva örneğinden (`assets/sablon/ornek_canva.mp4`) kare kare ölçüldü.
Tablodakiler **varsayılanlardır**; editör her animasyonu Tasarım Stüdyosu'nda değiştirebilir veya kapatabilir.

| Öğe | Konum / boyut | Zaman | Animasyon |
|---|---|---|---|
| Video | 960×1225, x=60, y=453; 6 px beyaz çerçeve, yuvarlak köşe | tüm video | — |
| Başlık 1 | 960×155, x=60, y=260; Google Sans Bold 58 px, büyük harf, beyaz, hafif glow; en fazla 2 satır | 0–9 sn | giriş yok, çıkış "merge" (8,77–9,03: sola kayarak satır satır söner) |
| "TARAFSIZ VE ŞEFFAF HABERCİLİK" (`slogan_1.png`) | başlık kutusunun ortası | 9,37–10,80 sn | "old tv": noktadan çizgiye, çizgiden yazıya (renk kayması) |
| "BEĞEN, PAYLAŞ, TAKİP ET" (`slogan_2.png`) | başlık kutusunun ortası | 11,37–12,85 sn | "old tv" |
| Başlık 2 | Başlık 1 ile aynı kutu ve yazı tipi | 13,13 sn → son | giriş "merge": 1. satır sağdan, 2. satır soldan kelime kelime |
| Logo kutusu (beyaz, yumuşak köşeli, içinde `logo.png`) | 200×200, x=440, alttan y=1737'ye yükselir | 15,03–17,69 sn | "slow baseline": hızlı çıkar, yavaşlayarak oturur, ışık geçer, hızla iner |
| Arka plan (`arka_plan_1..8.png`) | 1080×1920 (kaplayacak şekilde ölçeklenir) | tüm video | 8 arka plan; her iş günü (02:00) bir sonraki, aynı gün tüm haberler aynı; 24.09.2026 = 1 |

Not: Editörün notlarında logo 16–19 sn idi; Canva örneğinde 15,03'te çıkıp 17,69'da kayboluyor. Örnek esas alındı.
Videonun başına kaynak sesli kesit eklense de 1. başlık 0. saniyeden itibaren ekrandadır.
Zamanlar video uzunluğundan bağımsız, sabittir. Video **en az 20 sn**; daha uzunsa yalnızca arka plan ve 2. başlık
videonun sonuna kadar uzar. Seslendirme 20 sn'den kısaysa kurgu 20 sn'ye tamamlanır (son sahne sessiz devam eder).

## Açık sorular

- Yazı tipi: Canva'daki Binate Bold yerine editörün seçtiği Google Sans Bold (SIL OFL, `assets/sablon/fontlar/`).
  Google Sans biraz daha dar; görünüm editörün Windows testinde değerlendirilecek.
