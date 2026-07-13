# Buddy-Idle-Video

## Was

Das Aktionsfenster oben links im Buddy-Cockpit zeigt im Zustand `idle` ein eigens dafür erstelltes Hydra-Video als automatische Endlosschleife. In den Zuständen `working` und `speaking` bleibt die bestehende zustandsabhängige HydraMascot-Anzeige erhalten.

## Warum

Das Video wurde als ruhige Idle-Animation für genau dieses Fenster erstellt und soll den inaktiven Buddy lebendiger darstellen, ohne seine Arbeits- und Sprachzustände zu verdecken.

## Wie

- Quelle: `atelier/videos/b5345673144544e5ac0db48d3ee8448d.mp4`
- Repo-Ziel: `frontend/public/buddy/buddy-idle.mp4`
- Die AAC-Tonspur wird beim Übernehmen physisch entfernt; im Repo liegt nur der H.264-Videostream.
- Das Frontend verwendet zusätzlich `muted`, damit Browser-Autoplay zuverlässig erlaubt ist.
- Wiedergabeattribute: `autoPlay`, `loop`, `muted`, `playsInline`, `preload="auto"`.
- Das 16:9-Video füllt das bestehende Aktionsfenster mit `object-cover`.
- Die Reaction-Statuszeile unter dem Fenster bleibt bestehen.

## Akzeptanzkriterien

- Im Idle-Zustand läuft das Video automatisch und endlos.
- Das Video ist vollständig lautlos und enthält keinen Audiostream.
- Beim Arbeiten oder Sprechen wird weiterhin das bisherige zustandsabhängige Maskottchen angezeigt.
- Die bestehende Größe und Position des Aktionsfensters bleibt unverändert.
- Frontend-Typecheck, ESLint und Produktionsbuild sind grün.
