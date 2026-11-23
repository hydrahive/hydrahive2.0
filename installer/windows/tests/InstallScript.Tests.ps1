# Statische Prüfungen am Ablauf install.ps1 (Abnahme W1–W4); ausführen geht nur auf echtem Windows (W6).
BeforeAll { $script:src = Get-Content -Raw (Join-Path $PSScriptRoot '..' 'install.ps1') }

Describe 'install.ps1' {
    It 'prüft Adminrechte vor allem anderen' {
        $script:src.IndexOf('IsInRole') | Should -BeLessThan $script:src.IndexOf("Step 2 'StepWsl'")
    }
    It 'installiert Ubuntu-26.04 über die Distro-Variable, nicht 24.04' {
        $script:src | Should -Not -Match '24\.04'
        $script:src | Should -Match "'--install', '-d', \`$Distro"
    }
    It 'schreibt kein Passwort ins Protokoll und speichert es nirgends' {
        $script:src | Should -Match 'Secrets \+= \$p1'
        $script:src | Should -Match '-AsSecureString'
        $script:src | Should -Not -Match 'Set-Content[^\n]*\$p1'
        $script:src | Should -Not -Match 'Add-Content[^\n]*\$p1'
    }
    It 'führt .wslconfig zusammen und sichert sie vorher' {
        $script:src | Should -Match "Merge-HHIniSetting \`$old 'general' 'instanceIdleTimeout' '-1'"
        $script:src | Should -Match '\.wslconfig\.bak'
    }
    It 'Autostart bei Anmeldung, ohne gespeichertes Passwort' {
        $script:src | Should -Match 'New-ScheduledTaskTrigger -AtLogOn'
        $script:src | Should -Match '-LogonType Interactive'
        $script:src | Should -Not -Match '-LogonType (Password|S4U)'
    }
    It 'jeder Schritt prüft, ob er schon erledigt ist (W3)' {
        ([regex]::Matches($script:src, "Say 'Skip'")).Count | Should -BeGreaterOrEqual 4
        $script:src | Should -Match 'Register-ScheduledTask -Force'
    }
    It 'setzt die ExecutionPolicy nicht dauerhaft' { $script:src | Should -Not -Match 'Set-ExecutionPolicy' }
}
