# Axion Haber Automation — Yol Haritası

Bu dosya ürünün ana referansıdır. Her değişiklik şu soruyla değerlendirilir:
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

Sistem, Streamlit Cloud yerine **evdeki bilgisayarda** çalışır.

- Büyük videolar internete yüklenmez; diskten okunur.
- Veriler (projeler, TTS kalibrasyonu, üretim geçmişi) kalıcıdır.
- İş yerindeki tabletten erişim, bilgisayar açıkken özel bir ağ bağlantısıyla sağlanır (Tailscale gibi; internete açık port yok).
- Tek uygulama, tek şifre: News Studio ve Video Studio aynı projede buluşur. JSON/MP3 indirip yeniden yükleme adımı kalkar.

## Ürün kararları (editör)

**Haber metni ve TTS**
- Plaka, kimlik no ve benzeri teknik ayrıntılar hiçbir çıktıda yer almaz.
- Röportaj veren kişinin adı açık yazılır. Diğer sivil isimler baş harfle yazılır; TTS'te sivil isim kullanılmaz.
- TTS doğal ve konuşma dilindedir. Her cümle yeni bilgi verir; süreyi doldurmak için metin uzatılmaz.
- Viral potansiyeli olan yön öne çıkarılır, ama kaynakta olmayan fiil veya abartı kullanılmaz.

**Video**
- Kurgu çıktısı 1080×1440. Axion şablonu (başlık, alttan logo şeridi, font) ile birlikte son çıktı 1080×1920.
- Altyazı yok.
- Tanık sesi editör kararıdır:
  - dikkat çekici söz → videonun başına, TTS'ten önce;
  - tamamlayıcı röportaj → TTS'ten sonra;
  - gerekmiyorsa → kullanılmaz.
- Plaka ve reşit olmayanların yüzü bulanıklaştırılır. Otomasyon yalnızca öneri üretir; son kontrol editördedir.

## Fazlar

| Faz | İçerik | Sonuç |
|---|---|---|
| 0 ✅ | **Yerel çalışma:** tek uygulama ve tek şifre (`axion_local.py`), kalıcı proje klasörü, videoyu diskten alma, tek tıkla başlatma, tabletten erişim (Tailscale) | Yükleme sorunu biter |
| 1 | **News Studio:** zaman bilgili TTS (`convert_with_timestamps`), metin değişince sesin geçersiz sayılması, NewsPackage'da ses hash'i | TTS cümleleri zamanlanabilir |
| 2 | **Video Studio sözleşme geçişi:** `shared/` 2.1 modelleri, sabit kategoriler (enum), uzun shot'ları pencerelere bölme, tanık sesi ve kaynak ses alanları | Planner'a güvenilir veri |
| 3 | **Kaba kurgu:** kural tabanlı TTS ↔ shot eşleştirme + FFmpeg ile 1080×1440 MP4 | **CapCut'a gerek kalmaz** |
| 4 | **AI Edit Planner:** TTS segmentleri + shot açıklamaları → tek Luna metin çağrısı → `EditProject` | Otomatik kurgu kararı |
| 5 | **Axion şablon katmanı:** statik şablon PNG + başlık yazısı + logo animasyonu → 1080×1920 | **Canva'ya gerek kalmaz** (font lisansı uygunsa) |
| 6 | **Blur:** plaka ve yüz önerisi, yalnızca son videoya giren parçalarda, editör onayıyla | Gizlilik |

## Ortam

- Evdeki bilgisayar Windows; güçlü (AMD işlemci ve ekran kartı), 1000 Mbps internet, iş saatlerinde açık kalabilir.
- DHA videoları editör tarafından panelden normal yolla indirilir; Video Studio indirilenler klasöründen okur. Otomatik DHA erişimi hedef değil.

## Açık sorular

- Canva şablonundaki fontun adı ve lisansı.
