# Axion Local — Windows Kurulum ve Kullanım

Axion Local, Haber Stüdyosu ile Video Studio'yu evdeki bilgisayarda **tek uygulama, tek şifreyle** çalıştırır.
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
   - Not Defteri'nde `secrets.toml` dosyasını açar. Şifreni ve API anahtarlarını tırnak içine yaz, kaydet, kapat:
     ```toml
     APP_PASSWORD = "seçtiğin şifre"
     OPENAI_API_KEY = "sk-..."
     ANTHROPIC_API_KEY = "sk-ant-..."
     ELEVENLABS_API_KEY = "..."
     ```
   - Masaüstüne **Axion Local** kısayolu koyar.

### 1.3 Bilgisayarın uyumasını kapat (tabletten erişim için)

Ayarlar → Sistem → Güç → **Ekran ve uyku** → "Prize takılıyken cihazı uyku moduna geçir": **Hiçbir zaman**.
Ekranın kapanması sorun değil; uyku modu sorun.

## 2. Günlük kullanım

1. Masaüstündeki **Axion Local** kısayoluna çift tıkla. Siyah bir pencere açılır ve tarayıcıda uygulama başlar.
   - Siyah pencereyi **kapatma**; kapatırsan sistem durur. Küçültebilirsin.
   - İlk açılışta Windows Güvenlik Duvarı izin sorarsa **İzin ver** de (tabletten erişim için gerekli).
2. Şifreni gir. Soldaki menüden iki sayfa arasında geçersin: **Haber Stüdyosu** ve **Video Studio**.

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
5. Axion şifresini gir. Tablet sadece ekrandır; işi evdeki bilgisayar yapar.

Tablet bağlanamıyorsa:
- Evdeki bilgisayar açık mı, **Axion Local** penceresi çalışıyor mu?
- Tablette Tailscale "Connected" durumda mı?
- Windows Güvenlik Duvarı izni: Ayarlar → Gizlilik ve güvenlik → Windows Güvenliği → Güvenlik duvarı → "Güvenlik duvarından uygulamaya izin ver" → **python** için Özel ve Genel kutucuklarını işaretle.

## 4. Güncelleme

Yeni bir sürüm çıktığında:
1. Axion Local penceresini kapat.
2. `C:\Axion\windows\guncelle.bat` dosyasına çift tıkla.
3. Axion Local'i yeniden başlat.

## 5. Verilerin yeri

- Haber projeleri (haber paketi ve TTS sesi): `C:\Axion\data\projects\`
- TTS kalibrasyonu ve üretim geçmişi: `C:\Axion\data\`

Bu klasörü ara sıra yedeklemen yeterli.
