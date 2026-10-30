# Plan: System-Fenster mit Reitern

Task `36bd2884`, Schritt 3, dritter PR (nach #659 Archiv, #660 Module). Die Aufteilung hat Till am 30.10.2026 freigegeben.
Messung (Konto hydratest, 1440×900): **3,8 Bildschirme**, 9 Bereiche untereinander.

## Ziel

Reiter über `AdminTabs`, Adresse `tab=`:

| Reiter | Inhalt |
|---|---|
| `ueberblick` | Gesundheitsleiste, 8 Kennzahlen, Pfade |
| `netzwerk` | AgentLink, Tailscale, Netzwerk-Bridge, Samba |
| `erweiterungen` | Zusatz-Module, Lokale Bild-/Videogenerierung |
| `sicherung` | System-Backup, Server-Migration |

- Punkt an `ueberblick`, wenn eine Gesundheitsprüfung nicht ok ist. Die Leiste zeigt das heute nur im Reiter selbst.
- **Nicht-Admins** sehen nur, was sie heute sehen: Überblick und Netzwerk (nur AgentLink). Die Reiter Erweiterungen und Sicherung
  entfallen für sie.
- Die Kopfknöpfe (Einstellungen, Neustart) bleiben unverändert.

## Dateien

- `frontend/src/features/cockpit/admin/systemTabs.ts` + Test (neu): `systemTabList(isAdmin)`, `parseSystemTab(value, isAdmin)`,
  `systemTabs(checks, isAdmin, t)`
- `frontend/src/features/cockpit/admin/SystemOverlay.tsx`: `AdminTabs`, Bereiche je Reiter
- i18n `system.json` de/en: `tabs.ueberblick|netzwerk|erweiterungen|sicherung`

## Implementierungsreihenfolge

### Task 1: Logik
- [ ] Tests (ROT):
  - Admin: 4 Reiter in fester Reihenfolge; Nicht-Admin: `ueberblick, netzwerk`
  - Rückfall `ueberblick`; Nicht-Admin mit `tab=sicherung` → `ueberblick` (kein leerer Reiter)
  - Punkt bei Überblick, wenn mindestens eine Prüfung nicht ok ist; kein Punkt, wenn alle ok oder noch keine geladen
- [ ] Umsetzen (GRÜN), Mutanten: Nicht-Admin sieht Sicherung, Punkt immer aus

### Task 2: Fenster
- [ ] Bereiche je Reiter; die Rollenprüfungen bleiben wie heute
- [ ] Bestehende Tests grün

### Task 3: Prüfung
- [ ] vitest, tsc, eslint, build; Browser hydratest 1440/390, jeder Reiter gemessen, Neuladen behält den Reiter

## Akzeptanz
- [ ] Kein Reiter länger als etwa 1,5 Bildschirme
- [ ] Nicht-Admin sieht keine leeren Reiter

## Nicht in diesem Plan
Globale Einstellungen (eigenes Fenster, nächster PR), Benutzer, Umleitungen der alten Seiten.
