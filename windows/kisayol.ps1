# Masaustune "Axion Local" kisayolunu olusturur. Axion yalnizca bu ikonla acildiginda calisir.
$root = Split-Path -Parent $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$s = $shell.CreateShortcut((Join-Path $desktop 'Axion Local.lnk'))
$s.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
$s.Arguments = '"' + (Join-Path $root 'windows\axion_baslat.vbs') + '"'
$s.WorkingDirectory = $root
$s.IconLocation = Join-Path $root 'windows\axion_x.ico'
$s.Save()

# Eski surumun Windows acilisi kisayolu varsa kaldir.
$startup = Join-Path ([Environment]::GetFolderPath('Startup')) 'Axion Local.lnk'
if (Test-Path $startup) { Remove-Item $startup -Force }
