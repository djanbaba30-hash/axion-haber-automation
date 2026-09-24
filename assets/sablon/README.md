# Axion şablon dosyaları (Faz 5 — Tasarım Stüdyosu)

Tasarım Stüdyosu son videoyu (1080×1920) bu dosyalarla kurar. Ölçü ve zamanlar: `shared/axion_template.py`.

| Dosya | Ne | Not |
|---|---|---|
| `arka_plan_1.png` … `arka_plan_8.png` | 8 arka plan (9:16) | Numara = kullanım sırası. Her iş günü (02:00'de) bir sonrakine geçilir; aynı gün tüm haberler aynı arka planı kullanır. 24.09.2026 = 1. |
| `logo.png` | Axion Haber logosu, şeffaf zemin | Beyaz yuvarlak köşeli kutunun içine yerleştirilir (kutu kodda çizilir). |
| `slogan_1.png`, `slogan_2.png` | "TARAFSIZ VE ŞEFFAF HABERCİLİK", "BEĞEN, PAYLAŞ, TAKİP ET" | Canva'dan dışa aktarılmış hâlleri; %78 ölçekle başlık kutusunun ortasına gelir. |
| `fontlar/GoogleSans-Bold.ttf`, `fontlar/OFL.txt` | Başlık yazı tipi ve lisansı (SIL Open Font License) | Lisans dosyası fontla birlikte kalmalı. |
| `ornek_canva.mp4` | Editörün Canva'dan çıkmış örnek videosu | Animasyon zamanları bundan ölçüldü (yalnızca başvuru; uygulama kullanmaz). |

Bir dosyayı değiştirmek için aynı adla yeniden yüklemek yeterli (ör. yeni bir arka plan için `arka_plan_3.png`).
Yeni yazı tipi veya arka plan Tasarım Stüdyosu → **📦 Varlıklar** sekmesinden de eklenebilir: önce bilgisayarda
`data/varliklar/` altına yazılır, `GITHUB_TOKEN` tanımlıysa buraya da yüklenir.
