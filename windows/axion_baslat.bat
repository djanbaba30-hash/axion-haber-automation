@echo off
cd /d "%~dp0.."
title Axion Local
if not exist ".venv\Scripts\python.exe" (
  echo Once windows\kurulum.bat dosyasini calistir.
  pause
  exit /b 1
)
set AXION_LOCAL=1
echo Axion Local basliyor. Tarayici birazdan acilacak.
echo Bu pencereyi KAPATMA; kapatirsan sistem durur.
echo.
".venv\Scripts\python.exe" -m streamlit run axion_local.py --server.port 8501 --server.maxUploadSize 4096 --browser.gatherUsageStats false
pause
