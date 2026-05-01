# HydraHive2 — Übergabe (Stand 2026-05-01 spät, Tailscale + Projekt-Tabs + Installer-Härtung)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

## TL;DR der heutigen Session

Drei Themen + Installer-Saga:

1. **Projekt-Seite Tab-Layout** (#57 #58 #59 #60) — ProjectForm bekommt
   Übersicht/Sessions/Git/Statistiken/Einstellungen. Backend: neue
   Endpoints `/api/projects/{id}/git` (Branch/Remote/ahead-behind/Commits)
   und `/api/projects/{id}/stats` (Sessions/Tokens/Aktivität).
   Sub-Komponenten als `_OverviewTab.tsx`, `_SessionsTab.tsx`, etc.
   Save-Button erscheint nur dirty.

2. **Marvin-Onboarding für Master-Agent** — Bei `ensure_master` wird
   `startup.md` (Marvin-Stil, 6 Fragen) in den Workspace geschrieben.
   System-Prompt enthält Trigger: "wenn `startup.md` existiert, lies
   und arbeite ab, dann lösche". Selbstzerstörend nach erstem Onboarding.
   Pattern aus `octopos/skills/catalog/onboard-agent.md` übernommen.

3. **Tailscale-Saga** — fünf Iterationen durch sudo-Sandboxing-Hölle,
   am Ende: `/run/tailscale/tailscaled.sock` ist `srw-rw-rw-`, sudo
   war NIE nötig. Lösung: `tailscale set --operator=hydrahive` in
   80-tailscale.sh, kein sudo mehr im Python-Code, Service-Unit hat
   `NoNewPrivileges=true` zurück. Tailscale wird jetzt **default
   installiert** (opt-out via `HH_INSTALL_TAILSCALE=no`).

4. **Installer-Härtung** durch frisches Setup auf Produktiv-LXC:
   - `.config`/`.cache`/`.local/share`/`.mmx` für hydrahive-User
     vorlegen (ReadWritePaths-226-Errors)
   - nginx default-yes (war opt-in — Server war ohne nicht erreichbar)
   - TLS-Cert-SAN mit detektierter Server-IP statt nur 127.0.0.1
   - Update-Check via HTTPS-Remote (SSH-URL wird automatisch umgebogen
     — der hydrahive-User hat keine SSH-Keys)
   - nginx `enable + start` statt nur `reload`
   - Install-Zusammenfassung mit URL + Admin-Login am Ende

## Was läuft auf 218 + neuer Produktiv-Server

Gleicher Stand. Tailscale connected via Frontend-Login auf beiden.
Neuer Server: gleiche Setup-Pfade wie 218 — Setup-User chucky / Service-User
hydrahive (Passwort siehe Install-Output bzw. Journal).

## Frische Code-Änderungen heute (commits)

```
c666f12 Tailscale default installieren
285679a Tailscale ohne sudo — operator-Flag + Socket
8bace05 NoNewPrivileges raus (zwischenzeitlich, später wieder rein)
25fb8d0 Tailscale-Pfad via shutil.which (zwischenzeitlich)
23dfb3f update.sh NEEDS_REWRITE-Check für /run/sudo (zwischenzeitlich)
522a26a ExecStartPre /run/sudo (zwischenzeitlich)
cd0038b version-Check via HTTPS-Remote
d79dc20 /run/sudo in ReadWritePaths (zwischenzeitlich)
b5e76fd Projekt-Tabs: Übersicht/Sessions/Git/Stats/Einstellungen
8f68e80 Marvin-Onboarding via startup.md
53f8bb3 Install-Zusammenfassung URL + Login
da5d353 nginx default + TLS-SAN mit Server-IP
d98c1ab .mmx-Verzeichnis für hydrahive
5448242 .config/.cache/.local/share für hydrahive
```

Die "zwischenzeitlich"-Marker: NoNewPrivileges, /run/sudo, ExecStartPre
sind alle wieder zurückgerollt — `285679a` ist der saubere Endstand.
update.sh hat Migration die alte Service-Units mit dem Workaround
auf die saubere Form bringt.

## Was offen ist

### P1 (groß)

1. **#38 User-Backup Self-Service** — komplementär zu Admin-Backup, DSGVO Art. 20
2. **#43 Edit + Resend** Chat-Bubble
3. **#55 ToolsSelector-Akkordeon** + **#56 AgentForm Tabs**
4. **#62 Server-Tab im Projekt** (VMs+Container assignen) — bei den
   Projekt-Tabs heute bewusst ausgelassen, braucht eigene VM/Container-Logik
5. **#26 Skills-System** (SPEC-Lücke) — Marvin-Onboarding heute ist
   ein Vorläufer, aber ohne richtiges Skills-System

### P2 / P3

Wie gehabt — Chat-Polish-Reste, Discord/Telegram/Matrix, Projekt-Sektionen
Phase 2, ~30 Tags-Audit-Member-Webhooks-Issues.

## Lessons Learned heute (in Memory persistiert)

- **Erst Ist-Zustand checken, dann Hypothesen** — Tailscale-Saga lief
  zwei Stunden weil ich Code-Hypothesen iteriert habe statt am Live-218
  per SSH zu checken was tatsächlich anders ist. Bei Server-Bugs immer
  zuerst `cat`/`ls`/`groups`/`systemctl` auf dem funktionierenden
  Server, dann Code-Änderung. Memory-Eintrag: `feedback_check_actual_state_first.md`

- **update.sh Self-Update-Bug** — wenn update.sh sich selbst aktualisiert,
  greifen neue Checks erst beim NÄCHSTEN Lauf, weil bash das Skript schon
  geladen hat. Bei wichtigen Migration-Checks: zwei update.sh-Läufe
  einplanen, oder re-exec nach git pull einbauen. Bisher nicht umgesetzt.

## Test-Plan beim Reopen

1. Projekt-Tabs auf https://192.168.178.218/ (oder neuer Server) — alle
   5 Tabs öffnen: Übersicht/Sessions/Git/Statistiken/Einstellungen
2. Tailscale-Card: Status zeigt connected mit IP/Hostname
3. Neuer Master-Agent (z.B. zweiten User anlegen): kommt Marvin-Onboarding
   in der ersten Konversation? Stellt er die 6 Fragen? Löscht er
   `startup.md` am Ende?
4. Update-Knopf: ist er sichtbar wenn Server hinter `main`? Triggert er
   das Update?
