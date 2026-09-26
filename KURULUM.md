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

1. **Haber Stüdyosu:** Ham haberi yapıştır (ya da üstteki **📄 İndirilenler'deki haber metni** → DHA'dan indirdiğin TXT →
   **Aktar**) → istersen **Haberi işle**'nin yanındaki kutuya talimat yaz → **Haberi işle** → başlıkları, paylaşım metnini ve seslendirme metnini kontrol et → **Seslendir**.
   - **Talimat** (isteğe bağlı): üslubu ve vurguyu kendi cümlenle söyle ("tepkili anlat", "ailenin sözlerini öne
     çıkar", "yaralı sayısını başlığa koyma"). Başlıklara, paylaşım metnine, seslendirmeye ve yeniden üretimlere
     uygulanır; kuralları (bilgi uydurmama, isim baş harfleri, başlık uzunluğu, süre) değiştirmez. Boş bırakırsan
     objektif, standart haber dili. Her yeni haberde boş gelir.
   Kontrolü hızlandıranlar:
   - **🟡 Kaynakta yok:** çıktıda olup ham haberde geçmeyen sayı ve isimler (yapay zekâ uydurmuş ya da farklı yazmış
     olabilir; "iki" ↔ "2" gibi yazım farkları da çıkabilir).
   - Başlığın altında videodaki satır bölünmesi: **✅ Videoda** (sığıyor), **✅ Videoda (küçültülmüş yazı)** (biraz
     küçülerek sığıyor; istersen kısalt) ya da **⚠️ 2 satıra sığmıyor** (kaç karakter kısaltman gerektiği yazar).
     Yalnız başlık sığmazsa Axion kendiliğinden sadece başlıkları yeniden yazdırır (küçük, ucuz çağrı).
   - **Önbellek** (kenar çubuğunda modelin altında): ilk haberde yapay zekânın kuralları önbelleğe yazılır; süre
     dolmadan gelen haberde bu kısım ~%10 fiyatına gider. **🟢 Önbellek sıcak, ~N dk** tahminidir (Luna 30 dk, Claude
     1 saat; her haberde baştan). Haberin tahmini maliyeti ve önbellekten gelen pay **Geliştirici bilgileri**'nde.
   - **Okuyarak dinle:** ses çalarken söylenen kelime yeşil yanar; bir kelimeye dokununca oradan çalar.
   - **Okunuş sözlüğü** (kenar çubuğunda, kapalı bölüm): spiker bir kelimeyi yanlış okuyorsa her satıra
     `yazılış = okunuş` yaz (ör. `Heimlich = Haymlih`) ve yeniden **Seslendir**. Yalnız sese uygulanır: ekrandaki
     seslendirme metni, paylaşım metni ve videodaki yazılar değişmez. Sözlük hatırlanır; eşleşen kelimeler sesin
     altında "Okunuş sözlüğüyle okundu" diye yazar.
   - **🔁 Düzeltme çağrısı neyi değiştirdi:** ilk sonuç düzeltildiyse silinenler kırmızı, eklenenler yeşil.
2. Sayfanın altında **Kaydet ve Video Stüdyosu'na geç**. Haber, ses ve metin projeye kaydedilir; Video Stüdyosu bu projeyle açılır.
   - Seslendirmede saat, tarih ve ondalık sayılar okunabilir biçime çevrilir ("18.00'de" → "akşam 6'da").
   - Seslendirme metnini ses ürettikten sonra değiştirdiysen önce sesi yeniden üretmen istenir (yanlış ses videoya gitmesin diye).
   - Aynı haberi düzeltip yeniden kaydedersen aynı proje güncellenir; yapılmış video analizi kaybolmaz.
3. **DHA videosunu** her zamanki gibi panelden bilgisayarına indir (İndirilenler klasörüne).
4. **Video Stüdyosu** (ve Tasarım Stüdyosu) açılışta boş gelir: haberi listeden seç. Liste her gün saat 02:00'de
   sıfırlanır; önceki 2 günün haberleri için **Önceki günler**'i işaretle. Haberler **3 gün** saklanır, daha eskileri
   otomatik silinir (İndirilenler'deki DHA videolarına dokunulmaz). Video Stüdyosu adım adım ilerler; biten adım tek satıra daralır (tıklayınca yeniden açılır):
   - **1. Haber:** kaydettiğin haber ve sesi. Başka bir haberi buradan seçebilirsin.
   - **2. Görüntüler:** İndirilenler'deki videolar ve fotoğraflar (JPG, PNG, WEBP) en yeniden eskiye listelenir. Seç →
     **Görüntüleri analiz et**. Fotoğraflar da kurguya girer (yavaş yakınlaşmayla; telefonda yan çekilmişse dik
     çevrilir). Video kopyalanmaz, yerinden okunur. Analiz projeye kaydedilir; tekrar açınca yeniden ücret ödemezsin.
     Klasör, tarayıcıdan yükleme ve analiz yoğunluğu **⚙️ Ayarlar**'da.
   - **3. Kaynak sesli kesitler (isteğe bağlı):** Videodan bir bölümü **kendi sesiyle** seslendirmenin önüne
     (dikkat çekici an) veya arkasına (röportaj) ekler. Analizden önce de yapılabilir.
     **Videoyu izle ve kesit seç** → aralık kendiliğinden olayın olduğu yerden gelir (ani hareket/ses, ör. çarpma anı;
     "📍 Aralık olayın olduğu yerden seçildi"); bulunamazsa videoyu izleyip seç. Kaydırıcıyla başlangıç ve bitişi ayarla
     (dakika:saniye, ör. 01:20; oynatıcı yalnız o aralığı oynatır: her oynatma kesitin başından, sonunda durur,
     aralığın dışına sarılmaz) →
     **Seslendirmeden önce / sonra** → **Kesiti ekle**. Birden fazla kesit ekleyebilirsin (ör. röportajın iki kısmı);
     eklendiği sırayla oynar. Kesit olarak kullanılan görüntü, seslendirme sırasında tekrar gösterilmez.
     İlk açılışta videonun küçük bir önizlemesi hazırlanır (bir kez, birkaç saniye).
     **📝 Konuşmaları yazıya dök:** videodaki konuşma bu bilgisayarda yazıya dökülür (internet ve ücret yok; ilk
     seferde dil modeli bir kez iner, ~1,6 GB). Cümleler zamanlarıyla listelenir: bir cümleye dokun → kesit o cümle
     (video oynarken de); "Önceki/Sonraki cümleyi de ekle" ile uzat. Yanlış duyulan kelime olabilir; kesiti videodan
     dinleyerek seç. Haberde tırnak içinde bir alıntı varsa ve konuşmada bulunursa listenin başında
     **📍 Haberdeki alıntı: 00:54.5–01:01.9 · "…"** düğmesi çıkar: dokununca aralık o cümleler olur (kesit yine
     **➕ Kesiti ekle** ile eklenir). Emin olmadığında düğme çıkmaz.
   - **4. Video:** **Videoyu oluştur** → sahneleri Luna seçer (olay sırasıyla, aynı görüntü tekrarlanmadan, ilk sahne
     kapak; haber başına tek küçük çağrı, ~$0,001). Beğenmezsen **🔀 Sahneleri yeniden seç**: Luna farklı bir
     kurgu yapar. **Videoyu yeniden oluştur** aynı sahnelerle yeniden üretir (yeni çağrı yok).
     Kurguda bir sorun görürsen: sayfanın altındaki **Geliştirici bilgileri** → **📦 Teşhis dosyasını indir**; inen
     dosyayı Claude'a/GPT'ye sohbette gönder (internete kendiliğinden hiçbir şey gitmez). Aynı bölümde:
     **🩺 Durum ve maliyet** (disk, ElevenLabs'ta kalan karakter ve Axion'un bugün/bu ay harcadığı karakter,
     FFmpeg, bugünkü ve bu ayki tahmini maliyet; kalan karakter okunamazsa nedeni yazar, ör. API anahtarında
     "User → Read" izni yoksa ElevenLabs sitesinde anahtarın izinlerinden açılır) ve
     **📝 Düzeltme kaydını indir** (başlık, seslendirme, sahne ve kesit düzeltmelerin; ara sıra geliştiriciye yolla,
     istemi senin düzeltmelerine göre iyileştirsin. Kayıt ücretsizdir, yapay zekâya gönderilmez).
     Canva şablonundaki video alanının ölçüsünde (960×1226) MP4 hazırlanır.
     - Video alanı her sahnede tam dolu kalır; hiçbir yanda bulanık dolgu olmaz. Kadraj haberin ana öznesine
       (araç, konuşan kişi) kayar; özne çok genişse (ör. yandan otobüs) kadraj onun üzerinde yavaşça kayar. Sabit
       kamerada (güvenlik kamerası) kadraj hareketin olduğu yere, yani olayın geçtiği yere gelir.
     - DHA'nın kenarları bulanık dikey çekimlerinde Axion asıl görüntüyü kendisi bulur; bulanık kenar videoya girmez.
     - Sahneler seslendirmedeki duraklamalarda değişir, her sahne 2–5 sn. Video en az 20 sn olur.
     - İlk sahne sosyal medyada videonun kapağı olur: Axion ilk sahneye başlıktaki olayı net gösteren görüntüyü koyar;
       videonun ilk karesinde 1. başlık tam görünür (Reels/Shorts kapağı olarak ilk kare hazırdır).
     - **🎞️ Sahneleri göster ve değiştir:** video hazır olunca her sahnenin küçük karesi görünür. Beğenmediğin sahneye
       dokun → yerine konabilecek görüntüler (fotoğraflar dahil) → **✅ Bunu koy**: yalnız o sahne değişir, video
       yeniden oluşur (ücret yok). ✋ = elle değiştirdiğin sahne; **🔀 Sahneleri yeniden seç** bunları sıfırlar.
     - Ses: seslendirme ve kaynak sesli kesitler aynı dengeye getirilir (kesit spikerin biraz altında), hiçbir yerde ses
       patlamaz (tepe -2 dB); kesitlerin başı/sonu yumuşak.
     - Kurgu bitince Axion şablonu (arka plan, başlıklar, sloganlar, logo) hemen uygulanır: **Son videoyu indir**.
       Yanında **📋 Paylaşım metnini kopyala** (Tasarım Stüdyosu'nda da, İndir'in altında). İnen dosyanın adı haber
       başlığıdır. Video bitince hangi sayfadaysan kısa bir "✅ … videosu hazır" bildirimi çıkar.
     - Aynı haber başka bir cihazda da açıksa (bilgisayar + tablet) üstte uyarı çıkar: ikisinden aynı anda değiştirme.
     - Üretim arka planda, bilgisayarda sürer (geçen süre görünür): sayfadan ayrılabilir, tableti kapatabilirsin;
       dönünce video hazırdır.
     - Haber Stüdyosu'nda başlıkları değiştirip projeyi yeniden kaydedersen Tasarım Stüdyosu da yeni başlıkları alır
       (videoyu yeniden oluştur).
5. **Tasarım Stüdyosu** (4. adımdaki **Tasarım Stüdyosu'nda düzenle** veya sol menü): Canva'nın yerini alır.
   **Videoyu oluştur** dediğinde son video (1080×1920, şablonlu) zaten hazırlanır; bir şey değiştirmeyeceksen
   Video Stüdyosu'ndan **Son videoyu indir** yeterli. Tasarım Stüdyosu Canva gibi düzenlenmiştir:
   - **Sol kenar çubuğu:** son videonun durumu ("hazır ve güncel" / "değişiklikler işlenmedi"), **Yeniden oluştur**,
     **İndir**, iki başlığın metni (Enter ile satırı böl), **🎵 Müzik** ve **Yazı tipi / arka plan ekle**.
   - **🎵 Müzik (altlık):** son videoda sözsüz müzik çalar, video bitene kadar döner. Seslendirme, röportaj ya da
     konuşmalı kesit boyunca "varla yok arası"; konuşmasız kesitlerde ve sessiz kısımda duyulur ama yüksek değil
     (kesitte konuşma olup olmadığını Axion sesten anlar). Varsayılan **Gündem**; **Gerilim** (asayiş,
     son dakika), **Sakin** (insan hikâyesi) ya da **Kapalı** seçilebilir, seçmeden önce dinlenebilir. **Kendi
     müziğini ekle** ile MP3/M4A/WAV/OGG eklersen yalnız bu bilgisayarda kalır (GitHub'a gitmez). Değiştirince
     **Yeniden oluştur**.
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

- **Düzen:** solda (kenar çubuğu) geri/ileri/yenile/⌂, adres çubuğu ve **sekmeler**; ortada sayfa; sağda yazı paneli ve
  **indirilenler**. Tablet dik tutulursa sağ panel sayfanın altına iner.
- **Dokun** = tıkla. **Parmakla sürükle** = sayfayı kaydır (görüntü parmakla hemen kayar, yeni görüntü arkadan gelir).
- **⌂** DHA abone panelini açar (`dhaabone.dha.com.tr/news`); sayfa da açılışta onu açar.
- **Sekmeler:** DHA haberi yeni sekmede açar; soldaki listeden sekmeye dokunarak geçilir, ✕ ile kapatılır.
- **Yazmak için:** önce ekranda kutuya dokun, sonra sağdaki kutuya yaz ve **Yaz**'a bas. ↵ Enter, ⌫ sil, ⇥ sonraki kutu.
- **Giriş bilgileri bir kez kaydedilir:** DHA'ya ilk kez giriş yaparken **Giriş**'e bastığında üstte "girişi kaydedilsin
  mi?" çıkar → **Kaydet**. Sonraki girişlerde kullanıcı adı ve şifre kutuları kendiliğinden dolar ("Giriş bilgileri
  dolduruldu") → yalnızca **Giriş**'e dokun. Dolmazsa sağdaki **🔑 Girişi doldur**. Şifre değişirse yeniden sorar.
  Şifre bilgisayarda Windows hesabına bağlı şifrelenmiş olarak durur, tablete gönderilmez. Kayıtlı girişler kenar
  çubuğunda (**🔑 Kayıtlı girişler** → Sil).
- Oturum bilgisayarda kalır. Bu, Axion'un kendi Brave profilidir: normal Brave'ine, sekmelerine ve kayıtlı şifrelerine
  dokunmaz.
- **İndir**'e bastığında video bilgisayarın **İndirilenler** klasörüne iner; sağda "✅ … bilgisayarda" yazar.
  **🎬 Videoda kullan** seni Video Stüdyosu'na götürür, video 2. adımda seçili gelir.
- **Haber metni:** DHA'nın "metni kopyala" düğmesi evdeki bilgisayarın panosuna kopyalar, tablete gelmez. Onun yerine
  **TXT indir** → sağda **📰 Habere aktar**: metin Haber Stüdyosu'nda ham haber olarak açılır. Haber Stüdyosu'nun
  üstündeki **📄 İndirilenler'deki haber metni** listesinden de seçilebilir.
- Görüntü doğrudan akışla gelir: sayfa değiştikçe saniyede 15–20 kareye kadar, dokunuşlar anında gider. İnternet
  yavaşlarsa kare sayısı düşer ama gecikme birikmez. Video oynatmak için değil, haber bulup indirmek için tasarlandı.
- Brave bulunamazsa sayfa söyler: Brave'i kur ya da `anahtarlar.bat` ile `TARAYICI_YOLU`'na `brave.exe`'nin yolunu yaz.
- 20 dakika kullanılmazsa tarayıcı kendiliğinden kapanır (indirme sürerken kapanmaz); sayfayı açınca yeniden açılır.

### Yedek: bilgisayarın tamamına uzaktan erişim

Tarayıcı sayfasının yetmediği işler için bir **uzak masaüstü** uygulaması kullanılabilir (Tailscale ile, modem ayarı
gerekmez). Windows Pro ise Ayarlar → Sistem → **Uzak Masaüstü** → Aç ve tablete **Windows App** (bilgisayar adresi:
Tailscale'deki `100.x.x.x`); Windows Home ise **Chrome Uzaktan Masaüstü** ya da **RustDesk**.

## 5. Güncelleme

Yeni bir sürüm çıktığında `C:\Axion\windows\guncelle.bat` dosyasına çift tıkla.
Yeni sürüm olduğunu Axion kendisi gösterir: kenar çubuğunun altında **🔴 Güncelleme var** yazar (güncelse
**🟢 Axion güncel**; birkaç dakikada bir kendiliğinden kontrol edilir, tabletten de görünür).
Tabletin ekranı kapansa ya da başka uygulamaya geçsen de Axion'da yazdıkların 3 saat korunur.
Dükkândayken (bilgisayara erişim yokken) **🔴 Güncelleme var**'ın altındaki **⬇️ Güncelle ve yeniden başlat**'a bas:
Axion yeni sürümü indirir, kendini yeniden başlatır; sayfa yarım dakika içinde kendiliğinden geri gelir. Video
oluşturuluyorsa bitmesini bekle. Düğme, Axion masaüstündeki simgeyle açıldıysa görünür.
Yeni sürüm açılamazsa Axion kendiliğinden önceki sürüme döner ve kenar çubuğunda **⚠️ Son güncelleme açılamadı**
yazar; o zaman `data\axion.log`'u Claude'a/GPT'ye gönder. Kenar çubuğundaki satırda sürüm numarası da yazar
(**🟢 Axion güncel · v3.5.0** gibi).
Çalışan Axion'u durdurur ve yeni sürümü indirir. Axion'u kendisi açmaz: bitince masaüstündeki **Axion** simgesiyle aç.

Güncelleme bilgisayardaki kodu repodakinin aynısı yapar (`git pull`): repoda silinen dosyalar bilgisayardan da silinir,
eskinin üstüne yığılmaz. `data\` (projeler, ayarlar, girişler) ve API anahtarları güncellemeden etkilenmez.

Axion bir hatayla çökerse 5 saniye sonra kendiliğinden yeniden başlar (uzaktan çalışırken işe yarar). **Axion'u kapat**
düğmesi ve güncelleme yeniden başlatmaz. 10 dakikada 3 kez çökerse durur; o zaman `data\axion.log`'u Claude'a/GPT'ye gönder
(bir önceki çalışmanın kaydı `data\axion.onceki.log`).

## 6. Sorun giderme

- Axion açılmazsa bir uyarı çıkar ve hata kaydı (`C:\Axion\data\axion.log`) Not Defteri'nde açılır.
  İçeriğini Claude'a veya GPT'ye gönder.
- Hataları canlı görmek için: önce Axion'u kapat, sonra `C:\Axion\windows\sorun_giderme.bat` ile görünür pencerede başlat.

## 7. Verilerin yeri

- Projeler (haber, seslendirme, görüntü analizi, kesitler, kurgu ve video): `C:\Axion\data\projects\` — 3 günden eski projeler otomatik silinir.
- Seslendirme hız ayarı (kalibrasyon), üretim geçmişi ve ayarlar (okunuş sözlüğü dahil): `C:\Axion\data\`
- Adım süreleri (geliştirici için; haber yazımı, seslendirme, analiz, kurgu, son video): `C:\Axion\data\olcumler.jsonl`
- Tarayıcı sayfasının profili (DHA oturumu): `C:\Axion\data\tarayici\`; kayıtlı girişler (şifreli):
  `C:\Axion\data\tarayici_girisler.json`. Silersen DHA'ya yeniden giriş yaparsın.

Bu klasörü ara sıra yedeklemen yeterli.
