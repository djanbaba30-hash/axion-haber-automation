test:
	python -m unittest discover -s tests -v

news:
	streamlit run apps/news_studio/app.py

video:
	streamlit run apps/video_studio/app.py
