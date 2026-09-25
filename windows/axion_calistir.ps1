# Axion baslatici bekcisi: Axion'u calistirir, cokerse 5 sn sonra yeniden baslatir (uzaktan kullanirken ise yarar).
# Yeniden baslatmaz: "Axion'u kapat" (cikis kodu 0) ve guncelle.bat / Stop-Process ile durdurma (kod -1).
# 10 dakikada 3 kez cokerse durur (surekli coken bir hata dongusu olmasin). Kayit: data\axion.log
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root '.venv\Scripts\python.exe'
$data = Join-Path $root 'data'
$log = Join-Path $data 'axion.log'
New-Item -ItemType Directory -Force -Path $data | Out-Null
if (Test-Path $log) { Move-Item -Force $log (Join-Path $data 'axion.onceki.log') }
$crashes = @()
while ($true) {
    $command = '/c ""' + $python + '" -m streamlit run axion_app.py >> "' + $log + '" 2>&1"'
    # -Wait kullanilmaz: alt surecleri (Brave) de bekler; Axion coker Brave acik kalirsa bekci hic uyanmazdi.
    $process = Start-Process -FilePath 'cmd.exe' -ArgumentList $command -WindowStyle Hidden -PassThru
    $null = $process.Handle  # cikis kodunun okunabilmesi icin (Windows PowerShell 5.1)
    $process.WaitForExit()
    $code = $process.ExitCode
    if ($code -eq 0 -or $code -eq -1) { break }
    $now = Get-Date
    $crashes = @($crashes | Where-Object { ($now - $_).TotalMinutes -lt 10 }) + $now
    if ($crashes.Count -ge 3) {
        Add-Content -Path $log -Value "[$now] Axion 10 dakikada 3 kez coktu (kod $code); yeniden baslatma durdu."
        break
    }
    Add-Content -Path $log -Value "[$now] Axion kapandi (kod $code); 5 sn sonra yeniden baslatiliyor."
    Start-Sleep -Seconds 5
}
