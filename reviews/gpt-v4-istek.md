# GPT'den istek — v4.0.0 öncesi kod incelemesi

Editör ve Claude'dan GPT'ye (2026-09-26). Yüksek düşünme seviyesinde çalış; acele etme, kanıtla.

## Durum

4.0 özellikleri yedi ön sürümde (`v4.0.0-alpha.1` … `v4.0.0-alpha.7.3`) yapıldı ve editör Artvin haberiyle
(DHA 1524777) denedi: kadraj ve yazıya dökme artık doğru. `v4.0.0`'dan önce senin gözünle bir inceleme istiyoruz:
hatalar, olası hatalar, verimlilik, sadeleştirme. Raporu Claude okuyacak, editör onaylayacak, onaylananlar tek seferde
yapılıp `v4.0.0` çıkacak.

## Başlamadan

1. `C:\Axion`'da `git pull` (sonucu rapora yaz; commit kimliğiyle).
2. Oku: `AGENTS.md` (özellikle "Nerede kaldık" 4.0 bölümü ve kod haritası), `ROADMAP.md` (Ürün kararları ve
   istenmeyenler: bunları hata sayma, yeniden önerme), `reviews/README.md` (rapor biçimi), `CHANGELOG.md`'nin
   `v4.0.0-alpha.*` bölümleri. Eski raporlarda kapanmış konuları (`reviews/gpt-v3.2.md`, `reviews/claude-v3.md`)
   tekrar açma; yalnız yeniden bozulduysa yaz.
3. Kapsam: v3.7.2'den bu yana değişenler. `git diff --stat 8365e2b..HEAD` (52 dosya, ~3.400 satır). Değişen kodun
   dokunduğu eski kodu da oku (çağıranlar, ortak modeller); gerekirse bütün repoya bak.

## Kurallar

- **Kod değiştirme.** Yalnız `reviews/gpt-v4.md` dosyasını yaz; yalnız onu commit'le ve `main`'e push et.
- Testleri çalıştır: `.venv\Scripts\python.exe -m pytest -p no:cacheprovider` → sonuç satırını ve atlananları yaz.
- Axion'u başlatma/durdurma, `guncelle.bat` çalıştırma, paket kurma. Ücretli API çağrısı yapma.
- `.streamlit/secrets.toml`, `data/tarayici*`, `data/tarayici_girisler.json` açma. `data/projects/` altındaki gerçek
  projeleri **yalnız okuyabilirsin** (hiçbir şeyi repoya koyma, raporda kişisel bilgi/yol yazma). Özellikle Artvin
  projesinin `yazi/*.json` (cümleler + Whisper'ın ham `bolumler`i), `media_library.json` (`motion_region`),
  `edit_project.json`, `kesitler.json`, ayrıca `data/duzeltmeler.jsonl`, `data/maliyet.jsonl`, `data/axion.log` işine
  yarar.
- Emin olmadığın bulguyu "**doğrulanmadı**" diye işaretle; tahmini gerçek gibi yazma. Mümkünse çalıştırarak göster
  (küçük Python betiği, gerçek dosyayla ölçüm) ve nasıl ölçtüğünü yaz.

## Öncelikli bakılacaklar

1. **Yazıya dökme** (`apps/video_studio/modules/transcribe.py`, `page.transcript_picker`): cümle bölme sezgileri
   (büyük harf, `VERB_END`, tek kelime/1 sn birleştirme, 8 sn bölme) — Türkçede yanlış bölme örnekleri; `fix_names`
   yanlış düzeltme riski; `levels`/`_voiced` ses eşiği (sessiz video, müzikli video, gürültülü sokak); iş parçacığı,
   kilit, önbellek anahtarı (`VERSION`); Windows'ta faster-whisper (bellek, süre, HF önbellek uyarısı). Artvin'in
   gerçek `bolumler`inde "yanıma doğru koştu" var mı: Whisper hiç mi yazmadı, yoksa kelime listesine mi girmedi?
2. **Kesit oynatıcısı ve seçim** (`apps/video_studio/range_player.py` JS, `page.py` kesit bölümü): oynatırken
   seçim, `seeking`/`play` yarışları, Android tablette davranış; kaydırıcının `kesit_slider` sayaçlı anahtarı;
   `media_url` her yeniden çalıştırmada önizlemeyi belleğe okuyor mu (uzun videoda maliyeti).
3. **Kadraj** (`framing.motion_region`, `rough_cut._view_regions`): sabit kamera eşikleri, elde çekimde yanlış
   pozitif, analiz süresine eklenen FFmpeg çağrıları (pencere başına), `-ss` ile proxy'de doğru aralık.
4. **Kurgu ve sahne değiştirme** (`scene_swap.py`, `luna_edit.py`, `rough_cut.plan_rough_cut(user=, pick_origin=)`,
   `_chronological`): editör seçimi ↔ Luna planı ↔ imza değişimi; fotoğraflar (`PHOTO_SECONDS`, yakınlaşma).
5. **Render** (`video_studio/modules/render.py`, `design_studio/render.py`, `music.py`): fotoğraf `zoompan` ve EXIF,
   kapak karesi (`split` + `trim`), müzik seviye zarfı (`duck_expression`), ses kazançları; AMD `h264_amf` yolunda
   süre; FFmpeg filtre dizesinde kaçış (Türkçe/boşluklu yollar).
6. **Kayıtlar** (`corrections.py`, `ledger.py`, `status.py`, `diagnostics.py`): iki oturum aynı anda yazınca JSONL,
   dosya büyümesi, ElevenLabs arka plan iş parçacığı, teşhis dosyasının boyutu (artık `yazi/*.json` da giriyor).
7. **Maliyet:** 4.0'da yeni model çağrısı olmamalı ve istemler büyümemeliydi (editör kararı). Doğrula: istemler
   v3.7.2'ye göre ne kadar değişti (token tahmini), gereksiz çağrı var mı.
8. **Ölü kod ve borç:** kullanılmayan sabit/fonksiyon/oturum anahtarı (ör. `speech.py` hâlâ gerekli mi, `hotwords`
   kalıntısı, eski `yazi_anchor`), iki yerde yazılmış mantık, AGENTS/KURULUM/CHANGELOG ile kodun uyuşmadığı yerler.
9. **Testler:** kapsanmayan önemli yol, yanlış nedenle geçen test, zamanlamaya bağlı (kırılgan) test.

## Rapor (`reviews/gpt-v4.md`)

- Başta: `git pull` sonucu, commit, test sonuç satırı, neleri çalıştırıp neleri çalıştırmadığın.
- Bulgular `reviews/README.md` biçiminde (Önem, Tür, Yer `dosya.py:satır`, Sorun + somut örnek, Öneri), ayrıca her
  birinde **Kanıt** (doğrulandı: nasıl / doğrulanmadı) ve kimlik: `V4-G1`, `V4-G2`…
- Önem sırasına göre; sonra ayrı bölümler: "Verimlilik/optimizasyon", "Sadeleştirme (ölü kod)", "Test".
- Sonda tek tablo: kimlik, önem, yer, bir satır özet, önerilen iş (küçük/orta/büyük).
- Türkçe yaz; kısa ve somut ol. Editör kararlarını (ROADMAP) hata sayma.
