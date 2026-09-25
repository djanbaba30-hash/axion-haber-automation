@echo off
cd /d "%~dp0.."
title Axion testleri
rem Gelistirici icin: test paketini calistirir (make gerekmez). Axion calisirken de olur; sonuc data\test_sonucu.txt dosyasina da yazilir.
if not exist ".venv\Scripts\python.exe" (
  echo Python ortami yok. Once windows\kurulum.bat calistir.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -q -r requirements-dev.txt
if not exist data mkdir data
echo Testler calisiyor, bir dakika kadar surer...
".venv\Scripts\python.exe" -m pytest -q -p no:cacheprovider %* > data\test_sonucu.txt 2>&1
type data\test_sonucu.txt
echo.
echo ==============================================================
echo Sonuc yukaridaki SON SATIR (ornek: 240 passed, 25 skipped).
echo "failed" yoksa her sey yolunda. Tamami: data\test_sonucu.txt
echo Bu dosyayi ya da son satiri Claude veya GPT ile paylasabilirsin.
echo ==============================================================
pause
