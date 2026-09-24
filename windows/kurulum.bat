@echo off
setlocal
cd /d "%~dp0.."
title Axion Local kurulum
echo === Axion Local kurulum ===
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi, kuruluyor...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Python kuruldu. Bu pencereyi kapat ve kurulum.bat dosyasini TEKRAR calistir.
  pause
  exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg bulunamadi, kuruluyor...
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  echo.
  echo FFmpeg kuruldu. Bu pencereyi kapat ve kurulum.bat dosyasini TEKRAR calistir.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Python ortami olusturuluyor...
  py -3.12 -m venv .venv || py -3 -m venv .venv
)

echo Paketler kuruluyor, birkac dakika surebilir...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Paket kurulumu basarisiz oldu. Hata mesajini Claude'a gonder.
  pause
  exit /b 1
)

if not exist ".streamlit\secrets.toml" (
  copy ".streamlit\secrets.toml.example" ".streamlit\secrets.toml" >nul
  echo.
  echo API anahtarlarini girmen icin secrets.toml aciliyor.
  echo Anahtarlari tirnak icine yapistir, kaydet ve Not Defteri'ni kapat.
  notepad ".streamlit\secrets.toml"
)

echo Kisayollar olusturuluyor...
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\kisayol.ps1"

echo.
echo Kurulum tamam.
echo  - Masaustundeki "Axion Local" ikonuyla acabilirsin.
echo  - Bilgisayar acildiginda Axion arka planda kendiliginden baslar.
pause
