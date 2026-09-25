# Axion Local — Windows Kurulum ve Kullanım

Axion Local; Haber, Video ve Tasarım stüdyolarını evdeki bilgisayarda **tek uygulama** olarak çalıştırır.
Videolar internete yüklenmez, doğrudan diskten okunur; projeler ve ayarlar kalıcıdır.

## 1. Bir kerelik kurulum (yaklaşık 15 dakika)

### 1.1 Git'i kur ve projeyi indir

1. Başlat menüsüne **PowerShell** yaz ve aç.
2. Şu komutu yapıştırıp Enter'a bas (Git'i kurar):
   ```
   winget install -e --id Git.Git
   ```
3. PowerShell'i **kapatıp yeniden aç**, sonra projeyi `C:\Axion` klasörüne indir:
   ```
   git clone https://github.com/djanbaba30-hash/axion-haber-automation.git C:\Axion
   ```
   GitHub giriş penceresi açılırsa kendi hesabınla giriş yap.

### 1.2 Kurulum dosyasını çalıştır

1. Dosya Gezgini'nde `C:\Axion\windows` klasörünü aç.
2. **`kurulum.bat`** dosyasına çift tıkla. Kurulum dosyası şunları yapar:
   - Python ve FFmpeg yoksa kurar. Kurduktan sonra "pencereyi kapat ve tekrar çalıştır" der; öyle yap.
   - Gerekli paketleri kurar.
   - Not Defteri'nde **API anahtarları dosyasını** açar (aşağıda).
   - Masaüstüne **Axion Local** ikonunu koyar.

### 1.3 API anahtarları

Anahtarlar şu dosyada durur: `C:\Axion\.streamlit\secrets.toml`
Kurulum bu dosyayı Not Defteri'nde açar. Anahtarları tırnak içine yapıştır, kaydet, kapat:

```toml
APP_PASSWORD = ""
OPENAI_API_KEY = "sk-..."
ANTHROPIC_API_KEY = "sk-ant-..."
ELEVENLABS_API_KEY = "..."
```

- `APP_PASSWORD` boş kalırsa **şifre sorulmaz**. İstersen bir şifre yazabilirsin; o zaman her cihazda sorulur.
- Anahtarları sonradan değiştirmek için: `C:\Axion\windows\anahtarlar.bat`. Değişiklikten sonra Axion'u kapatıp yeniden aç.

Not: Şifre boşken, evindeki Wi-Fi'a bağlı başka bir cihaz da Axion'u açabilir. Evde başka kullanan yoksa sorun değil.

## 2. Günlük kullanım

1. Masaüstündeki **Axion Local** ikonuna çift tıkla. Siyah pencere açılmaz; birkaç saniye içinde tarayıcında Axion açılır.
   - Axion yalnızca sen ikona tıkladığında çalışır; Windows açılışında kendiliğinden başlamaz.
   - Axion zaten açıksa ikon sadece tarayıcıyı açar.
   - İlk açılışta Windows Güvenlik Duvarı izin sorarsa **İzin ver** de (telefon/tabletten erişim için gerekli).
2. Sol menüden sayfalar arasında geçersin: **Haber Stüdyosu**, **Video Stüdyosu** ve **Tasarım Stüdyosu**. Bir sayfadaki işin öbürüne geçince kaybolmaz.
3. Tarayıcı sekmesini kapatmak Axion'u kapatmaz. İşin bitince sol menünün altındaki **Axion'u kapat** düğmesine bas.
   Bu düğme sadece evdeki bilgisayardan açıldığında görünür; telefondan/tabletten yanlışlıkla kapatamazsın.

### Haberden videoya akış

1. **Haber Stüdyosu:** Ham haberi yapıştır → **Haberi işle** → başlıkları, paylaşım metnini ve seslendirme metnini kontrol et → **Seslendir**.
2. Sayfanın altında **Kaydet ve Video Stüdyosu'na geç**. Haber, ses ve metin projeye kaydedilir; Video Stüdyosu bu projeyle açılır.
   - Seslendirmede saat, tarih ve ondalık sayılar okunabilir biçime çevrilir ("18.00'de" → "akşam 6'da").
   - Seslendirme metnini ses ürettikten sonra değiştirdiysen önce sesi yeniden üretmen istenir (yanlış ses videoya gitmesin diye).
   - Aynı haberi düzeltip yeniden kaydedersen aynı proje güncellenir; yapılmış video analizi kaybolmaz.
3. **DHA videosunu** her zamanki gibi panelden bilgisayarına indir (İndirilenler klasörüne).
4. **Video Stüdyosu** (ve Tasarım Stüdyosu) açılışta boş gelir: haberi listeden seç. Liste her gün saat 02:00'de
   sıfırlanır; önceki 2 günün haberleri için **Önceki günler**'i işaretle. Haberler **3 gün** saklanır, daha eskileri
   otomatik silinir (İndirilenler'deki DHA videolarına dokunulmaz). Video Stüdyosu adım adım ilerler; biten adım tek satıra daralır (tıklayınca yeniden açılır):
   - **1. Haber:** kaydettiğin haber ve sesi. Başka bir haberi buradan seçebilirsin.
   - **2. Görüntüler:** İndirilenler'deki videolar en yeniden eskiye listelenir. Videoyu seç → **Görüntüleri analiz et**.
     Video kopyalanmaz, yerinden okunur. Analiz projeye kaydedilir; tekrar açınca yeniden ücret ödemezsin.
     Klasör, tarayıcıdan yükleme ve analiz yoğunluğu **⚙️ Ayarlar**'da.
   - **3. Kaynak sesli kesitler (isteğe bağlı):** Videodan bir bölümü **kendi sesiyle** seslendirmenin önüne
     (dikkat çekici an) veya arkasına (röportaj) ekler. Analizden önce de yapılabilir.
     **Videoyu izle ve kesit seç** → kaydırıcıyla başlangıç ve bitişi ayarla (oynatıcı o aralığı oynatır) →
     **Seslendirmeden önce / sonra** → **Kesiti ekle**. Birden fazla kesit ekleyebilirsin (ör. röportajın iki kısmı);
     eklendiği sırayla oynar. Kesit olarak kullanılan görüntü, seslendirme sırasında tekrar gösterilmez.
     İlk açılışta videonun küçük bir önizlemesi hazırlanır (bir kez, birkaç saniye).
   - **4. Video:** Axion sahneleri seslendirmeye göre kendisi seçer (ek ücret yok) → **Videoyu oluştur**.
     Canva şablonundaki video alanının ölçüsünde (960×1226) MP4 hazırlanır.
     - Video alanı her sahnede tam dolu kalır; hiçbir yanda bulanık dolgu olmaz. Kadraj haberin ana öznesine
       (araç, konuşan kişi) kayar; özne çok genişse (ör. yandan otobüs) kadraj onun üzerinde yavaşça kayar.
     - DHA'nın kenarları bulanık dikey çekimlerinde Axion asıl görüntüyü kendisi bulur; bulanık kenar videoya girmez.
     - Sahneler seslendirmedeki duraklamalarda değişir, her sahne 2–5 sn. Video en az 20 sn olur.
     - Kurgu bitince Axion şablonu (arka plan, başlıklar, sloganlar, logo) hemen uygulanır: **Son videoyu indir**.
5. **Tasarım Stüdyosu** (4. adımdaki **Tasarım Stüdyosu'nda düzenle** veya sol menü): Canva'nın yerini alır.
   **Videoyu oluştur** dediğinde son video (1080×1920, şablonlu) zaten hazırlanır; bir şey değiştirmeyeceksen
   Video Stüdyosu'ndan **Son videoyu indir** yeterli. Tasarım Stüdyosu Canva gibi düzenlenmiştir:
   - **Sol kenar çubuğu:** son videonun durumu ("hazır ve güncel" / "değişiklikler işlenmedi"), **Yeniden oluştur**,
     **İndir**, iki başlığın metni (Enter ile satırı böl) ve **Yazı tipi / arka plan ekle**.
   - **Ortada video:** son hâli oynar (animasyonlar, çerçeve, blur dahil). Bir öğeye (başlık, yazı, logo, blur) dokun.
   - **Üst çubuk (seçili yazı için):** yazı tipi, kalınlık, − boyut +, renk, **S̶ sansür** (bas, sonra videoda
     kelimeye dokun: üstü çizilir; tekrar dokununca kalkar), **aA** büyük harf, ✨ parıltı. İki başlığın stili ortaktır.
   - **Sol panel:** seçili yazının **animasyonu** (Girişte / Çıkışta: Birleşerek, Belirerek, Alttan kayarak, Daktilo,
     Büyüyerek, Yok); eklediğin yazının metni ve zamanı; blur seçiliyse geniş blur ayarları.
   - **Sağ panel:** arka plan (Günün = her gün 02:00'de sıradaki), video çerçevesi (sabit, kovalayan ışıklar, nefes alan
     parıltı, renk akışı, yok), renkler ve hız, sloganlar ve logo (efekt seç veya kapat).
   - **Altta zaman çizelgesi:** Başlık, Yazı, Logo, Blur, Video ve Arka plan izleri. Tıklayıp sar; klibe dokunup seç;
     eklediğin yazı ve blur kliplerini sürükleyerek kaydır, kenarından tutup uzat/kısalt. **➕ Yazı**, **◍ Blur**,
     **▦ Mozaik** buradan eklenir.
   - **Blur / mozaik (plaka, yüz):** efekt (bulanık/mozaik), şekil (dikdörtgen/kare, yuvarlak köşeli, elips/daire),
     güç, opaklık, **yumuşak kenar**, **açı**. Kutuyu sürükle; sağ alt yuvarlakla boyutlandır, üstteki yuvarlakla döndür
     (**1:1** kare yapar). Plaka hareket ediyorsa başka bir ana geç ve kutuyu yeniden taşı/döndür: her değişiklik o anda
     bir anahtar kare olur (◆), kutu aralarda kendiliğinden kayar. **Canlı takip** açıkken kutuya basılı tut: video
     yavaş oynar, sen plakayı takip ettikçe yol kaydedilir.
   - **🎬 Son video** (üst çubukta) oluşturulmuş MP4'ü oynatır. Her değişiklik projeye kendiliğinden kaydedilir
     (üst çubukta "✓ Kaydedildi"). **↶ ↷** ile geri al / yinele.
   - **Yeniden oluştur** arka planda çalışır: kenar çubuğunda geçen süre görünür, bu sırada düzenlemeye devam edebilirsin.
     Bu arada bir şey değiştirirsen **🔁 Değişikliklerle yeniden başlat** çıkar: eski üretim durur, yenisi başlar.
     Üst çubuktaki etiket son videonun durumunu söyler: "✓ Son video hazır", "⚠ Son videoya işlenmedi", "⏳ oluşturuluyor".
     Bitince kenar çubuğunda ne kadar sürdüğü ve kodlayıcı yazar (ör. "Son oluşturma 9 sn · AMD donanım").
   - Son video bitince kendiliğinden kontrol edilir (1080x1920, süre, ses). AMD kodlayıcı bozuk video üretirse
     Axion işlemciyle (x264) yeniden dener.
   - **Kısayollar** (üst çubukta ⌨): Boşluk oynat/durdur · ← → bir kare (Shift ile 1 sn) · Ctrl+Z / Ctrl+Y geri al /
     yinele · Ctrl+D seçiliyi çoğalt · Delete sil · Esc seçimi bırak · S sansür · K blura anahtar kare · L döngü.
     Zaman çizelgesinde kliplerin kenarları oynatma çizgisine ve diğer kliplere yapışır; klibe çift tıklayınca başına gider.

Videolar başka bir klasördeyse Video Stüdyosu'nda **⚙️ Ayarlar**'daki klasör kutusuna o klasörün yolunu yazman yeterli.
Telefondan/tabletten çalışırken dosyayı **Tarayıcıdan yükle** seçeneğiyle de gönderebilirsin.

## 3. Telefon veya tabletten Axion'a erişim (Tailscale)

Tailscale, bilgisayarınla telefon/tabletin arasında sadece senin cihazlarının gördüğü özel bir bağlantı kurar.
Ücretsizdir; Axion internete açılmaz.

1. Evdeki bilgisayara **Tailscale**'i kur: https://tailscale.com/download → Google hesabınla giriş yap.
2. Telefona/tablete Tailscale uygulamasını kur (App Store / Google Play) ve **aynı hesapla** giriş yap.
3. Tailscale uygulamasında evdeki bilgisayarın adını ve `100.` ile başlayan adresini görürsün.
4. Telefon/tabletin tarayıcısında şunu aç: `http://BILGISAYAR-ADI:8501` (olmazsa `http://100.x.x.x:8501`).

Bağlanamıyorsan:
- Evdeki bilgisayar açık mı, uyku modunda değil mi, Axion çalışıyor mu? (Evden çıkmadan ikona tıklayıp açık bırak.)
- Telefonda/tablette Tailscale "Connected" durumda mı?
- Windows Güvenlik Duvarı: Ayarlar → Gizlilik ve güvenlik → Windows Güvenliği → Güvenlik duvarı →
  "Güvenlik duvarından uygulamaya izin ver" → **python** için Özel ve Genel kutucuklarını işaretle.

Uzaktan kullanacaksan bilgisayarın uyumasını kapat: Ayarlar → Sistem → Güç → **Ekran ve uyku** →
"Prize takılıyken cihazı uyku moduna geçir": **Hiçbir zaman**.

### Tabletten çalışırken videolar nerede durur?

Tabletin tarayıcısında açtığın Axion aslında evdeki bilgisayarda çalışır; tabletteki dosyalara erişemez, tablet de
bilgisayardaki dosyaları görmez. Bu yüzden büyük DHA videolarını tablete indirip yüklemek gerekmez, önerilmez de
(dükkân internetinden iki kez geçer):
- DHA videosunu Axion'un **🌐 Tarayıcı** sayfasından indir (aşağıda); video evin internetiyle doğrudan bilgisayara iner.
- Axion'da her şey (analiz, kurgu, tasarım) bilgisayarda yapılır; tablete yalnızca küçük önizlemeler gelir.
- Bitince **İndir** ile son videoyu (~10–20 MB) tablete al ve paylaş.

## 4. Tabletten DHA'ya girip video indirme (🌐 Tarayıcı)

Axion'un menüsündeki **🌐 Tarayıcı** sayfası, evdeki bilgisayarda görünmeden çalışan bir **Brave** penceresini tablete
getirir. Bilgisayarın ekranına, iki monitöre ya da görev çubuğuna dokunmaz; uzak masaüstü gerekmez.

- **Dokun** = tıkla. **Parmakla sürükle** = sayfayı kaydır. Üstte ◀ ▶ ⟳ ⌂ ve adres çubuğu.
- **Yazmak için:** önce ekranda kutuya dokun, sonra alttaki metin kutusuna yaz ve **Yaz**'a bas. ↵ Enter, ⌫ sil, ⇥ sonraki
  kutu. İstersen DHA şifreni `windows\anahtarlar.bat` ile `DHA_SIFRE`'ye yaz: **🔑 Şifre** düğmesi onu seçili kutuya yazar.
- **Ana sayfa (⌂):** kenar çubuğundan DHA panelinin adresini bir kez yaz; hatırlanır.
- DHA'ya bu tarayıcıda **bir kez** giriş yap; oturum bilgisayarda kalır (arada bir yeniden şifre isteyebilir). Bu, Axion'un
  kendi Brave profilidir: normal Brave'ine, sekmelerine ve kayıtlı şifrelerine dokunmaz.
- **İndir**'e bastığında video bilgisayarın **İndirilenler** klasörüne iner; sayfanın altında "✅ … bilgisayara indi" yazar.
  Sonra **🎬 Video Stüdyosu'na geç** → video listede.
- Dükkân internetinden yalnızca sayfanın görüntüsü geçer (saniyede birkaç küçük resim). Video oynatmak için değil, haber
  bulup indirmek için tasarlandı.
- Brave bulunamazsa sayfa söyler: Brave'i kur ya da `anahtarlar.bat` ile `TARAYICI_YOLU`'na `brave.exe`'nin yolunu yaz.
- 20 dakika kullanılmazsa tarayıcı kendiliğinden kapanır (indirme sürerken kapanmaz); sayfayı açınca yeniden açılır.

### Yedek: bilgisayarın tamamına uzaktan erişim

Tarayıcı sayfasının yetmediği işler için bir **uzak masaüstü** uygulaması kullanılabilir (Tailscale ile, modem ayarı
gerekmez). Windows Pro ise Ayarlar → Sistem → **Uzak Masaüstü** → Aç ve tablete **Windows App** (bilgisayar adresi:
Tailscale'deki `100.x.x.x`); Windows Home ise **Chrome Uzaktan Masaüstü** ya da **RustDesk**.

## 5. Güncelleme

Yeni bir sürüm çıktığında `C:\Axion\windows\guncelle.bat` dosyasına çift tıkla.
Çalışan Axion'u durdurur, yeni sürümü indirir ve Axion'u yeniden başlatır.

## 6. Sorun giderme

- Axion açılmazsa bir uyarı çıkar ve hata kaydı (`C:\Axion\data\axion.log`) Not Defteri'nde açılır.
  İçeriğini Claude'a veya GPT'ye gönder.
- Hataları canlı görmek için: önce Axion'u kapat, sonra `C:\Axion\windows\sorun_giderme.bat` ile görünür pencerede başlat.

## 7. Verilerin yeri

- Projeler (haber, seslendirme, görüntü analizi, kesitler, kurgu ve video): `C:\Axion\data\projects\` — 3 günden eski projeler otomatik silinir.
- Seslendirme hız ayarı (kalibrasyon) ve üretim geçmişi: `C:\Axion\data\`

Bu klasörü ara sıra yedeklemen yeterli.
