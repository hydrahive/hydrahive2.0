# Plan: Globale Projekt-Handover-Datei

## Ziel

Projektzustand über Compactions und bewusst gestartete neue Chats hinweg automatisch erhalten.

## Dateien

- `core/src/hydrahive/handover.py` — Handover erzeugen, atomar schreiben, lesen und prompten.
- `core/src/hydrahive/compaction/compactor.py` — nach erfolgreicher Compaction persistieren.
- `core/src/hydrahive/api/routes/sessions.py` — wartender Handover-Endpunkt.
- `core/src/hydrahive/runner/runner.py` — Handover nur in leere neue Projekt-Session einlesen.
- `core/src/hydrahive/buddy/commands.py` — Buddy-Neustart mit Handover und Projektübernahme.
- `frontend/src/features/chat/api.ts` — Handover-API.
- `frontend/src/features/chat/ChatPane.tsx` und `commands.ts` — neue Chats warten lassen.
- `frontend/src/features/buddy/BuddyPage.tsx` — Busy-Anzeige.
- `core/tests/test_project_handover.py` — Unit-/Integrationsabdeckung.

## Implementierungsreihenfolge

### Task 1: Sicherer Handover-Store
- [ ] Tests für Projektpfad, Redaction, atomisches Schreiben und Lesen schreiben.
- [ ] Tests rot ausführen.
- [ ] Store und Prompt-Rendering implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(handover): add project checkpoint store`

### Task 2: Compaction und neuer Chat
- [ ] Tests für Compaction-Persistenz und wartenden API-Call schreiben.
- [ ] Handover nach erfolgreicher Compaction schreiben.
- [ ] Session-Endpunkt zum Erzeugen einer vollständigen Übergabe ergänzen.
- [ ] Buddy-Clear projektgebunden und wartend machen.
- [ ] Commit: `feat(handover): persist checkpoints across sessions`

### Task 3: Automatisches Einlesen und UI
- [ ] Test: nur leere neue Projekt-Session bekommt Handover-Prompt.
- [ ] Runner-Injektion implementieren.
- [ ] Alle expliziten Neuer-Chat-Pfade awaiten; Busy-Text anzeigen.
- [ ] Frontend-Build und Backendtests ausführen.
- [ ] Commit: `feat(chat): await project handover before new session`

## Akzeptanzkriterien

- [ ] Spec-Kriterien erfüllt.
- [ ] Backendtests, Ruff und Frontend-Build grün.
- [ ] HH2-Review ohne neue Verletzungen.

## Nicht in diesem Plan

- Automatische Git-Commits oder Handover-Historie.
