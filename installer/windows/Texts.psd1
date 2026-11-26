# Meldungen des Windows-Installers. Deutsch, sonst Englisch (Ziel §3).
@{
    NeedAdmin     = @{ de = 'Bitte PowerShell als Administrator öffnen: Startmenü, „PowerShell“ rechts anklicken, „Als Administrator ausführen“. Dann den Befehl erneut einfügen.'
                       en = 'Please open PowerShell as administrator: Start menu, right-click "PowerShell", "Run as administrator". Then paste the command again.' }
    OldWindows    = @{ de = 'Windows ist zu alt (Build {0}). Nötig ist Windows 10 ab Build 19041 oder Windows 11. Bitte zuerst Windows aktualisieren.'
                       en = 'Windows is too old (build {0}). Windows 10 build 19041 or newer, or Windows 11, is required. Please update Windows first.' }
    NoVirt        = @{ de = 'Die Virtualisierung ist im BIOS/UEFI ausgeschaltet. Bitte dort „Intel VT-x“ bzw. „AMD-V/SVM“ einschalten und das Skript erneut starten.'
                       en = 'Virtualization is disabled in BIOS/UEFI. Please enable "Intel VT-x" or "AMD-V/SVM" there and run the script again.' }
    Reboot        = @{ de = 'Windows muss neu starten. Nach der Anmeldung läuft die Installation von selbst weiter. Jetzt neu starten? (J/N)'
                       en = 'Windows needs to restart. After you sign in, the installation continues automatically. Restart now? (Y/N)' }
    RebootLater   = @{ de = 'Bitte Windows bald neu starten. Nach der Anmeldung läuft die Installation von selbst weiter.'
                       en = 'Please restart Windows soon. After you sign in, the installation continues automatically.' }
    AskUser       = @{ de = 'Name für den Ubuntu-Benutzer (klein, ohne Leerzeichen, z. B. anna)'
                       en = 'Name for the Ubuntu user (lowercase, no spaces, e.g. anna)' }
    BadUser       = @{ de = 'Ungültiger Name. Erlaubt: Kleinbuchstaben, Ziffern, - und _, beginnt mit einem Buchstaben, höchstens 32 Zeichen.'
                       en = 'Invalid name. Allowed: lowercase letters, digits, - and _, starting with a letter, at most 32 characters.' }
    AskPass       = @{ de = 'Passwort für den Ubuntu-Benutzer'; en = 'Password for the Ubuntu user' }
    AskPass2      = @{ de = 'Passwort wiederholen'; en = 'Repeat password' }
    PassMismatch  = @{ de = 'Die Passwörter sind verschieden oder leer. Bitte noch einmal.'
                       en = 'The passwords differ or are empty. Please try again.' }
    StepCheck     = @{ de = 'Prüfe Windows'; en = 'Checking Windows' }
    StepWsl       = @{ de = 'WSL und Ubuntu 26.04'; en = 'WSL and Ubuntu 26.04' }
    StepUser      = @{ de = 'Ubuntu-Benutzer'; en = 'Ubuntu user' }
    StepConf      = @{ de = 'WSL-Einstellungen (systemd, dauerhaft an)'; en = 'WSL settings (systemd, keep running)' }
    StepInstall   = @{ de = 'HydraHive installieren (etwa 10–20 Minuten)'; en = 'Installing HydraHive (about 10–20 minutes)' }
    StepAutostart = @{ de = 'Autostart bei der Windows-Anmeldung'; en = 'Autostart at Windows sign-in' }
    StepDone      = @{ de = 'Warte auf HydraHive'; en = 'Waiting for HydraHive' }
    Skip          = @{ de = '  schon erledigt'; en = '  already done' }
    WslFailed     = @{ de = 'WSL oder Ubuntu ließ sich nicht installieren. Details im Protokoll: {0}'
                       en = 'WSL or Ubuntu could not be installed. Details in the log: {0}' }
    NoSystemd     = @{ de = 'systemd läuft in Ubuntu nicht. Bitte „wsl --update“ ausführen und das Skript erneut starten.'
                       en = 'systemd is not running in Ubuntu. Please run "wsl --update" and start the script again.' }
    InstallFailed = @{ de = 'Die HydraHive-Installation ist fehlgeschlagen. Protokoll: {0}'
                       en = 'The HydraHive installation failed. Log: {0}' }
    Ready         = @{ de = 'Fertig! HydraHive läuft: {0}{1}Anmelden mit Benutzer „admin“ und dem Passwort, das oben angezeigt wurde (sofort notieren!).{1}Die Zertifikatswarnung im Browser ist normal: „Weiter“.{1}HydraHive startet ab jetzt bei jeder Windows-Anmeldung von selbst.'
                       en = 'Done! HydraHive is running: {0}{1}Sign in as "admin" with the password shown above (write it down now!).{1}The browser certificate warning is expected: "Continue".{1}From now on HydraHive starts automatically whenever you sign in to Windows.' }
    NotReady      = @{ de = 'HydraHive antwortet noch nicht unter {0}. Bitte in ein paar Minuten im Browser versuchen. Protokoll: {1}'
                       en = 'HydraHive is not answering at {0} yet. Please try in the browser in a few minutes. Log: {1}' }
}
