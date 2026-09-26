# Araştırma A — Altyapı ve ön yüz: Streamlit'te mi kalalım, taşınalım mı?

ROADMAP "v4.1 planı" 4. madde. Kod değiştirilmedi. Yazan: Claude, 2026-09-26. **Karar editörün.**

## Kısa cevap

**Toptan taşınmayı önermiyorum. Streamlit kabuk olarak kalsın; tablette en çok dokunulan ekranlar tek tek
"anında tepki veren" sayfalara dönüşsün. İlk deneme Tarayıcı sayfası olsun (5. maddeyle birlikte).** Beğenirsen aynı
yol sayfa sayfa sürer; beğenmezsen hiçbir şey kaybolmaz. Bu yol mümkün, çünkü Axion zaten Streamlit'in resmî
`st.App` kapısıyla açılıyor ve bu kapı Streamlit'in yanına istediğimiz sayfayı/kanalı eklemeye izin veriyor (Tarayıcı
akış kanalı bugün tam olarak böyle çalışıyor).

## 1. Bugünkü durum (ölçüldü)

| | |
|---|---|
| Streamlit sürümü | 1.64.0 (sabit). **Şu an yayımlanmış en yeni sürüm** (15.09.2026); 6. madde (yükseltme) bugün acil değil |
| Arayüz kodu (Python) | 4 sayfa + menü ≈ 1.870 satır (`apps/*/page.py`, `axion_local.py`) |
| Tarayıcıda çalışan bileşenler | ≈ 1.800 satır: Tasarım editörü (`editor.js` 892), Tarayıcı ekranı (`viewer.js` 202), kesit oynatıcısı, okuyarak dinleme, kopyala düğmesi + Python sarmalayıcıları |
| İş mantığı | `apps/*/modules`, `shared/` vb. ≈ 10.000+ satır; **arayüzden bağımsız**, taşınsa da aynen kalır |
| Testler | 408 test; bunların 55'i uygulamayı Streamlit'in AppTest'iyle uçtan uca sürer |
| Streamlit dışı kanal | Tarayıcı ekranı zaten Streamlit'in yanında ayrı WebSocket ile akıyor (`axion_app.py`, `stream.py`) |

**Streamlit'in bize çıkardığı sorunlar (CHANGELOG'dan, hepsi çözüldü ama "yamayla"):**
- Her dokunuşta sayfanın Python betiği baştan çalışır ve sonuç sunucudan gelir. Evde fark edilmez; dükkânda
  (Tailscale, 45/13 Mbps) her dokunuş bir gidiş-dönüş → "akıcı değil" hissinin ana nedeni.
- Metin kutusunda düzenleme kayboluyordu (v2.2.0 → `bound_text` deseni), kaydırıcı cümle seçilince güncellenmiyordu
  (`kesit_slider` anahtar hilesi), anahtar düğmesi tablette açılmadı (v4.0 → tam genişlik düğme), listeye dokununca
  klavye açılıyordu (`filter_mode=None`), ekran kapanınca oturum siliniyordu (v3.7.1 → 3 saat), Tarayıcı'da üstte/altta
  beyaz boşluk (v3.5.1 → Streamlit düzenini CSS ile ezme).
- Bazı özellikler Streamlit'in iç (belgelenmemiş) parçalarına dayanıyor (`_session_mgr`, `media_file_mgr`): her
  yükseltmede kırılabilir.

**Streamlit'in bize kazandırdıkları:** her şey tek dilde (Python) ve hızlı yazılıyor; arayüz uçtan uca test ediliyor
(AppTest); uzun işler (video, yazıya dökme) aynı süreçte arka planda sürüyor; editörün her gün kullandığı akış çalışıyor.
Ağır etkileşimler (Tasarım editörü, Tarayıcı) zaten tarayıcıda çalışan bileşenlere taşındı ve akıcı.

## 2. "Akıcılık" nereden gelir?

Streamlit'te bir düğmeye dokununca: tablet → sunucu → betik baştan → fark → tablet. Bu turu kısaltmanın yolları
(fragment, önbellek) var ve kullanıyoruz; ama "dokunduğum anda değişsin" hissi yalnızca **tablette çalışan arayüzle**
olur. Tasarım editörü ve Tarayıcı ekranı bunun kanıtı: ikisi de tablette çalışıyor, sunucuya yalnız sonuç gidiyor.
Yani soru "Streamlit mi, başka çatı mı" değil, **"hangi ekranlar tablette çalışan arayüze geçsin"**.

## 3. Seçenekler

| | 1. Kal ve cilala | 2. Kal + ada bileşenler | 3. Aynı süreçte yeni ön yüz, sayfa sayfa | 4. NiceGUI'ye toptan geçiş |
|---|---|---|---|---|
| Ne | CSS/düzen düzeltmeleri, 6. madde kontrol listesi | Sık dokunulan parçaları (ör. kesit/sahne adımları) Streamlit içinde JS bileşene | `st.App`'e JSON uç noktaları + tam ekran sayfalar (PWA, ana ekrana eklenir); her yeni sayfa hazır olunca Streamlit'teki karşılığı kalkar | Python'da olay tabanlı çatı (FastAPI + Vue/Quasar, betik baştan çalışmaz) |
| Tablette akıcılık | Az değişir | Taşınan parçada anında | Taşınan sayfada anında, tam ekran, Streamlit boşlukları yok | İyi (her dokunuş yine sunucuya gider ama yalnız o öğe güncellenir) |
| Tasarım serbestliği | Sınırlı (Streamlit düzeni) | Parça içinde serbest | Tam serbest | Orta-iyi (Quasar bileşenleri) |
| İş | 1–2 oturum | Parça başına 1–2 oturum | Altyapı 1–2 oturum (giriş/şifre, HTTPS, PWA); sonra sayfa başına 2–4 oturum; hepsi ≈ 10–15 oturum | Tüm arayüz + testler yeniden: ≈ 8–12 oturum, arada yarım uygulama riski |
| Risk | Düşük | Düşük | Orta, ama parça parça: her adım geri alınabilir, eski sayfa yedekte | Yüksek: iki çatı aynı anda zor, AppTest'lerin hepsi yeniden yazılır |
| Test | AppTest aynen | AppTest + elle tarayıcı denemesi (bugünkü gibi) | JSON uç noktaları pytest ile; sayfalar Playwright/Chromium ile (sandbox'ta var) | NiceGUI'nin kendi test aracı; hepsi yeniden |
| İki dil | Hayır | Evet (JS, bugünkü gibi) | Evet (JS) | Hayır |

Elenenler: yerel Android uygulaması (APK; ROADMAP'te istenmeyenler), Reflex/Flet gibi derleme gerektiren çatılar
(Windows kurulumuna Node/Flutter eklenir, güncelleme zinciri karmaşıklaşır).

**3. seçeneğin önemli ayrıntıları:**
- Uzun işler (video üretimi, yazıya dökme, tasarım üretimi) bugün Streamlit sürecinin iş parçacıkları; yeni sayfalar
  **aynı süreçte** olduğu için onları doğrudan görür, veri taşıma yok.
- Giriş: bugün isteğe bağlı şifre ve Tarayıcı akış jetonu Streamlit oturumuna bağlı. Yeni sayfalar için aynı şifreyle
  giriş + imzalı çerez gerekir (1 oturumluk iş; güvenlik testiyle).
- HTTPS: tablete "uygulama gibi" eklenen sayfa (PWA) tarayıcı kuralı gereği HTTPS ister. Tailscale bunu ücretsiz verir
  (`tailscale serve`, `https://<bilgisayar>.<ağ>.ts.net`); yan kazanç: kopyala düğmesinin http yedeğine gerek kalmaz.
  Editörün Tailscale ayarında "HTTPS sertifikaları" bir kez açılır.
- Ön yüz derleme gerektirmeyen hafif bir kütüphaneyle yazılır (dosyalar repoda hazır durur; Windows'a Node kurulmaz,
  "Güncelle" bugünkü gibi çalışır).

## 4. Önerilen yol (adım adım, her adımda editör "devam / dur" der)

1. **Pilot: Tarayıcı sayfası tam ekran ayrı sayfa olur** (5. maddeyle birlikte; 2–3 oturum). Neden bu sayfa: görüntüsü
   ve dokunuşları zaten Streamlit'ten bağımsız akıyor (`viewer.js` + `stream.py`); en çok şikâyet (kaydırınca beyazlık,
   çözünürlük) Streamlit'in sayfa düzeninden. Bu adım giriş, HTTPS ve "ana ekrana ekle" altyapısını da kurar.
   Streamlit'teki Tarayıcı sayfası pilot beğenilene kadar yedekte kalır, sonra silinir.
2. Editör bir hafta kullanır. **Karar noktası:** "fark etti mi?"
   - Evetse: sıradaki en çok dokunulan ekran (büyük olasılıkla Video Stüdyosu'nun kesit + sahne adımları, sonra Haber
     Stüdyosu) aynı yolla; her biri ayrı ön sürüm.
   - Hayırsa: Streamlit'te kal (seçenek 1–2); pilotun HTTPS/giriş işi yine işe yarar.
3. 6. madde (Streamlit yükseltmesi): bugün en yeni sürümdeyiz. Kalırsak yalnız kısa kontrol listesi yazılır (iç API'ler,
   `st.App`, medya sunucusu, components v2, tablet denemesi); yükseltme ihtiyaç doğunca.
4. 7. madde (sosyal medyaya yükleme) bu karardan bağımsız: yükleme işi arka tarafta (bilgisayarda) yapılır, düğmesi
   hangi arayüzdeyse oraya konur.

## 5. Editöre sorular (karar için)

1. **Yol:** (a) önerilen: pilot Tarayıcı sayfasıyla başla, beğenirsen sayfa sayfa sür; (b) Streamlit'te kal, yalnız
   cilala (1–2); (c) başka bir şey.
2. Tablette en çok hangi ekranda "yavaş/takılıyor" diyorsun? (Sıralamayı bu belirler.)
3. Tailscale'de HTTPS sertifikalarını açmak sorun olur mu? (Yönetim panelinde tek ayar; adres
   `https://…ts.net` olur. Açılmazsa "ana ekrana uygulama gibi ekle" olmaz, sayfa yine tam ekran çalışır.)

## Kaynaklar

- Streamlit 1.64.0 (15.09.2026): [duyuru](https://discuss.streamlit.io/t/version-1-64-0/122545),
  [2026 sürüm notları](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); `st.App`'in ek rota
  kabulü kurulu 1.64.0'ın kendi belgesinden (`routes: Additional routes to mount alongside Streamlit`).
- NiceGUI (FastAPI + Vue/Quasar, WebSocket, betik yeniden çalışmaz): [nicegui.io](https://nicegui.io/),
  [GitHub](https://github.com/zauberzeug/nicegui), [3.0 söyleşisi](https://talkpython.fm/episodes/show/525/nicegui-goes-3.0).
- Streamlit ↔ NiceGUI çalışma modeli farkı: [bitdoze karşılaştırması](https://www.bitdoze.com/streamlit-vs-nicegui/).
- PWA'nın HTTPS şartı ve Tailscale ile HTTPS: [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve),
  [HTTPS sertifikaları](https://tailscale.com/docs/how-to/set-up-https-certificates).
- Axion'daki ölçümler: bu repodaki satır sayıları, test sayısı ve CHANGELOG (v2.2.0, v3.5.1, v3.7.1, v4.0).
