# v4.0.0-alpha.7.4 — GPT incelemesinin düzeltmeleri — 2026-09-26

GPT'nin v4.0.0 öncesi incelemesi (`reviews/gpt-v4.md`) ve Claude'un yanıtı (`reviews/claude-v4.md`: her bulgu
ölçümle doğrulandı, kararlar ve nedenleri).

## Fixed
- **Telefon fotoğrafı videoda yan çıkıyordu (editörün bilgisayarında):** yeni FFmpeg (winget'in kurduğu sürüm),
  EXIF yönünü çıktı videoya "−90° döndür" etiketi olarak yazıyordu; fotoğraf zaten dik çevrildiği için oynatıcı bir
  kez daha çeviriyordu. Etiket silinir. Sandbox'ta en yeni FFmpeg ile yeniden üretildi; düzeltmeden sonra tüm testler
  hem FFmpeg 6.1 hem en yeni sürümle geçiyor.
- Aynı haber iki cihazda açıkken "Konuşmaları yazıya dök" aynı anda basılırsa tek iş çalışır.
- Yazıya döküm, aynı adlı ve aynı boyutlu videonun aynı saniye içinde değişmesini de fark eder (eski dökümler bir kez
  yeniden yapılır).
- Windows'ta kalan 4 test (Türkçe karakter kodlaması, satır sonu, fotoğraf yönü) ve bir test uyarısı; gürültü testleri
  sabit tohumlu (rastgele gürültü 60'ta 1 konuşma sanılıyordu).

## Changed
- Görüntü analizinde hareket bölgesi tek geçişte ölçülür (255 sn'lik videoda 7,3 sn → 3,0 sn).

# v4.0.0-alpha.7.3 — Yazıya dökümde cümleler büyük harften, kesit sesin bittiği yerde — 2026-09-26

Editörün alpha.7.2 denemesi (Artvin; teşhis dosyası, düzeltme kaydı, son video): kadraj doğru ("bu sefer framing'i
doğru yapmış"); dökümde "yanıma" parçası "doğru koştu" olmadan bitiyordu, bölme yerleri yanlıştı ("Ben de durumu
hemen" | "fark ettim Beyefendiye").

## Fixed
- **Cümle bölme:** Whisper nokta koymasa da cümle başını büyük harfle yazıyor ("…fark ettim Beyefendiye daha…").
  Büyük harfle başlayan kelime yeni cümle başlatır (haberdeki özel adlar hariç: "Heimlich" bölmez); tek kelimelik ya
  da 1 sn'den kısa cümle ("Uğurladık") öncekine katılır; 8 sn'den uzun kalan parça önce çekimli fiilden sonra
  ("koştu", "ettim", "uyguladım") bölünür. Artvin'de parçalar editörün elle seçtiği yerlere denk geliyor: "Ben de durumu
  hemen fark ettim" · "Beyefendiye daha öncesinden eğitimini almış olduğum Heimlich manevrasını uyguladım" (regresyon
  testi ekran görüntüsündeki dökümle).
- **"yanıma doğru koştu" kesiliyordu:** Whisper son iki kelimeyi yazmadı, parça 53,7'de bitti; ses 54,1'e kadar
  sürüyor (sandbox'ta videonun sesinden ölçüldü). Artık parçanın sonu sesle düzeltilir: son kelimeden sonra ses
  sürüyorsa kesit sesin sustuğu yere kadar uzar (en fazla 1,5 sn, sonraki kelimeyi geçmez; hece arası 0,15 sn'lik
  düşüşler susma sayılmaz). Artvin'in gerçek sesiyle: 53,91 yerine 54,37. Eksik kelimeler yazıda yine görünmez
  (Whisper'ın hatası; bu ortamdan model indirilemediği için nedeni ölçülemedi).
- Özel adlar artık modele ipucu (`hotwords`) olarak gitmiyor: alpha.7.1'de "Hemlik"i düzeltmemişti, yazımı alpha.7.2'den
  beri dökümden sonra düzeltiliyor. İpucunun kelime atlamaya etkisi olup olmadığı ölçülemedi; model ipucusuz çalışır.
- Teşhis dosyasına yazıya dökümler de girer (`yazi/*.json`; Whisper'ın ham bölümleri `bolumler` ile): bir dahaki
  sorunda Whisper'ın neyi duyduğu görülür. Eski dökümler bir kez yeniden yapılır (döküm biçimi v4).

# v4.0.0-alpha.7.2 — Kısa cümleler, özel adlar, cümleden kesit seçimi, güvenlik kamerasında kadraj — 2026-09-26

Editörün alpha.7.1 denemesi (Artvin, teşhis dosyasıyla): ilk cümle doğru yerden başlıyor, kesitler kelime ortasında
bitmiyor. Bulduğu sorunlar bu sürümde.

## Fixed
- **"Parça parça değil, upuzun cümleler":** Whisper konuşma dilinde çoğu zaman nokta koymuyor; röportaj iki 14 sn'lik
  cümle olmuştu. 7 sn'den uzun parça en uzun nefes arasından bölünür (virgülden sonraki ara öne alınır), parçalar en
  az 1,5 sn. Eski dökümler bir kez yeniden yapılır (döküm biçimi v3).
- **"Heimlich doğru yazılmamış"** ("Hemlik"; modele ipucu yetmedi): dökümdeki kelime, haberin metnindeki bir özel ada
  okunuşça çok benziyorsa (yabancı yazım Türkçe okunuşla karşılaştırılır: "ch" → "k") haberdeki yazımla değişir; ek
  korunur ("Hemlik'in" → "Heimlich'in"). Adın eki ("Artvinli") ve adın başı olan kelime ("yılma" ↔ "Yılmaz")
  değişmez. API yok.
- **"Video oynarken başka kesit seçemiyorum":** ikinci dokunuş "iki cümlenin arası" demekti; iki cümlelik dökümde öteki
  cümleye dokunmak hep ikisini birden seçiyordu. Artık **cümleye dokunmak yalnız o cümleyi seçer** (oynarken de: video
  durur, yeni kesitin başına gider); aralığı uzatmak için "⬅️ Önceki cümleyi de ekle" / "Sonraki cümleyi de ekle ➡️".
  Kaydırıcıdaki aralığın içindeki cümleler vurgulu. Tarayıcıda (dokunmatik) oynarken 5 kez cümle değiştirilerek
  denendi. Günlükteki "kesit_range … Session State API" uyarısı da giderildi (kaydırıcı cümle seçilince yeni anahtarla
  kurulur).
- **"Heimlich anında şahıslar kenarda kalmış":** Luna'nın özne kutusu tek kareden (güvenlik kamerasında vitrini ve
  masaları gösteriyordu, x 0,25–0,55); olay karenin 0,41–0,87'sindeydi, kadraj 0,18–0,62 → kişiler sağ kenarda.
  Görüntü analizi artık sabit kamerada **hareketin olduğu bölgeyi** ölçer (`framing.motion_region`, proxy'den pencere
  başına, API yok; elde çekimde ve hiçbir şey kıpırdamıyorsa ölçülmez); hareket alana sığıyorsa kadraj onun ortasına
  (Artvin: 0,42–0,86, kişiler ortada). Hareket alandan genişse (röportajda el kol) Luna'nın kutusu kalır. Yalnız yeni
  analizlerde: eski haberde "Görüntüleri yeniden analiz et".

# v4.0.0-alpha.7.1 — Yazıya dökme ve kesit oynatıcısı düzeltmeleri — 2026-09-26

Editörün Artvin denemesi (teşhis dosyasıyla): "kelimeleri bazı ufak hatalar dışında doğru tanıdı"; 71 sn'lik video
bilgisayarında yazıya döküldü. Bulduğu sorunlar bu sürümde.

## Fixed
- **İlk cümle videonun başından başlıyordu** (00:19,9; konuşma aslında ~42. sn'de) ve **kesit sonraki kelimenin
  ortasında bitiyordu**: cümle sınırları Whisper'ın kaba bölüm zamanlarından geliyordu. Artık kelime zamanlarından
  (`word_timestamps`): cümle ilk kelimeden 0,1 sn önce başlar, son kelimeden 0,25 sn sonra biter ama sonraki kelimeye
  taşmaz (0,08 sn önce kesilir). Cümleler nokta/soru/ünlemde, 1,2 sn'lik sessizlikte ya da 15 sn'de bölünür.
- **"Altyazı M.K." (01:10–01:40, video 01:10'da bitiyor):** Whisper'ın sessizlikte uydurduğu altyazı kalıbı. Videonun
  sonundan sonrası ve bilinen kalıplar ("altyazı", "abone ol", "izlediğiniz için") atılır.
- **Özel adlar:** haberin metnindeki özel adlar (ör. "Muzaffer Yazıcı Heimlich Hopa") modele ipucu olarak gider
  ("Heimlich" "hemlik" yazılıyordu). Cümle başındaki büyük harfli kelimeler ipucu sayılmaz. Eski dökümler bir kez
  yeniden yapılır (döküm biçimi v2).
- **Kesit oynatıcısı** (editör: "kesit seçtiğimde ne olursa olsun videoda yalnız o kesit oynasın"; yeni
  `video_studio/range_player.py`, `st.video(start_time, end_time)` yerine): yalnız seçili aralık oynar; her oynatma
  kesitin başından başlar (durdurup aralık içinde elle sarınca oradan sürer), sonunda durup başa döner, aralığın dışına
  sarılamaz; kaydırıcı ya da cümle değişince video durur ve yeni aralığın başına gider. Altında "Kesit: 00:58,0 –
  01:01,9 (3,9 sn)". Tarayıcıda denendi (oynatıp bitişte durma, dışarı sarma, durdur-oynat, oynarken aralık değişimi).
- **"🎞️ Sahneleri göster ve değiştir" tablette açılmıyordu:** küçük anahtar yerine tam genişlikte düğme ("🎞️ Sahneleri
  gizle" ile kapanır). Sandbox'ta dokunmatik tarayıcıda anahtar açılıyordu; asıl neden bulunamadı, düğme tablette
  güvenilir (cümle düğmeleri editörün tabletinde çalışıyor).

# v4.0.0-alpha.7 — Yerel yazıya dökme: kesit cümleden seçilir — 2026-09-26

4.0'ın son parçası. Editörün Artvin haberi (DHA 1524777.mp4, 70 sn: güvenlik kamerası + restoran sesi + röportaj) ve
DHA metniyle hazırlandı.

## Added
- **📝 Konuşmaları yazıya dök** (Video Stüdyosu → 3. Kaynak sesli kesitler; `video_studio/modules/transcribe.py`):
  videodaki konuşma bu bilgisayarda yazıya dökülür — API yok, token yok. Motor faster-whisper (Whisper large-v3-turbo,
  işlemcide int8, Türkçe sabit, sessiz yerler atlanır). Arka planda sürer (yüzde ve süre görünür, tablet kapansa da
  biter); sonuç projede saklanır, aynı video yeniden dökülmez. Cümleler zamanlarıyla listelenir: **cümleye dokun →
  kesit aralığı o cümle; ikinci cümleye dokun → iki cümlenin arası** (sonra her zamanki gibi önce/sonra → Kesiti ekle).
  İleride altyazının temeli (altyazı şu an ürün kararı gereği yok).
- Model ilk kullanımda bir kez iner (~1,6 GB, `data/modeller`, silinmez); sonra internetsiz çalışır. `faster-whisper`
  requirements'a eklendi (güncellemede bekçi kurar). Paket yalnız kullanılırken yüklenir: kurulamazsa Axion yine açılır,
  bu düğme yerine "kurulu değil" yazar.

## Notes
- **Türkçe doğruluk ve hız bu ortamda ölçülemedi:** modeller HuggingFace'ten iner, bu çalışma ortamında erişim kapalı.
  Editörün bilgisayarında ilk denemede ölçülür (Artvin videosu: röportajdaki "…eğitimini almış olduğum Heimlich
  manevrasını uyguladım…" cümleleri DHA metniyle karşılaştırılır; süre ekranda yazar). Yavaş kalırsa `transcribe.MODEL`
  daha küçük modele ("small") çekilir.
- Denenenler: sahte modelle tüm akış (testli); faster-whisper'ın DHA videosundan sesi okuması (70,6 sn, 0,2 sn) ve kendi
  konuşma bulucusu (konuşma 27,5–70,6 sn: restoran içi konuşma + röportaj; yalnız bu kısım modele gider).
- alpha.4.1'in konuşma tespiti bu gerçek DHA videosunda doğru: 0–18 sn sessiz, 18–36 sn restoran uğultusu "konuşma
  değil", 36–70 sn röportaj "konuşma".

# v4.0.0-alpha.6 — Durum paneli ve günlük/aylık maliyet — 2026-09-26

## Added
- **🩺 Durum ve maliyet** (Haber ve Video Stüdyosu → Geliştirici bilgileri; `apps/axion_local/status.py`):
  - **Disk:** veri klasörünün diskindeki boş alan (10 GB altında ⚠️) ve projelerin kapladığı yer.
  - **ElevenLabs:** kalan karakter / aylık sınır ve yenilenme günü (%10'un altında ⚠️). Abonelik sorgusu ücretsizdir
    (karakter harcamaz), 10 dakikada bir, arka planda yapılır: sayfa hiç beklemez, sonuç bir sonraki çizimde görünür;
    ulaşılamazsa "okunamadı" yazar.
  - **FFmpeg:** sürüm, AMD donanım kodlayıcısı var mı, FFprobe.
  - **Bugün / Bu ay:** tahmini toplam yapay zekâ maliyeti, çağrı sayısı, ElevenLabs karakteri ve türlere göre döküm.
- **Maliyet defteri** (`apps/axion_local/ledger.py` → `data/maliyet.jsonl`; projeler 3 günde silinse de silinmez, çağrı
  başına ~100 bayt): haber metni (düzeltme çağrısı dahil), başlık yenileme, seslendirme metni yenileme, görüntü
  analizi, sahne seçimi (yalnız yeni Luna çağrısı; kayıtlı plan ve kurallar ücretsiz) ve ses üretimi (karakter).
  Maliyetler kullanım sayılarından tahmindir (fiyat tablosu `news_studio/ai/cost.py`). Yazılamazsa iş durmaz.

## Notes
- Bu sürümden önceki harcamalar defterde yok (toplam bugünden başlar). Haber başına maliyet Video Stüdyosu'nda aynen
  görünmeye devam ediyor.
- ElevenLabs sorgusu sandbox'ta denenemedi (ağ kapalı; sahte istemciyle testli). Anahtarın abonelik okuma izni yoksa
  panel "okunamadı" yazar.

# v4.0.0-alpha.5 — Düzeltmelerden öğrenme kaydı — 2026-09-26

Editör: "benim düzeltmelerimden öğrenme mantıklı" (başlık kalitesi orta, küçük düzeltmeler yapıyor; seslendirme ve
kurgu değişiklikleri önemli, kesit aralığı önemli olabilir; tasarım ve kesit ekleme önemsiz).

## Added
- **Düzeltme kaydı** (`apps/axion_local/corrections.py` → `data/duzeltmeler.jsonl`; projeler 3 günde silinse de
  silinmez). Çalışma zamanında ek yapay zekâ çağrısı yok; geliştirici kaydı belli aralıklarla okuyup istemi/kuralları
  düzeltir (regresyon testiyle).
  - **Haber** (Haber Stüdyosu'nda kaydedince): modelin son çıktısı (ilk üretim ya da "yeniden üret" sonrası) ↔
    editörün kaydettiği; yalnız değişen alanlar önce/sonra (1. ve 2. başlık, paylaşım metni, seslendirme), değişmeyen
    alanların adı (kalite oranı için), ham haberin başı (2.000 karakter), model/sağlayıcı/üslup, kaç kez yeniden
    üretildiği ve beğenilmeyip yeniden üretilen başlıklar.
  - **Sahne** (Video Stüdyosu'nda sahne değiştirince): sahne no, o sahnede söylenen, önceki görüntü (açıklama, kaynak,
    an, kim seçmişti: Luna/kurallar) ↔ editörün koyduğu.
  - **Kesit** (kesit eklerken): önerilen aralık (olay anı) ↔ seçilen, değişti mi.
  - Aynı haber, sahne ya da kesit yeniden kaydedilince satır güncellenir (son hâl). Yazılamazsa editörün işi durmaz.
- **Geliştirici bilgileri** (Haber ve Video Stüdyosu): kaydın özeti ("N haber (1. başlık x, … kez düzeltildi) · sahne
  değişikliği · kesit") ve **📝 Düzeltme kaydını indir** (tüm haberler). Repo herkese açık: kayıt internete
  gönderilmez; editör indirip sohbette Claude'a/GPT'ye yollar.
- **Token etkisi yok** (editörün sorusu): kayıt yalnız bilgisayarda bir dosyaya yazılır, hiçbir model çağrısına
  eklenmez; haber üretiminin token sayısı değişmez. Kayda bakılarak istem düzeltilirse istem uzatılmaz (AGENTS).

## Changed
- Haber Stüdyosu'nda kullanılmayan içe aktarma (`datetime.date`) temizlendi.

# v4.0.0-alpha.4.1 — Müzik: konuşmada varla yok arası, konuşmasız kesitte duyulur; yumuşak piyano — 2026-09-26

Editör (müzikleri dinledi: "güzel, kullanılabilir"): "konuşma olmayan kesitlerimde duyulabilir şekilde çalsın, yüksek
olmadan; seslendirme, röportaj ya da konuşmalı video sesi varken varla yok arası çalsın; piyano notaları kulağa
batmasın".

## Changed
- **Müzik seviyesi konuşmaya göre** (`design_studio/music.py`): sidechain yerine zaman çizelgesinden kazanç zarfı.
  Seslendirmenin tamamı ve konuşmalı kaynak sesli kesitler boyunca müzik 18 dB kısık (~-45 LUFS; seslendirmenin ~27 dB
  altı: varla yok arası); konuşmasız kesitlerde ve sessiz kısımda ~-27 LUFS (duyulur, kesitin -20'sinin altında).
  Geçişler 0,5 sn'de yumuşak (konuşma başlamadan kısılmış olur). Ölçüldü (üç parça): seslendirme altında -44/-46,
  konuşmalı kesitte -45/-46, konuşmasız kesitte -27/-28, sessiz sonda -26/-28 LUFS.
- **Kesitte konuşma var mı** (yeni `video_studio/modules/speech.py`, API yok): kepstrumla perdeli (sesli harf) kareler
  sayılır; sesli karelerin %25–85'i perdeliyse konuşma. Sentez Türkçe konuşma (espeak-ng; gürültü altında da) konuşma;
  trafik, kalabalık uğultusu, çarpma, siren konuşma değil (testli; örnek `tests/ornekler/konusma.mp3`). Karar
  verilemezse (1 sn'den kısa) konuşma sayılır: müzik kısık kalır. Kurgu bilgisi yoksa tüm video konuşma sayılır.
- **Piyano notaları yumuşak** (`assets/muzik/uret.py`, Gündem ve Sakin yeniden üretildi; Gerilim'de piyano yok, aynı):
  daha yumuşak vuruş, tiz harmonikler zayıf ve çabuk sönüyor, Gündem'in arpeji bir oktav aşağıda, ikisi de daha kısık
  ve daha boğuk. Tiz bölgede ölçülen düşüş: Gündem 2–4 kHz -4 dB, 4–8 kHz -7 dB; Sakin 1–2 kHz -5 dB, 2–4 kHz -15 dB.

# v4.0.0-alpha.4 — Müzik altlığı — 2026-09-26

Editör: "haber videolarında kullanılan türden sözsüz arka plan müziği; seslendirmenin altında kısılsın; seçerim ya da
kapatırım".

## Added
- **Üç hazır haber müziği** (`assets/muzik/`): **Gündem** (nötr, varsayılan; 96 BPM, La minör, nabız bas + pad +
  arpej + saat tıkırtısı), **Gerilim** (asayiş/son dakika; 110 BPM, Re minör, 16'lık bas ostinatosu, koyu pad,
  tıkırtı, vuruşlar), **Sakin** (insan hikâyesi; 80 BPM, Do majör, piyano arpeji, davulsuz). Bu ortamdan müzik
  sitelerine erişilemediği ve repo herkese açık olduğu için (Pixabay vb. lisanslar yeniden dağıtımı yasaklar) parçalar
  `assets/muzik/uret.py` ile sıfırdan sentezlendi: telif yok, Axion'a ait. Dairesel hesap: döngüde dikiş yok
  (süreler tam ölçü: 80,0 / 69,8 / 72,0 sn; ölçüldü).
- **Son videoda karışım** (`design_studio/music.py`, `render.build_final_command(music=)`): müzik döngüyle sonuna
  kadar, 0,4 sn açılış / 1,5 sn kapanış; seviye parçaya göre ölçülür (sessizlikte ~-25 LUFS); seslendirme ve kesit
  konuşurken sidechain ile ~6 dB kısılır; sonda -2 dBFS sınırlayıcı. Ölçüldü (-18 LUFS'luk test sesiyle): konuşma
  kısmı müzikle/müziksiz farkı < 1 LU, sessiz kısımda müzik -25 LUFS civarı. Müzik açıkken ses yeniden kodlanır
  (AAC 192k); sandbox'ta 10 sn'lik video 4,2 → 9,5 sn.
- **Tasarım Stüdyosu → 🎵 Müzik** (kapalı bölüm, başlığında seçili müzik): seç, dinle, **Kapalı**; **Kendi müziğini
  ekle** (MP3/M4A/WAV/OGG) → `data/varliklar/muzik/`, yalnız bu bilgisayarda (GitHub'a yüklenmez). Seçim
  `tasarim.json` `music` alanında; değişince "işlenmedi" → Yeniden oluştur. Video Stüdyosu'nun otomatik ürettiği son
  video da varsayılan müzikle çıkar.

## Notes
- Müziklerin kulağa nasıl geldiği sandbox'ta dinlenemedi (yalnız spektrum, seviye ve döngü ölçüldü); editörün
  beğenisine göre parçalar değiştirilir ya da kapatılır.
- Varsayılan açık (editörün "seçer ya da kapatır" notu); eski haberlerin son videosu tasarım değiştiği için "işlenmedi"
  görünür, yeniden oluşturulunca müzikli olur.

# v4.0.0-alpha.3 — Kapak = videonun ilk karesi — 2026-09-26

Editör: "ayrı bir kapak görseli yüklemek boşa iş olur"; Reels/Shorts kapağı olarak videonun ilk karesi kullanılır.

## Added
- **İlk karede başlık hep tam:** Tasarım Stüdyosu'nda 1. başlığa giriş animasyonu (kayarak, daktilo, birleşme…)
  seçilse de videonun ilk karesinde başlık animasyonun son hâliyle tam görünür; animasyon ikinci kareden her zamanki
  gibi başlar (tek kare, 1/30 sn). Varsayılan şablonda 1. başlığın girişi "yok" olduğu için orada zaten tamdı. Tuval
  (önizleme) 0. saniyede aynısını gösterir.
- **İlk kare kapak sahnesinden:** seslendirmenin önüne kaynak sesli kesit konmuşsa video kesitle açılıyordu (kapak
  kesitin ilk karesi oluyordu). Artık ilk kare 1. seslendirme sahnesinden (kapak sahnesi: Luna/kurallar olayı en net
  gösteren görüntüyü seçer), kesit bir kare geç başlar; ses ve süre değişmez.
- Sahne ızgarasında 1. sahne "kapak" diye işaretli ("1. sahne videonun ilk karesi, yani paylaşımdaki kapak"): kapağı
  değiştirmek için o sahne değiştirilir.

## Notes
- Denendi: gerçek son video (1080x1920) 0. karede tam başlık; kesitli kurguda 0. kare kapak sahnesi, 1. kare kesit,
  süre aynı (testli). Tuval tarayıcıda hatasız açıldı.

# v4.0.0-alpha.2 — Kurguda sahne değiştirme — 2026-09-26

## Added
- **Sahneyi elle değiştirme** (Video Stüdyosu → 4. Video → "🎞️ Sahneleri göster ve değiştir"; API yok). Her
  seslendirme sahnesi videodaki kadrajıyla küçük kare olarak görünür (6'lı ızgara, süresiyle). Sahneye dokununca:
  o sahnede söylenen cümle ve aynı görüntülerden (fotoğraflar dahil) en uygun 4 seçenek. Seçenekler kurallı puanla
  sıralanır; şu anki görüntü ve videoda başka yerde kullanılan an seçenek olmaz, her seçenek başka çekimden.
  "✅ Bunu koy" → yalnız o sahne değişir, video arka planda yeniden oluşur; elle değiştirilen sahne "✋" ile işaretli.
  Bölüm açık kalır (art arda değiştirilebilir).
- Editörün seçimi `kurgu_plani.json`'da `editor` satırı olarak Luna'nın planının üstüne yazılır (yeni Luna çağrısı
  yok; klibin etiketi "user", kaynak sırasına dizmede yerinde kalır). Luna'ya ulaşılamamışsa şu anki kurgu `temel`
  olarak kaydedilir: kurallar öteki sahneleri yeniden seçmez.
- Haber, görüntüler ya da kesitler değişince editörün seçimi düşer (pencereler başka olur); "🔀 Sahneleri yeniden
  seç" onları da sıfırlar (düğmenin açıklamasında yazıyor).
- Geliştirici bilgileri: "Editörün değiştirdiği" satırı (sahne → pencere). Teşhis dosyasında zaten `kurgu_plani.json`
  var; 4.0'ın "düzeltmelerden öğrenme" parçası bu kaydı kullanacak.
- Küçük kareler proje klasöründe (`onizleme/kareler`, proje ile silinir); fotoğraf karesi EXIF yönüyle.

## Changed
- Kurgu klibi sahne numarasını taşır (`Clip.scene`, shared sözleşmede isteğe bağlı alan). 4.0 öncesi kurgularda
  numara yok: bölüm görünmez, "Videoyu yeniden oluştur" sonrası gelir.

## Fixed
- Okunamayan (bozuk) fotoğraf görüntü analizini durduruyordu (alpha.1'deki boyut okuma); artık boyutu boş kalır,
  kurgu o fotoğrafı atlar.
- alpha.1'de sahne tablosuna fotoğraf satırı eklenince FFmpeg'li ortamda bir test (`test_media_pipeline`) bozulmuştu
  (sandbox'ta FFmpeg olmadığı için atlanıyordu; editörün `testler.bat`'ında düşerdi). Test güncellendi; bu oturumda
  FFmpeg/FFprobe kurulu, tüm medya testleri çalıştı.

# v4.0.0-alpha.1 — Fotoğraflar kurguda — 2026-09-26

4.0'ın ilk parçası (editör kararı: 4.0 parça parça ön sürümlerle; denemeler hepsi bitince).

## Added
- **Fotoğraflar kurguda kullanılır** (bilinen borç; editör var sanıyordu). 2. adımda seçilen fotoğraflar zaten
  analiz ediliyordu, artık videoya da girer: yavaş yakınlaşma ya da uzaklaşma (sahneden sahneye sırayla; 5 sn'de
  en fazla 1,15x), alan hep tam dolu, bulanık dolgu yok. Öznenin tamamı yakınlaşmada da kadrajda kalır; özne alandan
  genişse videodaki gibi yavaşça kayar. Aynı fotoğraf, başka malzeme varken ikinci kez gelmez. Yalnız fotoğraflı
  haberden de video çıkar.
- **Luna'nın sahne seçimine fotoğraflar da gider** ("fotoğraf 1 | hareketsiz | açıklama"; her fotoğraf en fazla bir
  kez). İstem değiştiği için eski haberlerde "Videoyu yeniden oluştur" bir kez yeni sahne seçimi çağrısı yapar.
- **Telefonda dik çekilmiş fotoğraf** (EXIF yönü) hem Luna'ya hem videoya dik gider. Render'da FFmpeg'in kendi
  döndürmesi kapalı, yönü Axion uygular (FFmpeg sürümüne göre değişmesin).

## Notes
- Yakınlaşma 4 kat büyütülmüş karede hesaplanır (FFmpeg `zoompan` tam piksel adımında titriyor; sandbox'ta ölçüldü:
  titreme 3x'e göre ~%33 az; 4 fotoğraf sahneli 20 sn'lik kurgu 5,8 → 7,1 sn).
- Eski analizlerde fotoğrafın boyutu kayıtlı değil: kurguda dosyadan okunur; dosya silinmişse fotoğraf atlanır.
- Geliştirici bilgileri'ndeki sahne tablosunda fotoğraflar da görünür.

# v3.7.2 — Kısa çekimde 1 sn'lik ara sahne yok — 2026-09-26

Editörün Eymen haberi (255 sn, 29 çekimlik DHA paketi; teşhis dosyasıyla): "ufak metin düzeltmeleri dışında her şey
sorunsuz". Luna 9 sahnenin 9'unu seçti, olay örgüsünü doğru kurdu, tekrar yok. Maliyet: haber metni 4 çağrı $0,0046
(iki kez "Haberi işle", ikisinde de düzeltme çağrısı), görüntü analizi 40 kare $0,0066, sahne seçimi $0,0018.

## Fixed
- **1 sn'lik ara sahne:** Luna 3 sn'lik bir çekimi 4,2 sn'lik sahneye seçmişti; kalan 1 sn kurallarla başka bir
  çekimden geldi. Artık kalan süre 2 sn'den (en kısa sahne) azsa ayrı sahne açılmaz: sahne erken biter, sonraki sahne
  o kadar erken başlar (kesme seslendirmedeki duraklamadan biraz kayar; son sahnede olmaz). Editörün verisiyle yeniden
  kuruldu: 9 sahnenin hepsi Luna'dan, en kısası 2,7 sn. Regresyon testi.

# v3.7.1 — Tablette ekran kapanınca yazılanlar kaybolmaz; boştaki sayfa daha sakin — 2026-09-26

Editör: "sayfa inaktifken arada kendini mi yeniliyor?"

## Fixed
- **Asıl neden: kopan bağlantı 2 dk sonra oturumu siliyordu.** Tablette ekran kapanınca ya da başka uygulamaya
  geçince bağlantı kopar; Streamlit kopan oturumu varsayılan 2 dk saklıyordu. Daha uzun ayrı kalınca geri dönüşte
  sayfa sıfırdan açılıyor, yazılan ham haber, başlıklar, ses gidiyordu. Artık 3 saat saklanır
  (`.streamlit/config.toml` `disconnectedSessionTTL = 10800`). Tarayıcıda denendi (bağlantı sayfanın içinden
  koparılıp 160 sn engellendi): eski ayarla ham haber kutusu boşaldı, yeni ayarla yerinde kaldı.
- **Boştayken kendiliğinden yenilenen parçalar seyreldi:** kenar çubuğundaki güncelleme satırı 30 sn'de bir, Haber
  Stüdyosu'ndaki önbellek sayacı 60 sn'de bir sunucuya soruyordu (tablette sağ üstte kısa "çalışıyor" göstergesi).
  İkisi de artık 2 dk'da bir. Sayfanın tamamı hiç yenilenmiyordu (ölçüldü: yazılan metin ve imleç yerinde kalıyor).

# v3.7.0 — Luna kurguyu haberi bilerek yapar — 2026-09-26

Editör: "Faz 4'ü verimli geliştirmek için elimizden geleni yapalım; yapay zekâ olay örgüsünü, haberin konusunu bilerek
kurgu yapsın."

## Changed
- **Sahne seçimi haberin kendisini görür:** Luna'ya başlıklar ve seslendirme sahnelerinin yanında haberin anlatımı
  (paylaşım metninin ilk ~900 karakteri) gider. Pencerelerde kısa açıklamaya ek ipuçları: mekân, karede okunan yazı
  (ör. "OLAY YERİ İNCELEME", "AMBULANS"; DHA damgası hariç), insan var mı.
- **Luna önce olay örgüsünü kurar:** yanıt şeması düşünme sırasıyla: önce `olay_orgusu` (en fazla 2 cümle: ne oldu →
  kim müdahale etti → sonuç), sonra her sahneye `asama` (olay öncesi, olay anı, olay yeri, müdahale, sonuç, açıklama,
  genel), sonra o aşamayı en iyi gösteren pencere. Düşünme seviyesi yine "low" (verimli); örnek haberde istek ~1.600
  token, sahne seçimi başına ~$0,001.
- **Görüntü analizi haberi bilir:** analiz çağrısına haberin başlıkları ve seslendirmesi gider; açıklama ve rol
  (olay anı, kanıt, müdahale…) haberle ilgili görünen ayrıntıya göre seçilir. "Karede görmediğin hiçbir şeyi yazma,
  kişileri tanımlama" denir; sistem komutu aynı (önbellek). Yalnız yeni analizlerde (eski analizler yeniden yapılmaz).
- Geliştirici bilgileri'nde Luna'nın olay örgüsü ve sahne başına aşama → pencere.
- Sistem komutu değiştiği için eski projelerde "Videoyu yeniden oluştur" bir kez yeni sahne seçimi yapar.

## Denenmedi
- Gerçek Luna ile denenmedi (bu ortamda anahtar yok). İstem editörün Sultangazi haberinin gerçek verisiyle üretilip
  gözden geçirildi; testler sahte Luna yanıtıyla.

# v3.6.4 — İsim sansürü kuralı (suç, reşit olmayan, masumiyet karinesi) — 2026-09-26

## Changed
- **İsim kuralı netleşti (editör):** suç unsuru olan, reşit olmayan ve masumiyet karinesi/özel hayat gereği korunan
  kişilerin adı paylaşım metninde ve başlıkta yalnız baş harfleriyle: "A.K." (önce DHA'daki gibi "Abdullah K."
  çıkıyordu). Tanınmış kişiler ve röportaj veren/konuşan kişiler açık. Haber istemindeki kural bu tarifle yazıldı.
- **API'siz güvence** (`validation/news.protect_names`): DHA korunan kişiyi "Ad S." diye yazar (röportaj vereni tam
  adla); model bu yazımı bırakırsa paylaşım metninde ve başlıkta "A.K."ye çevrilir, bu kişilerin tek başına geçen adı
  da ("Ömer" → "Ö.Ş."). Ek almış tek ad ("Ömer'in") çevrilmez (ek baş harfe göre değişir: "Ö.Ş.'nin"); "elle düzelt"
  uyarısıyla gösterilir. Aynı adda tam adıyla geçen biri varsa (röportaj veren) tek ad çevrilmez. Regresyon testi
  editörün Sultangazi haberiyle. Gerçek modelle denenmedi (istemin etkisi); API'siz çevirme model ne yazarsa yazsın çalışır.

# v3.6.3 — Seslendirmede isim kontrolü, "baştan üret" onayı, yalnız seslendirmeyi yeniden üret — 2026-09-26

Editörün Sultangazi haberi ve tablet notları.

## Fixed
- **Seslendirmede sivil isim:** ilk seslendirmede "Abdullah K.", "Ömer Ş." gibi isimler vardı (kural: seslendirmede
  sivil isim ve baş harf yok). Deterministik kontrol (`civil_names_in_tts`, API yok): seslendirmedeki "Ad S." ve "A.K."
  biçimleri ile ham haberdeki bu kişilerin adları hata sayılır → haber işlenirken mevcut tek düzeltme çağrısı giderir.
  Regresyon testi editörün gerçek haberiyle.
- **Haber kendiliğinden baştan üretildi:** günlüğe göre "Haberi işle" ikinci kez çalışmış (08:26 ve 08:27); tablette
  seslendirmeyi düzeltirken dokunuş düğmeye gelmiş olmalı (klavye açılınca sayfa kayar). Ekranda haber varken
  "Haberi işle" artık önce sorar: "…silinip baştan üretilecek; düzeltmelerin kaybolur. Emin misin?" (Evet / Vazgeç).

## Added
- **"↻ Yeniden üret" (Seslendirme başlığının yanında, küçük):** yalnız seslendirme metnini yeniden yazar; başlıklar ve
  paylaşım metni kalır. Haber çağrısının sistem komutu ve istemi aynen gider (önbellek tutar, kurallar aynı), sonuna
  "önceki seslendirme beğenilmedi, farklı yaz" notu. Aynı temizlik ve kontroller (okunuş, plaka, sivil isim, uzunluk);
  sorun varsa kutunun altında "Kontrol et" notu (ek düzeltme çağrısı yok). Ses sonra yeniden üretilir ("Seslendir").

## Changed
- **Luna'ya "plakadan kaçın" denmiyor** (editör: "gerekirse ben blur eklerim"); pencerelerde "plaka" notu da gitmez.
  Sistem komutu değiştiği için eski projelerde "Videoyu yeniden oluştur" bir kez yeni sahne seçimi yapar.

## Editörün notları (değişiklik gerekmedi)
- "Başlıkları yeniden üret" yeni başlık veriyor; kalitesi orta, editör küçük düzeltmeler yapıyor (4.0'daki
  "düzeltmelerden öğrenme" bunu kaydedecek). Tasarım Stüdyosu'nda elle değişiklik sorunsuz; kaynak sesli kesit seçimi
  sorunsuz; Tarayıcı DHA girişini sorunsuz kaydediyor. Blur henüz ayrıntılı denenmedi.

# v3.6.2 — Haberin toplam maliyeti, son sahnede "göz kırpması" yok — 2026-09-26

Editörün ilk Luna kurgusu (Sultangazi, "eşimle telefonda görüştün"): "sorunsuz çalıştı, ürünü beğendim, paylaştım".
Teşhis dosyasından: Luna 7 sahnenin 7'sini seçti, hiçbir an tekrar etmedi, aynı çekimin parçaları kaynak sırasıyla;
sahne seçimi 1.449 girdi / 518 çıktı (359'u düşünme) ≈ $0,0009.

## Fixed
- **Son sahnede yarım saniyelik ara sahne:** Luna son sahne için çekimin sonuna 2,4 sn kala bir an seçti, sahne 2,9 sn
  sürüyordu; kalan 0,4 sn kurallarla başka bir çekimden geldi (göz kırpması gibi). Artık Luna'nın istediği an sahneye
  yetmiyorsa aynı pencerede biraz önceden başlanır. Regresyon testi.

## Added
- **Geliştirici bilgileri'nde haberin toplam yapay zekâ maliyeti** (editör: "yukarıdaki token tüm işlemlerin mi?" —
  değildi): en üstte "Bu haberin yapay zekâ maliyeti" = haber metni + görüntü analizi + sahne seçimi (çağrı sayılarıyla;
  seslendirme dahil değil). Dört kutu artık "Görüntü analizi (Luna) — yalnız bu adımın" başlığıyla; "Düşünme"
  çıktı tokenına dahildir. Haber Stüdyosu kaydederken metnin maliyetini pakete yazar (öncekilerde "—").

# v3.6.1 — Teşhis dosyası — 2026-09-26

## Added
- **"📦 Teşhis dosyasını indir"** (Video Stüdyosu → Geliştirici bilgileri): editör tabletteyken projenin dosyalarına
  erişemiyordu. Tek JSON dosyası iner: projenin `news_package`, `media_library`, `edit_project`, `kesitler`,
  `kurgu_plani`, `tasarim` dosyaları ve `axion.log`/`olcumler.jsonl`'un son 60 KB'ı (video ve ses yok). Hiçbir şey
  internete gönderilmez (repo herkese açık; editörün seçimi); editör dosyayı Claude'a/GPT'ye sohbette yollar.
- Uzaktan güncellemede proje dosyalarını repoya yükleme fikri (herkese açık repo nedeniyle) bırakıldı; o iş için
  yazılan taslak hiç yayımlanmadı ve silindi.

# v3.6.0 — Faz 4: sahneleri Luna seçer — 2026-09-26

Editör kararı: "kurguyla, yanlış kesilmiş videolarla sürekli uğraşmayalım; bu işi Luna yapsın, verimli olsun.
4.0'dan önceki son büyük güncelleme bu olsun."

## Added
- **Sahneleri Luna seçer** (`apps/video_studio/modules/luna_edit.py`): "Videoyu oluştur" deyince arka planda önce tek,
  görüntüsüz bir Luna çağrısı (`gpt-5.6-luna`, düşünme "low"). Giden: başlıklar, seslendirme sahneleri (duraklamalarda
  2–5 sn'lik parçalar, o sırada söylenen metinle; ilki "kapak") ve analizdeki pencereler (video/çekim, kaynak zamanı,
  tür/rol, kısa açıklama, özne var mı, plaka, kesit). Aynı çekimde aynı görünen ardışık pencereler tek satır (uzun
  röportajda token tasarrufu). Luna her sahneye bir pencere ve o penceredeki başlangıç anını seçer; şema pencere
  kimliklerini enum'la sınırlar. Kurallar: olay örgüsü, tekrar yok, ilk sahne kapak, röportaj/genel görüntü/plaka
  ancak gerekirse, kesit aralıkları kullanılmaz. Örnek haberde istek ~2.700 karakter (~1.300 token sistemle); tahmini
  maliyet haber başına ~$0,001.
- Kurallar kalanı yapar: kesme zamanları (duraklamalar), kadraj (tam dolu, dikeyde sabit), kaynak sesli kesitler,
  aynı anın iki kez kullanılmaması (Luna aynı anı iki kez isterse ikincisi pencerenin kullanılmamış kısmından gelir),
  aynı çekimin parçalarının kaynak sırası (v3.3). Luna'nın seçtiği pencere sahneye yetmezse ya da bir sahneyi boş
  bırakırsa kalan süre kurallarla dolar. Luna'nın klipleri `origin: "llm"`.
- **Plan saklanır** (`kurgu_plani.json`: imza, seçimler, token): girdiler (seslendirme, görüntüler, kesitler) aynıysa
  "Videoyu yeniden oluştur" yeni çağrı yapmaz, aynı kurguyu üretir.
- **"🔀 Sahneleri yeniden seç"**: video hazırken; önceki kurguyu "editör beğenmedi, farklı seç" notuyla gönderir.
- Luna'ya ulaşılamazsa ya da anahtar yoksa video yine çıkar: sahneler kurallarla seçilir, sayfada uyarı görünür.
- Durum satırı: "Sahneler seçiliyor (Luna)… → Kurgu oluşturuluyor… → Axion şablonu uygulanıyor…". Token ve maliyet
  Geliştirici bilgileri'nde; adım süresi `data/olcumler.jsonl`'da (`sahne_secimi`).

## Changed
- Kurallı kurgu (`rough_cut`) artık yalnız yedek ve kalan süreyi doldurma; kuralları ayrıca geliştirilmeyecek (editör:
  "sistemin kendi başına çözmeye çalıştığı alanı basitleştirelim"). Kod, Luna ile ortak "hazırlık" (`prepare`: kesitler,
  sahne zamanları, adaylar) ve seçim (`plan_rough_cut(picks=...)`) olarak ayrıldı.

## Denenmedi
- Gerçek Luna ile denenmedi (bu ortamda API anahtarı yok); testler sahte Luna yanıtıyla. İlk gerçek denemede Geliştirici
  bilgileri'ndeki sahne tablosu ve `kurgu_plani.json` ile kontrol edilir.

# v3.5.1 — Tablet denemesinden: klavye, Tarayıcı boşluğu, başlık yenileme — 2026-09-26

Editörün dükkândaki tablet denemesi (ekran görüntüleriyle).

## Fixed
- **Seçim kutularına dokununca klavye açılıyordu** (spiker, üslup, dosya seçimi vb.): Streamlit'in seçim kutusu
  yazarak aramaya izin veriyordu. Bütün seçim kutuları artık yalnız dokunarak seçilir (`filter_mode=None`; tarayıcıya
  `inputmode="none"` gider, klavye açılmaz). Dosya seçimindeki İngilizce "Select all" satırı kalktı. Test: bütün seçim
  kutularını kaynakta tarar; tarayıcıda dokunmatik taklidiyle doğrulandı.
- **Tarayıcı'da altta/üstte beyaz boşluk kalıyordu** (tablet ve bilgisayar): kaydırırken ekran anında tepki versin diye
  görüntü parmakla birlikte kaydırılıyor, yeni kare gelince yerine oturuyordu. Sayfanın başı/sonu gibi kaymayan yerde
  yeni kare gelmediği için görüntü kaymış kalıyordu. Artık 0,8 sn içinde yeni kare gelmezse görüntü yerine oturur
  (tarayıcıda denendi: kaymayan sayfada 240 px kayma → 1,5 sn sonra sıfır).
- **"↻ Başlıkları yeniden üret" hep aynı başlığı veriyordu:** küçük başlık çağrısı önceki başlıkları görmüyordu, aynı
  paylaşım metninden aynı başlığı yazıyordu. Artık bu haberde gösterilen başlıklar (son 4 çift) "editör bunları
  beğenmedi; haberin başka bir çarpıcı yönünü öne çıkar, farklı fiil ve kelime kullan, küçük değişiklikle tekrar etme"
  isteğiyle gider (sistem komutu değişmedi, önbellek korunur; ek maliyet birkaç düzine token). Gerçek modelle
  denenmedi (bu ortamda API anahtarı yok): editörün denemesi bekleniyor.

## Açık
- Kurguda aynı görüntünün tekrar kullanılması ve olay sırasından çıkma ("eşimle telefonda görüştün" haberi): editörün
  projesindeki `media_library.json` ve `edit_project.json` ile incelenecek.

# v3.5.0 — Güncellemede geri dönüş, sürüm numarası — 2026-09-26

## Added
- **Güncellemede geri dönüş** (editör: "mantıklı, ana sürümden önce"): uygulamadan güncellenen sürüm açılamazsa Axion
  kendiliğinden önceki sürüme döner. Güncellemeden önce çalışan sürüm `data\guncelleme_onceki.txt`'ye yazılır; bekçi
  (`axion_calistir.ps1`) paketleri kurduktan sonra yeni sürümü **açılış kontrolünden** geçirir
  (`python -m apps.axion_local.self_check`: bütün Python dosyaları derlenir, modüller içe aktarılır, Haber/Video/Tasarım
  sayfaları boş bir veri klasöründe bir kez çizilir; ~3 sn, API yok, projelere dokunmaz). Kontrol geçmezse ya da yeni
  sürüm ilk 3 dakikada çökerse bekçi önceki sürüme döner (`git reset --keep`: yerel değişikliklere dokunmaz, çakışırsa
  dönmez ve günlüğe yazar), paketleri yeniden kurar ve Axion'u açar.
- Geri dönüldüyse kenar çubuğunda "⚠️ Son güncelleme açılamadı; Axion önceki sürüme döndü" yazar ve aynı bozuk sürüm
  için güncelle düğmesi çıkmaz; düzeltilmiş sürüm yayımlanınca düğme geri gelir.
- **Sürüm numarası** kenar çubuğunda: "🟢 Axion güncel · v3.5.0" (tek kaynak: CHANGELOG'un ilk başlığı).
- Sandbox'ta PowerShell 7 ile bekçinin kendisi sahte bir Axion'la denendi (4 senaryo): sözdizimi hatalı sürüm → geri
  döndü; çizilirken hata veren sayfa → geri döndü; güncellemeden hemen sonra çökme → geri döndü; sağlam sürüm → kaldı.
  Windows PowerShell 5.1'de denenmedi.

## Not
- Bekçi betiği Axion açılırken bir kez okunur: geri dönüş, bu sürüme geçtikten sonra Axion **bir kez masaüstü
  simgesiyle yeniden açılınca** (ya da bilgisayar yeniden başlayınca) devreye girer. O zamana kadar çalışan eski bekçi
  güncellemeyi eskisi gibi yapar.

# v3.4.3 — Güncelleme daha sık kontrol edilir — 2026-09-26

## Changed
- **Güncelleme kontrolü 30 dk yerine 2 dk'da bir** (editör: "zararı yoksa daha sık"). Zararı yok: `git ls-remote`
  yalnız son commit numarasını sorar (~1 KB, indirme yok, arka planda, sayfa beklemez) ve yalnız Axion bir tarayıcıda
  açıkken çalışır.
- Kenar çubuğundaki 🟢/🔴 satırı kendi başına yenilenir (30 sn'de bir, yalnız o satır): yeni sürüm yayımlanınca sayfaya
  dokunmadan birkaç dakika içinde 🔴 görünür (önce bir tıklama/sayfa değişimi gerekiyordu).
- Sandbox'ta tarayıcıyla denendi: 🟢/🔴 dokunmadan ~30 sn'de göründü; 🔴 → "⬇️ Güncelle ve yeniden başlat" → onay →
  yeni sürüm indi → Axion 3 koduyla çıktı.

# v3.4.2 — Uygulamadan güncelle ve yeniden başlat — 2026-09-25

## Added
- **"⬇️ Güncelle ve yeniden başlat"** (editör: "dükkândayken bilgisayara erişemem"): 🔴 Güncelleme var görünürken kenar
  çubuğunda, tabletten de. Onay ister (video oluşturuluyorsa uyarır). Axion yeni sürümü kendisi indirir (`git pull
  --ff-only`, guncelle.bat gibi), Brave'i kapatır ve 3 koduyla çıkar; bekçi (`axion_calistir.ps1`) bu kodda paketleri
  kurar (`pip install -r requirements.txt`; çalışan Python kapalıyken, Windows dosya kilidi yüzünden) ve hemen yeniden
  başlatır (çökme sayılmaz). Sayfa ~yarım dakikada kendiliğinden yeniden bağlanır. İndirme olmazsa (ör. yerel değişiklik)
  hata metni gösterilir, Axion kapanmaz. Düğme yalnız Axion bekçiyle (masaüstü simgesi) çalışıyorsa görünür
  (`AXION_BEKCI=1`); `sorun_giderme.bat` ile açıldıysa yeniden başlatacak kimse yok.
- İlk kez: bu sürüm evde `guncelle.bat` ile alınıp Axion masaüstü simgesiyle açılmalı (yeni bekçi çalışsın).
- Yeniden başlatmadan sonra sayfa kendiliğinden yenilenir (sunucu kapanıp açılınca; 2 dk'da olmazsa da). Streamlit
  yeniden bağlanıyor ama sayfayı yeniden çizmiyordu (dokunuş bekliyordu).
- Sandbox'ta uçtan uca denendi (bekçi taklidi + repoda yeni commit + dışarıdan tarayıcı): 🔴 göründü → düğme → onay →
  yeni sürüm indi → çıkış kodu 3 → yeniden başladı → sayfa 9 sn'de kendiliğinden yenilendi.

# v3.4.1 — Güncelleme göstergesi — 2026-09-25

## Added
- **Kenar çubuğunda güncelleme göstergesi** (editör: "PC'de güncellemeyi unutursam görünsün"): "🟢 Axion güncel" ya da
  "🔴 Güncelleme var: bilgisayarda `windows\guncelle.bat`". Bilgisayardaki sürüm repodaki `main` ile karşılaştırılır
  (`git ls-remote`: yalnız son commit numarası, indirme yok); arka planda, yarım saatte bir, sayfa beklemez. Git ya da
  internet yoksa hiçbir şey gösterilmez. Tabletten de görünür.

# v3.4.0 — Kurgu olay örgüsünü izler, kadraj bulanığın bittiği yerden, indirmeler Brave'siz — 2026-09-25

Editörün "kadın polis arızalı midibüsü itti" denemesi (tam çözünürlüklü DHA videosu, oluşan video, `axion.log`,
`media_library.json`, `edit_project.json`). Kurgu bu projenin gerçek Luna analiziyle sandbox'ta yeniden üretildi.

## Fixed
- **Kurgu tek uzun çekimde hep aynı pencereyi seçiyordu:** kullanım çekim başına tek imleçle tutuluyordu; geç bir
  pencere bir kez seçilince öncekiler "tekrar" sayılıyordu. Sonuç: video yalnız 46–55. sn'den (boş yol), 46. sn iki
  kez, ilk pencerenin açıklamasıyla 52. sn. Artık kullanım aralık aralık tutulur, görüntü seçilen pencereden gelir,
  aynı an iki kez gösterilmez.
- **Kadraj net görüntüyü yandan kesiyordu:** kenar tespiti bulunan alanı en yakın standart orana (9:16) daraltıyordu;
  bu videodaki 3:4 dikey çekimin (net şerit %41,2) üçte biri kesilip ~1,5 kat fazla yakınlaştırılıyordu (%27,7).
  Artık DHA'nın net görüntüyü bulanık kopyaya yapıştırdığı sınır çizgisi (iki yanda simetrik, her karede aynı yerde)
  bulunur: kırpma tam bulanığın bittiği yerden (sandbox: 0,2954–0,7046; gerçek 0,2938–0,7063). Çizgi yoksa eski
  yöntem yedek. Bu videoda üst+alttan kesilen %37 → %7.
- **İndirme:** "Tüm Materyali İndir"de Brave yine çöktü (günlük: TXT `blob:` olduğu için hâlâ Brave kaydediyordu).
  Artık sayfadaki indirme bağlantıları (tıklama ya da sayfanın `a.click()`'i) Brave'e hiç gitmez: http dosyası
  Axion'un kendi indirmesine, sayfanın ürettiği dosya (TXT) baytlarıyla doğrudan Axion'a (adres hemen geri alınsa
  da). Sunucunun verdiği dosya adı kullanılır. Brave profiline "birden çok dosya indirmeye sormadan izin" yazılır.
  Diğer yollar (yönlendirme, pencere) v3.3.2'deki gibi: Brave iptal, Axion indirir.

## Changed
- **Tek uzun çekim (cep telefonu) olay örgüsüyle:** seslendirmenin başı çekimin başına, sonu sonuna yakın pencereden;
  parça, Luna'nın gördüğü karenin çevresinden alınır (elde çekimde kamera pencere içinde başka yere dönebiliyor).
  Öznesi olmayan pencereler (kutu net görüntünün tamamı: ağaçlık, boş yol) geride kalır. Bu projede: 0–35. sn
  (midibüs, itme, yardım) + son parça trafiğin açılması; ağaçlık yok.
- **Dikey (yanları dolgulu) görüntüde hiç kaydırma yok** (editör): ne klip içinde ne klipten klibe; net şeridin tam
  genişliği, tüm video boyunca aynı yükseklik (özne merkezlerinin ortalaması). Kaydırma yalnız tam karede (yatay),
  özne alandan genişse.
- **Luna'ya yanları bulanık videoda yalnız net şerit gider:** özne daha büyük görünür, token daha az (kare ~231 →
  ~154); özne kutusu tam kare koordinatına çevrilir.

## Yapılmayan
- Kaynak çözünürlüğü: önceki denemedeki 640x480 dosya yerine tam çözünürlüklü (1920x1080) dosya kullanılmalı —
  editör bu kez onu gönderdi; net şerit 791 px, alan 960 px (~1,2x büyütme).

# v3.3.2 — Tarayıcı: indirmeleri Axion yapar (Brave çöküyordu); tek çekim sırasıyla oynar — 2026-09-25

## Changed
- **Aynı çekimden alınan parçalar kaynaktaki sırasıyla oynar** (editör: "kadın polis midibüsü itti" haberinde tek,
  55 sn'lik cep telefonu çekimi 2–5 sn'lik parçalara bölünüp 46 → 4 → 50. sn diye atlanıyordu, olay anlaşılmıyordu).
  Hangi anların seçildiği değişmez; her parça kadrajını yanında taşır; aynı an iki kez gösterilmez. Sığmazsa (çekim
  sonu, kaynak sesli kesit aralığı) o çekim eski sırasında kalır. Regresyon testi: `test_one_long_shot_plays_in_source_order`.

## Fixed
- **DHA'dan indirirken Brave çöküyordu** (editörün `axion.log`'u: "Tarayıcı (Brave) beklenmedik şekilde kapandı" iki
  kez; Tüm Materyali İndir ve video İndir'de hata, ikinci denemede iniyor). Artık Brave'in indirme hattı kullanılmıyor:
  indirme başlar başlamaz iptal edilir, dosyayı Axion aynı oturum çerezleriyle (girişli DHA) kendisi indirir; parça
  parça diske yazar (büyük video belleği doldurmaz), yönlendirmeleri izler, indirilenlerde ilerleme (MB) görünür.
  Sunucu reddederse kartta "HTTP 403" gibi neden yazar ve günlüğe düşer. Sayfanın kendi ürettiği dosyalar (`blob:`)
  eskisi gibi tarayıcıyla kaydedilir. Sandbox'ta: yeni sekme, aynı sekme, `window.open`, `download` bağlantısı,
  yalnız çerezle açılan ve yönlendiren indirme. Windows + Brave + gerçek DHA ile denenmedi.

# v3.3.1 — Tarayıcı: indirirken "yeniden başlatılıyor"da kalma — 2026-09-25

## Fixed
- **DHA'da İndir / Tüm Materyali İndir'e basınca "Tarayıcı yeniden başlatılıyor…" yazıp kalıyordu** (editör, acil).
  İki sorun vardı:
  - Ekran bir kez alınamayınca (ör. indirme sekmesi yanıt vermiyor, 15 sn) tarayıcı "çöktü" sayılıyordu. Artık
    tarayıcı ayaktaysa son görüntü kalır; sekme başlığı ve canlı görüntü adımlarının süresi sınırlı (1–3 sn);
    uzun süren tıklama hata vermez.
  - "Çöktü" sayılınca ekran bölümü kapalı tarayıcıda kalıyordu (yeni tarayıcı yalnız sayfa baştan yüklenince
    açılıyordu). Artık Brave gerçekten çökerse (ya da kapanırsa) ekran kendiliğinden yeni tarayıcı açar, çökmeden önceki
    sayfaya döner, bitmiş indirmeler listede kalır. Nedeni `data\axion.log`'a yazılır.
- **Aynı adlı dosyalar aynı anda inince biri düşüyordu** ("No such file … haber.mp4.iniyor"): hâlâ inen dosyaların
  adı da dolu sayılır → "haber (2).mp4".
- Sandbox'ta denendi (Chromium): tarayıcı süreci öldürüldü → uyarı çıkmadan aynı sayfaya dönüldü; yeni sekme,
  aynı sekme, `window.open` ile üç eşzamanlı indirme. Brave'e özgü asıl tetikleyici Windows'ta görülmedi:
  tekrar olursa `data\axion.log`'daki "Tarayıcı" satırları nedeni gösterir.

# v3.3.0 — Kesit olay anından, token tasarrufu, önbellek sayacı — 2026-09-25

Editörün 3.2.0 denemesi (Antalya "otomobil yayaya çarpıp durağa daldı") ve GPT'nin 3.2 incelemesi
(`reviews/gpt-v3.2.md`). Plan: AGENTS.md → v3.3.0.

## Added
- **Kaynak sesli kesit olay anından başlar** (API yok): önizlemede sabit kamerada ani hareket (en çok değişen küçük
  bölge; kesmeler ve elde çekim sayılmaz), ani ses (çarpma; müziğin başlaması değil) ve Luna'nın "olay" sahneleri
  aranır; varsayılan aralık olaydan 2 sn önce … 3 sn sonra. Belirgin an yoksa "bulunamadı, elle seç" yazar (önceden
  hep ilk 5 sn). Editörün videosundaki güvenlik kamerası bölümünde yayanın savrulduğu an (2,9. sn) bulundu.
- **Önbellek sayacı** (Haber Stüdyosu kenar çubuğunda, modelin altında): "🟢 Önbellek sıcak, ~N dk (tahmini)" /
  "⚪ Önbellek soğuk"; dakikada bir yenilenir, her haberde süre baştan (Luna 30 dk, Claude 1 saat). Önbellek tutmadıysa
  (okunan ve yazılan 0) sayaç başlamaz.
- **Haber başına tahmini maliyet** ve girdinin önbellekten gelen payı: Geliştirici bilgileri'nde (AGENTS kural 10).
  Fiyat tablosu tarihli (`apps/news_studio/ai/cost.py`); önbellek okuma/yazma ayrı, düşünme çıktının içinde.

## Changed
- **Başlık yalnız hatalıysa küçük başlık çağrısı:** tam düzeltme çağrısı (sistem + ham haber + tüm çıktı) yerine
  yalnız başlıklar; geçerli başlık korunur, tek deneme, sonuç yeniden ölçülür. Kalın font (v3.1) bu hatayı sıklaştırmıştı.
- Varsayılan boyutta sığmayıp **50 px'e kadar küçülerek 2 satıra sığan başlık hata değil uyarı** (düzeltme çağrısı
  yok); satır yazısı "✅ Videoda (küçültülmüş yazı, 54 px): …". 42 px'e kadar küçülen başlıklar videoda zayıf kaldığı
  için hâlâ hata.
- **Claude önbelleği 1 saat** (`ttl: "1h"`; yazma 2x, okuma 0,1x): haberler arası 10–20 dk'da 5 dk'lık önbellek her
  haberde yeniden yazılıyordu. Luna (GPT-5.6) önbelleği zaten en az 30 dk ve tek seçenek bu; 24 saatlik saklama
  5.6'da yok. OpenAI'ın önbelleğe yazılan token sayısı da okunuyor.
- **Görüntü analizi token'ı:** kareler Luna'ya uzun kenarı 512 px ile gider (GPT-5.6 görseli 32 px'lik parçalarla sayar:
  dikey 640x1138 kare ~864 → ~173 token); aynı sahnede öncekiyle aynı görünen kareler gönderilmez (küçük bir bölgedeki
  olay elenmez), tüm kareleri aynı olan pencerenin sonucu önceki pencereden kopyalanır; açıklama en fazla 8 kelime.
  Editörün videosunda (6 sahne, 12 kare) görüntü token'ı ~7.500 → ~3.000. `detail: "low"` 5.6'da doğrulanamadığı için
  kullanılmadı. Yerel kareler (kadraj tespiti) 640 px kalır.

## Removed
- Haber Stüdyosu'ndaki başlık görsel önizlemesi (editör: satırlara sığıp sığmadığını görmek yeter). API'siz yerel
  çizimdi; token'la ilgisi yoktu, arayüz sadeliği için kalktı.

## Fixed (GPT v3.2 bulguları, `reviews/claude-v3.md` G6–G8)
- Bekçi, `guncelle.bat` çalışırken Axion'u yeniden açmaz (komut satırında `guncelle.bat` geçen `cmd.exe` varsa çıkar).
- Tarayıcı akış durumu oturum başına (jeton oturuma bağlı, imzalı): bir tabletin akışı ötekinin görüntüsünü kesmez.
- Akış kanalı kapanınca alıcı görevin istisnası tüketilir; kopma normal kapanış.

## Yapılmayan
- Sistem komutunu kısaltmak (plan 5. adım): önbellek artık tuttuğu için kazanç küçük; gerçek haberle önce/sonra
  karşılaştırması gerekiyor (AGENTS kural 5). Editörün kararına bırakıldı.

# v3.2.0 — "Sonraya" bırakılanlar, akıcı Tarayıcı, temizlik — 2026-09-25

Editörün Windows testinden sonraya bıraktığı işler ve Claude'un QoL notları (ROADMAP → Sıradaki işler) bu sürümde.

## Added
- **Axion çökerse kendini yeniden başlatır:** başlatıcı artık bir bekçi betiği çalıştırır (`windows/axion_calistir.ps1`):
  hata koduyla kapanırsa 5 sn sonra yeniden başlatır; **Axion'u kapat** (kod 0) ve güncelleme (Stop-Process, kod -1)
  yeniden başlatmaz; 10 dakikada 3 çöküşte durur. Brave alt süreçleri beklenmez (yalnız ana süreç). Önceki kayıt
  `data/axion.onceki.log`. `guncelle.bat`'ın `git pull` öncesine dokunulmadı (çalışırken okunduğu için).
- **Kalite kontrolünü hızlandıranlar (Haber Stüdyosu, API yok):**
  - 🟡 **Kaynakta yok:** paylaşım metni ve seslendirmede ham haberde geçmeyen sayılar ve isimler; başlıklarda sayılar.
    Okunuşa çevrilmiş saat/tarih ("akşam 6'da") kaynak sayılır.
  - 🖼️ **Başlıklar videoda böyle görünür:** Tasarım Stüdyosu'nun çizimiyle (yazı tipi, parıltı, satır kırılımı, günün
    arka planı).
  - **Okuyarak dinleme:** ses çalarken söylenen kelime vurgulanır, kelimeye dokununca oradan çalar (ElevenLabs'in
    karakter zamanlarıyla; ek çağrı yok).
  - 🔁 **Düzeltme çağrısı neyi değiştirdi:** kelime farkı (silinen kırmızı, eklenen yeşil).
- İnen son videonun **dosya adı haber başlığı**; video bitince **hangi sayfadaysan "✅ … videosu hazır" bildirimi**.
- **Aynı haber iki cihazda açıksa uyarı** (Video/Tasarım Stüdyosu; bağlantısı kopmuş oturum sayılmaz).
- **Adım süreleri** `data/olcumler.jsonl` (haber yazımı, seslendirme, analiz, kurgu, son video, tasarım; geliştirici için).
- `axion_app.py`: yeni başlatma noktası (`st.App` = Streamlit'in resmi ASGI yolu) + Tarayıcı'nın akış kanalı.

## Changed
- `guncelle.bat` Axion'u artık kendisi açmaz (editör isteği); masaüstündeki simgeyle açılır.
- **Tarayıcı doğrudan akışla:** kareler Chrome ürettiği anda WebSocket'ten gider, dokunuş/kaydırma/yazı doğrudan gelir
  (jetonlu; yalnız Axion'a girmiş sayfa). Tablet her kareyi gösterince onaylar, en fazla 2 kare yolda: yavaş internette
  gecikme birikmez. Kanal yoksa eski yola düşer. Ölçüm (sandbox, headless Chromium): sürekli kaydırmada ~4 → ~19 kare/sn,
  kaydırmadan yeni kareye 0,27 → 0,15 sn; 10 Mbps/80 ms taklidinde ~17 kare/sn, kaydırma bitince son kare 0,25 sn.
- **Tarayıcı görüntüsü daha net:** sayfa 1,5 kat çözünürlükte çizilir (tablette yazılar büyütülünce bulanıklaşmıyor),
  JPEG 60 → 70 (basit sayfada kare ~67 KB).
- **Tarayıcı düzeni dengelendi:** indirilenler sağ panele (yazının altına) taşındı; solda gezinme, adres ve sekmeler.

## Removed / temizlik
- Okunurluk: `validation/news.py` ve `tts/calibration.py`'deki noktalı virgülle sıkıştırılmış kod açıldı (davranış aynı).
- Başlık yerleşiminde satır dengelemesi her aday için iki kez hesaplanıyordu; bir kez.
- Kayıtlı girişler dosyası Tarayıcı'da saniyede birkaç kez okunuyordu; dosya değişmedikçe bellekten.
- Test ortak hazırlığı `tests/conftest.py`'de; lint artıkları. Sahipsiz modül yok (tarandı).

## Verification
- `make test`: 282 geçti (FFmpeg ve Chromium'la). Yeni testler: akış kanalı (jeton, ack, yalnız hızlı olaylar),
  Windows betikleri ASCII+CRLF ve başlatıcı zinciri, kalite kontrol araçları (uçtan uca Haber Stüdyosu dahil), bildirim,
  iki cihaz uyarısı, ölçüm kaydı.
- Gerçek tarayıcıda: Tarayıcı akışı (kare sayısı, gecikme, yavaş ağ taklidi), okuyarak dinleme (dokun → oradan çal,
  vurgu ilerliyor).
- Windows'ta denenmedi: bekçi betiği (PowerShell), `axion_app.py` ile başlatma, Tailscale üzerinden akış.

# v3.1.0 — Editörün ilk gerçek gün denemesi (4 haber, Windows + tablet) — 2026-09-25

Editör bir günün haberlerini baştan sona Axion'la hazırladı ve geri bildirim yazdı. Hepsi bu sürümde; editörün
Windows'ta yeniden denemesi bekleniyor.

## Fixed
- **Haber Stüdyosu'na dönünce çökme** (`NewsPackage ... tts_alignment ... instance of TTSAlignment`): ses zamanları
  oturumda artık düz veri; Streamlit dosya izleyicisi kapalı (`fileWatcherType = "none"`; modüller yeniden
  yüklenmez, güncelleme zaten Axion'u yeniden başlatır). Regresyon testi.
- **Ses:** tek geçişli `loudnorm` kısa kesitlerde pompalama/bozulma yapıyordu (editör: ilk videonun sonunda kısa bozulma).
  Her parça ölçülüp sabit kazançla hedefe getirilir (seslendirme -18 LUFS, kaynak sesli kesit -20 LUFS), kesit
  kenarları 30 ms yumuşak, sonda -2 dBFS sınırlayıcı ("ses patlamasın"). FFmpeg'li test: tepe ≤ -1,5 dB, kesit spikerin altında.
- Paylaşım metninde röportaj verenlerin adı sansürleniyordu: yalnız şüpheli, mağdur, yaralı, ölen ve çocuklar baş harfle.

## Changed
- **Haber yazımı (istem, az token):** başlıkta il/ilçe adı yok (afet gibi yerin önemli olduğu olaylar hariç); seslendirme
  metni haber spikeri gibi doğal ve canlı (kısa/orta cümle karışık, doğal bağlar, yazı dili yok). Gerçek modelle
  editörün denemesi bekleniyor (AGENTS kural 5).
- **İlk sahne = kapak:** ilk sahnede başlıktaki olayı net gösteren görüntü öne geçer (genel görüntü/manzara/grafik geri
  düşer). Test.
- **Kesit aralığı dakika:saniye** (80 sn yerine 01:20).
- **Çerçeveler kalınlaştı:** kovalayan ışıklar hep görünen bir taban çizgisi ve iki kat uzun kuyrukla (video çıplak
  kalmaz); nefes alan parıltı 4→10 px ve belirgin parıltı; renk akışı 5→8 px (`effects.json`, önizleme ve son video aynı).
- **Varsayılan yazı tipi Google Sans Flex ExtraBold** (aynı tasarımın kalını; Google Fonts, OFL; Türkçe tam). Black da
  seçilebilir. Eski tasarımlar kendi yazı tipini korur.
- **Kenar çubuğu sabit 250 px**, boyutlandırılamaz; sayfalar kazanılan alanı kullanır (içerik 1240 px'e kadar).
- **Tarayıcı yeniden tasarlandı:** kenar çubuğunda geri/ileri/yenile/⌂, adres, **sekmeler (seçilebilir, kapatılabilir)**
  ve indirilenler; ortada 4:3 ekran (yatay tablette dikey alanı doldurur); sağda yazı paneli; dik tutuşta panel alta
  iner. Ana sayfa ayarı ve açıklama kalktı: ⌂ ve açılış `https://dhaabone.dha.com.tr/news`. Düğmeler yeniden tasarlandı.
- **Tarayıcı hızı:** Chrome'un canlı görüntü akışı (CDP screencast; yalnız değişen kare), ekran 0,25 sn'de bir yenilenir,
  dokunuş/kaydırmadan sonra taze kare beklenir, kaydırırken görüntü parmakla hemen kayar. Ölçüm (sandbox, yerel ağ):
  kaydırmadan yeni kareye 0,43 → 0,27 sn. Dükkân internetinde ayrıca ağ gecikmesi eklenir.

## Added
- **📋 Paylaşım metnini kopyala:** Video Stüdyosu'nda video hazır olunca ve Tasarım Stüdyosu'nda İndir'in altında
  (tablette `http://` ile de çalışır: pano API'si yoksa yedek yol; ikisi de tarayıcıda denendi) + kapalı metin.
- **TXT'den haber:** DHA'nın "metni kopyala"sı uzaktan tablete gelmez. "TXT indir" → Tarayıcı'da **📰 Habere aktar**
  ya da Haber Stüdyosu'nun üstündeki **📄 İndirilenler'deki haber metni** → **Aktar** (UTF-8 / Windows Türkçe kodlama).
  Ekrandaki haber temizlenir, önceki kayıtlı proje korunur.

## Verification
- `make test`: 271 geçti, 0 atlandı (bu kez FFmpeg ve Chromium'la; ses, render ve tarayıcı testleri gerçekten koştu).
- Tarayıcı ve kopyalama düğmesi gerçek uygulamada headless Chromium ile denendi (1280×740 yatay, 800×1220 dik):
  sekme açma/seçme, indirme kartı, kenar çubuğu 250 px ve tutamaç yok. TXT aktarma AppTest ile (uygulama içi akış).
- Windows'ta, gerçek DHA'da ve gerçek model/ElevenLabs çağrısıyla denenmedi.

# v3.0.1 — GPT'nin ilk Windows gözlemleri — 2026-09-25

GPT (editörün bilgisayarındaki uygulama) repoyu yerelde inceledi; üç gözlem ve kararlar `reviews/claude-v3.md` sonunda.

## Fixed
- Tasarım Stüdyosu'ndaki üretim 60 sn içinde durmazsa Video Stüdyosu son videoyu artık yazmaz (aynı dosyaya iki
  üretim yazabiliyordu); "Tasarım Stüdyosu'nda yeniden oluştur" der.
- Tersi de: Video Stüdyosu bir haberi üretirken o haberin Tasarım Stüdyosu yeni üretim başlatmaz ("⏳ Video Stüdyosu bu
  haberin videosunu oluşturuyor"), bitince kendiliğinden yenilenir. İki stüdyonun "üretiyor mu → başlat" adımı tek
  kilitte (GPT'nin ikinci turu: sayfadaki kontrolle başlatma arasında yarış kalıyordu).

## Added
- **Axion'u kapat** onayında, arka planda video üretiliyorsa "yarıda kalır" uyarısı.
- `windows/testler.bat`: Windows'ta `make` olmadan test paketi (geliştirici/GPT için).

## Verification
- `make test`: 240 geçti, 25 atlandı. Yeni testler: iptal zamanında bitmezse son video yazılmaz; video üretimi
  sürerken Tasarım Stüdyosu bekler ve `start` de reddeder; kapatma onayındaki uyarı (üretim varken / yokken).

# v3.0.0 — 2.x'in toparlanması: repo incelemesi, DHA giriş kaydı, arka planda video — 2026-09-25

Editörün isteği: 3. sürüme geçmeden tüm repoyu kontrol et, optimize et, toparla, hayat kalitesini artır; DHA girişini
bir kez kaydedip otomatik doldur; Faz 4 ROADMAP'te ihtiyaç halinde dönülecek biçimde kalsın. Bulgular ve kararlar:
`reviews/claude-v3.md`.

3.0 itibarıyla: Faz 0–3 ve 5 tamam, Faz 6'nın temel akışı (tabletten DHA → video → son video) hazır, Faz 4 ertelendi.

## Added
- **DHA girişi bir kez kaydedilir:** Tarayıcı sayfasında giriş formu gönderilirken "girişi kaydedilsin mi?" sorulur;
  kaydedilince sonraki girişlerde kullanıcı adı ve şifre kutuları kendiliğinden dolar (Giriş'e dokunmak yeter).
  **🔑 Girişi doldur** düğmesi, kenar çubuğunda **🔑 Kayıtlı girişler** (Sil). Şifre Windows'ta DPAPI ile şifreli
  (`data/tarayici_girisler.json`), tablete gönderilmez. Şifre değişirse yeniden sorar; "Hayır" denen sorulmaz.
- **🎬 Video Stüdyosu'nda kullan:** Tarayıcıda inen video tek dokunuşla Video Stüdyosu'nda seçili gelir.
- **Video arka planda üretilir:** "Videoyu oluştur" sayfayı kilitlemez; kurgu ve son video bilgisayarda sürer (geçen
  süre görünür), tablet kapansa da biter. Aynı haberin Tasarım Stüdyosu'nda süren üretimi önce durdurulur.
- Üslup örnekleri hatırlanır (`data/ayarlar.json`).

## Fixed
- Haber Stüdyosu'nda başlıklar değişip proje yeniden kaydedilince Tasarım Stüdyosu ve son video eski başlıkları
  kullanıyordu. Artık yeni başlıklar gelir; yalnız Tasarım Stüdyosu'nda yapılan başlık düzenlemeleri (satır kırma,
  sansür) haber değişmedikçe korunur.
- Haber yeniden kaydedilince eski son video da silinir (eski başlık/sesle üretilmişti).
- "Başlıkları yeniden üret" çağrısının token kullanımı toplama eklenmiyordu.
- Video Stüdyosu'nda "Son videoyu indir" videoyu her etkileşimde belleğe okuyordu; artık yalnız tıklanınca.
- "Axion'u kapat" ve `guncelle.bat` Tarayıcı sayfasının görünmez Brave'ini arkada bırakabiliyordu; artık kapatılır.
  Profil kilitli kalmışsa tarayıcı başlarken artık süreci kapatıp yeniden dener (normal Brave'e dokunulmaz).

## Changed
- `news_studio/ai/clients.py`: OpenAI/Claude çağrıları tek yerde (davranış aynı; çağrı biçimi testleri eklendi).
- `news_studio/page.py` okunur biçimde yeniden yazıldı (yıldızlı import ve sıkıştırılmış satırlar kaldırıldı).
- Kesit adımında video süresi dosya başına bir kez ölçülür (FFprobe her etkileşimde çalışmaz).
- Streamlit'in eskiyen `use_container_width` parametresi `width="stretch"` oldu. Ölü kod ve kullanılmayan importlar
  temizlendi.
- `🔑 Şifre` düğmesi `🔑 Girişi doldur` oldu (`DHA_SIFRE` eski yol olarak çalışmaya devam eder).
- README, KURULUM, ROADMAP (Faz 4 "ertelendi; ihtiyaç halinde geri dönülecek", planıyla), AGENTS güncellendi.

## Verification
- `make test` geçti. Gerçek Chromium ile giriş kaydı/otomatik doldurma testleri (6 kez üst üste kararlı), AppTest ile
  arka plan video işi (başarı, hata + yeniden deneme), tasarım işi iptali, başlık eşitleme, yapay zekâ çağrı biçimi.
- Headless Chromium'da tablet boyutunda: giriş → kaydet → yeniden girişte kutuların dolması → indirme → "Video
  Stüdyosu'nda kullan".
- **Windows'ta, gerçek DHA panelinde ve AMD kodlayıcıyla denenmedi** (deneme listesi `reviews/claude-v3.md`).

# v2.10.0 — Tarayıcı: tabletten DHA'ya girip videoyu doğrudan bilgisayara indirme — 2026-09-25

Editörün durumu: dükkân başka ilçede, interneti yavaş (45/13 Mbps). Tablete indirip yüklemek olmaz; bilgisayarı uzak
masaüstüyle kullanmak da (iki monitör, gizli görev çubuğu) pratik değil. Faz 6'nın ilk işi.

## Added
- **🌐 Tarayıcı** sayfası: evdeki bilgisayarda görünmez bir **Brave** (yoksa Chrome; Edge kendiliğinden seçilmez)
  açılır, tablete ekran görüntüsü gelir. Dokun = tıkla, parmakla sürükle = kaydır, ◀ ▶ ⟳ ⌂ ve adres çubuğu, yeni
  sekmeler öne gelir (✕ ile kapanır). Yazı: ekranda kutuya dokun, alttaki kutuya yaz → **Yaz**; ↵ ⌫ ⇥ tuşları; fiziksel
  klavye de çalışır.
- İndirilen dosyalar bilgisayarın **İndirilenler** klasörüne evin internetiyle iner (yarımken `.iniyor` uzantılı,
  Video Stüdyosu'nun listesine karışmaz); sayfada "✅ … bilgisayara indi". Aynı adlı dosyanın üzerine yazılmaz.
- Axion'un kendi tarayıcı profili (`data/tarayici`): DHA'ya bir kez giriş yeter; editörün normal Brave'ine dokunmaz.
- İsteğe bağlı `DHA_SIFRE` (🔑 Şifre düğmesi seçili kutuya yazar), `TARAYICI_YOLU` (brave.exe bulunamazsa).
- Ana sayfa adresi (⌂) kenar çubuğunda, hatırlanır. Tarayıcı 20 dk boşta kalırsa kapanır (indirme sürerken kapanmaz).
- Bağımlılık: `playwright` (yalnızca sürücü; tarayıcı indirmez, bilgisayardaki Brave'i kullanır).

## Changed
- `media_url` ortak modüle taşındı (`apps/axion_local/media.py`); Tasarım Stüdyosu ve Tarayıcı kullanır.
- KURULUM 4. bölüm: DHA videoları artık Tarayıcı sayfasından; uzak masaüstü yedek. ROADMAP Faz 6 güncellendi.

## Verification
- Gerçek Chromium ile testler: yazma (Türkçe), tuşlar, kaydırma, indirme (İndirilenler'e, `.iniyor` kalmadan), yeni
  sekmenin öne gelmesi ve kapanması, paylaşılan tarayıcının yeniden başlaması; olay doğrulama (ekran dışı tıklama, uzun
  metin, bilinmeyen tuş, olay yağmuru sınırı); AppTest ile sayfa (Brave yok uyarısı, ana sayfanın açılıp hatırlanması).
- Headless Chromium'da tablet boyutunda (1180x820, dokunmatik): yerel deneme sitesinde giriş formu, Enter, dokunarak
  video indirme, sürükleyerek kaydırma; 60 sn sürekli değişen ekranda sunucu belleği sabit (164 MB), saniyede 2 görüntü.
- **Gerçek DHA paneliyle ve Windows'ta Brave ile denenmedi.**

# v2.9.1 — GPT incelemesinin ardından: doğrulama testleri, kayıt yarışı düzeltmesi — 2026-09-25

GPT v2.9.0'ı inceledi (`reviews/claude-faz5.md` → "GPT revizyonu"); kararlarına itiraz etmedi.

## Fixed
- Tasarım sayfası ile arka plandaki son video üretimi `tasarim.json`'a aynı anda yazabiliyordu. Biten üretimin
  "güncel" imzası silinebiliyor, nadiren editörün o anki değişikliği kaybolabiliyordu. Artık yazmalar sırayla yapılıyor ve
  imzayı yalnızca üretim yazıyor.

## Added
- Kenar çubuğunda son oluşturmanın süresi ve kodlayıcısı ("Son oluşturma 9 sn · AMD donanım (h264_amf)").
- FFprobe bulunamayınca son video kontrolünün atlandığı `data/axion.log`'a yazılır.
- Gerçek FFmpeg testleri: kırpılmış bölgedeki blur tüm karedekiyle aynı (kenara taşan, dönen, yumuşak kenarlı;
  en kötü kare PSNR 52 dB); kurgu kısa ya da uzun olsa da son video tam süre ve kare sayısında.
- Blur sayısı/boyutuna göre süre ölçümü (`reviews/claude-faz5.md`).

## Changed
- Üst çubuk durum dili birleşti: "✓ Kaydedildi", "✓ Son video hazır", "⚠ Son videoya işlenmedi", "⏳ Son video oluşturuluyor".

## Verification
- `make test` geçti; FFmpeg'li testler ayrıca çalıştırıldı. Windows'ta (AMF, FFprobe, yeniden başlatma) denenmedi.

# v2.9.0 — Son video daha hızlı ve güvenilir — 2026-09-25

Editörün isteği: Tasarım Stüdyosu optimizasyonları. GPT'nin önerileri ve Claude'un ölçümleri karşılaştırıldı; kararlar
`reviews/claude-faz5.md`'de.

## Changed
- **Son video yaklaşık 3 kat hızlı** (18 sn'lik haber, 4 çekirdek, x264; bu ortamda ölçüldü):
  standart şablon 25,7 → 8,8 sn; 6 blur + kovalayan çerçeve 53,5 → 18,8 sn. Görüntü aynı (standart şablonda
  bit bit aynı; blurlu videoda PSNR ≥ 44,8 dB, gözle fark yok).
  - Zemin görseli her karede yeniden okunmuyor; bir kez okunup tekrarlanıyor.
  - Çerçeve ve grafik katmanları kare çoğaltılmadan önce YUV'a çevriliyor (her farklı görsel bir kez).
  - Blur/mozaik yalnızca kutunun geçtiği bölgede ve yalnızca görünür olduğu sürede hesaplanıyor (önce tüm kare
    her an bulanıklaştırılıyordu). Hiç görünmeyen blur videoya eklenmiyor.
- Efekt süre ve mesafeleri tek dosyada: `apps/design_studio/effects.json` (son video ve canlı önizleme aynı dosyayı okur).

## Added
- **Son video kontrolü:** oluşan video FFprobe ile denetlenir (açılıyor mu, 1080x1920 mi, süresi kurguyla aynı mı,
  kurguda ses varsa seste var mı). AMD kodlayıcı bozuk video üretirse x264 ile yeniden denenir; yine bozuksa neden
  kenar çubuğunda yazar. FFprobe yoksa kontrol atlanır.
- **Değişikliklerle yeniden başlat:** son video oluşturulurken tasarım değişirse kenar çubuğunda bu düğme çıkar; eski
  üretim hemen durdurulur (FFmpeg kapatılır), yenisi başlar. Eski tasarımın bitmesi beklenmez.
- Editörün üst çubuğunda son video durumu: "Son video güncel" / "Son videoya işlenmedi" / "oluşturuluyor".
- `tests/test_effects_parity.py`: editor.js'in efekt formüllerini Node'da çalıştırıp Python'la karşılaştırır
  (yazı giriş/çıkış × satır düzenleri, slogan, logo; 0,01 sn adımla). Node yoksa atlanır.

## Fixed
- Eski TV slogan efektinde renk kayması, tam yarıma denk gelen karelerde önizlemeden 1 px farklıydı (Python ile JS
  farklı yuvarlıyordu). Eşlik testi yakaladı.

## Verification
- `make test` geçti. Eski ve yeni son video aynı tasarımla üretilip kare kare karşılaştırıldı. Headless Chromium'da
  üst çubuk durumu (işlenmedi → oluşturuluyor → güncel) denendi.
- FFprobe bu ortamda yok: son video kontrolü sahte FFprobe çıktılarıyla test edildi, gerçek FFprobe ile denenmedi.
  AMD kodlayıcı (h264_amf) ile hız Windows'ta ölçülmedi.

# v2.8.0 — Tasarım Stüdyosu: akıcılık — 2026-09-24

Editör v2.7.0'ı denedi ("sorunsuz çalıştı") ve yalnızca arayüz / kullanım kolaylığı iyileştirmesi istedi.

## Added
- **Geri al / yinele:** üst çubukta ↶ ↷, Ctrl+Z / Ctrl+Y (Ctrl+Shift+Z). Son 60 adım.
- **Klavye kısayolları** (⌨ düğmesinde listesi): Boşluk oynat/durdur, ← → bir kare (Shift: 1 sn), Home/End,
  Ctrl+D seçili blur/yazıyı çoğalt, Delete sil, Esc seçimi bırak / sansür modundan çık, S sansür modu, K blura bu anda
  anahtar kare, L döngü. Metin yazarken kısayollar devre dışı.
- **"Kaydediliyor… / Kaydedildi ✓"** göstergesi (Python değişikliği kaydedince onaylanır).
- **Arka planda render:** "Yeniden oluştur" (ve eski projede ilk açılıştaki otomatik üretim) editörü kilitlemez; kenar
  çubuğunda geçen süre saniyede bir yenilenir, bitince editör yeni videoyu gösterir. Bu sırada yapılan düzenlemeler
  ezilmez (iş yalnızca kendi imzasını yazar; "işlenmedi" uyarısı doğru kalır).
- **Zaman çizelgesi:** klip kenarları oynatma çizgisine, diğer kliplerin kenarlarına ve başa/sona yapışır (mıknatıs);
  klibe çift tıklayınca başına gider.
- Tuvalde üzerine gelince imleç öğeye göre değişir (taşı, boyutlandır, döndür, seç; sansür modunda kelime).
- Döngüde oynatma düğmesi (🔁).

## Fixed
- Eklenen bir yazıda sansür (kelimeye dokunma) Python'da uygulanıyor, tarayıcıdaki kopya eski kalıyordu; sonraki
  değişiklik sansürü geri alabiliyordu. Artık yazılarda sansür tarayıcıda uygulanır (geri alınabilir); başlıklarda
  kenar çubuğundaki metne yazılır.
- İndir düğmesi son videoyu her etkileşimde belleğe okumuyor; yalnızca tıklanınca okunur.

## Verification
- `make test` geçti. Headless Chromium'da: blur ekleme, Ctrl+D, iki kez geri al, yinele, Shift+→, arka planda render
  sırasında mozaik ekleme ve bitince durumun güncellenmesi denendi. Windows'ta denenmedi.

# v2.7.0 — Tasarım Stüdyosu Canva düzeninde — 2026-09-24

Editör v2.6.0'ı denedi: işlevler çalışıyor, düzen kullanışsızdı (boş alanlar, dağınık araçlar, zor zaman çizelgesi).

## Changed
- **Yeni düzen (Canva örneğiyle):**
  - Kenar çubuğu: son video durumu, **Yeniden oluştur**, **İndir**, iki başlığın metni (sığma göstergesiyle),
    yazı tipi / arka plan ekleme.
  - Ortada video (ekran yüksekliğine göre boyutlanır); **Düzenle / Son video** geçişi.
  - Üstte seçili öğeye göre araç çubuğu: yazı için yazı tipi, kalınlık, − boyut +, renk, **S̶ sansür**, aA, parıltı;
    blur için efekt, şekil, 1:1, sil.
  - Solda seçili öğenin paneli: yazılar için **animasyon kartları** (Girişte / Çıkışta, hareketli önizlemeyle),
    eklenen yazının metni ve zamanı; blur için geniş kaydırıcılar (güç, opaklık, yumuşak kenar, açı), zaman, anahtar
    kareler, canlı takip.
  - Sağda arka plan küçük resimleri, video çerçevesi kartları, renkler, hız, slogan/logo seçimi.
  - Altta **katmanlı zaman çizelgesi**: Başlık (başlıklar + sloganlar), Yazı, Logo, Blur/Mozaik (anahtar karelerle),
    Video (kare şeridi), Arka plan; saniye cetveli, sürüklenebilir oynatma çizgisi; yazı ve blur klipleri sürüklenerek
    kaydırılır, kenarından uzatılır.
- **Sansür Canva gibi:** başlığı/yazıyı seç, S̶'ye bas, videoda kelimeye dokun (üstü çizilir, tekrar dokununca kalkar).
- Tasarım sayfası tüm ekran genişliğini kullanır.

## Removed
- Paylaş düğmesi (editör: kullanışsız) ve tasarım sayfasındaki paylaşım metni. KURULUM'daki HTTPS/Paylaş adımları
  yerine "tabletten çalışırken videolar nerede durur" açıklaması.

## Verification
- `make test` geçti. Headless Chromium'da: başlığa dokunup seçme, animasyon kartı, boyut, sansür (kelimeye dokununca
  metinde ~~…~~), blur ekleme, zaman çizelgesinde blur klibini taşıma (anahtar kareler birlikte) ve uzatma denendi.
- Windows'ta ve tablet dokunmatiğinde denenmedi.

# v2.6.0 — Tasarım Stüdyosu: sade Canva, başlık 2 satır kuralı, otomatik son video — 2026-09-24

## Added
- **Başlıklar videoda 2 satıra sığar (editörün temel kuralı):** başlık videodaki yazıyla (Google Sans Bold 58 px,
  920 px) piksel olarak ölçülür (`shared/text_layout.py`). Prompt'lara "EN FAZLA 44 KARAKTER" eklendi; sığmayan
  başlık kalite kontrolünde hata sayılır ve mevcut tek düzeltme çağrısına "yaklaşık x karakter kısalt" hedefi gider.
  Haber Stüdyosu'nda başlık kutularının altında canlı gösterge: "✅ Videoda: MANSUR YAVAŞ / CHP'DEN İSTİFA ETTİ".
- **Otomatik son video:** Video Stüdyosu'nda "Videoyu oluştur" kurgudan hemen sonra Axion şablonunu uygular;
  editör Tasarım Stüdyosu'na gelmeden **Son videoyu indir** hazır. Eski projelerde Tasarım Stüdyosu açılınca üretilir.
- **Tasarım Stüdyosu yeni arayüz:** solda canlı önizleme (tuval: video, blur/mozaik, çerçeve animasyonu, başlık/slogan/
  logo/yazı efektleri son videodaki gibi oynar; kare kare ileri/geri, 0,5x/0,25x) ve son video; sağda durum
  ("hazır ve güncel" / "değişiklikler işlenmedi"), Oluştur, İndir, **Paylaş** ve sekmeler:
  - **Başlıklar:** metin, giriş/çıkış animasyonu (Birleşerek, Belirerek, Alttan kayarak, Daktilo, Büyüyerek, Yok),
    **sansür** (seçilen kelimenin üstü çizilir), yazı tipi, kalınlık, boyut, renk, parıltı, BÜYÜK HARF.
  - **Yazılar:** videoya kalıcı yazı ekleme (metin, stil, görünme aralığı, animasyon; konumu tuvalde sürükleyerek).
  - **Efektler:** çerçeve stili (sabit, **kovalayan ışıklar** — simetrik, kalından inceye —, nefes alan parıltı,
    renk akışı, yok), renkler ve hız; sloganlar ve logo kutusu aç/kapat ve efekt seçimi.
  - **Arka plan:** küçük resimlerden seçim ("Günün" varsayılan, her gün 02:00'de sıradaki).
  - **Varlıklar:** yazı tipi (.ttf/.otf) ve arka plan ekleme; `data/varliklar/`'a yazılır, `GITHUB_TOKEN` varsa
    GitHub'a da yüklenir. Değişken fontların kalınlıkları ayrı seçenek olur.
- **Blur v2:** mozaik efekti; şekiller dikdörtgen/kare (▢ Kare), yuvarlak köşeli, elips/daire; **döndürme** (tutamaç veya
  açı kaydırıcısı, anahtar karelerle takip edilir); **yumuşak kenar** (opaklık kenara doğru solar); ◆ anahtar kareler
  arasında gezinme ve silme.
- **Paylaş düğmesi:** tablette son videoyu doğrudan Android paylaşım menüsüne verir (Instagram, TikTok, YouTube).
  HTTPS gerektirir: KURULUM'a Tailscale serve adımları eklendi.
- `.streamlit/secrets.toml.example`: isteğe bağlı `GITHUB_TOKEN`.

## Changed
- `tasarim.json` sürüm 2; v2.5.0 dosyaları otomatik yükseltilir (başlıklar, arka plan, blurlar korunur).
- Şablon katmanları: yazılar kelime kelime sprite (parıltı, sansür çizgisi dahil), tek grafik katmanı; çerçeve
  döngüsel animasyonda yalnızca bir periyot çizilir. Farklı kareler paralel yazılır (4 çekirdekte katman hazırlığı
  varsayılan tasarımda ~2 sn, kovalayan çerçeveyle ~6 sn).
- Yazı tipleri `shared/fonts.py` kaydından (repo + uygulamadan eklenenler).

## Verification
- `make test`: tümü geçti (FFmpeg'siz ortamda FFmpeg testleri atlanır; FFmpeg ile son video testi — 1080x1920,
  blur + mozaik, ses — geçti).
- Headless Chromium'da elle denendi: tasarım sayfası, v1 belgesinin yükseltilmesi, efekt seçimi, yazı ekleme ve tuvalde
  sürükleme (konum kaydı), tuvalde animasyonlar (merge, eski TV, logo, ışık geçişi), "Yeniden oluştur" ile yazı katmanlı
  ve kovalayan çerçeveli son video.
- **Denenmedi:** gerçek model çağrısıyla başlık kısaltma (API anahtarı yok), Windows/AMD kodlayıcı, tablette Paylaş
  (HTTPS), GitHub'a yükleme (yalnızca sahte sunucuyla test).

# v2.5.0 — Tasarım Stüdyosu: Canva'nın yerine Axion şablonu ve elle blur (Faz 5) — 2026-09-24

## Added
- **Tasarım Stüdyosu son videoyu kendisi hazırlar (1080×1920, sesiyle):** günün arka planı (8'li sıra, her iş günü
  02:00'de sonrakine geçer), beyaz çerçeveli yuvarlak köşeli video alanı, 1. başlık (0–9 sn, "merge" çıkışı), iki
  slogan ("old tv"), 2. başlık (13. sn'den sona, kelime kelime "merge" girişi), alttan yükselen logo kutusu (ışık
  geçişiyle). Ölçü ve zamanlar editörün Canva örneğinden kare kare ölçüldü. Tek FFmpeg komutu; önce AMD donanım
  kodlayıcısı, olmazsa x264. API/token yok.
- Başlıklar sayfada düzeltilebilir (Enter ile satır bölme; yoksa en dengeli 2 satır, sığmazsa yazı küçülür).
  Arka plan elle de seçilebilir. Ayarlar projeye kaydedilir (`tasarim.json`).
- **Canlı önizleme:** 9:16 tuvalde arka plan, video, çerçeve, o anki başlık/slogan ve logo; oynat, 0,5x/0,25x, zaman
  çizelgesinde şablon öğeleri ve blurlar.
- **Elle blur (plaka/yüz):** kutu ekle; şekil (dikdörtgen, yuvarlak köşeli, elips), güç, opaklık; videoyu bir ana
  getirip sürükle/boyutlandır → anahtar kare, kutu aralarda doğrusal kayar; başlangıç/bitiş "şu an"; anahtar kareler
  arasında gezinme ve silme; **canlı takip** (basılı tutunca video yavaş oynar, yol kaydedilir). Son videoda aynı
  hareketle Gauss bulanıklığı. Otomatik tespit yok (editör kararı).
- Şablon dosyaları `assets/sablon/` (editörden): 8 arka plan, logo, slogan görselleri, Google Sans Bold (SIL OFL)
  ve örnek Canva videosu.
- Son video değiştiyse uyarı: başlık, arka plan, blur veya kurgu değişince "yeniden oluştur".

## Changed
- Yazı tipi Binate Bold yerine Google Sans Bold (editör kararı; lisansı serbest).
- `shared/axion_template.py` Canva örneğinden ölçülen değerlerle güncellendi; slogan 1 "TARAFSIZ VE ŞEFFAF HABERCİLİK".
  Logo kutusu örnekteki gibi 15,03–17,69 sn (notlardaki 16–19 sn yerine).
- Faz 4 (Luna Edit Planner) ertelendi; blur Faz 6 yerine Tasarım Stüdyosu'nun elle kullanılan aracı oldu (ROADMAP).

## Verification
- `make test`: 175 geçti, 21 atlandı (FFmpeg'siz). FFmpeg ile son video testi (1080x1920, blur, ses) geçti.
- Editörün Canva örneğinin görüntüsüyle yan yana karşılaştırıldı (başlık yeri/boyutu, çerçeve, slogan ve logo zamanları).
- Tarayıcı editörü headless Chromium'da elle denendi: blur ekleme, iki anda sürükleme (ara karede kayma), canlı
  takip, kayıt ve "Son videoyu oluştur" düğmesiyle blurlu 1080x1920 çıktı.
- Editörün Windows'ta gerçek haberle denemesi bekleniyor (animasyonların Canva'ya benzerliği, yazı tipi, AMD kodlayıcı).

# v2.4.0 — Faz 3 kod incelemesi düzeltmeleri — 2026-09-24

GPT ve Claude incelemesinin sonucu (`reviews/`). Kullanıcıya görünen davranış aynı; daha hızlı, daha ucuz, daha sağlam.

## Changed
- Luna görsel analizi düşük düşünme seviyesiyle (`low`) çalışır; 180 sn zaman aşımı.
- Analiz kopyası (proxy) 640 px, sessiz ve en hızlı ayarla üretilir: görüntü analizi daha kısa sürer.
- Video başına Luna'ya en fazla 40 kare gider (yüksek analiz yoğunluğunda maliyet tavanı).
- Render tek kadraj yoluna indirildi; bulanık dolgu kodu tamamen kaldırıldı.

## Fixed
- Otomatik silmede silinemeyen klasör artık sessizce "silindi" sayılmıyor; `data/axion.log`'a yazılır, ertesi gün
  yeniden denenir. Temizlik hatası uygulamanın açılmasını engellemez.
- Tarayıcıdan yüklenen dosya yalnızca ad+boyutla eşleştiriliyordu; artık SHA-256 ile.
- Kesit olarak seçilen aralık, aynı sahnenin komşu kısmından uzayan dolgu görüntüsüyle tekrar görünebiliyordu.
- Kesit videonun süresini aşıyorsa açık hata; sonu taşıyorsa kırpılır.
- FFmpeg sahne tespiti hata verirse video sessizce tek sahne sayılıyordu; artık hata gösterilir.
- Yarıda kalan analiz geçici klasörde proxy/kare bırakıyordu.

## Removed
- Kullanılmayan kod: `validate_edit_project`, `add_timeline_item`, `add_news_segment`, `build_news_package`,
  `save_news_package`, kadraj modu parametreleri.

## Verification
- `make test`: 178 test geçti (gerçek FFmpeg ile). Gerçek Luna çağrısı ve Windows E2E editörde.

# v2.3.0 — Dikey çekimlerde güvenli kaydırma — 2026-09-24

## Fixed
- Dumanlı, gece veya yumuşak görüntülü dikey çekimlerde (Kars yangını) bulanık kenar tespit edilemiyor, kadraj yatay
  kayarken DHA'nın bulanık kenarına giriyordu. Luna artık her sahne için "dikey çekim, yanları dolgulu" bilgisini de
  veriyor; tespit kaçırırsa görüntü ortadaki 9:16 alana kilitlenir.

## Changed
- Kaydırma kuralı: yanları dolgulu dikey çekimde yalnızca yukarı/aşağı; tam 16:9 görüntüde yatay, dikey veya çapraz.
- Kaydırma hızı saniyede kare genişliğinin %3'ü.
- Luna prompt v2.5: önceki analizler için yeniden analiz istenir.

## Verification
- `make test` geçti (Kars durumu ve kaydırma yönü regresyon testleri dahil). Windows testi bekleniyor.

# v2.2.1 — Haberler 3 gün saklanır — 2026-09-24

## Changed
- Haber projeleri en fazla 3 iş günü (bugün + önceki 2 gün) saklanır; daha eskileri her gün ilk açılışta otomatik
  silinir (ses, analiz, kesitler, kurgu, video ve önizlemeler dahil). Üretim geçmişindeki eski kayıtlar da silinir.
  İndirilenler'deki kaynak videolara dokunulmaz.

## Verification
- `make test` geçti (3 gün sınırı ve proje olmayan klasöre dokunulmaması testleri dahil).

# v2.2.0 — Her gün taze başlangıç, metin düzenleme düzeltmesi — 2026-09-24

## Fixed
- Haber Stüdyosu'nda metin kutusunu düzenleyip dışına tıklayınca değişikliğin kaybolup ilk hâline dönmesi
  (seslendirme metni, paylaşım metni, başlıklar, ham haber). Metinler sayfa değiştirince de korunur.

## Changed
- Video ve Tasarım stüdyosu açılışta haber seçili gelmez; Haber Stüdyosu'ndan geçince kaydedilen haber seçilidir.
- Haber listesi her gün 02:00'de (bilgisayar saati) sıfırlanır; "Önceki günler" ile eski haberler seçilebilir.
- Geniş özne kaydırması daha yavaş (saniyede kare genişliğinin %2,5'i).

## Verification
- `make test` geçti (taze açılış, 02:00 sınırı, düzenlenen metnin korunması testleri dahil). Windows testi bekleniyor.

# v2.1.0 — Bulanık dolgu yok, okunabilir saatler — 2026-09-24

## Changed
- Video alanı her sahnede tam dolu; hiçbir yanda bulanık dolgu yok. Kadraj haberin ana öznesine kayar; özne çok
  genişse (ör. yandan otobüs) kadraj sahne boyunca onun üzerinde yavaşça kayar. "Akıllı / Tüm kare" seçimi kaldırıldı.
- Seslendirme metninde saat, tarih, binlik ve ondalık sayılar okunuşuna çevrilir: "saat 18.00'de" → "akşam 6'da",
  "09.30'da" → "sabah 9 buçukta", "24.09.2026'da" → "24 Eylül'de", "1.500" → "1500", "2,5" → "2 buçuk".
  Haber üretiminde ve "Seslendir"de uygulanır; çevrilemeyen sayı için uyarı çıkar. Yönergeye kural eklendi.

## Verification
- `make test` geçti: tam dolu kadraj ve kaydırma (gerçek FFmpeg render), saat/tarih dönüşümü regresyon testleri
  (Kayseri haberi). Windows testi bekleniyor.

# v2.0.0 — Kaynak sesli kesitler, adım adım Video Stüdyosu, Tasarım Stüdyosu — 2026-09-24

## Added
- **Kaynak sesli kesitler:** videodan bir bölüm kendi sesiyle seslendirmenin önüne (dikkat çekici an) veya arkasına
  (röportaj) eklenir. Önizleme oynatıcısı + aralık kaydırıcısı; birden fazla kesit; analizden önce de seçilebilir.
  Kesit sesi ile seslendirme aynı ses yüksekliğine getirilir; kesit görüntüsü dolgu olarak tekrar kullanılmaz.
- **Tasarım Stüdyosu** sayfası: video ve kopyalamaya hazır başlıklar/paylaşım metni. Faz 5'te Canva'nın yerini alacak.
- Video Stüdyosu'ndan "Tasarım Stüdyosu'na geç".

## Changed
- Video Stüdyosu adım adım: 1. Haber → 2. Görüntüler → 3. Kaynak sesli kesitler → 4. Video. Biten adım tek satırlık
  özete daralır; ayarlar "⚙️ Ayarlar" düğmesinde.
- Arayüz terimleri Türkçe: "Video Studio" → "Video Stüdyosu", TTS → seslendirme metni, caption → paylaşım metni,
  shot → sahne, Speaker Boost → ses netliği artırma, Input/Output → girdi/çıktı token. Doğrulama uyarıları da Türkçe.
- Video en az 20 sn kuralı artık seslendirme + kesitlerin toplamına uygulanır.

## Verification
- `make test` geçti (163 test): kesit planı, kesit sesinin gerçekten duyulduğu render testi, kesit seçicinin uçtan uca
  arayüz testi, Tasarım Stüdyosu. Arayüz gerçek tarayıcıda ekran görüntüsüyle kontrol edildi. Windows testi bekleniyor.

# v1.9.4 — Özneyi kesmeyen kadraj, daha az token — 2026-09-24

## Changed
- Akıllı kadraj: Luna ana öznenin tamamını içeren kutuyu verir; kadraj özneyi asla kesmez ve olabildiğince az
  yakınlaştırır. Özne dikey alana sığmayacak kadar genişse (ör. yandan minibüs) üst/alt bulanık dolguyla tamamı gösterilir.
- Kadraj seçenekleri: "Akıllı" (önerilen) ve "Tüm kare" (önceki "Doldur"/"Bulanık kenar").
- Yanları bulanık dikey çekimlerde kadraj ortalanıyor ve güvenlik payı %2 (tek yanda ince bulanık şerit kalıyordu).
- Luna'ya gönderilen analiz kareleri 640 px genişlikte (önce 960): girdi token'ı azalır.
- Luna prompt v2.4: önceki analizler için yeniden analiz istenir.

## Verification
- `make test` geçti: geniş özne tam görünür, dar özne alanı tam doldurur (gerçek FFmpeg render testleri).
  Windows'ta yeni bir haberle doğrulanacak.

# v1.9.3 — Doğal kesmeler ve bulanık kenarın tamamen atılması — 2026-09-24

## Changed
- Sahne geçişleri seslendirmedeki duraklamalara konuyor (cümle sonu, virgül, nefes arası); her sahne 2–5 sn.
  Önceki sürüm sabit ≤3 sn parçalara bölüyordu, bazı geçişler 1 sn'nin altına düşüyordu.
- Sahne, o aralıkta söylenen kelimelere göre seçiliyor (cümlenin tamamına göre değil).
- Yanları bulanık dikey çekimlerde bulunan alan standart orana (9:16, 1:1, 4:3) daraltılıyor; gerçek DHA videosunda
  kenarda kalan bulanık şerit gideriliyor.

## Fixed
- "Saat 17.00" gibi saat/sayılardaki nokta cümle sonu sayılıyordu; ayrı ve çok kısa bir sahneye yol açıyordu.

## Verification
- `make test` geçti (Manavgat videosundaki gerçek tespit değerleriyle regresyon testi dahil). Windows testi bekleniyor.

# v1.9.2 — Video en az 20 saniye — 2026-09-24

## Changed
- Şablon videosu en az 20 sn: seslendirme daha kısaysa kurgu 20 sn'ye tamamlanır, son sahne sessiz devam eder.
  EditProject doğrulaması "timeline ≤ TTS" yerine "timeline ≤ max(TTS, 20 sn)".
- Şablon zamanları (9/13/16. sn) sabit olarak kaydedildi (editör onayı).

## Verification
- `make test` geçti (15 sn TTS → 20 sn kurgu ve 4 sn TTS → 20 sn MP4 render testleri dahil).

# v1.9.1 — Kurgu ölçüsü Canva şablonuna göre — 2026-09-24

## Changed
- Kaba kurgu 1080×1440 yerine Canva şablonundaki video alanının ölçüsünde üretiliyor: 960×1226 (alan 960×1225;
  H.264 çift sayı istediği için 1 px fazla). Canva'da ikinci kez kırpma gerekmez.
- Eski ölçüdeki kurgu projeleri açılışta yeniden kuruluyor.

## Added
- `shared/axion_template.py` ve ROADMAP'te Axion Canva şablonunun tam tanımı (Faz 5 için): başlık, slogan ve logo kutusu
  konum/zaman/animasyonları, yazı tipi, arka plan rotasyonu.

## Verification
- `make test` geçti.

# v1.9.0 — Akıllı kadraj — 2026-09-24

## Added
- Bulanık/siyah kenar tespiti: DHA'nın yatay formata bulanık kenarlarla koyduğu dikey çekimlerde asıl görüntü alanı
  analiz karelerinden bulunur (API yok). Kurgu bu alandan kadrajlanır; bulanık kenar videoya girmez.
- Odak noktası: Luna her pencere için ana öznenin konumunu verir (birkaç token). "Doldur" kadrajı bu noktaya ortalanır.
- "Bulanık kenar" modunda arka plan, DHA'nın bulanık kenarından değil asıl görüntüden üretilir.
- Geliştirici kurgu tablosunda odak ve kenar kırpma bilgisi.

## Changed
- Luna prompt sürümü v2.3: önceki analizler için "yeniden analiz et" bilgisi çıkar (yaklaşık yarım sent).

## Verification
- `make test` geçti; sentetik DHA tipi (bulanık kenar + logo), siyah bantlı, tam kare ve tek yanı düz videolarla
  tespit testleri ve iki kadraj modunda gerçek FFmpeg render testleri dahil. Gerçek DHA videolarıyla Windows testi bekleniyor.

# v1.8.0 — Faz 3: ilk otomatik kaba kurgu — 2026-09-24

## Added
- Video Studio "3. Video": TTS cümlelerine sahneleri kurallarla eşleştiren kaba kurgu (API çağrısı yok, ek maliyet yok).
  Kesitler en fazla 3 sn; röportaj görüntüsü sessiz dolgu olarak kullanılmaz, aynı sahne art arda gelmez.
- "Videoyu oluştur": FFmpeg ile 1080×1440 MP4 (`kaba_kurgu.mp4`, proje klasöründe), sayfada önizleme ve indirme.
  AMD donanım kodlayıcı (h264_amf) varsa kullanılır, yoksa x264.
- Kadraj seçimi: Doldur (kırp) / Bulanık kenar; son seçim hatırlanır.
- Geliştirici bilgilerinde kurgu tablosu (hangi cümleye hangi sahne kesiti).

## Changed
- `ClipOrigin` sözleşmesine `rule` eklendi.
- FFmpeg çıktısı UTF-8 okunuyor (Windows'ta Türkçe dosya adlarında çözme hatası riskine karşı).

## Verification
- `make test` geçti (Linux, gerçek FFmpeg ile iki kadraj modunda 1080×1440 render testi dahil).
- AMD kodlayıcı ve gerçek DHA videosuyla render editörün Windows testinde doğrulanacak.

# v1.7.1 — Luna sınıflandırma düzeltmesi ve uzun shot pencereleri — 2026-09-24

## Fixed
- Luna sonuçlarında `visual_type`/`editorial_role` `unknown`, `description` boş kalıyordu: açıklama yanlış alana
  yazılıyordu ve serbest metin kategoriler enum'a eşlenemiyordu. Luna şeması artık enum'lu; tüm alanlar aktarılıyor.
- Eski formatta kayıtlı `media_library.json` Video Studio'yu çökertiyordu; artık "yeniden analiz et" bilgisi gösteriliyor.
- Tarayıcıdan yüklenen görsel analizden sonra silinip ardından okunmaya çalışılıyordu (çökme); proje `media/` klasöründe kalıyor.
- Yüklenen dosya adları `hash()` ile (her açılışta farklı) üretiliyordu; aynı dosya yeniden yüklenince kopya birikmesi önlendi.
- v1.7.0 ile kırılan 3 test düzeltildi.

## Added
- Uzun shot'lar en fazla 10 sn'lik analiz pencerelerine bölünüyor (tek Luna çağrısı korunuyor); her pencerenin kendi görsel analizi var.

## Verification
- `make test` geçti (Linux). Gerçek Luna çağrısı ve Windows doğrulaması editör tarafından yapılacak.

# v1.7.0 — Faz 2 sözleşme geçişi — 2026-09-24

## Changed
- Video Studio medya çıktısı shared.media_models 2.1 sözleşmesine taşındı.
- Medya kaynaklarına gerçek SHA-256 kimliği eklendi.
- Luna görsel sınıfları ortak VisualType / EditorialRole enum değerlerine normalize ediliyor; ek API çağrısı eklenmedi.
- EditProject üretimi shared.edit_models 2.1'e taşındı.
- Eski 1.1 EditProject dosyaları açılışta kullanılmıyor; yeniden oluşturuluyor.
- Browser upload medya kaynakları aktif proje altında media/ klasöründe saklanıyor.
- TTS audio metadata'sında gerçek SHA-256 tutuluyor.
- Faz 2 için ortak sözleşme regresyon testi eklendi.
- Gerçek Windows testinde medya analizi ve EditProject üretimi doğrulandı: 157.28 sn video, 15 shot, 21.27 sn TTS timeline.
- EditProject TTSAlignment süre erişim hatası düzeltildi; syntax/import hataları giderildi.

## Verification
- Kod GitHub main üzerinde doğrudan güncellendi.
- Bu oturumda gerçek Windows/FFmpeg ortamında make test çalıştırılmadı; Windows uçtan uca doğrulama açık test adımıdır.

# v1.6.1 — 2026-09-24

## Changed
- Removed the logo from the sidebar and the password screen; the sidebar starts with the page links. The Axion X mark stays only as the browser tab icon and the desktop icon.
- The desktop icon file is renamed to `windows/axion_x.ico` so Windows' icon cache picks up the new X mark. `guncelle.bat` now recreates the desktop shortcut on every update.

# v1.6.0 — Axion branding, remembered settings, leaner Video Studio — 2026-09-24

## Changed
- White theme in the Axion logo colours (navy `#123249` primary, light blue and green accents). The logo is in the sidebar above custom page links; the X mark is the browser tab icon and the new `windows/axion.ico`.
- Haber Stüdyosu sidebar:
  - style, duration, AI provider, model, reasoning level and voice are always visible;
  - voice fine-tuning sits in a collapsed "Ses ince ayarları" section;
  - all of these settings are remembered across sessions in `data/ayarlar.json` (`apps/axion_local/preferences.py`).
- Video Studio:
  - the shot table moved to developer info;
  - the news text box was removed; the text comes from the project;
  - browser upload became a toggle under "Gelişmiş";
  - status is a single line.

# v1.5.0 — Timed TTS (Faz 1) and a simpler interface — 2026-09-24

## Added
- Faz 1: ElevenLabs `convert_with_timestamps` returns the audio and per-character timings in one call, at no extra cost. The timings are stored as `TTSAlignment` in `news_package.json`. An alignment that does not match the text exactly is dropped; the audio is still used. TTS text is trimmed before synthesis.

## Changed
- Haber Stüdyosu:
  - the sidebar shows only style, duration and voice; AI engine, reasoning level and voice sliders moved under "Gelişmiş ayarlar";
  - headlines sit side by side; validation notes are grouped in one "Kontrol et" box;
  - token usage moved to a collapsed "Geliştirici bilgileri" section;
  - "Sistemi Sıfırla" became "Yeni haber" and keeps the voice and engine choices.
- Video Studio:
  - the steps are "1. Haber" and "2. Görüntüler"; the news text sits in a collapsed section;
  - folder and analysis density moved under "Gelişmiş";
  - the EditProject is built and saved automatically when news, audio and media are ready (no button);
  - cost and the project folder moved to developer info.
- Axion red is the primary colour in both light and dark themes (the system theme is followed). Page top padding is tighter. "Axion'u kapat" sits at the bottom of the sidebar.

# v1.4.0 — Fully local, single linked app — 2026-09-24

## Changed
- Streamlit Cloud support removed. Axion runs only on the editor's PC:
  - no `AXION_LOCAL` mode switch;
  - no per-page passwords (the optional password lives only in `axion_local.py`);
  - no NewsPackage JSON download or upload, no TTS upload;
  - `packages.txt` and `REPO_MANIFEST.txt` deleted.
- Pages renamed to `apps/news_studio/page.py` and `apps/video_studio/page.py`; `axion_local.py` is the only entry point. Streamlit settings moved to `.streamlit/config.toml`.
- News → Video linking:
  - "Kaydet ve Video Studio'ya geç" saves the project and opens it in Video Studio;
  - re-saving the same raw news updates the same project instead of creating a new one;
  - the sidebar shows the active project.
- Video Studio page rewritten (1140 → about 230 lines) in the order 1. news project → 2. media → 3. project:
  - the media pipeline moved to `modules/media_pipeline.py`;
  - a time-coded shot table (usable for manual CapCut cuts) is shown;
  - media analysis and the EditProject are saved to the project folder and restored when the project is reopened, so Luna does not run again.
- Proxy videos and analysis frames are deleted after analysis; previously they piled up in the temp folder.
- News Studio data files use the fixed `data/` folder (`AXION_DATA_DIR`) regardless of the working directory.
- Axion no longer starts with Windows; it runs only when the desktop icon is clicked. `kisayol.ps1` removes the old Startup shortcut.

## Added
- `AGENTS.md`: shared guide for AI developers (rules, code map, where we left off, known debts). `CLAUDE.md` imports it. README rewritten; KURULUM.md covers phone access and full remote desktop.

# v1.3.1 — Axion Local polish — 2026-09-24

## Changed
- Password is optional in local mode: an empty `APP_PASSWORD` opens Axion directly. The apps no longer require `APP_PASSWORD` in local mode. Streamlit Cloud still requires it.
- Windows launcher `windows/axion_baslat.vbs` replaces the console `.bat`:
  - no console window; the log goes to `data/axion.log`;
  - if Axion is already running, it only opens the browser;
  - it waits up to 60 s and opens the log if startup fails.
- `kurulum.bat` creates a desktop shortcut with the Axion icon and a Startup shortcut that launches Axion in the background at login (`windows/kisayol.ps1`). The Streamlit "Deploy" toolbar is hidden.
- "Axion'u kapat" button in the sidebar, shown only when Axion is opened on the home PC itself (Host header is localhost), so it cannot be closed from the tablet by mistake.
- `windows/anahtarlar.bat` opens the API key file. `windows/sorun_giderme.bat` runs Axion in a visible console for troubleshooting. `guncelle.bat` stops, updates and restarts Axion.

## Fixed
- Video Studio's news text box no longer empties when switching between pages.

# v1.3.0 — Axion Local (Faz 0) — 2026-09-24

## Added
- `axion_local.py`: Haber Stüdyosu and Video Studio run as one Streamlit app with one password (`st.navigation`). The modules stay separate.
- `apps/axion_local/store.py`: persistent project folder (`data/projects/<time>_<headline>/news_package.json + tts.mp3`) and media inbox listing (default `~/Downloads`, overridable with `AXION_DATA_DIR` / `AXION_INBOX_DIR`).
- News Studio (local mode only): "Projeye kaydet" stores the package together with the audio and its sha256. Saving is blocked when the TTS text changed after the audio was generated.
- Video Studio (local mode only):
  - media can be picked from a local folder and is read in place, without upload or copy (`LocalMediaFile`);
  - saved news projects load caption and TTS audio directly; the audio hash is verified.
- Windows `windows/kurulum.bat`, `axion_baslat.bat`, `guncelle.bat` and the Turkish guide `KURULUM.md` (Tailscale access from the tablet).

## Unchanged
- News generation, prompts and validation. The Streamlit Cloud behaviour of both apps is unchanged outside local mode.

# v1.2.0 — Viral TTS quality — 2026-09-24

## Changed
- News prompt tuned for Turkish social media:
  - first TTS sentence carries the most striking event;
  - every sentence must add new information (restating an event or a number counts as repetition);
  - the duration target is an upper bound — add unused facts, otherwise finish short;
  - conversational tone without agency phrases, semicolons or street-level addresses;
  - no license plates or ID-type details;
  - witness guesses are attributed, not stated as fact;
  - the two headlines must not repeat each other or use verbs that are not in the source.
- Structured output gains `tts_plani` (one short line per TTS sentence, before `tts`), so the model plans distinct facts inside the same call. No extra API call.
- Validation:
  - TTS below the target is now a warning instead of an error, so it no longer triggers a correction call. Below 60% of the minimum is still an error; above the maximum still is too.
  - Heuristic repetition warning for TTS sentences (a shared number plus a shared word stem, or 3+ shared stems).
  - `NN ABC NNN plakalı` is removed automatically, with a warning.
  - TTS semicolons are split into sentences.

## Cost
- About +345 input tokens per request, mostly in the cached system prompt, and about +60 output tokens for the plan. Under-length TTS no longer costs a second request.

# v1.1.2 — Contract revision and fixes — 2026-09-24

## Fixed
- Video Studio: Luna image data URLs were sent as the literal text `{image_mime_type(...)}` (missing f-string), breaking visual analysis for every video. Frames and standalone images now both use the real MIME type from the file extension (`image_data_url`).
- Video Studio: every FFmpeg/FFprobe call goes through `modules/ffmpeg_runner.py`. Probe and frame extraction: 60 s. Proxy transcode (previously no timeout) and scene detection: 4× video duration, clamped to 300–3600 s. A timeout raises a readable `RuntimeError`, and temporary proxy/frame files are removed.
- Video Studio: wrong password now shows "Şifre yanlış."; password comparison uses `hmac.compare_digest`.
- News prompt: the caption source instruction was truncated ("ek." → "ekle.").
- News prompt: `build_correction_prompt` no longer uses a backslash inside an f-string expression (SyntaxError on Python < 3.12). Prompt output is unchanged.
- Retry: `anthropic.OverloadedError` (529) is now treated as transient. The OpenAI/Anthropic SDK internal retries are disabled (`max_retries=0`), so `retry_transient` is the only retry layer (previously up to 3×3 = 9 requests).

## Contract (shared/)
- NewsPackage: `parse_news_package` is the single entry point for every version. 1.0 files (flat, nested `news`, Turkish field names, `schema_version: null`) are migrated to 1.1. Unknown legacy fields are kept under `metadata.legacy_fields`.
- Video Studio's NewsPackage import now uses the shared contract instead of its own parser.
- NewsReference validates `tts_alignment` against `tts_text`.
- EditProject cross-validation:
  - segment text equals `tts_text[char_start:char_end]`;
  - segments are ordered, non-overlapping and cover the whole `tts_text` (whitespace excepted);
  - clip `asset_id` exists in `media` (audio clips: `audio.asset_id` or `media`) and clip `segment_id` exists;
  - timeline end does not exceed the TTS duration;
  - `media` has no duplicate asset ids.
- Timeline and track rules:
  - no overlapping clips within a track;
  - clip and track ids are unique;
  - transition in + out ≤ clip duration;
  - `cut`/`none` transitions have a duration of 0 and `fade` has a duration above 0;
  - segment `order` runs 1..n.
- Media:
  - Shot `start_seconds` ≥ 0;
  - AnalysisWindow must lie inside its Shot, and AnalysisFrame inside its window;
  - fractional rotation is rejected;
  - `exif_orientation` must be 1–8.
- `FramingMode.VERTICAL_CROP` merged into `FILL_CROP` (both are documented). The unused `EditPlan.snapshot_id` field was removed.

## Process
- Tests run with pytest: `make test` (80 tests; previously only 4 unittest tests ran). `pytest` moved to `requirements-dev.txt`.
- `.github/workflows/extract-repo.yml` removed. `.pytest_cache/` and `*.zip` added to `.gitignore`.

## Known / deferred
- Video Studio still builds its draft project with `apps/video_studio/modules/edit_plan.py` (format 1.1). The target contract is `shared/edit_models.py` (2.1); the switch happens when the Edit Planner is connected.
- ElevenLabs TTS calls are not retried, because a retry could consume character quota twice.

# Axion Repo Reset — 2026-09-24

## Included
- Clean monorepo layout for News Studio + Video Studio.
- News app split into AI, prompts, validation, TTS, integration, and models modules.
- Existing editorial prompt rules preserved as the baseline.
- Reset no longer removes authentication state.
- Generated TTS bytes persist in Streamlit session state across reruns.
- Real MP3 duration measured with Mutagen and calibration persisted locally.
- Selected ElevenLabs voice is remembered in session state.
- AI (OpenAI/Claude) transient retry and request timeouts added. ElevenLabs has a request timeout but no retry.
- Censorship terms are reported as validation warnings rather than silently rewritten.
- Simple SQLite production history log added.
- Shared `NewsPackage` contract added for News → Video handoff.
- Video Studio accepts NewsPackage JSON and continues to use GPT-5.6 Luna only for visual analysis.
- Basic unit tests included.

## Deliberately deferred
- AI Edit Planner: not implemented yet; objective media indexing remains separate from editorial selection.
- Final renderer/export pipeline: not implemented yet.
- Durable external database/object storage: not implemented; local SQLite/JSON is ephemeral on Streamlit Cloud.
