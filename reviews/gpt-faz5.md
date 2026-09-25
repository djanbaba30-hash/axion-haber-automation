# GPT Faz 5 önerileri (2026-09-25, v2.8.0 üzerinde)

Editör GPT'ye repoyu (AGENTS, ROADMAP, `apps/design_studio/*`, `apps/video_studio/*`, `apps/news_studio/page.py`,
store) inceletti. Aşağıdaki GPT'nin yanıtının özetidir; numaralar GPT'nindir. Kararlar ve yapılanlar:
`reviews/claude-faz5.md`.

GPT'nin ana tezi: eksik olan zekâ değil, **durum yönetimi ve üretim yaşam döngüsü**. Her çıktı hangi girdilerden
üretildiğini ve neyin onu geçersiz kıldığını bilmeli, gerekmiyorsa yeniden üretmemeli, gerekiyorsa nedenini söylemeli.

1. **Değişiklik zinciri (artifact dependency graph):** haber → TTS → Media Library → kaba kurgu → tasarım → son video.
   `signature()` kaba kurgunun `st_mtime`'ına dayanıyor; içerik aynı mı bilmiyor. Kullanıcıya ✅/⚠️ zincir durumu.
2. **Efekt mantığı iki yerde** (`effects.py` ve `editor.js`): önizleme ile son video ayrışabilir. Seçenek A: parametreleri
   tek JSON'da tutmak (şimdilik yeterli). Seçenek B: hesaplamayı ortaklaştırmak.
3. **Editörde yeni buton değil akış:** "Tasarım kaydedildi" ile "Son videoya işlendi" UI'da açıkça ayrılsın.
4. **Eski render'ı öldürme:** render sürerken tasarım değişirse eski iş boşuna sürüyor; revizyon/iptal mantığı.
5. **Tasarım önizlemesinde gereksiz tekrar üretim:** `build_scene`, `block_data` (atlas) her Streamlit yeniden
   çalıştırmasında; tasarım imzası + başlık + yazı tipi + süre anahtarlı önbellek.
6. **Luna'ya giden veri hacmi:** pencere × kare, `detail="auto"`; tek çağrı büyüyebilir. Kare bütçesi (normal ≤3,
   ayrıntılı ≤4/pencere, uzun videoda seyreltme).
7. **Proxy önbelleği:** `create_proxy()` her seferinde FFmpeg; SHA256(video) + genişlik + sürümle önbellek.
8. **Media Library önbelleği:** yalnız `analysis_prompt_version` değil; kaynak parmak izi + pipeline sürümü + prompt
   sürümü + analiz ayarları.
9. **Ortak varlık kimliği:** `video_ingestion`'daki SHA256 tüm zincirde (proxy, kare, Luna, MediaLibrary) kullanılsın.
10. **Son video doğrulaması:** FFprobe ile açılıyor mu, 1080x1920, fps, görüntü/ses akışı, süre.
11. **Önizleme / Final ayrımı** ürün dilinde belirgin olsun (hızlı düşük çözünürlük vs gerçek 1080x1920).
12. **Tasarım geçmişi:** undo/redo'ya ek olarak adlandırılmış geri dönüş noktaları.
13. **Tablet:** `@container (max-width: 860px)` iyi temel; dokunmatik sürükleme, zaman çizelgesi ve boyutlandırma
    tutamakları ayrıca test edilmeli.
14. **İş akışı durum çizgisi:** ① Haber ✓ → ② Görüntüler ✓ → ③ Kurgu ✓ → ④ Tasarım ⚠ → ⑤ Son video.
15. **"Neden yeniden oluşturuyoruz?"** kullanıcıya söylensin (ör. "Tasarım değişikliği — yalnızca final render").

GPT'nin önerdiği sıra: A) 1 artifact/imza sistemi, 10 son video doğrulaması, 7 proxy önbelleği, 8 Media Library
önbelleği, gereksiz final render engelleme; B) 2 efekt tek kaynak, 4 revizyon/eski iş, 5 atlas önbelleği,
3 kaydedildi/işlendi ayrımı, 12 tasarım geçmişi; C) 6 kare bütçesi, proxy parmak izi, Media Library parmak izi, son
render kalite kontrolü, kesit zaman çizelgesi; D) sonra: Luna Edit Planner, daha fazla yapay zekâ, karmaşık paneller.
