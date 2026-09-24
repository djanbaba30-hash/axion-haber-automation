@echo off
rem API anahtarlarini ve istege bagli sifreyi duzenlemek icin.
cd /d "%~dp0.."
if not exist ".streamlit\secrets.toml" copy ".streamlit\secrets.toml.example" ".streamlit\secrets.toml" >nul
notepad ".streamlit\secrets.toml"
echo Degisikliklerin gecerli olmasi icin Axion'u kapatip yeniden ac.
timeout /t 5 >nul
