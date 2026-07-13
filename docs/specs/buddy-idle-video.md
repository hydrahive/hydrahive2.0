# Buddy-Aktionsvideos

## Was

Das Aktionsfenster oben links im Buddy-Cockpit bildet einen vollständigen Arbeitszyklus mit eigens erstellten Videos ab:

1. `idle` — wartender Buddy als Endlosschleife
2. `starting` — einmaliger Übergang von Idle zu Working
3. `working` — arbeitender Buddy als Endlosschleife
4. `success` oder `error` — einmalige Ergebnisreaktion
5. `stopping` — einmaliger Übergang von Working zu Idle
6. zurück zu `idle`

Die bestehende Speaking-Animation des HydraMascot hat während einer Sprachausgabe Vorrang. Danach wird der unterbrochene Videoablauf fortgesetzt.

## Warum

Die Videos wurden gezielt für das kleine Aktionsfenster erstellt. Loops stellen Dauerzustände dar; Übergänge und Ergebnisreaktionen laufen genau einmal. Dadurch ist jederzeit sichtbar, ob Buddy wartet, arbeitet, erfolgreich fertig wurde oder einen Fehler hatte.

## Assets und Wiedergabe

| Phase | Workspace-Quelle | Repo-Ziel | Loop |
|---|---|---|---|
| `idle` | `atelier/videos/b5345673144544e5ac0db48d3ee8448d.mp4` | `frontend/public/buddy/buddy-idle.mp4` | ja |
| `starting` | `atelier/videos/4cba382d05cd46629095eb6e8ef7b8c4.mp4` | `frontend/public/buddy/buddy-idle-to-working.mp4` | nein |
| `working` | `atelier/videos/03b80fbb77ec4f59a9e599f2a5e60c43.mp4` | `frontend/public/buddy/buddy-working.mp4` | ja |
| `error` | `atelier/videos/01fd74364e344bf3bcc944b518a10347.mp4` | `frontend/public/buddy/buddy-error.mp4` | nein |
| `success` | `atelier/videos/3a2d1bfc97fa4c9baa88cdb8e92e5b5c.mp4` | `frontend/public/buddy/buddy-success.mp4` | nein |
| `stopping` | `atelier/videos/1a7db6d6135540068b7c5ce7d37794af.mp4` | `frontend/public/buddy/buddy-working-to-idle.mp4` | nein |

## Zustandslogik

- Ein neuer Chat-Lauf wechselt von `idle` zu `starting` und danach in den `working`-Loop.
- Endet der Lauf erfolgreich, folgt `success`, danach `stopping`, danach `idle`.
- Endet der Lauf mit Fehler, folgt `error`, danach `stopping`, danach `idle`.
- Endet ein sehr kurzer Lauf bereits während `starting`, wird das Ergebnis vorgemerkt; das Startvideo wird nicht abgeschnitten.
- Wird ein Fehler durch einen anschließenden Reload aus dem Chat-State entfernt, beendet die Video-State-Machine dennoch zuerst die bereits gestartete Fehlerreaktion.
- Ein abgebrochener Lauf ohne Ergebnis wechselt über `stopping` zurück zu `idle`.
- `lastTurnTokens` wird beim Start jedes neuen Laufs zurückgesetzt. Ein gesetzter Wert nach Laufende dient als Erfolgssignal und wird bei passiven Reloads beibehalten.

## Gemeinsame Regeln

- Alle AAC-Tonspuren werden beim Übernehmen physisch entfernt; im Repo liegen nur H.264-Videostreams.
- `muted` bleibt zusätzlich gesetzt, damit Browser-Autoplay zuverlässig erlaubt ist.
- Alle Videos verwenden `autoPlay`, `playsInline`, `preload="auto"` und `object-cover`.
- Ausschließlich `idle` und `working` besitzen Loop-Verhalten.
- Die Größe und Position des Fensters sowie die Reaction-Statuszeile bleiben unverändert.

## Akzeptanzkriterien

- Der Erfolgsablauf lautet: Idle-Loop → Idle→Working → Working-Loop → Gelungen → Working→Idle → Idle-Loop.
- Der Fehlerablauf lautet: Idle-Loop → Idle→Working → Working-Loop → Error → Working→Idle → Idle-Loop.
- Gelungen, Error und beide Übergänge laufen jeweils genau einmal.
- Kurze Läufe schneiden den Idle→Working-Übergang nicht ab.
- Speaking zeigt weiterhin die bestehende Speaking-Animation.
- Alle sechs Repo-Videos sind vollständig lautlos und enthalten keinen Audiostream.
- Frontend-Typecheck, ESLint, Offline-Guard und Produktionsbuild sind grün.
