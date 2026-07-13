# Plan: Buddy Idle→Working-Übergangsvideo

## Ziel

Beim Wechsel in den Working-Zustand spielt das Buddy-Aktionsfenster einmalig ein eigens erstelltes Idle→Working-Video ab. Danach zeigt es den bisherigen Working-Zustand. Das bestehende Idle-Video bleibt eine Endlosschleife.

## Dateien

- `frontend/public/buddy/buddy-idle-to-working.mp4` — lautloses Übergangsvideo im Repo
- `frontend/src/features/buddy/_BuddyActionVisual.tsx` — Zustandsdarstellung und einmaliger Übergang
- `frontend/src/features/buddy/BuddyPage.tsx` — bindet die neue Zustandskomponente ein
- `docs/specs/buddy-idle-video.md` — erweitert die Aktionsvideo-Spezifikation
- `docs/plans/buddy-action-transition-video.md` — Implementierungs- und Verifikationsplan

## Implementierungsreihenfolge

### Task 1: Übergangsasset übernehmen

- [x] Workspace-Video ohne Neucodierung des H.264-Bildes kopieren
- [x] AAC-Tonspur physisch entfernen
- [x] Mit ffprobe bestätigen: ein Videostream, kein Audiostream, vier Sekunden

### Task 2: Zustandskomponente

- [x] Idle rendert `buddy-idle.mp4` mit Loop
- [x] Working startet `buddy-idle-to-working.mp4` ohne Loop
- [x] `onEnded` schaltet auf das bestehende Working-Maskottchen
- [x] Speaking zeigt weiterhin direkt das bestehende Speaking-Maskottchen
- [x] Komponente beim Zustandswechsel per Key remounten, damit ein neuer Working-Eintritt den Übergang neu startet

### Task 3: Verifikation

- [x] TypeScript-Typecheck grün
- [x] ESLint ohne neue Errors
- [x] Cockpit-Offline-Guard grün
- [x] Produktionsbuild grün und beide Videos in `dist/buddy/`
- [x] HH2-Strukturreview grün

## Akzeptanzkriterien

- [x] Idle-Video bleibt eine Endlosschleife
- [x] Idle→Working-Video läuft genau einmal pro Working-Eintritt
- [x] Übergangsvideo besitzt kein `loop`-Attribut
- [x] Nach dem Übergang wird Working-Maskottchen angezeigt
- [x] Alle Repo-Videos sind physisch lautlos

## Nicht in diesem Plan

- Working→Idle-Übergang
- Speaking-Übergangsvideos
- Backend- oder API-Änderungen
