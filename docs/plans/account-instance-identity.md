# Plan: Konto, Rolle und HydraHive-Instanz dauerhaft sichtbar

## Ziel

Auf jeder HydraHive-Seite mit globaler Topbar sind Benutzername, Rolle und aktuelle Browserinstanz dauerhaft sichtbar. Das Systemkonto `admin` ist unübersehbar als privilegierter Arbeitskontext markiert und erklärt, dass seine Chats/Sitzungen getrennt von normalen Benutzerkonten geführt werden.

## Entscheidungen

- Instanzkennung ist `window.location.host`; kein zweiter Backend-Konfigurationsweg.
- Die Anzeige sitzt im bestehenden `CockpitUserMenu`, das von `AreaTopbar` global verwendet wird.
- Normal: Benutzername plus `Nutzer · <host>`.
- Admin: Warnfarbe, Shield-Icon und `SYSTEM-ADMIN · <host>` bereits im geschlossenen Topbar-Schalter.
- Das geöffnete Admin-Menü enthält einen Warnhinweis zur getrennten Sitzungszuordnung.
- Die Anzeige ist rein informativ; Serverautorisierung bleibt unverändert.

## Dateien

- `frontend/src/features/cockpit/CockpitUserMenu.tsx` — permanente Identitätsanzeige und Adminwarnung.
- `frontend/src/features/cockpit/CockpitUserMenu.test.tsx` — normal/admin/Instanz/Storewechsel.
- `frontend/src/features/cockpit/instanceIdentity.ts` — sichere Host-/Rollenbeschriftung.
- `frontend/src/features/cockpit/instanceIdentity.test.ts` — Fallback- und Labeltests.

## TDD

1. RED: Normalnutzer zeigt Benutzer, Rolle und Host.
2. RED: Admin zeigt `SYSTEM-ADMIN`, Warnstil und Erklärung.
3. RED: geänderter Storezustand erzeugt andere sichtbare Identität.
4. RED: fehlender Browserhost nutzt sicheren Fallback.
5. GREEN: Helper und Usermenü implementieren.
6. TypeScript, Zieltests und Frontend-Gesamtsuite.
7. HH-/Accessibility-Review, Commit, PR, CI.

## Akzeptanzkriterien

- Benutzername, Rolle und Host sind ohne Öffnen des Menüs sichtbar.
- `admin` kann optisch nicht mit einem normalen Nutzer verwechselt werden.
- Das Menü erklärt die getrennte Chat-/Sessionzuordnung.
- Der Button hat ein vollständiges `aria-label` und bleibt mobil nutzbar.
- Keine Authlogik und keine Serverrechte werden clientseitig verändert.
