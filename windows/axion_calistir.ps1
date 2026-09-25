# Axion baslatici bekcisi: Axion'u calistirir, cokerse 5 sn sonra yeniden baslatir (uzaktan kullanirken ise yarar).
# Yeniden baslatmaz: "Axion'u kapat" (cikis kodu 0), Stop-Process ile durdurma (kod -1) ve guncelle.bat calisirken.
# Kod 3 = uygulama icinden guncellendi: paketleri kurar, hemen yeniden baslatir (cokme sayilmaz).
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
$env:AXION_BEKCI = '1'  # Axion bunu gorunce "Guncelle ve yeniden baslat" dugmesini gosterir
function Test-Updating {
    $found = Get-CimInstance Win32_Process -Filter "Name = 'cmd.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match 'guncelle\.bat' }
    return [bool]$found
}
while ($true) {
    $command = '/c ""' + $python + '" -m streamlit run axion_app.py >> "' + $log + '" 2>&1"'
    # -Wait kullanilmaz: alt surecleri (Brave) de bekler; Axion coker Brave acik kalirsa bekci hic uyanmazdi.
    $process = Start-Process -FilePath 'cmd.exe' -ArgumentList $command -WindowStyle Hidden -PassThru
    $null = $process.Handle  # cikis kodunun okunabilmesi icin (Windows PowerShell 5.1)
    $process.WaitForExit()
    $code = $process.ExitCode
    if ($code -eq 0 -or $code -eq -1) { break }
    if ($code -eq 3) {
        # Uygulama yeni surumu indirdi (git pull); calisan Python kapaliyken paketleri kur, sonra yeniden baslat.
        Add-Content -Path $log -Value "[$(Get-Date)] Axion guncellendi; paketler kontrol ediliyor, yeniden baslatiliyor."
        & $python -m pip install --disable-pip-version-check -q -r requirements.txt *>> $log
        continue
    }
    # guncelle.bat calisiyorsa yeniden baslatma (cift tiklayinca komut satiri: cmd.exe /c ""...\guncelle.bat" ").
    if (Test-Updating) { break }
    $now = Get-Date
    $crashes = @($crashes | Where-Object { ($now - $_).TotalMinutes -lt 10 }) + $now
    if ($crashes.Count -ge 3) {
        Add-Content -Path $log -Value "[$now] Axion 10 dakikada 3 kez coktu (kod $code); yeniden baslatma durdu."
        break
    }
    Add-Content -Path $log -Value "[$now] Axion kapandi (kod $code); 5 sn sonra yeniden baslatiliyor."
    Start-Sleep -Seconds 5
    if (Test-Updating) { break }  # bu arada guncelleme baslamis olabilir
}
