# Agent löschen: Daten ins Archiv statt weg

Task 58c680df. Stand 13.10.2026.

## Problem

Beim Löschen eines Agenten (`agents/config.delete()`) passieren heute zwei Dinge,
und beide sind falsch:

1. `agents/<id>/` wird **endgültig gelöscht** (`shutil.rmtree`). Darin liegen
   nicht nur Config und Prompt, sondern auch das Gedächtnis des Agenten:
   `crystals.jsonl`, `compressed/`, `observations/`, `soul/`. Auf Prod sind das
   zusammen 281 MB. Der Hinweis im Dialog sagt nur „Inkl. Memory + Workspace“.
2. Der **Arbeitsordner** `workspaces/specialists/<id>` bzw. `workspaces/master/<id>`
   bleibt liegen, ohne Agent, und wird von nichts mehr angezeigt.

Wege, auf denen gelöscht wird (alle über `agent_config.delete`):
- Admin → Agent → Löschen
- Nutzer löschen (alle Agenten des Nutzers)
- Projekt löschen (Projekt-Agent und Spezialisten des Projekts)
- Externe Instanz löschen

## Ist-Stand (nur lesend geprüft)

| | Prod | hydratest |
|---|---|---|
| `workspaces/specialists` ohne Agent | 28 (26 leer), 239 MB | 270 (269 leer) |
| `workspaces/master` ohne Agent | 2 (beide leer) | 73 (1 leer) |

Die eine große Waise auf Prod: `specialists/2efc2a67…/rom` (278 MB,
angelegt 18.06.). Darin liegt ein Projekt mit Server-Code, SQL und Doku
(`CLAUDE.md`, `HANDOVER.md`, `server/`, `sql/`, `docs/`).

Projekt-Arbeitsordner (`workspaces/projects/<id>`) gehören zum Projekt, nicht
zum Projekt-Agenten. Sie werden schon heute nur beim Löschen des Projekts
entfernt und sind **nicht Teil dieser Spec**.

## Lösung

### Archiv statt löschen

`agent_config.delete(agent_id)` verschiebt statt zu löschen:

```
<Archiv>/agents/<JJJJMMTT-HHMMSS>_<agent_id>/
    agent/        ← bisher agents/<id>/ (Config, Prompt, Gedächtnis, Soul)
    workspace/    ← Arbeitsordner (nur specialist/master, falls vorhanden)
    archiv.json   ← Name, Typ, Besitzer, Projekt, Zeitpunkt, Grund
```

- `archiv.json` enthält, was man zum Wiederfinden braucht:
  `{"agent_id", "name", "type", "owner", "project_id", "deleted_at", "reason"}`.
  `reason` ist z. B. `agent_deleted`, `user_deleted`, `project_deleted` oder
  `instance_deleted`.
- Leere Arbeitsordner werden nicht archiviert, sondern einfach entfernt.
- Erst wenn das Verschieben geklappt hat, ist der Agent weg. Scheitert das
  Archivieren (Platte voll, Ziel weg), bricht das Löschen ab und der Agent
  bleibt bestehen. Die API meldet einen klaren Fehler (`agent_archive_failed`).

### Wohin

Till hatte das NAS gewünscht (`//192.168.178.3/Hydrahive_backups`). Befund:
Das NAS ist auf Prod nur als **Projekt-Mount** eingehängt, unter
`workspaces/projects/<DEV-Projekt>/mounts/Hydrahive_backups`. Es wird beim
Backend-Start neu eingehängt und ist ein CIFS-Laufwerk ohne Unix-Rechte und
Symlinks (`nounix`). Agent-Ordner enthalten aber Symlinks (z. B.
`master/<id>/projects/…`).

Deshalb:
- **Standard:** lokaler Ordner `$HH_DATA_DIR/archive/` (gleiche Platte wie die
  Agent-Ordner). Verschieben ist dort ein `rename`, sofort fertig, Symlinks und
  Rechte bleiben.
- Einstellung `HH_AGENT_ARCHIVE_DIR` (Admin → Einstellungen), damit das Archiv
  auf einem anderen Pfad liegen kann. Liegt das Ziel auf einer anderen Platte,
  wird kopiert und erst nach erfolgreichem Kopieren gelöscht.
- Das NAS bekommt das Archiv über die normale Sicherung: `archive/` liegt unter
  `$HH_DATA_DIR` und kann in das System-Backup aufgenommen werden (siehe Entscheidung 2).

### Altlasten

Ein Skript `agent-waisen-archivieren.sh` (Probelauf ohne Argument, mit `--los`
ausführen) verschiebt die vorhandenen Waisen ins Archiv, mit `reason =
orphan_cleanup`. Leere Waisen werden nur entfernt. Auf Prod betrifft das
2 Ordner mit Inhalt und 28 leere.

### Oberfläche

Der Löschen-Dialog wird ehrlich: „Agent „X“ löschen? Gedächtnis und
Arbeitsordner werden ins Archiv verschoben und nicht gelöscht.“ Ebenso die
Dialoge für Nutzer und Projekt, soweit sie Agenten mitlöschen. Ein eigenes
Archiv-Fenster zum Ansehen oder Wiederherstellen gehört **nicht** in diese Etappe.

### Was nicht gemacht wird

- Kein automatisches Löschen alter Archive (keine Frist). Kann später kommen.
- Keine Wiederherstellung über die Oberfläche. Von Hand: Ordner zurückschieben.
- Sessions in der Datenbank bleiben wie heute erhalten.

## Etappen

1. Kern: `agents/_archive.py` (verschieben, `archiv.json`, Rückfall kopieren),
   `config.delete()` nutzt es, Grund durchreichen, Fehler `agent_archive_failed`,
   Einstellung `HH_AGENT_ARCHIVE_DIR`, Dialogtexte de/en.
2. Skript für die Altlasten, getestet auf hydratest (270 + 73 Waisen).
3. Prod: Till führt `update.sh` aus, dann das Skript (Probelauf, `--los`).

## Offene Entscheidungen (Till)

1. Archiv lokal unter `/var/lib/hydrahive2/archive/` als Standard
   (Empfehlung, s. o.) statt direkt auf das NAS?
2. Soll `archive/` ins System-Backup? Der Stand heute: Gesichert wird
   `agents/`, `workspaces/` usw.; ohne Aufnahme fiele das Archiv aus der
   Sicherung heraus. Empfehlung: ja.
3. Die große Waise `specialists/2efc2a67…/rom` (278 MB, Juni): archivieren wie
   die anderen (Empfehlung) oder vorher selbst ansehen?
