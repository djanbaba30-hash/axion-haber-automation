@echo off
rem Sorun giderme icin: Axion'u gorunur pencerede baslatir ve hata mesajlarini gosterir.
rem Gunluk kullanim icin masaustundeki "Axion Local" ikonunu kullan.
cd /d "%~dp0.."
title Axion Local (sorun giderme)
if not exist ".venv\Scripts\python.exe" (
  echo Once windows\kurulum.bat dosyasini calistir.
  pause
  exit /b 1
)
set AXION_LOCAL=1
echo Adres: http://localhost:8501
echo Axion arka planda zaten calisiyorsa once uygulamadaki "Axion'u kapat" dugmesini kullan.
echo.
".venv\Scripts\python.exe" -m streamlit run axion_local.py --server.port 8501 --server.headless true --server.maxUploadSize 4096 --browser.gatherUsageStats false --client.toolbarMode minimal
pause
