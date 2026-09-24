# Masaustu ve Windows acilisi icin "Axion Local" kisayollarini olusturur.
$root = Split-Path -Parent $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell
$launcher = Join-Path $root 'windows\axion_baslat.vbs'
$targets = @(
    @{ Folder = [Environment]::GetFolderPath('Desktop'); Args = '' },
    @{ Folder = [Environment]::GetFolderPath('Startup'); Args = ' /arkaplan' }
)
foreach ($t in $targets) {
    $s = $shell.CreateShortcut((Join-Path $t.Folder 'Axion Local.lnk'))
    $s.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
    $s.Arguments = '"' + $launcher + '"' + $t.Args
    $s.WorkingDirectory = $root
    $s.IconLocation = Join-Path $root 'windows\axion.ico'
    $s.Save()
}
