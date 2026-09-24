@echo off
cd /d "%~dp0.."
title Axion Local guncelleme
echo Son surum indiriliyor...
git pull --ff-only
if errorlevel 1 (
  echo Guncelleme basarisiz. Hata mesajini Claude'a gonder.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Guncelleme tamam. Axion Local aciksa kapatip yeniden baslat.
pause
