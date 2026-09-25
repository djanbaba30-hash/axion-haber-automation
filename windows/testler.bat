@echo off
cd /d "%~dp0.."
title Axion testleri
rem Gelistirici icin: test paketini calistirir (make gerekmez). Axion calisirken de olur, dosyalara dokunmaz.
if not exist ".venv\Scripts\python.exe" (
  echo Python ortami yok. Once windows\kurulum.bat calistir.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -q -r requirements-dev.txt
".venv\Scripts\python.exe" -m pytest -q %*
echo.
echo Sonucu Claude veya GPT ile paylasabilirsin.
pause
