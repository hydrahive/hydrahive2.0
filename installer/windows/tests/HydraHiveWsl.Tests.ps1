# Pester 5 – läuft in CI unter pwsh auf Linux (.github/workflows/windows-installer.yml). Abnahme W2/W3.
BeforeAll { Import-Module (Join-Path $PSScriptRoot '..' 'HydraHiveWsl.psm1') -Force }

Describe 'Merge-HHIniSetting (.wslconfig / wsl.conf zusammenführen, nie überschreiben)' {
    It 'behält vorhandenes dnsTunneling und andere Abschnitte' {
        $old = "[wsl2]`ndnsTunneling=false`nmemory=4GB`n`n# Kommentar`n[experimental]`nsparseVhd=true`n"
        $new = Merge-HHIniSetting $old 'general' 'instanceIdleTimeout' '-1'
        $new | Should -Match 'dnsTunneling=false'
        $new | Should -Match 'memory=4GB'
        $new | Should -Match '# Kommentar'
        $new | Should -Match 'sparseVhd=true'
        Get-HHIniValue $new 'general' 'instanceIdleTimeout' | Should -Be '-1'
        Get-HHIniValue $new 'wsl2' 'dnsTunneling' | Should -Be 'false'
    }
    It 'ersetzt einen vorhandenen Wert statt ihn doppelt anzulegen' {
        $new = Merge-HHIniSetting "[general]`ninstanceIdleTimeout=15000`n" 'general' 'instanceIdleTimeout' '-1'
        ([regex]::Matches($new, 'instanceIdleTimeout')).Count | Should -Be 1
        Get-HHIniValue $new 'general' 'instanceIdleTimeout' | Should -Be '-1'
    }
    It 'fügt im vorhandenen Abschnitt ein, nicht dahinter' {
        $new = Merge-HHIniSetting "[boot]`ncommand=x`n[user]`ndefault=anna`n" 'boot' 'systemd' 'true'
        Get-HHIniValue $new 'boot' 'systemd' | Should -Be 'true'
        Get-HHIniValue $new 'user' 'systemd' | Should -BeNullOrEmpty
        Get-HHIniValue $new 'user' 'default' | Should -Be 'anna'
    }
    It 'legt eine leere Datei sauber an' {
        Merge-HHIniSetting '' 'general' 'instanceIdleTimeout' '-1' | Should -Be "[general]`ninstanceIdleTimeout=-1`n"
    }
    It 'ist idempotent (zweiter Lauf ändert nichts)' {
        $a = Merge-HHIniSetting "[wsl2]`ndnsTunneling=false`n" 'general' 'instanceIdleTimeout' '-1'
        Merge-HHIniSetting $a 'general' 'instanceIdleTimeout' '-1' | Should -BeExactly $a
    }
    It 'behält Windows-Zeilenenden' {
        Merge-HHIniSetting "[wsl2]`r`nmemory=4GB`r`n" 'general' 'x' '1' | Should -Match "`r`n\[general\]`r`nx=1`r`n$"
    }
}

Describe 'Prüfungen' {
    It 'Windows-Build' { Test-HHWindowsBuild 19041 | Should -BeTrue; Test-HHWindowsBuild 19040 | Should -BeFalse }
    It 'Linux-Benutzername <n> → <ok>' -ForEach @(
        @{ n = 'anna'; ok = $true }, @{ n = 'a-b_1'; ok = $true }, @{ n = 'Anna'; ok = $false },
        @{ n = '1anna'; ok = $false }, @{ n = 'root'; ok = $false }, @{ n = 'hydrahive'; ok = $false },
        @{ n = "an na"; ok = $false }, @{ n = "x'; rm -rf /"; ok = $false }, @{ n = ('a' * 33); ok = $false }
    ) { Test-HHLinuxUserName $n | Should -Be $ok }
    It 'erkennt Ubuntu-26.04 in UTF-16-Ausgabe von wsl --list' {
        Test-HHDistroInstalled @("U`0b`0u`0n`0t`0u`0-`02`06`0.`00`04`0", 'docker-desktop') | Should -BeTrue
        Test-HHDistroInstalled @('Ubuntu-24.04', 'Ubuntu') | Should -BeFalse
        Test-HHDistroInstalled @() | Should -BeFalse
    }
}

Describe 'Neustart-Erkennung' {
    It 'erkennt <t>' -ForEach @(
        @{ t = 'The requested operation is successful. Changes will not be effective until the system is rebooted.' },
        @{ t = 'Die angeforderte Operation ist erfolgreich. Änderungen werden erst nach einem Neustart des Systems wirksam.' }
    ) { Test-HHRebootRequired @('x', $t) | Should -BeTrue }
    It 'sonst nicht' { Test-HHRebootRequired @('Ubuntu-26.04 wurde installiert.') | Should -BeFalse }
}

Describe 'Befehle für Ubuntu' {
    It 'ruft den Linux-Installer auf statt ihn nachzubauen (W2)' {
        $c = Get-HHInstallCommand
        $c | Should -Match 'installer/install\.sh'
        $c | Should -Not -Match '/mnt/c'
        $c | Should -Not -Match 'apt-get install -y -q (?!git)'
    }
    It 'zweiter Lauf aktualisiert /opt/hydrahive2 statt neu zu klonen (W3)' {
        Get-HHInstallCommand | Should -Match 'if \[ -d /opt/hydrahive2/\.git \]'
    }
    It 'Passwort geht nie als Argument an Ubuntu' {
        $c = Get-HHUserCommand 'anna'
        $c | Should -Match 'chpasswd$'
        $c | Should -Not -Match 'passwd .*anna:'
    }
    It 'lehnt unsichere Namen ab' { { Get-HHUserCommand "a'b" } | Should -Throw }
    It 'Autostart startet Ubuntu-26.04 ohne Fenster' {
        Get-HHAutostartArgument | Should -Be '-d Ubuntu-26.04 --exec /bin/true'
    }
}

Describe 'Texte und Protokoll' {
    It 'jeder Text hat Deutsch und Englisch' {
        $t = Import-PowerShellDataFile (Join-Path $PSScriptRoot '..' 'Texts.psd1')
        foreach ($k in $t.Keys) { $t[$k].de | Should -Not -BeNullOrEmpty; $t[$k].en | Should -Not -BeNullOrEmpty }
    }
    It 'Sprache aus der Windows-Oberfläche' { Get-HHLanguage 'de-DE' | Should -Be 'de'; Get-HHLanguage 'en-US' | Should -Be 'en' }
    It 'Passwort wird im Protokoll geschwärzt' {
        ConvertTo-HHSafeLog 'anna:Geh3im!' @('Geh3im!') | Should -Be 'anna:***'
    }
}
