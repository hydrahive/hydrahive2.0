# Plan: Admin-Cockpit-Startseite kompakt

Task `36bd2884` („Lange Seiten kürzen“), Folgeschritt. Till am 30.10.2026: „mache es der reihe nach, und mache was am besten ist“.
Messung (hydratest, 1440×900): **1,8 Bildschirme**, 8 Kästen in drei Spalten.

## Befund
- Reine Entwickler-/Erklärtexte ohne Nutzen für den Admin: **Status** („Admin ist jetzt kein leerer Platzhalter mehr …“),
  **Nächste Ausbaustufen** (Roadmap), **Sicherheitsregeln** (Erklärtext + 4 Spiegelstriche).
- Doppelte Einstiege:
  - Module, Plugins, Credentials stehen links (Admin-Bereiche) **und** in „Integrationen“
  - Archiv steht links **und** in „Wartung & Backups“
  - „Backup“ öffnet nur das System-Fenster (links schon da)
  - „System-Settings“ ist Kopfknopf im System-Fenster
- Nur in den Doppel-Kästen, also beim Zusammenlegen zu erhalten: **Gitea** (→ Extensions), **Freigaben** (→ access),
  **Globale Einstellungen** (→ system-settings).

## Ziel (eine Seite, jeder Einstieg genau einmal)

| Spalte | Inhalt |
|---|---|
| links: **Verwaltung** | System, Benutzer, Freigaben, Module, Extensions (Gitea), Plugins, Credentials, Archiv (kurze Zeilen) |
| Mitte: **Betriebszentrale** | Hinweis zu neuen Freigaben (`AccessNotice`, wie bisher), Kacheln LLM … Zahnfee + Globale Einstellungen |
| rechts: **Zustand** | echte Gesundheitsprüfung (`systemApi.health`, wie `HealthBar`) kompakt als Liste; Problem → Status `fehler` am Kasten; Knopf „Admin-Agent öffnen“ |

- Gesundheit wird beim Öffnen **einmal** geladen, nicht in einer Schleife. Der Erklärtext „Logs und Status werden nicht breit gepollt“
  bleibt damit gültig.
- Ein Klick auf eine Prüfung mit Problem öffnet das System-Fenster.

## Dateien
- `frontend/src/features/cockpit/adminCockpitLinks.ts` + Test (neu): Linklisten als Daten, Test „jeder Pfad genau einmal“
  und „Freigaben, Gitea, Globale Einstellungen bleiben erreichbar“
- `frontend/src/features/cockpit/admin/AdminHealthPanel.tsx` + Test (neu): kompakte Gesundheitsliste, Status am Kasten
- `frontend/src/features/cockpit/AdminCockpitPage.tsx`: drei Kästen statt acht
- `AdminInfoCard.tsx`: prüfen, ob noch genutzt, sonst entfernen

## Reihenfolge
1. `adminCockpitLinks.test.ts` (ROT) → Daten (GRÜN); Mutante: Archiv doppelt, Freigaben fehlt
2. `AdminHealthPanel.test.tsx` (ROT): alle ok → `ok`-Schild, eine nicht ok → `fehler`, Zeile nennt Prüfung; leer → Ladehinweis
3. Seite umbauen, alte Kästen raus
4. vitest, tsc, eslint, build; Browser hydratest 1440/1024/390: Seite ≤ 1 Bildschirm bei 1440, jeder Einstieg öffnet sein Fenster

## Nicht in diesem Plan
Projekt-Cockpit (nächster PR), Module.
