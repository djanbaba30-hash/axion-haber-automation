# Claude çalışma kuralları

- Değişiklikleri doğrudan `main` branch'ine commit ve push et; ayrı branch veya PR açma. (Repo sahibinin açık talimatı.)
- Push etmeden önce `make test` çalıştır ve geçtiğinden emin ol (`pip install -r requirements-dev.txt`).
- Ürün hedefi, editör kararları ve faz sırası için `ROADMAP.md` ana referanstır; değişiklikleri ona göre değerlendir.
- Hedef çalışma ortamı editörün evdeki bilgisayarıdır (yerel öncelikli). Streamlit Cloud geçiş sürecinde `main`'den deploy olmaya devam eder: News Studio `apps/news_studio/app.py`, Video Studio `apps/video_studio/app.py`.
