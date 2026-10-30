# Plan: Globale Einstellungen mit Reitern

Task `36bd2884`, Schritt 3, vierter PR (nach #659 Archiv, #660 Module, #661 System). Till hat am 30.10.2026 freigegeben:
„Globale Einstellungen: ein Reiter je Gruppe“.
Messung (Konto hydratest, 1440×900): **3,4 Bildschirme**. 22 Einstellungen in 10 Gruppen
(Websuche 2, Mail 9, Discord 1, AgentLink 2, Health 1, Krypto 2, Home Assistant 2, Hilfe 1, System 1, Module 1).

## Ziel

- Ein Reiter je Gruppe über `AdminTabs`, in der Reihenfolge, die das Backend liefert. Die Gruppen kommen dynamisch vom
  Server, im Frontend steht keine feste Liste.
- Adresse: **`gruppe=<slug>`**, nicht `tab=`. Das Fenster öffnet sich auch aus dem System-Fenster heraus (Knopf
  „Einstellungen“). Mit `tab=` würde jeder Reiterwechsel hier den Reiter des System-Fensters dahinter verstellen.
- Slug: klein, Umlaute umgeschrieben (ä→ae …), alles andere zu `-` („Home Assistant“ → `home-assistant`). Gültig als
  HTML-ID, weil `AdminTabs` den Fokus per `#id` setzt.
- Zähler je Reiter = Anzahl Einstellungen.
- Ein Punkt erscheint, wenn eine Einstellung der Gruppe beim Speichern fehlschlug, solange das Fenster offen ist (Regel: „Punkt markiert Ungültiges“).

## Dateien

- `frontend/src/features/cockpit/admin/settingsTabs.ts` + Test (neu): `groupSlug`, `settingGroups(settings)`,
  `parseGroup(slugs, value)`
- `frontend/src/features/cockpit/admin/SystemSettingsOverlay.tsx`: `AdminTabs`, nur die Gruppe des Reiters,
  Fehlermeldung aus `SettingRow` nach oben melden (`onError(key, failed)`)

## Implementierungsreihenfolge

### Task 1: Logik
- [ ] Tests (ROT):
  - `groupSlug`: „Home Assistant“ → `home-assistant`, „Größe & Ä“ → `groesse-ae`, kein Rand-Bindestrich
  - `settingGroups`: Reihenfolge des ersten Auftretens, Einstellungen je Gruppe, Slug, Zähler
  - Rückfall auf die erste Gruppe; leere Liste → `null`
- [ ] Umsetzen (GRÜN), Mutanten: Umlaut nicht umgeschrieben, Reihenfolge alphabetisch

### Task 2: Fenster
- [ ] Test: zeigt nur die Gruppe aus `gruppe=`, liest kein `tab=` (System-Fenster dahinter bleibt unberührt)
- [ ] Punkt bei fehlgeschlagenem Speichern

### Task 3: Prüfung
- [ ] vitest, tsc, eslint, build; Browser hydratest: allein (`section=system-settings`) und aus dem System-Fenster heraus,
  Reiterwechsel ändert den Reiter des System-Fensters nicht; 1440/390

## Nicht in diesem Plan
Benutzer (nächster PR), alte Seiten `/federation`, `/modules`.
