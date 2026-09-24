@echo off
cd /d "%~dp0.."
title Axion Local guncelleme
echo Calisan Axion durduruluyor...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo Son surum indiriliyor...
git pull --ff-only
if errorlevel 1 (
  echo Guncelleme basarisiz. Hata mesajini Claude'a veya GPT'ye gonder.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Paket kurulumu basarisiz. Hata mesajini Claude'a veya GPT'ye gonder.
  pause
  exit /b 1
)
echo Axion yeniden baslatiliyor...
wscript "%~dp0axion_baslat.vbs"
echo Guncelleme tamam.
timeout /t 3 >nul
