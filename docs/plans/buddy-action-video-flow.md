# Plan: Vollständiger Buddy-Aktionsvideo-Ablauf

## Ziel

Das Buddy-Aktionsfenster zeigt den gesamten Chat-Lifecycle mit sechs lautlosen Videos. Idle und Working loopen; Start, Erfolg, Fehler und Rückkehr zu Idle laufen einmal.

## Dateien

- `frontend/public/buddy/buddy-working.mp4` — Working-Loop
- `frontend/public/buddy/buddy-error.mp4` — einmalige Fehlerreaktion
- `frontend/public/buddy/buddy-success.mp4` — einmalige Erfolgsreaktion
- `frontend/public/buddy/buddy-working-to-idle.mp4` — einmaliger Rückübergang
- `frontend/src/features/buddy/_buddyActionState.ts` — pure Zustandsmaschine
- `frontend/src/features/buddy/_BuddyActionVisual.tsx` — rendert Video oder Speaking-Maskottchen
- `frontend/src/features/buddy/BuddyPage.tsx` — leitet Busy-, Fehler- und Erfolgssignal weiter
- `frontend/src/features/chat/useChat.ts` — setzt das Erfolgssignal beim Start eines neuen Laufs zurück
- `docs/specs/buddy-idle-video.md` — vollständige fachliche Spezifikation

## Implementierungsreihenfolge

### Task 1: Assets

- [x] Vier Workspace-Videos mit kopiertem H.264-Bildstream übernehmen
- [x] AAC-Tonspuren physisch entfernen
- [x] 1280×720, vier Sekunden und fehlende Audiostreams mit ffprobe bestätigen

### Task 2: Zustandsmaschine (TDD)

- [x] RED: Erfolgs-, Fehler-, Kurzlauf- und Abbruchsequenzen als Assertions definieren
- [x] GREEN: pure Zustandsübergänge implementieren
- [x] Ergebnis während des Startvideos vormerken statt den Übergang abzuschneiden
- [x] Ergebnisreaktion bei anschließendem Idle-Signal vollständig abspielen

### Task 3: UI-Integration

- [x] `lastTurnTokens` bei Sendestart auf `null` setzen
- [x] Chat-State auf `idle | working | success | error` abbilden
- [x] Speaking-Maskottchen als temporäres Overlay erhalten
- [x] Nur Idle und Working loopen

### Task 4: Verifikation

- [x] Unit-Assertions für die pure State-Machine grün
- [x] Headless-Chromium verifiziert beide kompletten Abläufe und Loop-Attribute
- [x] TypeScript-Typecheck grün
- [x] ESLint ohne neue Fehler oder Warnungen
- [x] Cockpit-Offline-Guard grün
- [x] Produktionsbuild grün und alle sechs Videos in `dist/buddy/`
- [x] HH2-Strukturreview grün

## Akzeptanzkriterien

- [x] Erfolgsablauf vollständig und in richtiger Reihenfolge
- [x] Fehlerablauf vollständig und in richtiger Reihenfolge
- [x] Gelungen läuft genau einmal
- [x] Error läuft genau einmal
- [x] Working→Idle läuft genau einmal
- [x] Idle und Working laufen als Loops
- [x] Keine der sechs Repo-Dateien enthält Audio

## Nicht in diesem Plan

- Neue Backend-Events oder API-Endpunkte
- Eigene Speaking-Videos
- Änderungen an Größe oder Position des Aktionsfensters
