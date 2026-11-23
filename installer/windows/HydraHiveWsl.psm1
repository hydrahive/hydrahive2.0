# HydraHive unter Windows (WSL) – testbare Bausteine für install.ps1.
# Ziel: hydrahive2-modules/ziele/windows-installer.md (freigegeben 23.11.2026, Nachtrag Ubuntu 26.04).
# Reine Funktionen (Text rein, Text raus) werden in tests/*.Tests.ps1 (Pester) auf Linux-CI geprüft.

Set-StrictMode -Version Latest

$script:Distro = 'Ubuntu-26.04'
$script:TaskName = 'HydraHive (WSL)'
$script:RepoUrl = 'https://github.com/hydrahive/hydrahive2.0.git'
$script:MinBuild = 19041

function Get-HHDistroName { $script:Distro }
function Get-HHTaskName { $script:TaskName }

function Test-HHWindowsBuild { param([int]$Build) $Build -ge $script:MinBuild }

function Test-HHLinuxUserName {
    param([string]$Name)
    # Wie adduser (NAME_REGEX von Ubuntu); belegte Systemnamen ausgeschlossen.
    if ($Name -cnotmatch '^[a-z][a-z0-9_-]{0,31}$') { return $false }
    $Name -notin @('root', 'hydrahive', 'daemon', 'bin', 'sys', 'nobody', 'postgres', 'www-data')
}

function Test-HHDistroInstalled {
    # wsl.exe --list --quiet gibt UTF-16 aus; Nullbytes entfernen.
    param([string[]]$ListOutput, [string]$Name = $script:Distro)
    $names = @($ListOutput | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ })
    $names -contains $Name
}

function Merge-HHIniSetting {
    <# Setzt Section/Key=Value in einem INI-Text. Andere Abschnitte, Schlüssel und Kommentare bleiben.
       Schlüssel vorhanden → Wert ersetzt; Abschnitt fehlt → am Ende angehängt. #>
    param([AllowEmptyString()][string]$Text, [Parameter(Mandatory)][string]$Section,
          [Parameter(Mandatory)][string]$Key, [Parameter(Mandatory)][string]$Value)
    $nl = if ($Text -match "`r`n") { "`r`n" } else { "`n" }
    $lines = [System.Collections.Generic.List[string]]::new()
    if ($Text) { foreach ($l in ($Text -split "`r?`n")) { $lines.Add($l) } }
    while ($lines.Count -and $lines[$lines.Count - 1] -eq '') { $lines.RemoveAt($lines.Count - 1) }
    $secRe = '^\s*\[\s*' + [regex]::Escape($Section) + '\s*\]\s*$'
    $keyRe = '^\s*' + [regex]::Escape($Key) + '\s*='
    $start = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match $secRe) { $start = $i; break } }
    if ($start -lt 0) {
        $lines.Clear()   # GEGENPROBE: überschreibt statt zusammenzuführen
        $lines.Add("[$Section]"); $lines.Add("$Key=$Value")
    } else {
        $end = $lines.Count
        for ($i = $start + 1; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^\s*\[') { $end = $i; break } }
        $found = $false
        for ($i = $start + 1; $i -lt $end; $i++) {
            if ($lines[$i] -match $keyRe) { $lines[$i] = "$Key=$Value"; $found = $true; break }
        }
        if (-not $found) {
            $insert = $end
            while ($insert -gt $start + 1 -and $lines[$insert - 1] -eq '') { $insert-- }
            $lines.Insert($insert, "$Key=$Value")
        }
    }
    ($lines -join $nl) + $nl
}

function Get-HHIniValue {
    param([AllowEmptyString()][string]$Text, [string]$Section, [string]$Key)
    $in = $false
    foreach ($l in ($Text -split "`r?`n")) {
        if ($l -match '^\s*\[\s*(.+?)\s*\]\s*$') { $in = ($Matches[1] -eq $Section); continue }
        if ($in -and $l -match ('^\s*' + [regex]::Escape($Key) + '\s*=\s*(.*?)\s*$')) { return $Matches[1] }
    }
    $null
}

function Get-HHInstallCommand {
    <# Der normale Linux-Installer, keine zweite Logik. Klon im Linux-Dateisystem (nie /mnt/c).
       install.sh verschiebt den Klon nach /opt/hydrahive2; ist der da, wird von dort aktualisiert. #>
    param([string]$RepoUrl = $script:RepoUrl, [string]$Branch = 'main')
    @(
        'set -e'
        'export DEBIAN_FRONTEND=noninteractive'
        'command -v git >/dev/null || { apt-get update -q; apt-get install -y -q git; }'
        'if [ -d /opt/hydrahive2/.git ]; then'
        '  git config --global --add safe.directory /opt/hydrahive2'
        "  git -C /opt/hydrahive2 fetch -q origin '$Branch'"
        "  git -C /opt/hydrahive2 checkout -q '$Branch'"
        '  git -C /opt/hydrahive2 pull -q --ff-only'
        '  exec bash /opt/hydrahive2/installer/install.sh'
        'fi'
        'rm -rf /root/hydrahive2-src'
        "git clone -q --branch '$Branch' '$RepoUrl' /root/hydrahive2-src"
        'exec bash /root/hydrahive2-src/installer/install.sh'
    ) -join "`n"
}

function Get-HHUserCommand {
    # Benutzer anlegen (falls fehlt), Gruppe sudo. Passwort geht über stdin an chpasswd – nie als Argument.
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Test-HHLinuxUserName $Name)) { throw 'invalid user name' }
    "id -u '$Name' >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo '$Name'; chpasswd"
}

function Get-HHAutostartArgument {
    # Startet Ubuntu ohne Fenster; instanceIdleTimeout=-1 hält es danach am Laufen.
    param([string]$Distro = $script:Distro)
    "-d $Distro --exec /bin/true"
}

$script:Texts = Import-PowerShellDataFile -Path (Join-Path $PSScriptRoot 'Texts.psd1')

function Get-HHLanguage {
    param([string]$Culture = (Get-UICulture).Name)
    if ($Culture -like 'de*') { 'de' } else { 'en' }
}

function Get-HHText {
    param([Parameter(Mandatory)][string]$Key, [string]$Lang = (Get-HHLanguage), [object[]]$Arg = @())
    if (-not $script:Texts.ContainsKey($Key)) { return $Key }
    $t = $script:Texts[$Key]
    $s = if ($t.ContainsKey($Lang)) { $t[$Lang] } else { $t['en'] }
    if ($Arg.Count) { $s -f $Arg } else { $s }
}

function ConvertTo-HHSafeLog {
    # Nie Passwörter ins Protokoll: bekannte Geheimnisse durch *** ersetzen.
    param([AllowEmptyString()][string]$Line, [string[]]$Secret = @())
    foreach ($s in $Secret) { if ($s) { $Line = $Line.Replace($s, '***') } }
    $Line
}

Export-ModuleMember -Function *-HH*
