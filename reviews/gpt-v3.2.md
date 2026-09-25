# GPT incelemesi — v3.2.0 sonrası

İnceleme tarihi: 2026-09-25

Dal: `main` (`ac2ced3`)

Başlangıçta `git pull` çalıştırıldı; `Already up to date.`

`AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` içindeki v3.1.0/v3.2.0 bölümleri ve `reviews/claude-v3.md` sonundaki G1–G5 tablosu okundu. G1–G5'teki eski konular tekrar bulgu olarak açılmadı.

## Doğrulama

- İstenen test komutu: `.venv\Scripts\python.exe -m pytest -p no:cacheprovider`
- Sonuç satırı: `281 passed, 1 skipped in 56.40s`
- Atlanan test: `tests/test_effects_parity.py:46`; `-rs` ile tekrar çalıştırmada neden `Node.js kurulu değil` olarak bildirildi. Claude'un 282 geçen testinden farklı olarak burada 281 geçti, 1 atlandı.
- FFmpeg kullanan entegrasyon testleri geçti. FFmpeg'in sürüm numarasını ayrıca kaydetmedim; bu nedenle doğruladığım şey bu test ortamında kullanılan FFmpeg ile testlerin geçmesidir.
- Windows PowerShell 5.1.26100.9444 ile şu ayrıştırma komutu çalıştırıldı; hata listesi boş döndü: `powershell -NoProfile -Command "$e=$null; [System.Management.Automation.Language.Parser]::ParseFile('C:\Axion\windows\axion_calistir.ps1',[ref]$null,[ref]$e) | Out-Null; $e"`. Bu işlem betiği çalıştırmadı. `cmd /c` komut satırı ve süreç çıkış kodları da çalışma anında denenmedi.
- `windows/` altındaki `.bat`, `.vbs`, `.ps1` betiklerinin tümü ASCII ve CRLF olarak doğrulandı.
- Axion başlatılmadı/durdurulmadı; `guncelle.bat` çalıştırılmadı; paket kurulmadı. `data/` ve `.streamlit/secrets.toml` açılmadı.

## Bulgular

### 1. Şüpheli — Orta: Güncelleme akışı bekçiye durma sinyali vermiyor

**Dosyalar:** `windows/guncelle.bat:5-9`, `windows/axion_calistir.ps1:14-20,27-28`

Güncelleyici 8501 portunu dinleyen süreci `Stop-Process -Force` ile sonlandırıp `git pull` işlemine geçiyor. Bekçi ise başlattığı `cmd.exe` sürecini bekliyor; yalnızca çıkış kodu `0` veya `-1` ise döngüden çıkıyor. Güncelleyici bekçiye açıkça `-1` göndermiyor veya bekçiyi durdurmuyor. Dolayısıyla kod, zorla sonlandırılan Python sürecinin `cmd.exe` üzerinden bekçinin gördüğü `-1` değerine dönüşeceğini garanti etmiyor.

**Senaryo:** Masaüstü başlatıcısıyla açılmış Axion çalışırken `guncelle.bat` kullanılır. Python süreci öldükten sonra bekçi bunu çökme olarak yorumlarsa 5 saniye sonra Axion'ı yeniden açabilir; bu sırada `git pull` veya gereksinim kurulumu sürüyor olabilir. Tam çıkış kodu ve zamanlama betikleri çalıştırmadan doğrulanamadı; bu nedenle bulgu şüpheli olarak işaretlendi.

**Güvenli düzeltme:** Güncelleme başlamadan bekçiye açık bir durdurma sinyali/işareti verip yeniden başlatma döngüsünün bunu kontrol etmesini sağlayın veya güncelleyicide bekçi ve alt süreçleri koordineli biçimde durdurun. Windows'ta Axion açıkken güncelleme senaryosu için süreç düzeyinde regresyon testi ekleyin. Windows süreç sonlandırma davranışı için [Microsoft'un süreç sonlandırma açıklaması](https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process) da dikkate alınmalı.

### 2. Orta: Bir istemcinin WebSocket akışı diğer istemcilerin yedek görüntüsünü kapatabiliyor

**Dosyalar:** `apps/remote_browser/stream.py:27-32,70`, `apps/remote_browser/page.py:106-109`

`_last_stream` süreç genelinde tek zaman damgası. `page.py`, bu zaman damgası son iki saniyede yenilendiyse her oturum için `img=None` gönderiyor; durum hangi istemcinin akış aldığını ayırt etmiyor.

**Senaryo:** Tablet A WebSocket üzerinden kare almaya devam ederken tablet B'nin WebSocket bağlantısı ağ veya tarayıcı sorunu nedeniyle kurulamıyor. A, süreç genelindeki zaman damgasını sürekli güncellediğinden B'nin Streamlit/fragment yedek yolu da görüntü göndermiyor; B'de ekran boş kalabilir.

**Güvenli düzeltme:** Akış durumunu istemci/oturum bazında tutun ve yalnızca kendi WebSocket'i kare almış oturumun yedek `img` gönderimini kapatın. Bir istemcinin akışı çalışırken ikinci istemcinin WebSocket'siz fragment yedeğini doğrulayan test ekleyin.

### 3. Düşük: WebSocket kopuşundaki alıcı görevi istisnası tüketilmiyor

**Dosya:** `apps/remote_browser/stream.py:48-54,63-79`

`receive_text()` bağlantı kapanınca `WebSocketDisconnect` üretebilir; alıcı döngüsü yalnızca `ValueError` yakalıyor. Dış döngü `reader.done()` olduğunda sona erse de `finally` yalnızca `reader.cancel()` çağırıyor ve görevi bekleyip istisnasını tüketmiyor.

**Senaryo:** Tablet ağı değiştirir veya sekmeyi kapatır. Akış döngüsü sonlanıp istemci yeniden bağlanabilir, fakat alıcı görevinin tüketilmemiş istisnası asyncio günlüğünde `Task exception was never retrieved` uyarısı oluşturabilir.

**Güvenli düzeltme:** Beklenen WebSocket kopuşunu alıcıda normal kapanış olarak yakalayın; `finally` içinde tamamlanan görevi await edip beklenen kopuş/iptal istisnalarını bastırın. Bağlantı kesme ve yeniden bağlanma testi ekleyin.

## İncelenen diğer alanlar

- Başlatıcıdaki `cmd /c ""python.exe" ... >> "log" 2>&1"` biçimi beklenen tırnaklama biçimine uyuyor. PowerShell 5.1'de `Start-Process -PassThru` ile alınan süreçte handle edinimi, `WaitForExit()` ve ardından `ExitCode` okumasında statik bir sorun görmedim. Gerçek komut satırı/çıkış kodu davranışı çalıştırılmadı.
- `Start-Process` `-Wait` kullanmıyor; bekçi doğrudan dönen `cmd.exe` sürecini bekliyor. Kaynakta Brave sürecini bekleten bir ilişki görülmedi.
- CDP sekme seçme/kapatma ve kapanan etkin sekmeden diğer açık sekmeye geçiş kodunda yeni bir hata görmedim.
- `source_check`, `diff`, `read_along` ve başlık önizlemesinde bu incelemede yeni ve somut bir hata senaryosu bulmadım. Kaynak kontrolü heuristik olduğundan kodun kendi açıklamasındaki yazım farkı/özel isim sınırlamaları sürüyor.

