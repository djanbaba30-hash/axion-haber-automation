# GPT Faz 3 Kod İncelemesi

## Kapsam ve doğrulama notu

- İnceleme, `main` branch'indeki mevcut repo üzerinden yapıldı.
- Önce `AGENTS.md`, `ROADMAP.md` ve `reviews/README.md` okundu; ardından `axion_local.py`, `apps/`, `shared/`, `windows/` ve `tests/` kapsamındaki kod statik olarak incelendi.
- **Çalıştırma notu:** Bu ortamda Windows ve repo çalışma ortamı olmadığı için `make test` ve gerçek Windows E2E çalıştırılmadı. Aşağıdaki bulgular statik incelemedir; çalışma zamanı doğrulaması gerektirenler ayrıca **doğrulanmadı** diye işaretlenmiştir.
- Editör kararları (doğrudan `main`, 3 gün saklama, bulanık dolgu yok, GPT-5.6 Luna, vb.) hata olarak değerlendirilmedi.

---

## Bulgular

- **Önem:** yüksek
- **Tür:** güvenlik
- **Yer:** `apps/axion_local/store.py:127-128, 136-140`
- **Sorun:** Eski proje temizliği `shutil.rmtree(folder, ignore_errors=True)` ile yapılıyor. Bu, klasörün kısmen silinmesi, kilitli dosyalar veya izin problemi gibi durumlarda hatayı görünmez kılıyor; fonksiyon yine klasör adını `deleted` listesine ekliyor. Özellikle Windows'ta FFmpeg/Streamlit tarafından halen açık tutulan `kaba_kurgu.mp4` veya önizleme dosyaları silinemezse bu durum oluşabilir.
- **Öneri:** `ignore_errors=True` yerine kontrollü silme kullanılsın; en azından `OSError` yakalanıp başarısız klasörler ayrı bir sonuç listesinde tutulmalı ve geliştirici günlüğüne/arayüze uyarı düşürülmeli. Başarılı silinenler yalnızca gerçekten yokluğu doğrulandıktan sonra `deleted` olarak raporlanmalı.

- **Önem:** yüksek
- **Tür:** veri kaybı riski
- **Yer:** `axion_local.py:70-75` ve `apps/axion_local/store.py:127-140`
- **Sorun:** Otomatik saklama temizliği uygulama açılışında, `@st.cache_resource` ile iş günü başına bir kez çalışıyor ve proje klasörünün tamamını kalıcı olarak siliyor. Bu editör kararıdır; sorun kararın uygulanışındaki geri dönüşsüzlük. Yanlış sistem saati, bozuk proje klasöründeki tarih adı veya geçici bir yeniden kurulum durumunda haber + TTS + analiz + kurgu + önizlemelerin tamamı tek `rmtree` ile gidiyor. Silme öncesi manifest, yedek, geri dönüş noktası veya dry-run yok.
- **Öneri:** Editörün 3 günlük kararını değiştirmeden önce silinecek klasörleri tespit edip loglamak; mümkünse önce `.siliniyor`/çöp klasörüne taşımak, sonra periyodik temizlemek. En azından silme öncesi klasör adını, yaşını ve içerik özetini kaydetmek güvenli olur. Bu bulgunun işlevsel etkisi gerçek Windows'ta ayrıca doğrulanmalı (**doğrulanmadı**).

- **Önem:** yüksek
- **Tür:** hata
- **Yer:** `apps/video_studio/modules/render.py:31-52`
- **Sorun:** `_clip_filter()` içinde `FramingMode.FIT_BLUR` için hâlâ açıkça `boxblur` + `overlay` filtresi oluşturuluyor. `clip_framing()` şu an her zaman `FILL_CROP` üretse de veri sözleşmesi/gelecekteki planner başka bir mode gönderirse render doğrudan bulanık dolgu üretir. ROADMAP editör kararı "hiçbir sahnede bulanık dolgu yok" olduğundan bu, kararın kod seviyesinde tek noktadan zorunlu kılınmaması anlamına geliyor.
- **Öneri:** Renderer'da `FIT_BLUR` üretimine izin vermek yerine bu mode için açık hata verilmeli veya tek bir tam-dolgu stratejisine normalize edilmeli. Böylece planner/bozuk JSON yanlışlıkla editoryal kararı delmez.

- **Önem:** orta
- **Tür:** maliyet (token)
- **Yer:** `apps/video_studio/modules/visual_analysis.py:112-156`
- **Sorun:** Her analiz penceresi için 1–4 kare `input_image` olarak `detail="auto"` ile gönderiliyor. Uzun shot'lar 10 saniyelik pencerelere bölündüğü için yaklaşık 72 saniyelik bir röportaj 8 pencereye ayrılıyor; "En ayrıntılı" seçiminde bunun üzerine pencere başına 4 kare gönderilmesi tek haber için 32 kareye çıkabiliyor. Kod bunu token/kare açısından sınırlamıyor; yalnızca kullanıcı arayüzündeki seçim maliyeti belirliyor.
- **Öneri:** API'ye gitmeden önce toplam kare sayısı veya tahmini görüntü yükü için bir üst sınır koymak; sınır aşılırsa otomatik olarak ekonomik örneklemeye dönmek veya editörden onay istemek. Bu, ürün kararındaki "token tasarrufu" ilkesiyle uyumlu olur.

- **Önem:** orta
- **Tür:** performans
- **Yer:** `apps/video_studio/modules/visual_analysis.py:75-91` ve `apps/video_studio/modules/media_pipeline.py:67-111`
- **Sorun:** Her frame için önce tüm dosya `read_bytes()` ile belleğe alınıyor, ardından base64'e çevrilip tekrar yeni bir Python string oluşuyor. Çok sayıda 640 px JPEG'de bu gereksiz kopyalama/bellek baskısı yaratıyor; ayrıca tüm pencerelerin görselleri tek büyük `content` listesinde aynı anda tutuluyor.
- **Öneri:** Frame boyutları zaten düşük olduğundan içerik boyutunu ölçmek; toplam payload için üst sınır uygulamak ve mümkünse daha küçük JPEG/standart kaliteyle göndermek. En azından toplam byte ve frame sayısını analiz başlamadan hesaplayıp büyük işlerde kontrollü davranmak.

- **Önem:** orta
- **Tür:** hata
- **Yer:** `apps/video_studio/modules/video_ingestion.py:245-259`
- **Sorun:** Tarayıcıdan yüklenen aynı adlı dosyanın daha önce kaydedilmiş eşini bulmak için yalnızca dosya boyutu karşılaştırılıyor. Aynı isim + aynı boyuta sahip farklı video gelirse eski dosya yeniden kullanılıyor ve yeni dosya analiz edilmiyor. Bu, aynı DHA dosya adının farklı içeriklerle tekrar kullanıldığı durumda yanlış medyanın kalıcı kalmasına yol açabilir.
- **Öneri:** Eşleşmeyi SHA-256 ile yapın; aynı boyut yalnızca hızlı ön filtre olsun. Son eşleşme hash üzerinden doğrulansın.

- **Önem:** orta
- **Tür:** hata
- **Yer:** `apps/video_studio/modules/video_ingestion.py:253-259`
- **Sorun:** Farklı içerikte aynı adlı dosyalar için `_2`, `_3` adlandırması yapılıyor, ancak medya sözleşmesinde kaynak kimliği dosya içeriği hash'iyle birleştirilmiş bir cache anahtarı görünmüyor. Bu durumda aynı kaynak videonun farklı adlandırılmış kopyaları yeniden analiz edilebilir; tersine aynı adlı farklı içeriklerde eski dosyanın korunması daha ciddi bir doğruluk riski.
- **Öneri:** Kalıcı medya adını doğrudan içerik hash'ine bağlamak (ör. `<sha256>_<slug>.<ext>`) ve `source.sha256` ile çözümlemek.

- **Önem:** orta
- **Tür:** hata
- **Yer:** `apps/video_studio/modules/soundbites.py:41-64`
- **Sorun:** `Soundbite` doğrulaması yalnızca `start_s < end_s` kontrol ediyor; kesitin kaynak video süresini aşmadığını doğrulamıyor. UI mevcut videonun süresinden slider üretiyor, ancak `kesitler.json` elle bozulursa veya kaynak dosya sonradan değişirse geçersiz aralık saklanabiliyor. Sonraki render FFmpeg tarafında başarısız olabilir.
- **Öneri:** Kesit kaydını kaynak medya metadata'sıyla doğrulayan bir sınır kontrolü ekleyin; yükleme/parse aşamasında kaynak yoksa kesiti geçersiz işaretleyin.

- **Önem:** orta
- **Tür:** güvenlik
- **Yer:** `apps/video_studio/modules/video_ingestion.py:249-259`
- **Sorun:** `storage_dir / name.name` kullanımı path traversal'ı büyük ölçüde `Path(...).name` ile engelliyor, ancak dosya adı doğrulaması platforma özgü rezerve isimler, çok uzun isimler ve Windows'taki son nokta/boşluk kuralları açısından yapılmıyor. Editörün gerçek dosya adları Türkçe olabilir; bu nedenle kararlılık sınırları tam ele alınmamış.
- **Öneri:** Kalıcı medya adı için kullanıcı dosya adını doğrudan kullanmak yerine kontrollü slug/hash tabanlı ad kullanın; orijinal adı metadata'da saklayın.

- **Önem:** orta
- **Tür:** performans
- **Yer:** `apps/video_studio/modules/video_ingestion.py:192-219`
- **Sorun:** Proxy her analizde yeniden oluşturuluyor ve geçici dosyada tutuluyor. Aynı proje yeniden analiz edilirse, örneğin yalnızca prompt sürümü değiştiğinde, orijinal büyük dosyadan yeniden encode + scene detection + frame extraction yapılıyor. Cache yalnızca nihai MediaLibrary seviyesinde; ara FFmpeg işleri yeniden kullanılamıyor.
- **Öneri:** Kaynak dosya hash'i + pipeline sürümü ile proxy/sampling cache'i eklenmesi değerlendirilebilir. Özellikle 100+ MB dosyalarda ikinci analiz maliyetini azaltır.

- **Önem:** orta
- **Tür:** test
- **Yer:** `tests/test_axion_local_store.py`, `tests/test_media_pipeline.py`, `tests/test_soundbites.py`
- **Sorun:** Testler başarılı silme, normal ingest ve normal soundbite akışını kapsıyor; fakat Windows'a özgü kritik sınırlar eksik: Türkçe/özel karakter içeren gerçek Windows yolları, aynı ad + aynı boyut fakat farklı içerik, dosya kilitliyken otomatik silme, renderer fallback'i (AMF başarısız → x264), FFmpeg timeout ve bozuk/yarım MP4 gibi durumlar görünür değil.
- **Öneri:** En azından salt-Python testleriyle bu sınırların çoğu eklenmeli; gerçek FFmpeg testleri Windows CI/E2E'de ayrı koşulabilir.

- **Önem:** orta
- **Tür:** test
- **Yer:** `tests/test_axion_local_app.py`
- **Sorun:** Streamlit AppTest ile ana akış test ediliyor olsa da kod içinde açıkça "tarayıcıya özgü davranışlar AppTest'te görünmeyebilir" denmiş. Buna rağmen `bound_text()` gibi geçmişte gerçek tarayıcı hatasını hedefleyen davranışlar için gerçek browser regresyon testi yok.
- **Öneri:** Tam browser otomasyonu zorunlu değil; en azından kritik metin alanı → rerun → kaybolmama davranışı için bir manuel smoke-test senaryosu dokümante edilmeli. İleride Playwright/Selenium benzeri ince bir E2E katmanı eklenebilir.

- **Önem:** düşük
- **Tür:** sadeleştirme
- **Yer:** `apps/news_studio/ai/clients.py:44-45, 61-62`
- **Sorun:** OpenAI ve Claude üretim yolları oldukça fazla ortak akış taşıyor; özellikle retry → parse edilmiş çıktı kontrolü → usage metadata paketleme deseni iki kez yazılmış. Çalışıyor ancak ileride provider değişikliklerinde iki tarafta ayrışma riski oluşturuyor.
- **Öneri:** Provider'a özel yalnızca SDK çağrısını ayırıp ortak doğrulama/usage normalizasyonunu tek yardımcı yapıya taşımak.

- **Önem:** düşük
- **Tür:** doküman
- **Yer:** `AGENTS.md` "Kod haritası" vs. mevcut `apps/video_studio/modules/...`
- **Sorun:** AGENTS mevcut dosya haritasını doğru genel hatlarıyla veriyor; ancak bazı açıklamalar davranışın tüm ayrıntısını yansıtmıyor. Örneğin `media_pipeline.py` geçici görsel/frame/proxy temizliğini de kendi içinde yönetiyor; `video_ingestion.py` browser upload kalıcılığını belirliyor. Bu bir işlev hatası değil, gelecekte kod arayan geliştiricinin yaşam döngüsünü tek dosyadan takip edememesine yol açan hafif bir doküman açığı.
- **Öneri:** Özellikle "dosya yaşam döngüsü / hangi dosya kalıcı, hangisi geçici" bölümünü AGENTS'ta birkaç net maddeyle belirtin.

- **Önem:** düşük
- **Tür:** maliyet (token)
- **Yer:** `apps/news_studio/page.py:97-107`
- **Sorun:** Kalite kontrolünde hata varsa ikinci model çağrısı yapılıyor. Bu editör kurallarına uygun ve bilinçli bir davranış; ancak `check.errors` içine TTS karakter uzunluğu gibi deterministik hatalar da girebildiği için, küçük bir uzunluk sapması veya basit format düzeltmesi tek başına ek model çağrısı tetikleyebilir. Bu, gereksiz retrigger riskidir.
- **Öneri:** Düzeltme çağrısını yalnızca gerçekten üretken model düzeltmesi gerektiren hatalara daraltın; salt biçim/karakter sınırı gibi deterministik düzeltmeleri kod tarafında çözün. Bu bulgu davranışa etkisi açısından mevcut testlerle doğrulanmalı (**doğrulanmadı**).

- **Önem:** düşük
- **Tür:** performans
- **Yer:** `apps/news_studio/integration/history.py` ve `axion_local.py:66-75`
- **Sorun:** Geçmiş verisinin günlük temizliği ile proje temizliği aynı açılış kancasına bağlı. `delete_runs_before` veya dosya silme yavaşlarsa uygulama ilk açılışını doğrudan etkileyebilir. Büyük SQLite geçmişi veya çok sayıda proje biriktiğinde başlangıçta bekleme yaşanabilir.
- **Öneri:** Temizliği yine günlük tek sefer şartında tutup açılış render'ından bağımsız hafif bir başlangıç işi olarak çalıştırmak; gerekiyorsa süre ölçümü ve log eklemek.

---

## Pozitif doğrulamalar / sorun görülmeyen alanlar

- NewsPackage 1.1 sözleşmesi, TTS alignment ve legacy 1.0 migration için belirgin doğrulama katmanı var.
- Ses dosyasında SHA-256 doğrulaması proje yüklemede doğru bir bütünlük kontrolü sağlıyor.
- FFmpeg çağrıları ortak `ffmpeg_runner.py` üzerinden timeout ile sınırlandırılmış.
- Render önce geçici `.yaziliyor.mp4` üretip başarıdan sonra hedef dosyaya taşıyor; bu, yarım çıktı bırakma riskini azaltıyor.
- Video analizinde tek Luna çağrısı hedeflenmiş ve prompt/cache maliyeti göz önünde tutulmuş.
- Proxy ve analiz karelerinin nihai MediaLibrary dışında tutulup analiz sonunda temizlenmesi disk birikimini azaltıyor.
- Kurgunun video alanını tam doldurması ve framing testlerinin gerçek FFmpeg örnekleriyle desteklenmesi, Faz 3 editoryal kararının kod/test tarafında güçlü biçimde temsil edildiğini gösteriyor.
- Test suite; store, shared contracts, media pipeline, framing, rough cut, soundbites, TTS alignment ve viral TTS kalite kontrolü gibi ana sözleşme noktalarını kapsıyor.

## Sonuç

Statik incelemede Faz 4'e geçmeden önce düzeltilmesi en anlamlı başlıklar: otomatik silmenin hata görünmezliği/geri dönüşü, browser upload dosya eşleştirmesinde yalnızca boyut kullanılması, render katmanında `FIT_BLUR` yolunun hâlâ bulunması ve yüksek yoğunluklu görsel analizde üstten maliyet sınırının olmaması.

Windows gerçek E2E ve `make test` bu ortamda çalıştırılmadığı için bu rapor bir çalışma zamanı onayı değil, kod incelemesidir.