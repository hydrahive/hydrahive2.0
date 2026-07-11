# Spec: Globale Projekt-Handover-Datei

## Was

HydraHive pflegt pro Projektworkspace eine kanonische `.hydrahive/HANDOVER.md`. Jede erfolgreiche Compaction aktualisiert sie. Vor einem bewusst gestarteten neuen Chat wird eine aktuelle Übergabe erzeugt; die UI wartet darauf. Der erste Runner-Aufruf einer leeren Projekt-Session liest die Übergabe automatisch als Startkontext.

## Warum

Compaction und neue Chats verlieren sonst wichtigen Arbeitszustand. Das trifft kleine Codex-Kontextfenster besonders, ist aber ein modellunabhängiges Projektproblem.

## Wie

- Projektgebundener, secret-redacteter Markdown-Checkpoint mit Session-, Agent- und Zeit-Metadaten.
- Atomisches Schreiben über temporäre Datei plus `replace`.
- Nach erfolgreicher Compaction wird deren strukturierte Summary geschrieben.
- `POST /api/sessions/{id}/handover` fasst den aktuellen Verlauf zusammen und wartet auf Abschluss.
- Neue-Chat-Pfade rufen den Endpunkt vor der Session-Erstellung auf.
- Buddy-Clear erzeugt serverseitig die Übergabe und übernimmt die Projektbindung.
- Nur eine leere neue Session erhält `HANDOVER.md` als volatilen Startkontext; bestehende Chats werden nicht rückwirkend beeinflusst.
- Chats ohne Projektbindung schreiben/lesen keine Projekt-Handover-Datei.

## Akzeptanzkriterien

- Jede erfolgreiche projektgebundene Compaction aktualisiert `.hydrahive/HANDOVER.md`.
- „Neuer Chat“ wartet sichtbar auf die Übergabe.
- Eine neue Session desselben Projekts erhält die Übergabe beim ersten Run.
- Kein Handover außerhalb des zugehörigen Projektworkspaces.
- Secrets werden vor dem Schreiben redigiert.
- Schreibvorgang ist atomar; Fehler bei automatischem Compaction-Handover brechen die Compaction nicht.
- Tests decken Pfad, Redaction, leere Session, Compaction und API ab.

## Nicht enthalten

- Automatische Git-Commits, Pushes oder Merges.
- Handover für projektlose Chats.
- Ein historisches Handover-Archiv in Version 1.
