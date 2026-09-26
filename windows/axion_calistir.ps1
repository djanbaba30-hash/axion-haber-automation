# Axion baslatici bekcisi: Axion'u calistirir, cokerse 5 sn sonra yeniden baslatir (uzaktan kullanirken ise yarar).
# Yeniden baslatmaz: "Axion'u kapat" (cikis kodu 0), Stop-Process ile durdurma (kod -1) ve guncelle.bat calisirken.
# Kod 3 = uygulama icinden guncellendi: paketleri kurar, hemen yeniden baslatir (cokme sayilmaz).
# Geri donus (v3.5): yeni surum acilis kontrolunden (apps.axion_local.self_check) gecmezse ya da ilk 3 dakikada
# cokerse onceki surume doner (git reset --keep; yerel degisikliklere dokunmaz) ve bunu Axion'a bildirir.
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
$previousFile = Join-Path $data 'guncelleme_onceki.txt'  # Axion guncellemeden once calisan surumu yazar
$rollbackFile = Join-Path $data 'guncelleme_geri_alindi.txt'  # geri donulurse Axion kenar cubugunda uyarir
$previous = $null
$updatedAt = $null
function Invoke-Rollback([string]$reason) {
    $failed = (& git rev-parse HEAD 2>$null | Out-String).Trim()
    Add-Content -Path $log -Value "[$(Get-Date)] Yeni surum acilamadi ($reason); onceki surume donuluyor: $previous"
    Add-Content -Path $log -Value (& git reset --keep $previous 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        Add-Content -Path $log -Value "[$(Get-Date)] Onceki surume donulemedi (yerel degisiklik?); guncelle.bat gerekir."
        return
    }
    & $python -m pip install --disable-pip-version-check -q -r requirements.txt *>> $log
    Set-Content -Path $rollbackFile -Encoding ASCII -Value @("failed=$failed", "reason=$reason", "time=$(Get-Date -Format s)")
}
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
    $justUpdated = $previous -and $updatedAt -and ((Get-Date) - $updatedAt).TotalMinutes -lt 3
    $updatedAt = $null
    if ($code -eq 0 -or $code -eq -1) { break }
    if ($code -eq 3) {
        # Uygulama yeni surumu indirdi (git pull); calisan Python kapaliyken paketleri kur, sonra yeniden baslat.
        Add-Content -Path $log -Value "[$(Get-Date)] Axion guncellendi; paketler kontrol ediliyor, yeniden baslatiliyor."
        & $python -m pip install --disable-pip-version-check -q -r requirements.txt *>> $log
        $previous = $null
        if (Test-Path $previousFile) {
            $previous = (Get-Content -Path $previousFile -TotalCount 1).Trim()
            Remove-Item -Force $previousFile
        }
        if ($previous) {
            Add-Content -Path $log -Value (& $python -m apps.axion_local.self_check 2>&1 | Out-String)
            if ($LASTEXITCODE -ne 0) {
                Invoke-Rollback 'kontrol'
                $previous = $null
            } else {
                $updatedAt = Get-Date
            }
        }
        continue
    }
    if ($justUpdated -and -not (Test-Updating)) {
        # Guncellemeden hemen sonra coktu: yeni surum bozuk sayilir.
        Invoke-Rollback 'cokme'
        $previous = $null
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
