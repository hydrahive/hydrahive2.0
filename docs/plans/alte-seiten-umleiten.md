# Plan: Alte Seiten `/modules` und `/federation` ins Admin-Fenster

Task `36bd2884`, Schritt 3, letzter PR. Till 26.10.2026: „Jede Einstellung hat nur ein Zuhause.“
`/users` und `/system` leiten schon ins Admin-Fenster um (`UsersPage`, `SystemPage`). `/modules` und `/federation`
zeigen noch die alte, lange Seite im alten Look (violett, `box`).

## Befund
- `/modules`: Route hinter `AdminGuard`, also nur Admins. → einfache Umleitung nach `/admin?section=modules`.
- `/federation`: Fähigkeit `core.federation` (admin_only, **per Freigabe auch für Nutzer**, Backend `require_capability`).
  Freigegebene Nicht-Admins kommen nicht ins Admin-Cockpit (`AdminGuard`). Eine reine Umleitung würde sie aussperren.
  → wie `SystemPage`: Admin → Umleitung; sonst dasselbe `FederationOverlay` mit Reitern, Schließen → `/dashboard`.
- Der Reiter (`tab=`) wird bei der Umleitung mitgenommen.

## Dateien
- `frontend/src/features/modules/ModulesPage.tsx`: nur noch Umleitung (bisherige Seite entfällt). `ModuleCard.tsx`, `UpdateAllPanel`
  prüfen: `UpdateAllPanel` nutzt das Admin-Fenster weiter; `ModuleCard` hat nach dem Umbau keinen Nutzer mehr und wird entfernt.
- `frontend/src/features/federation/FederationPage.tsx`: Umleitung bzw. Fenster
- `frontend/src/features/legacyRedirects.test.tsx` (neu)

## Tests (ROT zuerst)
- `/modules` → `/admin?section=modules`; `/modules?tab=verfuegbar` → `…&tab=verfuegbar`
- `/federation` als Admin → `/admin?section=federation`, Reiter mitgenommen
- `/federation` als Nutzer → Föderations-Fenster mit Reitern, keine Umleitung
- Mutanten: Nutzer wird umgeleitet, Reiter geht verloren

## Prüfung
vitest, tsc, eslint, build; Browser hydratest: beide Adressen landen im richtigen Fenster und im richtigen Reiter.
