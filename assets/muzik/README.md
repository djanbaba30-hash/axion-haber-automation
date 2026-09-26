# Müzik altlıkları

Axion'un son videolarında seslendirmenin altında çalan sözsüz haber müzikleri (v4.0.0-alpha.4).

| Dosya | Ad | Tempo, ton | Ne zaman |
|---|---|---|---|
| `gundem.mp3` | Gündem (nötr, varsayılan) | 96 BPM, La minör | Genel haber |
| `gerilim.mp3` | Gerilim | 110 BPM, Re minör | Asayiş, kaza, son dakika |
| `sakin.mp3` | Sakin | 80 BPM, Do majör | İnsan hikâyesi, duygusal haber |

**Lisans:** parçalar `uret.py` ile sıfırdan sentezlendi (kayıt ya da örnek yok); telif yok, Axion'a aittir ve
CC0 (kamu malı) olarak kullanılabilir. Yeniden üretmek: `python assets/muzik/uret.py` (numpy + FFmpeg; aynı tohum,
aynı sonuç). Parçalar tam ölçü uzunluğunda ve dairesel hesaplandığı için döngüde dikiş yoktur.

Editörün uygulamadan eklediği müzikler (Tasarım Stüdyosu → 🎵 Müzik → "Kendi müziğini ekle") yalnız o bilgisayarda
`data/varliklar/muzik/` altında kalır; GitHub'a yüklenmez (başkasının müziği, telif).
