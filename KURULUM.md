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
   sıfırlanır; eski haberler için **Önceki günler**'i işaretle. Video Stüdyosu adım adım ilerler; biten adım tek satıra daralır (tıklayınca yeniden açılır):
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
5. **Tasarım Stüdyosu** (4. adımdaki **Tasarım Stüdyosu'na geç** veya sol menü): videoyu ve kopyalamaya hazır başlıklarla
   paylaşım metnini burada bulursun; Canva şablonuna aktar. Bu sayfa ileride Canva'nın yerini alacak.

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

## 4. Bilgisayarın tamamına uzaktan erişim (Firefox, DHA paneli vb.)

Tailscale ile telefondan/tabletten **sadece Axion'u** açarsın. Evdeki bilgisayarın ekranını görüp Firefox'tan DHA paneline
girmek, video indirmek gibi işler için bir **uzak masaüstü** uygulaması gerekir. Önce Windows sürümüne bak:
Ayarlar → Sistem → Hakkında → "Sürüm".

- **Windows Pro ise (önerilen):** Ayarlar → Sistem → **Uzak Masaüstü** → Aç. Telefona/tablete Microsoft'un
  **Windows App** (eski adı Uzak Masaüstü) uygulamasını kur; bilgisayar adresi olarak Tailscale'deki `100.x.x.x` adresini
  yaz, Windows kullanıcı adın ve şifrenle bağlan. Tailscale sayesinde modem ayarı gerekmez, internete açılmaz.
- **Windows Home ise:** **Chrome Uzaktan Masaüstü** (ücretsiz, Google hesabıyla) ya da **RustDesk** (ücretsiz, açık kaynak)
  kullan. İkisinin de telefon/tablet uygulaması var.

Tipik uzaktan akış: uzak masaüstüyle evdeki Firefox'tan DHA videosunu İndirilenler'e indir → Axion'da Video Stüdyosu'ndan seç.

## 5. Güncelleme

Yeni bir sürüm çıktığında `C:\Axion\windows\guncelle.bat` dosyasına çift tıkla.
Çalışan Axion'u durdurur, yeni sürümü indirir ve Axion'u yeniden başlatır.

## 6. Sorun giderme

- Axion açılmazsa bir uyarı çıkar ve hata kaydı (`C:\Axion\data\axion.log`) Not Defteri'nde açılır.
  İçeriğini Claude'a veya GPT'ye gönder.
- Hataları canlı görmek için: önce Axion'u kapat, sonra `C:\Axion\windows\sorun_giderme.bat` ile görünür pencerede başlat.

## 7. Verilerin yeri

- Projeler (haber, seslendirme, görüntü analizi, kesitler, kurgu ve video): `C:\Axion\data\projects\`
- Seslendirme hız ayarı (kalibrasyon) ve üretim geçmişi: `C:\Axion\data\`

Bu klasörü ara sıra yedeklemen yeterli.
