# Araştırma A — Altyapı ve ön yüz: Streamlit'te mi kalalım, taşınalım mı?

ROADMAP "v4.1 planı" 4. madde. Kod değiştirilmedi. Yazan: Claude, 2026-09-26. **Karar editörün.**

## Kısa cevap (editörün sorusundan sonra güncellendi, 6. bölüm)

İlk sürümde soruyu "tablette yavaşlık" diye okudum ve "kal, ekranları tek tek düzelt" dedim. Editörün asıl hedefi
**daha işlevsel, daha güzel, daha çok seçenekli bir arayüz**. Bu hedefte **darboğaz gerçekten Streamlit**. Değecek
seçenek var: **iş mantığı aynen kalır, arayüz modern bir web uygulaması olarak yeniden yapılır** (Python arka taraf +
tablette çalışan ön yüz). Bu `v5.0` olur; sayfa sayfa geçilir, Streamlit bitene kadar yedekte kalır. İlk adım kod
değil, **tıklanabilir tasarım prototipi**: editör görünüşü onaylamadan taşınmaya başlanmaz. Ayrıntı: 6. bölüm.

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

## 4. İlk öneri (hedef "hız" sanılarak yazıldı; yerine 6. bölüm geçer)

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

## 5. İlk sorular (1. ve 3. cevaplandı: hedef zengin arayüz, HTTPS açılabilir → 6. bölüm)

1. **Yol:** (a) önerilen: pilot Tarayıcı sayfasıyla başla, beğenirsen sayfa sayfa sür; (b) Streamlit'te kal, yalnız
   cilala (1–2); (c) başka bir şey.
2. Tablette en çok hangi ekranda "yavaş/takılıyor" diyorsun? (Sıralamayı bu belirler.)
3. Tailscale'de HTTPS sertifikalarını açmak sorun olur mu? (Yönetim panelinde tek ayar; adres
   `https://…ts.net` olur. Açılmazsa "ana ekrana uygulama gibi ekle" olmaz, sayfa yine tam ekran çalışır.)

## 6. Editörün sorusu (2026-09-26): "Sıkıntı yavaşlık değil; daha işlevsel, güzel, çok seçenekli arayüz istiyorum"

**Bu hedefte sorun Streamlit mi? Evet.** Streamlit veri panoları için yapılmış bir çatı:
- Sayfa yukarıdan aşağı dizilen hazır parçalardan oluşur (kutu, düğme, kaydırıcı, açılır bölüm). Yan yana paneller,
  sürükle-bırak, zaman çizelgesi, sağ tık/uzun basma menüsü, çekmeceler, açılır pencereler, dalga formu üzerinde seçim,
  küçük resim ızgarasından seçme gibi şeyler Streamlit'in parçalarında yok.
- Görünüm sınırlı: renk/yazı tipi dışında değişiklik Streamlit'in iç yapısını CSS ile ezmek demek (Tarayıcı'daki beyaz
  boşluk gibi) ve her sürümde bozulabilir.
- Kanıt bizde: arayüzde "hayal edilen"e en yakın iki yer (Tasarım editörü, Tarayıcı ekranı) **Streamlit'ten çıkıp
  tarayıcıda çalışan kodla** yazılabildi. Yani zengin arayüz istediğimiz her yerde zaten Streamlit'in dışına çıkıyoruz;
  kalırsak bunu her ekranda, Streamlit'in düzeniyle boğuşarak yapacağız.

**Seçenekler (bu hedefe göre):**

| | Streamlit + ada bileşenler | NiceGUI (yalnız Python) | **Modern web arayüzü (önerim)** |
|---|---|---|---|
| Ne | Bugünkü yol | Python'la yazılan, hazır zengin bileşenli çatı (Quasar) | Python arka taraf (FastAPI, bugünkü `apps/` + `shared/` aynen) + tablette çalışan ön yüz (React + Tailwind) |
| Arayüz tavanı | Düşük; her zengin parça ayrı JS bileşeni | Orta-iyi: çekmece, sekme, açılır pencere, tablo, sürükle-bırak hazır; özel parça yine JS | **En yüksek**: Canva/CapCut benzeri her şey mümkün; hazır kütüphaneler (zaman çizelgesi, dalga formu, sürükle-bırak) |
| Görünüm | Streamlit görünümü | Material (Google) görünümü, özelleştirilebilir | Tamamen Axion'a özel tasarım |
| İş | Ekran başına 1–2 oturum, tavan değişmez | ≈ 8–12 oturum (hepsi yeniden, tek seferde) | ≈ 15–20 oturum, sayfa sayfa (her sayfa ayrı ön sürüm) |
| Risk | Düşük | Orta-yüksek (toptan geçiş) | Orta: sayfa sayfa, eski sayfa yedekte; iki dil (Python + JS) |
| Yapay zekâyla geliştirme | Bugünkü gibi | Daha az örnek, daha az bilinen çatı | Claude ve GPT'nin en güçlü olduğu alan |

**Modern web arayüzüyle neler olur (örnekler):**
- **Haber Stüdyosu:** ham haber | çıktı yan yana; başlıklar videodaki hâliyle (şablon üzerinde) canlı önizleme;
  seslendirme dalga formu üzerinde kelime kelime; talimat için sık kullanılan kısa seçenekler; TXT'yi sürükleyip bırakma.
- **Video Stüdyosu:** gerçek zaman çizelgesi: sahneleri sürükleyerek sıralama, kırpma, küçük resim ızgarasından sahne
  değiştirme; kesiti dalga formu ve yazıya döküm üzerinde seçme; analiz ve video üretimi canlı ilerleme çubuğuyla
  (bugünkü saniyelik yenileme yerine anında).
- **Tasarım Stüdyosu:** bugünkü editör (`editor.js`) tam ekran ve pencere düzeniyle, sınırsız.
- **Genel:** tek uygulama hissi (sayfa geçişi anında), bildirimler, koyu/açık tema, tablet için ayrı yerleşim, ana ekrana
  eklenen uygulama (PWA; HTTPS'i editör açabilir), klavye kısayolları (bilgisayarda).

**Nasıl kurulur (Windows'a yük getirmeden):** ön yüz geliştirme ortamında derlenir, hazır dosyaları repoya konur; editörün
bilgisayarına Node vb. kurulmaz, "Güncelle" bugünkü gibi çalışır. Arka plan işleri (video, yazıya dökme, tasarım) aynı
süreçte kalır. Testler: arka taraf pytest, ekranlar Playwright/Chromium (sandbox'ta var).

**Önerilen yol (v5.0, her adımda editör "devam / dur"):**
1. **Tasarım prototipi** (1–2 oturum, ürün kodu yok): Haber Stüdyosu ve Video Stüdyosu'nun yeni hâli, tablette açılıp
   dokunulabilen örnek sayfa (gerçek veri yok). Editör görünüşü ve akışı onaylar ya da değiştirir.
2. **Altyapı** (2 oturum): arka taraf uç noktaları, giriş/şifre, HTTPS, ana ekrana ekleme, tasarım dili (renk, yazı,
   bileşenler). Streamlit aynı adreste yedek.
3. **Sayfa sayfa** (her biri ayrı ön sürüm): Haber Stüdyosu → Video Stüdyosu → Tarayıcı (5. madde burada) → Tasarım
   Stüdyosu. Her sayfa editör onaylayınca Streamlit'teki karşılığı silinir (çöp kalmaz).
4. Son: Streamlit ve ona bağlı yamalar (iç API'ler, AppTest'ler) kaldırılır; 6. madde (Streamlit yükseltmesi) düşer.

**Editöre sorular:** (1) Prototiple başlayalım mı? (2) Öncelik tablet mi bilgisayar mı (yerleşim ona göre)?
(3) Beğendiğin, "böyle olsun" dediğin uygulamalar var mı (Canva, CapCut, başka)?

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
