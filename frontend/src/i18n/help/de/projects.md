# Projekte

## Was ist das?

Ein Projekt ist die mittlere Ebene der **3-Ebenen-Architektur**: Master beauftragt Projekte, Projekte nutzen Spezialisten. Es ist eine Kombination aus:

- **Workspace** — eigener Dateisystem-Ordner (`data/workspaces/projects/<id>/`)
- **Project-Agent** — automatisch erstellt, an den Workspace gebunden, kann nicht außerhalb operieren
- **Members** — User die Zugriff haben

Ein Projekt = ein abgegrenzter Arbeits-Kontext. Beispiel: dein Vorhaben "Webseite XY" hat ein Projekt mit eigenem Git-Repo, eigenem Memory, eigenen Sessions.

## Was kann ich hier tun?

- **Neues Projekt anlegen** — Name, Beschreibung, Members, Modell für den Project-Agent, optional `git init`
- **Members hinzufügen / entfernen** über Chips im Detail
- **Status setzen** — aktiv / archiviert
- **Löschen** — räumt alles weg (Project-Agent + Workspace + alle Sessions)
- **Sessions** in diesem Projekt: über Chat-Tab "Projekte"

## Wichtige Begriffe

- **Project-Agent** — Agent vom Typ `project`, an dieses Projekt gekoppelt
- **Workspace** — der zugewiesene Dateisystem-Bereich, isolated von anderen Projekten
- **Member** — User mit Zugriff. Admin sieht alle Projekte.

## Schritt-für-Schritt

### Projekt für ein Code-Vorhaben anlegen

1. **+ Neu** klicken
2. Name: z.B. *Website-Relaunch*, Beschreibung: kurze Erklärung
3. Members: dich selbst (oder mehrere User)
4. Modell: `claude-sonnet-4-6`
5. **Workspace mit `git init`** ankreuzen — direkt versionierbar
6. **Anlegen** — Project-Agent wird erstellt, Workspace existiert leer

### Code in den Workspace laden

Workspace liegt unter `data/workspaces/projects/<project_id>/`. Drei Wege:

```bash
# Variante 1: Symlink existierender Code
ln -s /pfad/zu/deinem/code/* /home/till/.hh2-dev/data/workspaces/projects/<id>/

# Variante 2: Kopieren
cp -r /pfad/zu/deinem/code/* /home/till/.hh2-dev/data/workspaces/projects/<id>/

# Variante 3: Git-Clone
cd /home/till/.hh2-dev/data/workspaces/projects/<id>/
git clone <repo-url> .
```

### Projekt-Chat starten

1. **Chat** in der Sidebar öffnen
2. **+ Neu** → Modus **Im Projekt**
3. Projekt wählen — Project-Agent ist automatisch dabei
4. Tools wie `file_read`, `shell_exec` operieren jetzt im Projekt-Workspace

### Member entfernen

1. Projekt öffnen
2. Im Members-Bereich auf das `×` neben dem User-Chip klicken
3. Bestätigen

## Typische Fehler

- **`User existiert nicht`** beim Hinzufügen eines Members — User muss erst angelegt werden (System-Page → Users, oder per Backend).
- **Project-Agent verwaist** wenn der Project-Agent direkt gelöscht wird statt das Projekt — Projekt zeigt den Agent dann nicht. Lösung: Projekt löschen oder Agent über Agents-Page neu anlegen mit `project_id`.

## Tipps

- **Pro großes Vorhaben ein eigenes Projekt** — saubere Trennung, eigener Verlauf, eigenes Memory
- **Members reduzieren auf wer wirklich arbeitet** — Sessions sind sichtbar für alle Members
- **Optional `git init`** auch wenn du nicht remote pushen willst — lokale Versionierung hilft beim Zurückrollen wenn der Agent was kaputt macht
