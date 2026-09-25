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
- Röportaj veren kişinin adı açık yazılır. Diğer sivil isimler baş harfle yazılır; TTS'te sivil isim kullanılmaz.
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
- Altyazı yok.
- Tanık sesi editör kararıdır:
  - dikkat çekici söz → videonun başına, TTS'ten önce;
  - tamamlayıcı röportaj → TTS'ten sonra;
  - gerekmiyorsa → kullanılmaz.
  Video Stüdyosu'nda "Kaynak sesli kesitler" adımıyla yapılır (v2.0.0); birden fazla kesit seçilebilir.
- Haberler en fazla 3 gün saklanır (bugün + önceki 2 gün); eskiler otomatik silinir. Liste her gün 02:00'de sıfırlanır.
- Kaydırma: yanları dolgulu dikey çekimde yalnızca yukarı/aşağı; tam 16:9 görüntüde her yön.
- Video alanı hep tam dolu: hiçbir sahnede üst/alt/yan bulanık dolgu yok (editör, Kayseri testi).
- Seslendirmede saat/tarih/ondalık sayı okunuşuyla: "18.00'de" değil "akşam 6'da" (ElevenLabs okuyamıyor).
- Plaka ve reşit olmayanların yüzü bulanıklaştırılır. Blur tamamen elle: editör Tasarım Stüdyosu'nda blur kutusu ekler
  (şekil, boyut, güç, opaklık ayarlanır), videoda sürükleyerek takip ettirir. Otomatik tespit yok (editör kararı).

## Fazlar

Sürüm 3.0.0 (2026-09-25): Faz 0–3 ve 5 tamam, Faz 6'nın temel akışı hazır; Faz 4 bilinçli olarak ertelendi.

| Faz | İçerik | Sonuç |
|---|---|---|
| 0 ✅ | **Yerel çalışma:** tek uygulama (`axion_local.py`), kalıcı proje klasörü, videoyu diskten alma, ikonla konsolsuz başlatma, Tailscale ile uzaktan erişim | Yükleme sorunu biter |
| 1 ✅ | **News Studio:** zaman bilgili TTS (`convert_with_timestamps`), metin değişince sesin geçersiz sayılması, NewsPackage'da ses hash'i | TTS cümleleri zamanlanabilir |
| 2 ✅ | **Video Studio sözleşme geçişi:** `shared/` 2.1 modelleri, enum'lu Luna şeması, uzun shot pencereleri (Windows'ta doğrulandı) | Planner'a güvenilir veri |
| 3 ✅ | **Kaba kurgu:** kural tabanlı TTS ↔ shot eşleştirme + FFmpeg ile şablon video alanı ölçüsünde (960×1226) MP4 | **CapCut'a gerek kalmaz** |
| 4 (ertelendi; ihtiyaç halinde geri dönülecek) | **AI Edit Planner:** TTS segmentleri + shot açıklamaları → tek Luna metin çağrısı → sahne seçimi. Editör kararı: token harcamamak için şimdilik yapılmıyor (3.0'da da yok); günlük kullanımdaki sahne seçimi şikâyetleri önce kurallarla (API'siz, `rough_cut.py`) çözülür. Kurallar yetmezse yapılacak biçim hazır: her haberde otomatik değil, yalnızca editörün Video Stüdyosu'nda bastığı "Sahneleri Luna ile düzenle" düğmesiyle, haber başına tek metin çağrısı (görüntü yok; mevcut analiz açıklamaları kullanılır). | Daha isabetli sahne seçimi |
| 5 ✅ (v2.5–v2.9; Windows doğrulaması bekliyor) | **Tasarım Stüdyosu = sade Canva:** Axion şablonu otomatik (kurguyla birlikte son video hazır); canlı önizleme (tuval, efektler oynar); başlık/yazı stili, sansür, eklenen yazılar, seçilebilir animasyonlar, çerçeve animasyonları, arka plan seçimi, varlık ekleme; **elle blur/mozaik** (şekil, açı, yumuşak kenar, anahtar kare, canlı takip). Ayrıntı: aşağıda ve `shared/axion_template.py` | **Canva'ya gerek kalmaz** |
| 6 (3.0'da temel akış hazır) | **Tabletten tam kullanım:** Axion tablette Tailscale ile açılır; iş bilgisayarda yapılır, tablete yalnızca önizleme ve son video (İndir) gelir. Dükkân başka ilçede, interneti yavaş (45/13 Mbps): büyük dosya tabletten yüklenmez, tablete de indirilmez. DHA videoları Axion'un **🌐 Tarayıcı** sayfasından indirilir (v2.10.0): evdeki bilgisayarda görünmez bir Brave (Axion'un kendi profili; editör Edge kullanmaz), tablete yalnızca ekran görüntüsü gelir, video evin internetiyle İndirilenler'e iner. Giriş bilgileri bir kez kaydedilir (Windows'ta şifreli), sonra kutular kendiliğinden dolar; inen video "🎬 Video Stüdyosu'nda kullan" ile seçili gelir (v3.0.0). Video ve son video arka planda üretilir: tablet kapansa da bilgisayarda sürer (v3.0.0). Uzak masaüstü yalnızca yedek (editör: iki monitör + gizli görev çubuğuyla pratik değil). Paylaş düğmesi ve APK yok (editör: işe yaramıyor). Açık işler: Tarayıcı sayfasının gerçek DHA paneliyle denenmesi, tablet dokunmatiğinde Tasarım Stüdyosu denemesi, aynı haberin iki cihazda açılması uyarısı. | Evde olmadan haber → video |

## Sıradaki işler (editörle konuşuldu, 2026-09-25)

Hedef: DHA'da haberi gördükten sonra tabletten, en az dokunuşla paylaşıma hazır video. Asıl darboğaz otomasyon değil
**kalite kontrolü**: editör başlıkları, paylaşım metnini ve seslendirmeyi her haberde kendisi kontrol eder; amaç bu
kontrolü kaldırmak değil, hızlandırmak.

1. **Windows testi** (`reviews/claude-v3.md` listesi) ve çıkan düzeltmeler: ilk gerçek gün denemesi (4 haber) yapıldı,
   geri bildirimi v3.1.0'da. ✅
2. **Axion çökerse kendini yeniden başlatsın**: bekçi betiği `windows/axion_calistir.ps1` (v3.2.0). ✅
3. **Kalite kontrolünü hızlandırmak** (API'siz, v3.2.0): 🟡 kaynakta yok işaretleri, başlıkların videodaki gibi
   önizlemesi, seslendirmeyi okuyarak dinleme, düzeltme çağrısının farkı, son video dosya adı = başlık, her sayfada
   "✅ … videosu hazır" bildirimi, paylaşım metnini tek dokunuşla kopyalama (v3.1.0). ✅
4. **Ölçüm:** adım süreleri `data/olcumler.jsonl` (v3.2.0). ✅ Birkaç günlük kullanımdan sonra okunup en yavaş adım seçilecek.
5. Tablette Tasarım Stüdyosu ve Tarayıcı denemesi (editör yapacak); aynı haberin iki cihazda açılması uyarısı (v3.2.0 ✅).
   Tarayıcı akıcılığı: doğrudan akış kanalı (v3.2.0), editörün Tailscale üzerinden denemesi bekleniyor.

6. **v3.3.0** (2026-09-25, yapıldı): GPT bulguları, kesitin olay anından başlaması (API'siz), başlık hatasında küçük
   çağrı, önbellek sayacı + haber başına maliyet, Claude 1 saatlik önbellek, Luna'ya 512 px kare + aynı kare eleme.
   Açık: sistem komutunu kısaltmak (editörün kararı; gerçek haberle önce/sonra). Ayrıntı: CHANGELOG, AGENTS.md.

Gerekmeyenler: Windows açılışında otomatik başlatma. (Haber metni: DHA'nın "metni kopyala"sı uzaktan tablete
gelmediği için v3.1.0'da "TXT indir" → Haber Stüdyosu'na aktarma eklendi.)

## Ortam

- Evdeki bilgisayar Windows; güçlü (AMD işlemci ve ekran kartı), 1000 Mbps internet, iş saatlerinde açık kalabilir.
- DHA videoları editör tarafından panelden normal yolla indirilir (evde doğrudan, dışarıda Axion'un Tarayıcı sayfasıyla);
  Video Studio indirilenler klasöründen okur. Otomatik DHA erişimi (kazıma, toplu indirme) hedef değil: editör kendisi
  gezer ve seçer.

## Faz 2 uygulama notları

- media_library.json artık 2.1 ortak sözleşmesiyle yazılıyor.
- edit_project.json artık 2.1 ortak sözleşmesiyle yazılıyor; eski 1.1 dosyalar yeniden kullanılamıyor.
- Browser upload medya kaynakları proje altında saklanıyor; local inbox dosyaları yerinde okunuyor.
- TTS alignment varsa karakter aralıkları doğrulanıyor; yoksa segmentler deterministik noktalama sınırlarından üretiliyor.
- Windows gerçek E2E testinde analiz + EditProject üretimi doğrulandı; 157.28 sn videoda 15 shot, 21.27 sn TTS timeline üretildi.
- v1.7.1: `unknown`/boş sınıflandırma (eşleme hatası) düzeltildi; uzun shot'lar 10 sn'lik pencerelere bölünüyor.

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
