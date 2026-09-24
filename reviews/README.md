# Kod incelemeleri

Faz sonlarında Claude ve GPT repoyu ayrı ayrı inceler ve bulgularını buraya yazar; inceleme sırasında kod değiştirilmez.
Editör raporları karşılaştırır, onaylanan düzeltmeler sonra tek seferde yapılır.

Rapor biçimi (her bulgu için):

- **Önem:** kritik / yüksek / orta / düşük
- **Tür:** hata / güvenlik / performans / maliyet (token) / sadeleştirme / test / doküman
- **Yer:** `dosya.py:satır`
- **Sorun:** ne yanlış, hangi durumda ortaya çıkar (somut örnek)
- **Öneri:** nasıl düzeltilir
