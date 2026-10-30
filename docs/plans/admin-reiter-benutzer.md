# Plan: Benutzer-Fenster mit Reitern

Task `36bd2884`, Schritt 3, fünfter PR (nach #659–#662). Till hat am 30.10.2026 freigegeben: „Benutzer: Reiter Benutzer, Gruppen, API-Keys“.
Messung (Konto hydratest, 1440×900): **2,1 Bildschirme**, drei Teile untereinander.

## Ziel
- Reiter über `AdminTabs`, Adresse `tab=benutzer|gruppen|api-keys`
  - **Benutzer**: Liste mit Aktionen, Zähler = Anzahl Benutzer
  - **Gruppen**: `GroupsSection`
  - **API-Keys**: `ApiKeysSection`
- Der Kopfknopf „+ Neuer Benutzer“ erscheint nur im Reiter Benutzer. In den anderen Reitern wäre er missverständlich, denn Gruppen und
  API-Keys haben ihre eigenen Anlege-Knöpfe.
- Fehler- und Erfolgsmeldungen (Tresor-Zurücksetzen, Laden) stehen über den Reitern.

## Dateien
- `frontend/src/features/cockpit/admin/usersTabs.ts` + Test: `USERS_TABS`, `parseUsersTab`
- `frontend/src/features/cockpit/admin/UsersOverlay.tsx`: Benutzerliste als eigene Komponente `UserRows` (Datei bleibt < 200 Zeilen),
  `AdminTabs`
- `frontend/src/features/cockpit/admin/UsersOverlay.test.tsx` (neu): Teil je Reiter, Kopfknopf nur bei Benutzer
- i18n `users.json`: `tabs.benutzer|gruppen|api-keys`

## Reihenfolge
1. Tests (ROT) → Logik + Fenster (GRÜN) → Mutanten: Gruppen im falschen Reiter, Kopfknopf überall
2. vitest, tsc, eslint, build; Browser hydratest 1440/390

## Nicht in diesem Plan
Umleitung der alten Seiten `/federation`, `/modules` (letzter PR dieses Schritts).
