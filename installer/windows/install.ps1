#Requires -Version 5.1
<#
.SYNOPSIS
  HydraHive unter Windows: WSL + Ubuntu 26.04 + HydraHive + Autostart, mit einem Befehl.
.DESCRIPTION
  Ziel: hydrahive2-modules/ziele/windows-installer.md. Wiederholbar: jeder Schritt prüft, ob er schon erledigt ist.
  Protokoll: %LOCALAPPDATA%\HydraHive\install.log (ohne Passwörter).
  Start (PowerShell als Administrator) – Datei laden und als Datei starten, nicht „| iex“ (sonst schließt ein
  Fehler das ganze Fenster); ExecutionPolicy nur für diesen einen Aufruf:
    irm https://raw.githubusercontent.com/hydrahive/hydrahive2.0/main/installer/windows/install.ps1 -OutFile $env:TEMP\hh-install.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\hh-install.ps1
#>
[CmdletBinding()]
param([string]$Branch = 'main', [switch]$Resume)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$Raw = "https://raw.githubusercontent.com/hydrahive/hydrahive2.0/$Branch/installer/windows"
$HHDir = Join-Path $env:LOCALAPPDATA 'HydraHive'
$Log = Join-Path $HHDir 'install.log'
New-Item -ItemType Directory -Force -Path $HHDir | Out-Null

# Modul, Texte und dieses Skript nach %LOCALAPPDATA%\HydraHive holen (Start aus TEMP), damit auch der
# Weiterlauf nach einem Neustart sie findet.
$here = if ($PSScriptRoot) { $PSScriptRoot } else { $HHDir }
if (-not (Test-Path (Join-Path $here 'HydraHiveWsl.psm1'))) {
    foreach ($f in 'HydraHiveWsl.psm1', 'Texts.psd1', 'install.ps1') {
        Invoke-WebRequest -UseBasicParsing -Uri "$Raw/$f" -OutFile (Join-Path $HHDir $f)
    }
    $here = $HHDir
}
Import-Module (Join-Path $here 'HydraHiveWsl.psm1') -Force
$Distro = Get-HHDistroName
$script:Secrets = @()

function Write-Log([string]$m) {
    Add-Content -Path $Log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), (ConvertTo-HHSafeLog $m $script:Secrets))
}
function Say([string]$key, [object[]]$a = @()) { $t = Get-HHText $key -Arg $a; Write-Host $t; Write-Log $t }
function Step([int]$n, [string]$key) { $t = "[$n/7] " + (Get-HHText $key); Write-Host "`n$t" -ForegroundColor Cyan; Write-Log $t }
function Fail([string]$key, [object[]]$a = @()) { $t = Get-HHText $key -Arg $a; Write-Host $t -ForegroundColor Red; Write-Log "FEHLER: $t"; exit 1 }
# Windows PowerShell 5.1: bei 2>&1 und ErrorActionPreference=Stop bricht die erste stderr-Zeile eines Programms
# alles ab – install.sh schreibt viel nach stderr. Deshalb in diesen Hüllen lokal „Continue“.
function Wsl([string[]]$a) {
    $ErrorActionPreference = 'Continue'
    & wsl.exe @a 2>&1 | ForEach-Object { ("$_" -replace "`0", '') }
}
function InDistro([string]$cmd, $stdin = $null, [switch]$Show) {   # $stdin bewusst ohne [string]: $null bleibt $null
    $ErrorActionPreference = 'Continue'
    # PowerShell hängt beim Weiterreichen \r\n an – in bash mit tr entfernen (sonst \r im Passwort).
    $full = if ($null -ne $stdin) { "tr -d '\r' | { $cmd; }" } else { $cmd }
    $run = { if ($null -ne $stdin) { $stdin | & wsl.exe -d $Distro -u root -- bash -c $full 2>&1 }
             else { & wsl.exe -d $Distro -u root -- bash -c $full 2>&1 } }
    & $run | ForEach-Object {
        $l = "$_"
        if ($Show) { Write-Host $l }
        # Admin-Startpasswort und andere Passwortzeilen nie ins Protokoll.
        if ($l -notmatch '(?i)passwor[dt]\s*:') { Write-Log $l } else { Write-Log '(Passwortzeile ausgelassen)' }
    }
    $LASTEXITCODE
}
function Get-DistroFile([string]$path) {
    $ErrorActionPreference = 'Continue'
    (& wsl.exe -d $Distro -u root -- bash -c "cat '$path' 2>/dev/null") -join "`n"
}
function Set-DistroFile([string]$path, [string]$text) { [void](InDistro "cat > '$path'" $text) }

Write-Log "=== Start (Branch $Branch, Resume=$Resume) ==="

# 1 – Vorprüfung
Step 1 'StepCheck'
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Fail 'NeedAdmin' }
$build = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber
if (-not (Test-HHWindowsBuild $build)) { Fail 'OldWindows' @($build) }
$virt = (Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled
$hyper = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent
if (-not $virt -and -not $hyper) { Fail 'NoVirt' }

# 2 – WSL und Ubuntu
Step 2 'StepWsl'
$wslOk = $null -ne (Get-Command wsl.exe -ErrorAction SilentlyContinue)
$list = if ($wslOk) { Wsl @('--list', '--quiet') } else { @() }
if (Test-HHDistroInstalled $list) { Say 'Skip' }
else {
    Wsl @('--install', '--no-distribution') | ForEach-Object { Write-Log $_ }
    Wsl @('--update') | ForEach-Object { Write-Log $_ }
    $out = Wsl @('--install', '-d', $Distro, '--no-launch')
    $out | ForEach-Object { Write-Log $_ }
    if (-not (Test-HHDistroInstalled (Wsl @('--list', '--quiet')))) {
        if (($out -join ' ') -match '(?i)restart|reboot|neustart|neu ?gestartet|neu starten') {
            # Einmaliger Weiterlauf nach der nächsten Anmeldung (RunOnce, löscht sich selbst).
            # RunOnce startet ohne Adminrechte → Weiterlauf fordert sie selbst an (UAC-Abfrage nach der Anmeldung).
            $inner = "Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass " +
                     "-NoExit -File `"$HHDir\install.ps1`" -Branch $Branch -Resume'"
            $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))
            $cmd = "powershell.exe -NoProfile -WindowStyle Hidden -EncodedCommand $enc"
            if ((Join-Path $here 'install.ps1') -ne "$HHDir\install.ps1") {
                Copy-Item -Force (Join-Path $here 'install.ps1') "$HHDir\install.ps1" -ErrorAction SilentlyContinue
            }
            New-ItemProperty -Force -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' `
                -Name 'HydraHiveInstall' -Value $cmd | Out-Null
            if ((Read-Host (Get-HHText 'Reboot')) -match '^[jJyY]') { Restart-Computer -Force }
            Say 'RebootLater'; exit 0
        }
        Fail 'WslFailed' @($Log)
    }
}

# 3 – Ubuntu-Benutzer (Standardbenutzer; das Passwort wird nirgends gespeichert)
Step 3 'StepUser'
$conf = Get-DistroFile '/etc/wsl.conf'
$existing = Get-HHIniValue $conf 'user' 'default'
if ($existing -and (InDistro "id -u '$existing' >/dev/null 2>&1") -eq 0) { Say 'Skip' }
else {
    do { $name = (Read-Host (Get-HHText 'AskUser')).Trim(); if (-not (Test-HHLinuxUserName $name)) { Say 'BadUser' } }
    until (Test-HHLinuxUserName $name)
    do {
        $p1 = [Net.NetworkCredential]::new('', (Read-Host (Get-HHText 'AskPass') -AsSecureString)).Password
        $p2 = [Net.NetworkCredential]::new('', (Read-Host (Get-HHText 'AskPass2') -AsSecureString)).Password
        $ok = $p1 -and ($p1 -ceq $p2); if (-not $ok) { Say 'PassMismatch' }
    } until ($ok)
    $script:Secrets += $p1
    if ((InDistro (Get-HHUserCommand $name) "${name}:$p1") -ne 0) { Fail 'InstallFailed' @($Log) }
    $p1 = $p2 = $null
    $conf = Merge-HHIniSetting $conf 'user' 'default' $name
    Set-DistroFile '/etc/wsl.conf' $conf
}

# 4 – WSL-Einstellungen: systemd in Ubuntu, dauerhaft an (.wslconfig zusammenführen, Sicherung)
Step 4 'StepConf'
$restart = $false
if ((Get-HHIniValue $conf 'boot' 'systemd') -ne 'true') {
    Set-DistroFile '/etc/wsl.conf' (Merge-HHIniSetting $conf 'boot' 'systemd' 'true'); $restart = $true
}
$wslconfig = Join-Path $env:USERPROFILE '.wslconfig'
$old = if (Test-Path $wslconfig) { Get-Content -Raw $wslconfig } else { '' }
if ((Get-HHIniValue $old 'general' 'instanceIdleTimeout') -ne '-1') {
    if ($old) { Copy-Item -Force $wslconfig "$wslconfig.bak" }
    [IO.File]::WriteAllText($wslconfig, (Merge-HHIniSetting $old 'general' 'instanceIdleTimeout' '-1'), [Text.UTF8Encoding]::new($false))
    $restart = $true
}
if ($restart) { Wsl @('--shutdown') | Out-Null; Start-Sleep -Seconds 10 }   # Microsoft: „8-Sekunden-Regel“
if ((InDistro 'test -d /run/systemd/system') -ne 0) { Fail 'NoSystemd' }
if (-not $restart) { Say 'Skip' }

# 5 – HydraHive: der normale Linux-Installer
Step 5 'StepInstall'
if ((InDistro 'systemctl is-active --quiet hydrahive2') -eq 0) { Say 'Skip' }
# Skript über stdin statt als mehrzeiliges Argument an wsl.exe.
elseif ((InDistro 'bash -s' (Get-HHInstallCommand -Branch $Branch) -Show) -ne 0) { Fail 'InstallFailed' @($Log) }

# 6 – Autostart bei der Anmeldung (Stufe A; ohne Anmeldung geht WSL nicht: microsoft/WSL#9231)
Step 6 'StepAutostart'
$me = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$task = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument (Get-HHAutostartArgument)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $me
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -Force -TaskName (Get-HHTaskName) -Action $task -Trigger $trigger -Principal $principal `
    -Settings $settings -Description 'Startet HydraHive (Ubuntu in WSL) bei der Anmeldung.' | Out-Null
Write-Log "Aufgabe '$(Get-HHTaskName)' für $me eingerichtet"
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'HydraHiveInstall' -ErrorAction SilentlyContinue

# 7 – Warten, bis https://localhost antwortet (curl.exe ist seit Windows 10 1803 dabei)
Step 7 'StepDone'
$url = 'https://localhost'
$deadline = (Get-Date).AddMinutes(3); $code = ''
while ((Get-Date) -lt $deadline) {
    $code = & curl.exe -sk -o NUL -w '%{http_code}' --max-time 5 "$url/api/health" 2>$null
    if ($code -eq '200') { break }; Start-Sleep -Seconds 5
}
if ($code -eq '200') { Write-Host ''; Write-Host (Get-HHText 'Ready' -Arg @($url, [Environment]::NewLine)) -ForegroundColor Green; Write-Log 'Fertig' }
else { Say 'NotReady' @($url, $Log) }
