# Buddy-Aktionsvideos

## Was

Das Aktionsfenster oben links im Buddy-Cockpit verwendet zwei eigens dafür erstellte Videos:

1. Im Zustand `idle` läuft das Idle-Video als automatische Endlosschleife.
2. Beim Eintritt in `working` läuft einmalig ein Idle→Working-Übergangsvideo. Nach dessen Ende erscheint die bestehende Working-Animation des HydraMascot.

Im Zustand `speaking` bleibt die bestehende Speaking-Animation des HydraMascot erhalten.

## Warum

Die Videos wurden gezielt für das kleine Aktionsfenster erstellt. Das Idle-Video macht den wartenden Buddy lebendiger; das Übergangsvideo visualisiert den Beginn einer Arbeitsphase, darf deshalb aber nicht geloopt werden.

## Assets

### Idle-Schleife

- Quelle: `atelier/videos/b5345673144544e5ac0db48d3ee8448d.mp4`
- Repo-Ziel: `frontend/public/buddy/buddy-idle.mp4`
- Wiedergabe: `autoPlay`, `loop`, `muted`, `playsInline`

### Idle→Working-Übergang

- Quelle: `atelier/videos/4cba382d05cd46629095eb6e8ef7b8c4.mp4`
- Repo-Ziel: `frontend/public/buddy/buddy-idle-to-working.mp4`
- Wiedergabe: `autoPlay`, `muted`, `playsInline`, ausdrücklich **ohne** `loop`
- Nach `onEnded` wird das bestehende Working-Maskottchen sichtbar.

## Gemeinsame Regeln

- Die AAC-Tonspuren werden beim Übernehmen physisch entfernt; im Repo liegen nur H.264-Videostreams.
- `muted` bleibt zusätzlich gesetzt, damit Browser-Autoplay zuverlässig erlaubt ist.
- Die 16:9-Videos füllen das bestehende Aktionsfenster mit `object-cover`.
- Die Größe und Position des Fensters sowie die Reaction-Statuszeile bleiben unverändert.
- Ein erneuter Eintritt in den Working-Zustand startet den Übergang erneut.

## Akzeptanzkriterien

- Im Idle-Zustand läuft ausschließlich das Idle-Video endlos.
- Das Idle→Working-Video läuft bei einem Working-Eintritt genau einmal und enthält kein Loop-Verhalten.
- Nach Ende des Übergangsvideos wird die bestehende Working-Animation angezeigt.
- Speaking zeigt weiterhin die bestehende Speaking-Animation.
- Beide Repo-Videos sind vollständig lautlos und enthalten keinen Audiostream.
- Frontend-Typecheck, ESLint, Offline-Guard und Produktionsbuild sind grün.
