@echo off
cd /d "%~dp0.."
title Axion Local guncelleme
echo Calisan Axion durduruluyor...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
rem Tarayici sayfasinin gorunmez Brave'i (Axion profili: data\tarayici) acik kaldiysa kapat; normal Brave'e dokunmaz.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('\data\tarayici') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
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
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\kisayol.ps1"
echo Guncelleme tamam. Axion kapali: masaustundeki Axion simgesiyle ac.
timeout /t 5 >nul
