# Axion Local — Windows Kurulum ve Kullanım

Axion Local, Haber Stüdyosu ile Video Studio'yu evdeki bilgisayarda tek uygulama olarak çalıştırır.
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
   - Axion'u Windows açılışına ekler; bilgisayar açıldığında arka planda kendiliğinden başlar.

### 1.3 API anahtarları

Anahtarlar şu dosyada durur: `C:\Axion\.streamlit\secrets.toml`
Kurulum bu dosyayı Not Defteri'nde açar. Anahtarları tırnak içine yapıştır, kaydet, kapat:

```toml
APP_PASSWORD = ""
OPENAI_API_KEY = "sk-..."
ANTHROPIC_API_KEY = "sk-ant-..."
ELEVENLABS_API_KEY = "..."
```

- `APP_PASSWORD` boş kalırsa **şifre sorulmaz**. İstersen bir şifre yazabilirsin; o zaman hem bilgisayarda hem tablette sorulur.
- Anahtarları sonradan değiştirmek için: `C:\Axion\windows\anahtarlar.bat`. Değişiklikten sonra Axion'u kapatıp yeniden aç.

Not: Şifre boşken, evindeki Wi-Fi'a bağlı başka bir cihaz da `http://BILGISAYAR-ADI:8501` adresinden Axion'u açabilir. Evde başka kullanıcı yoksa sorun değil; varsa bir şifre belirle.

### 1.4 Bilgisayarın uyumasını kapat (tabletten erişim için)

Ayarlar → Sistem → Güç → **Ekran ve uyku** → "Prize takılıyken cihazı uyku moduna geçir": **Hiçbir zaman**.
Ekranın kapanması sorun değil; uyku modu sorun.

## 2. Günlük kullanım

1. Masaüstündeki **Axion Local** ikonuna çift tıkla. Siyah pencere açılmaz; birkaç saniye içinde tarayıcıda Axion açılır.
   - Axion zaten arka planda çalışıyorsa ikon sadece tarayıcıyı açar.
   - İlk açılışta Windows Güvenlik Duvarı izin sorarsa **İzin ver** de (tabletten erişim için gerekli).
2. Soldaki menüden iki sayfa arasında geçersin: **Haber Stüdyosu** ve **Video Studio**. Bir sayfadaki işin öbürüne geçince kaybolmaz.
3. Tarayıcı sekmesini kapatmak Axion'u kapatmaz; arka planda çalışmaya devam eder. Tamamen kapatmak istersen sol menünün altındaki **Axion'u kapat** düğmesini kullan. Bu düğme sadece evdeki bilgisayardan açıldığında görünür; tabletten yanlışlıkla kapatamazsın.

### Haberden videoya akış

1. **Haber Stüdyosu:** Ham haberi yapıştır → **Haberi İşle** → başlık/caption/TTS'i kontrol et ve düzelt → **Seslendir**.
2. Aynı sayfanın altında **Projeye kaydet (Video Studio'da kullan)** düğmesine bas.
   - TTS metnini ses ürettikten sonra değiştirdiysen sistem kaydetmeye izin vermez; önce sesi yeniden üret. Bu, yanlış sesin videoya gitmesini önler.
3. **DHA videosunu** her zamanki gibi panelden bilgisayarına indir (İndirilenler klasörüne).
4. **Video Studio:** "Bilgisayardaki klasör" seçili gelir; İndirilenler'deki videolar en yeniden eskiye listelenir. Videoyu seç → **Medyaları hazırla**. Video kopyalanmaz, yerinden okunur; büyük dosyalar sorun değil.
5. "Axion Haber bağlantısı" bölümünde kaydettiğin haberi seç → **Projeyi yükle**. Haber metni ve TTS sesi otomatik gelir; JSON/MP3 indirip yükleme yok.
6. **Projeyi hazırla.**

Videolar başka bir klasördeyse Video Studio'daki klasör kutusuna o klasörün yolunu yazman yeterli.

## 3. İş yerindeki tabletten erişim (Tailscale)

Tailscale, bilgisayarınla tabletin arasında sadece senin cihazlarının gördüğü özel bir bağlantı kurar. Ücretsizdir; uygulama internete açılmaz.

1. Evdeki bilgisayara **Tailscale**'i kur: https://tailscale.com/download → Google hesabınla giriş yap.
2. Tablete de Tailscale uygulamasını kur (App Store / Google Play) ve **aynı hesapla** giriş yap.
3. Tailscale uygulamasında evdeki bilgisayarın adını ve `100.` ile başlayan adresini görürsün.
4. Tabletin tarayıcısında şunu aç: `http://BILGISAYAR-ADI:8501` (olmazsa `http://100.x.x.x:8501`).
5. Tablet sadece ekrandır; işi evdeki bilgisayar yapar.

Tablet bağlanamıyorsa:
- Evdeki bilgisayar açık mı? Bilgisayar yeniden başladıysa oturum açılmış olmalı; Axion oturum açılınca kendiliğinden başlar.
- Tablette Tailscale "Connected" durumda mı?
- Windows Güvenlik Duvarı izni: Ayarlar → Gizlilik ve güvenlik → Windows Güvenliği → Güvenlik duvarı → "Güvenlik duvarından uygulamaya izin ver" → **python** için Özel ve Genel kutucuklarını işaretle.

## 4. Güncelleme

Yeni bir sürüm çıktığında `C:\Axion\windows\guncelle.bat` dosyasına çift tıkla.
Çalışan Axion'u durdurur, yeni sürümü indirir ve Axion'u yeniden başlatır.

## 5. Sorun giderme

- Axion açılmazsa bir uyarı çıkar ve hata kaydı (`C:\Axion\data\axion.log`) Not Defteri'nde açılır. İçeriğini Claude'a gönder.
- Hataları canlı görmek için: önce Axion'u kapat, sonra `C:\Axion\windows\sorun_giderme.bat` ile görünür pencerede başlat.
- Axion'un Windows açılışında başlamasını istemiyorsan: Windows+R → `shell:startup` → "Axion Local" kısayolunu sil.

## 6. Verilerin yeri

- Haber projeleri (haber paketi ve TTS sesi): `C:\Axion\data\projects\`
- TTS kalibrasyonu ve üretim geçmişi: `C:\Axion\data\`

Bu klasörü ara sıra yedeklemen yeterli.
