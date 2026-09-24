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
- Telefon/tabletten erişim, bilgisayar açıkken Tailscale ile sağlanır (internete açık port yok).
- Tek uygulama: Haber Stüdyosu ve Video Studio aynı projede buluşur ("Kaydet ve Video Studio'ya geç"). JSON/MP3 indirip yükleme yok.

## Ürün kararları (editör)

**Haber metni ve TTS**
- Plaka, kimlik no ve benzeri teknik ayrıntılar hiçbir çıktıda yer almaz.
- Röportaj veren kişinin adı açık yazılır. Diğer sivil isimler baş harfle yazılır; TTS'te sivil isim kullanılmaz.
- TTS doğal ve konuşma dilindedir. Her cümle yeni bilgi verir; süreyi doldurmak için metin uzatılmaz.
- Viral potansiyeli olan yön öne çıkarılır, ama kaynakta olmayan fiil veya abartı kullanılmaz.

**Arayüz**
- Beyaz zeminli, Axion logosu renklerinde (lacivert, açık mavi, yeşil) sade arayüz; uygulama içinde logo yok.
- Editörün görmesi gerekmeyen bilgiler gizli (geliştirici bölümü); son kullanılan ayarlar hatırlanır.

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

| Faz | İçerik | Sonuç |
|---|---|---|
| 0 ✅ | **Yerel çalışma:** tek uygulama (`axion_local.py`), kalıcı proje klasörü, videoyu diskten alma, ikonla konsolsuz başlatma, Tailscale ile uzaktan erişim | Yükleme sorunu biter |
| 1 ✅ | **News Studio:** zaman bilgili TTS (`convert_with_timestamps`), metin değişince sesin geçersiz sayılması, NewsPackage'da ses hash'i | TTS cümleleri zamanlanabilir |
| 2 ✅ | **Video Studio sözleşme geçişi:** `shared/` 2.1 modelleri, enum'lu Luna şeması, uzun shot pencereleri (Windows'ta doğrulandı) | Planner'a güvenilir veri |
| 3 ✅ | **Kaba kurgu:** kural tabanlı TTS ↔ shot eşleştirme + FFmpeg ile şablon video alanı ölçüsünde (960×1226) MP4 | **CapCut'a gerek kalmaz** |
| 4 (ertelendi) | **AI Edit Planner:** TTS segmentleri + shot açıklamaları → tek Luna metin çağrısı → sahne seçimi. Editör kararı: token harcamamak için şimdilik yapılmıyor; günlük kullanımdaki sahne seçimi şikâyetleri önce kurallarla (API'siz) çözülür. Gerekirse her haberde otomatik değil, yalnızca editörün bastığı "Sahneleri Luna ile düzenle" düğmesiyle çalışır. | Daha isabetli sahne seçimi |
| 5 (sıradaki) | **Tasarım Stüdyosu = sade, otomatik Canva:** arka plan + başlıklar + slogan yazıları + logo kutusu animasyonu → 1080×1920 (ayrıntı: aşağıda, `shared/axion_template.py`); canlı önizleme + zaman çizelgesi; **elle blur aracı** (şekil/boyut/güç/opaklık, sürükleyerek takip). Şablon dosyaları: `assets/sablon/` | **Canva'ya gerek kalmaz** (font lisansı uygunsa) |

## Ortam

- Evdeki bilgisayar Windows; güçlü (AMD işlemci ve ekran kartı), 1000 Mbps internet, iş saatlerinde açık kalabilir.
- DHA videoları editör tarafından panelden normal yolla indirilir; Video Studio indirilenler klasöründen okur. Otomatik DHA erişimi hedef değil.

## Faz 2 uygulama notları

- media_library.json artık 2.1 ortak sözleşmesiyle yazılıyor.
- edit_project.json artık 2.1 ortak sözleşmesiyle yazılıyor; eski 1.1 dosyalar yeniden kullanılamıyor.
- Browser upload medya kaynakları proje altında saklanıyor; local inbox dosyaları yerinde okunuyor.
- TTS alignment varsa karakter aralıkları doğrulanıyor; yoksa segmentler deterministik noktalama sınırlarından üretiliyor.
- Windows gerçek E2E testinde analiz + EditProject üretimi doğrulandı; 157.28 sn videoda 15 shot, 21.27 sn TTS timeline üretildi.
- v1.7.1: `unknown`/boş sınıflandırma (eşleme hatası) düzeltildi; uzun shot'lar 10 sn'lik pencerelere bölünüyor.

## Axion Canva şablonu (Faz 5 girdisi, editörden)

Kanvas 1080×1920. Konumlar sol üst köşeye göre piksel; koddaki karşılığı `shared/axion_template.py`.

| Öğe | Konum / boyut | Zaman | Animasyon |
|---|---|---|---|
| Video | 960×1225, x=60, y=453 | tüm video | — |
| Başlık 1 | 960×155, x=60, y=260; Binate Bold 45, glow 100 | 0–9 sn | giriş yok, çıkış "merge" |
| "TARAFSIZ HABERCİLİĞİN ADRESİ" | başlık kutusunun ortası | 9–11 sn | giriş/çıkış "old tv" (Text Studio) |
| "BEĞEN, PAYLAŞ, TAKİP ET" | başlık kutusunun ortası | 11–13 sn | giriş/çıkış "old tv" |
| Başlık 2 | Başlık 1 ile aynı kutu ve yazı tipi | 13 sn → son | giriş "merge", çıkış yok |
| Axion Haber logo kutusu (yumuşak köşeli) | alttan yükselir | 16–19 sn | "slow baseline": alttan çıkar, geri iner |
| Arka plan | 1080×1920 | tüm video | 8 arka plan; her gün bir sonraki, aynı gün tüm haberler aynı |

Videonun başına kaynak sesli kesit eklense de 1. başlık 0. saniyeden itibaren ekrandadır.
Zamanlar video uzunluğundan bağımsız, sabittir. Video **en az 20 sn**; daha uzunsa yalnızca arka plan ve 2. başlık
videonun sonuna kadar uzar. Seslendirme 20 sn'den kısaysa kurgu 20 sn'ye tamamlanır (son sahne sessiz devam eder).

Faz 5'te gerekecek dosyalar (editörden): 8 arka plan, logo kutusu (şeffaf PNG), varsa slogan yazılarının görselleri.

## Açık sorular

- Binate Bold yerine lisansı serbest, Türkçe karakterli benzer yazı tipi (Faz 5'te örnek çıktıyla karşılaştırılacak).

- Canva şablonundaki fontun adı ve lisansı.
