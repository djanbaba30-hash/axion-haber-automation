# Claude çalışma kuralları

- Değişiklikleri doğrudan `main` branch'ine commit ve push et; ayrı branch veya PR açma. (Repo sahibinin açık talimatı.)
- Push etmeden önce `make test` çalıştır ve geçtiğinden emin ol (`pip install -r requirements-dev.txt`).
- Streamlit Cloud uygulamaları `main`'den deploy edilir: News Studio `apps/news_studio/app.py`, Video Studio `apps/video_studio/app.py`.
