# Game Studio — Modulspezifikation V0.1

**Stand:** 2026-11-05

**Status:** Fachlich freigegeben; noch nicht implementiert. Ausführende Godot-Jobs bleiben an den Linux-MicroVM-Nachweis und die separate Core-Vorarbeit gebunden; Unreal bleibt in V0.1 `inventory_only`.

**Zielprodukt:** installierbares HydraHive-Modul `game-studio` plus Workstation-Game-Runner und kuratiertes Agenten-/Skill-Paket

**HydraHive-Basis:** `origin/main` bei `8e1be23a`

**Upstream-Inspiration:** [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios), geprüft bei `05ad7c8`, MIT-Lizenz

**Verwandte Spezifikationen:** `workstation-client.md`, `compute-cluster-v1.md`, `project-member-roles.md`, `ui-standard.md`

---

## 1. Entscheidung

### 1.1 Freigabebeschluss

Folgende Produkt- und Sicherheitsentscheidungen sind fachlich freigegeben:

- Game Studio bleibt ein Projekt-, Workflow- und Evidenz-Cockpit; Godot und Unreal bleiben lokale Editoren.
- Die drei getrennten Einstiege „Neues Spiel“, „Bestehendes Projekt übernehmen“ und „Archiv untersuchen“ gehören zu V0.1.
- Der geführte Fünf-Schritte-Weg, die Werkbank und der Grundsatz „Evidenz statt Behauptung“ gehören zu V0.1.
- Es gibt keine freie Remote-Shell, keine Host-Ausführung und keinen Fallback bei fehlender Isolation.
- `inventory_only` und `sandboxed` bleiben getrennte Trust Modes; eine Hochstufung erfolgt nie automatisch.
- Workstations werden über opake Handles gebunden; absolute lokale Pfade bleiben lokal.
- Die Core-Erweiterungen für projektgebundene Compute-Jobs und sichere Artefaktuploads werden als separate Vorarbeit umgesetzt.
- Der Linux-MicroVM-Nachweis für Godot ist eine verbindliche Voraussetzung für ausführende Godot-Jobs.
- **Gestufter Engine-Scope:** V0.1 unterstützt Godot vollständig bis Build, Test, Beobachtung und Export. Unreal bleibt in V0.1 auf statische Erkennung, Inventarisierung, Planung und sichtbare Capability-/Sicherheitsbegründungen beschränkt. Ausführende Unreal-Jobs werden erst in einer Folgeversion nach einem nachgewiesenen Windows-VM-Sandbox-Runner freigegeben.
- Der zweiphasige, hash- und quotageprüfte Artefaktvertrag ist verbindlich.

Game Studio wird als **hybrides HydraHive-Modul** gebaut:

1. Das **HydraHive-Modul** ist Projektübersicht, Workflow- und gemeinsame Arbeitsoberfläche.
2. Der **bestehende Core-Projektagent der projektbesitzenden HydraHive-Instanz** bearbeitet Quellcode und Projektdokumente im kanonischen Git-Repository.
3. Ein **deterministischer Game-Runner auf der Workstation** führt ausschließlich typisierte, signierte und allowlistete Engine-Aufträge aus.
4. **Godot und Unreal bleiben lokale Engines.** Das Modul ersetzt weder Editor noch SDK.
5. Ein HydraHive-Projekt repräsentiert genau **ein Spielprojekt mit einer primären Engine**.
6. V0.1 orchestriert keine Agenten über Instanzgrenzen. Ein Workstation-lokaler Projektagent ist nur dann zuständig, wenn die Workstation-HydraHive-Instanz das Projekt selbst besitzt; Zusammenarbeit an servereigenen Projekten über einen Workstation-Agenten bleibt eine spätere Ausbaustufe des Workstation-Clients.

Das Modul darf keine freie Remote-Shell anbieten. Fremde oder archivierte Projekte werden vor jeder Engine-Ausführung als potenziell ausführbarer, nicht vertrauenswürdiger Code behandelt.

## 2. Problem

Angefangene Spiele liegen häufig als unvollständige Godot-/Unreal-Projekte, lose Archive oder mehrere widersprüchliche Versuche vor. Bestehende KI-Workflows sind entweder zu allgemein, nur terminalbasiert oder für einen einzelnen Nutzer gedacht. Es fehlt eine gemeinsame Lösung, die:

- neue Spieleprojekte strukturiert beginnt;
- bestehende Projekte übernimmt, ohne vorhandene Arbeit zu überschreiben;
- Archive sicher inventarisiert;
- Godot und Unreal getrennt und versionsbewusst behandelt;
- mehrere Nutzer mit Projektrollen unterstützt;
- Agentenarbeit, Engine-Jobs, Berichte und Artefakte an einem Ort sichtbar macht;
- einen kleinen spielbaren Vertical Slice priorisiert statt unkontrolliert Umfang aufzubauen.

## 3. Ziele von V0.1

V0.1 liefert:

- eine installierbare Game-Studio-Moduloberfläche;
- Projektanlage, Übernahme und Archiv-Inventarisierung als drei getrennte Einstiege;
- einen geführten Minimalworkflow vom Game Brief bis zum geprüften Vertical Slice;
- Godot- und Unreal-Profil mit statischer Erkennung und Capability-Anzeige;
- projektbezogene Workstation-Bindung über einen opaken Workspace-Handle;
- signierte Jobs für Inventarisierung, Validierung, Build, Test, Beobachtung und Export;
- sichtbare Jobphasen, Logs, Fehler, Screenshots und Artefakte;
- ein kuratiertes Agententeam und neun schlanke Game-Workflows;
- Mehrbenutzerrechte über die bestehenden Core-Projektrollen;
- nachvollziehbare Herkunft aller übernommenen Upstream-Bestandteile.

## 4. Nicht-Ziele von V0.1

V0.1 enthält ausdrücklich nicht:

- keinen eingebauten Level-, Blueprint-, Material-, Animation- oder Code-Editor;
- keine Fernsteuerung des Unreal- oder Godot-Editors;
- keine freie Shell und keine frei formulierbaren Engine-Kommandos;
- keine automatische Migration zwischen Godot-Hauptversionen oder Unreal-Versionen;
- keine Portierung eines Spiels zwischen Godot und Unreal;
- keine automatische Engine-, SDK- oder Plugin-Installation;
- keinen vollständigen MMORPG-Produktionsprozess;
- keine Steam-, Epic-, Konsolen- oder App-Store-Veröffentlichung;
- keine automatische Nutzung oder Lizenzfreigabe gefundener Assets;
- keine gleichzeitige Schreibarbeit mehrerer Agenten im selben Git-Worktree;
- keine vollständige Übernahme aller Upstream-Agenten, Skills, Hooks und Vorlagen.

## 5. Leitprinzipien

1. **Minimalmodus zuerst:** Ein Game Brief, kleine Tasks und echte Spielbeobachtung sind wichtiger als Dokumentmenge.
2. **Bestehendes bleibt bestehen:** Adoption ergänzt Lücken; sie regeneriert oder überschreibt keine vorhandenen Artefakte.
3. **Ein Projekt, eine Engine:** Godot- und Unreal-Versuche derselben Idee werden als getrennte, optional verknüpfte HydraHive-Projekte geführt.
4. **Beobachten statt behaupten:** Ein sichtbares Feature gilt erst nach ausgeführtem Spiel und gesicherter Evidenz als abgenommen.
5. **Engine-Versionen sind Teil des Projekts:** Keine stillen Upgrades.
6. **Keine Host-Ausführung:** Fremder Spielcode läuft nur in einer geeigneten Sandbox.
7. **Core-Rechte bleiben maßgeblich:** Das Modul führt keine zweite Membership-Quelle ein.
8. **Repos über Git, Metadaten über API:** Kein Schreiben in SQLite über Netzlaufwerke und kein gemeinsamer Git-Worktree über SMB.
9. **Agent und Runner sind getrennt:** Der Agent plant und ändert; der Runner führt eng typisierte Engine-Operationen aus.
10. **Fehlende Isolation ist ein Fehlerzustand:** Es gibt keinen Rückfall auf unsichere Host-Ausführung.

## 6. Nutzer und Rollen

### 6.1 Zielgruppen

- Einsteiger, die aus einer Idee einen kleinen spielbaren Prototyp bauen möchten.
- Entwickler, die ein bestehendes Godot-/Unreal-Projekt strukturieren wollen.
- Besitzer alter Archive, die zuerst nur wissen möchten, was darin steckt.
- Kleine Teams mit Designer-, Entwickler- und Testerrollen.
- Administratoren, die Workstations und sichere Engine-Ausführung bereitstellen.

### 6.2 Autoritative Rechte

Es gelten ausschließlich die Core-Projektrollen:

| Core-Rolle | Bedeutung im Game Studio |
|---|---|
| `read` | Projekt, Dokumente, Jobs, Berichte und Artefakte ansehen/herunterladen |
| `write` | Dokumente ändern, Agentenläufe und Engine-Jobs starten, Playtests erfassen |
| `admin` | Workstation binden, Engineprofil ändern, Mitglieder/Agentenpaket verwalten, Projekt archivieren |
| System-Admin | globale Modulfreigabe, Runner enrollment/revoke, Sicherheits- und Quotenverwaltung |

Fachbezeichnungen wie Producer, Designer oder QA sind Zuständigkeiten und dürfen die Core-Autorisierung nicht ersetzen.

## 7. Komponentenarchitektur

```text
HydraHive Master
├── Modul-Frontend: Game Studio
├── Modul-Backend: Projekte, Dokumente, Runs, Artefakte, Audit
├── Core-Projekte: Membership, Projekt-Agent, Workspace, Tasks
├── Compute-Control-Plane: signierte Jobs, Lease, Cancel, Events
└── Artefaktannahme: projekt- und jobgebunden
          │
          │ ausgehender mTLS-Kanal, signierte allowlistete Jobs
          ▼
Game Workstation
├── lokaler Git-Clone eines unveränderlich adressierten Quellstands
├── Game-Runner `game-runtime/v1` in MicroVM/VM
├── Godot und/oder Unreal mit administrativ bestätigten Capabilities
├── lokaler Artefaktbereich
└── optional eigene HydraHive-Instanz für eigene lokale Projekte
```

### 7.1 Modul-Frontend

Das Frontend zeigt Projektzustand, Workflow, Jobs und Ergebnisse. Es sendet keine Shellbefehle und keine Hostpfade.

### 7.2 Modul-Backend

Das Backend:

- prüft Projektrollen;
- hält strukturierte Metadaten und Revisionen;
- erzeugt ausschließlich typisierte Jobs;
- verknüpft Core-Tasks und Core-Agenten;
- nimmt Berichte und erlaubte Artefakte an;
- protokolliert fachliche Änderungen und Engine-Aufträge.

### 7.3 Projektagent

V0.1 verwendet den bestehenden Core-Projektagenten der HydraHive-Instanz, die das Projekt besitzt. Der Projektagent:

- arbeitet in einem Projekt-Worktree des kanonischen Git-Repositorys;
- verwendet das kuratierte Game-Studio-Skillpaket;
- liefert Änderungen über Branch/Commit/PR statt über einen geteilten Netz-Worktree;
- besitzt standardmäßig keine freie Host-Shell;
- erhält Dateiwerkzeuge, die technisch auf den zugewiesenen Worktree begrenzt sind, sowie allowlistete Git-Aktionen;
- startet Build, Import, Test, Paketmanager-Hooks und Projektcode ausschließlich über signierte Game-Runner-Jobs.

Repository-, Archiv-, Dokument-, Log- und Assetinhalte gelten gegenüber dem Agenten als nicht vertrauenswürdige Daten und niemals als Autorisierungs- oder Tool-Instruktionen. Sie können weder Toolrechte erweitern noch Nutzerbestätigungen ersetzen. Der Standard-Agentenpack erhält keinen Zugriff auf Home-Verzeichnisse, SSH-, Git-, Cloud- oder HydraHive-Credentials, Docker/Incus, andere Workspaces oder frei adressierbares Netzwerk. Eine separat vom Projektadmin gewährte Core-Shellfreigabe liegt außerhalb des sicheren Game-Studio-V0.1-Vertrags und darf nicht zum Bestehen seiner Abnahme verwendet werden.

Die spätere Zusammenarbeit eines Workstation-Agenten an einem servereigenen Projekt benötigt einen eigenen `workstation-agent/v1`-Vertrag für Delegation, Benutzeridentität, kurzlebige Git-Berechtigung, Branch-Locking und Provenienz. Dieser Vertrag ist nicht Teil von V0.1.

### 7.4 Game-Runner

Der Game-Runner ist kein LLM-Agent und nimmt keine freie Shell entgegen. V0.1 registriert genau den Compute-Provider **`game-runtime/v1`**. Der Runner:

- validiert signierte Jobangebote und lehnt unbekannte Felder ab;
- prüft Node-, Projekt-, Workspace-, Generation-, Provider- und Quellstand-Bindung;
- löst einen opaken Workspace-Handle lokal auf;
- führt eine fest kodierte Operation mit validierten Parametern aus;
- startet jeden Job in einer frischen Linux-MicroVM oder Windows-VM mit eigenem Kernel;
- sammelt strukturierte Ergebnisse und Artefakte;
- beendet den vollständigen Prozessbaum bei Cancel oder Timeout.

Shared-Kernel-Container und direkte Hostprozesse sind für Game-Studio-Jobs keine zulässige Sicherheitsgrenze.

## 8. Installations- und Abhängigkeitsmodell

### 8.1 Modulmanifest

Vorgesehene Werte:

```json
{
  "id": "game-studio",
  "name": "Game Studio",
  "version": "0.1.0",
  "description": "Godot- und Unreal-Spiele gemeinsam planen, übernehmen, prüfen und als Vertical Slice entwickeln.",
  "icon": "Gamepad2",
  "nav_group": "working",
  "permissions": [],
  "capabilities": [
    {
      "id": "module.game-studio",
      "label": "Game Studio nutzen",
      "default": "admin_only"
    },
    {
      "id": "game-studio.create_project",
      "label": "Game-Studio-Projekte anlegen",
      "default": "admin_only"
    }
  ],
  "has_service": false,
  "default_agent_tools": true,
  "min_core_version": "2.0.0"
}
```

`has_service: false` bedeutet hier **kein externer Sidecar-Dienst**. Das Backend wird über den bestehenden In-Process-Modulvertrag `backend/__init__.py::register(ctx)` geladen; darüber registriert es Router, additive Migrationen, Agentenwerkzeuge und den periodischen Orphan-Job. Der Core bleibt Eigentümer von Authentifizierung, Projekten, Compute-Jobs und Node-Verbindungen. Die Modulversion darf erst veröffentlicht werden, wenn die angegebene `min_core_version` die projektgebundenen Game-Jobs und Artifact Uploads vollständig enthält; für die Designfassung bleibt der im Repository übliche Mindestwert `2.0.0` gesetzt.

### 8.2 Verhalten ohne Workstation

Ohne kompatible Workstation bleibt das Modul im **Planungsmodus** nutzbar:

- Game Brief und Designarbeit funktionieren;
- Tasks, Agenten und Dokumente funktionieren;
- Engine-Aktionen sind sichtbar, aber deaktiviert;
- die UI nennt die konkret fehlende Capability;
- es gibt keinen automatischen Fallback auf den HydraHive-Host.

## 9. Projektmodell

### 9.1 Grundregel

Ein Core-HydraHive-Projekt entspricht genau einem Game-Studio-Spiel. Das Modul speichert nur einen fachlichen Marker und Zusatzmetadaten. Projektmitgliedschaften, Projektagenten und Tasks bleiben Core-Verantwortung.

### 9.2 Projektarten

| `source_mode` | Bedeutung |
|---|---|
| `new` | neues Spiel, zunächst ohne bestehendes Engine-Projekt |
| `adopt` | bestehendes Engine-Projekt übernehmen |
| `archive` | Archiv oder Projektbestand zunächst nur inventarisieren |

### 9.3 Engineprofile

| `engine` | Bedeutung |
|---|---|
| `unknown` | noch nicht erkannt oder absichtlich nicht festgelegt |
| `godot` | genau ein Godot-Hauptprojekt |
| `unreal` | genau ein Unreal-Hauptprojekt |

Eine Änderung von `godot` zu `unreal` oder umgekehrt ist keine normale Einstellung. Sie erzeugt ein neues HydraHive-Projekt oder einen expliziten, späteren Migrationsvorgang.

### 9.4 Projektphasen

```text
unclassified → concept → prototype → preproduction → production
             → release → maintenance → archived
```

Das Modul speichert getrennt:

- `configured_stage`: bewusst gesetzte Projektphase;
- `observed_stage`: aus Artefakten erkannte Phase;
- `stage_confidence`: `pass|concerns|not_assessed|fail`.

Eine Abweichung wird sichtbar gemeldet und niemals still überschrieben.

## 10. Dateistruktur und Quellen der Wahrheit

### 10.1 Kanonische Game-Studio-Dokumente

Die gemeinsame, auch ohne Workstation verfügbare Quelle für Briefs, Planung und Berichte liegt im Core-Projektworkspace:

```text
game-studio/
├── design/
│   ├── game-brief.md
│   ├── quick-specs/
│   └── gdd/                    # erst bei größerem Bedarf
├── architecture/
├── production/
│   ├── milestones/
│   └── playtests/
├── reports/                    # Inventar-, Validierungs- und Migrationsberichte
├── evidence/                   # Screenshots, kleine Videos und Metadaten
├── artifacts/                  # ausdrücklich hochgeladene Artefakte
├── trash/                      # wiederherstellbare Modulobjekte
└── cache/                      # jederzeit neu aufbaubar, nicht kanonisch
```

Die Dokument-API liest und schreibt diese Dateien atomar. SQLite enthält nur relativen Pfad, Revision und Hash, nie eine zweite Textkopie. Der Projektagent der besitzenden HydraHive-Instanz sieht diesen Bereich direkt im Projektworkspace. Ein späterer Claude-Code-Adapter darf ausdrücklich markierte Exportkopien in ein Spiele-Repository schreiben; diese Kopien sind nicht kanonisch und benötigen einen eigenen Einweg-Exportvertrag.

### 10.2 Kanonischer Quellstand des Spiels

Enginecode und Engine-Assets liegen in genau einem als primär registrierten Git-Repository. Neue Projekte erhalten ein privates Repository; bestehende Projekte registrieren ihr vorhandenes Remote. Workstations verwenden normale lokale Clones und synchronisieren ausschließlich über Git, niemals über einen gemeinsamen SMB-Worktree.

Jeder Build-, Test-, Beobachtungs- und Exportjob referenziert einen vollständigen `source_commit_sha` oder – nur für noch nicht versionierte Archive – einen unveränderlichen `source_snapshot_digest`. Dirty Worktrees sind keine gültige Jobquelle. Submodule- und Git-LFS-Zustand werden in den Snapshotnachweis aufgenommen.

### 10.3 In SQLite

SQLite enthält strukturierte Metadaten, Revisionen, Run-Verknüpfungen, Artefaktindizes und Auditereignisse. Große Binärdateien werden nicht als BLOB gespeichert.

## 11. Datenmodell

Alle Tabellen entstehen additiv und tragen das Präfix `module_game_studio_`.

### 11.1 `module_game_studio_projects`

```text
project_id TEXT PRIMARY KEY
source_mode TEXT NOT NULL CHECK (source_mode IN ('new','adopt','archive'))
engine TEXT NOT NULL CHECK (engine IN ('unknown','godot','unreal'))
engine_version TEXT
language TEXT
configured_stage TEXT NOT NULL
observed_stage TEXT
stage_confidence TEXT
rigor TEXT NOT NULL DEFAULT 'minimal'
agent_pack_version TEXT
active_game_resource_id TEXT
settings_json TEXT NOT NULL DEFAULT '{}'
revision INTEGER NOT NULL DEFAULT 1
created_by TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
orphaned_at TEXT
```

`project_id` verweist logisch auf ein Core-Projekt. Da Core-Projekte dateibasiert sind, existiert kein SQL-Foreign-Key. Ein periodischer Job markiert verwaiste Datensätze; er löscht sie nicht sofort.

### 11.2 Core-Ressource `compute_game_workspaces`

Die sicherheitskritische Workstation-Bindung gehört dem Core, nicht dem Modul. V0.1 führt für den fest registrierten Provider `game-runtime/v1` additiv ein:

```text
resource_id TEXT PRIMARY KEY
provider TEXT NOT NULL CHECK (provider = 'game-runtime/v1')
project_id TEXT NOT NULL
node_id TEXT NOT NULL REFERENCES compute_nodes(node_id)
workspace_handle TEXT NOT NULL
engine TEXT NOT NULL CHECK (engine IN ('unknown','godot','unreal'))
engine_version TEXT
engine_project_relpath TEXT NOT NULL DEFAULT '.'
trust_mode TEXT NOT NULL CHECK (trust_mode IN ('inventory_only','sandboxed'))
status TEXT NOT NULL CHECK (status IN ('pending','ready','offline','incompatible','revoked','error'))
isolation_profile_id TEXT NOT NULL
runner_version TEXT NOT NULL
policy_digest TEXT NOT NULL
generation INTEGER NOT NULL DEFAULT 1
created_by TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
last_seen_at TEXT
revoked_at TEXT
```

Core verantwortet Projektberechtigung, Node-Zuordnung, Workspace-Handle, Generation, Widerruf und Providerkompatibilität. Das Modul speichert nur `active_game_resource_id` als fachliche Referenz. V0.1 erlaubt genau eine aktive, nicht widerrufene Game-Ressource pro Projekt; ein Rebind widerruft die alte Ressource, erhöht die Generation und invalidiert alle noch nicht gestarteten Jobs sowie aktiven Leases der alten Generation.

`workspace_handle` ist eine lokal erzeugte, opake ID. `engine_project_relpath` wird als normalisierter relativer Pfad ohne leere Segmente, `.` oder `..` validiert. Core nimmt keine absoluten Nutzerpfade entgegen und sendet keine Hostpfade in Jobs.

### 11.3 `module_game_studio_documents`

```text
document_id TEXT PRIMARY KEY
project_id TEXT NOT NULL REFERENCES module_game_studio_projects(project_id) ON DELETE CASCADE
kind TEXT NOT NULL
relative_path TEXT NOT NULL
sha256 TEXT NOT NULL
revision INTEGER NOT NULL DEFAULT 1
created_by TEXT NOT NULL
updated_by TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
UNIQUE(project_id, relative_path)
```

Der eigentliche Text liegt in der Datei. Änderungen verlangen `base_revision` und `base_sha256`; Konflikte liefern HTTP 409 mit aktuellem Stand. Vor dem atomaren Ersetzen wird die bisherige Fassung unter `game-studio/.versions/<document_id>/<revision>` unveränderlich abgelegt.

#### 11.3.1 `module_game_studio_document_versions`

```text
version_id TEXT PRIMARY KEY
document_id TEXT NOT NULL REFERENCES module_game_studio_documents(document_id) ON DELETE CASCADE
project_id TEXT NOT NULL
revision INTEGER NOT NULL
relative_version_path TEXT NOT NULL
sha256 TEXT NOT NULL
size_bytes INTEGER NOT NULL
created_by TEXT NOT NULL
created_at TEXT NOT NULL
UNIQUE(document_id, revision)
```

Wiederherstellen erzeugt eine neue Revision; es überschreibt oder löscht keine Historie.

### 11.4 `module_game_studio_runs`

```text
run_id TEXT PRIMARY KEY
project_id TEXT NOT NULL REFERENCES module_game_studio_projects(project_id) ON DELETE CASCADE
game_resource_id TEXT
compute_job_id TEXT
workflow TEXT NOT NULL
operation TEXT NOT NULL
status TEXT NOT NULL
requested_by TEXT NOT NULL
input_revision INTEGER NOT NULL
summary_json TEXT NOT NULL DEFAULT '{}'
created_at TEXT NOT NULL
started_at TEXT
finished_at TEXT
```

Die Tabelle ist fachliche Verknüpfung und ersetzt nicht die Core-Compute-Jobtabelle.

### 11.5 `module_game_studio_artifacts`

```text
artifact_id TEXT PRIMARY KEY
project_id TEXT NOT NULL REFERENCES module_game_studio_projects(project_id) ON DELETE CASCADE
run_id TEXT REFERENCES module_game_studio_runs(run_id) ON DELETE SET NULL
kind TEXT NOT NULL CHECK (kind IN ('report','log','screenshot','video','build','export','manifest'))
logical_name TEXT NOT NULL
storage_class TEXT NOT NULL CHECK (storage_class IN ('server','workstation'))
relative_path TEXT
workstation_handle TEXT
media_type TEXT NOT NULL
size_bytes INTEGER NOT NULL
sha256 TEXT NOT NULL
retention TEXT NOT NULL CHECK (retention IN ('temporary','project','release'))
created_by TEXT NOT NULL
created_at TEXT NOT NULL
UNIQUE(project_id, artifact_id)
```

Serverseitige Pfade werden ausschließlich vom Backend erzeugt. Node-Ergebnisse dürfen keinen Zielpfad bestimmen.

### 11.6 `module_game_studio_events`

```text
event_id INTEGER PRIMARY KEY AUTOINCREMENT
project_id TEXT NOT NULL
object_kind TEXT NOT NULL
object_id TEXT
actor_id TEXT NOT NULL
actor_kind TEXT NOT NULL CHECK (actor_kind IN ('user','agent','workstation','system'))
event_type TEXT NOT NULL
data_json TEXT NOT NULL DEFAULT '{}'
created_at TEXT NOT NULL
INDEX(project_id, created_at)
```

Fachliche Änderungen sind append-only. Secrets, absolute Workstation-Pfade und Rohkommandos dürfen nie in Events stehen.

## 12. Frontend und Seitenaufbau

### 12.1 Routen

```text
/game-studio
/game-studio/:projectId
/game-studio/:projectId/guided
/game-studio/:projectId/workbench
/game-studio/:projectId/artifacts
/game-studio/:projectId/activity
/game-studio/:projectId/settings
```

### 12.2 Projektübersicht

Die Startseite zeigt:

- zugängliche Game-Studio-Projekte;
- Engine, Version, Phase und Workstation-Status;
- nächsten empfohlenen Schritt;
- laufende Jobs und letzte Artefakte;
- Aktionen „Neues Spiel“, „Bestehendes Projekt“ und „Archiv untersuchen“.

Nichtmitglieder sehen ein Projekt nicht. Die Filterung erfolgt serverseitig.

### 12.3 Projektkopf

Der Kopf zeigt jederzeit:

- Projektname;
- primäre Engine und Version;
- konfigurierte und beobachtete Phase bei Abweichung;
- Workstation-/Sandboxstatus;
- aktive Jobs;
- „Geführten Weg fortsetzen“.

### 12.4 Geführter Weg

V0.1 verwendet fünf Schritte:

1. **Idee und Zielgruppe** — Pitch, Genre, Plattform, gewünschtes Gefühl.
2. **Spielkern** — Core Loop, Sieg/Niederlage, zentrale Mechanik.
3. **Technik und Umfang** — Engineprofil, Vertical-Slice-Grenze, größte Risiken.
4. **Prototyp** — Tasks, Build/Test und beobachtbare Hypothese.
5. **Playtest und Entscheidung** — Evidenz, Befunde, `PROCEED|PIVOT|KILL|NOT_ASSESSED`.

„Weiter“ nennt fehlende Voraussetzungen konkret. Ein Schritt gilt nicht allein durch Dokumenterzeugung als abgeschlossen.

### 12.5 Werkbank

Semantische Tabs:

- **Design** — Brief und Quick Specs;
- **Produktion** — Milestones und Core-Tasks;
- **Engine** — Bindung, Capabilities, Build/Test/Export;
- **Playtest** — Berichte und Evidenz;
- **Team** — Projektagent und Spezialisten.

V0.1 enthält keinen eingebauten Code- oder Level-Editor.

### 12.6 Artefakte

Artefaktkarten zeigen:

- Typ, Name, Quelle und Erstellzeit;
- zugehörigen Run und Commit, soweit vorhanden;
- Größe und SHA-256;
- Vorschau für Bilder/Videos ausschließlich aus passiven Derivaten gemäß Abschnitt 17.2; Originalartefakte, SVG/HTML/XML und unbekannte Medientypen besitzen keine Inline-Vorschau;
- Speicherort `HydraHive` oder `Workstation`;
- Download nur bei serverseitigem Artefakt;
- „Von Workstation übertragen“ nur bei ausreichender Rolle, Quota und sicherem Uploadpfad.

### 12.7 Aktivität

Die Aktivität zeigt:

- laufende und vergangene Runs;
- beobachtete Phase statt erfundener Prozentwerte;
- Start, Fortschritt, Ergebnis und strukturierte Fehlercodes;
- Abbrechen, sofern der Job abbrechbar und der Nutzer berechtigt ist;
- gefilterte Logs und Artefakte je Run.

### 12.8 Responsive und Accessibility

Verbindlich:

- kein horizontaler Überlauf bei 320 px;
- Paneele werden unter `xl` zu Tabs;
- echte `tablist`-/`tab`-/`tabpanel`-Semantik und Pfeiltastatursteuerung;
- sichtbarer Fokus und WCAG-AA-Kontrast;
- Labels für alle Inputs und Iconbuttons;
- `aria-live="polite"` für Abschlussstatus, `role="alert"` für Fehler;
- Fokusfalle und Fokus-Rückgabe in Dialogen;
- `prefers-reduced-motion` bei Spinnern und Fortschrittsanimationen;
- i18n-Schlüssel für mindestens Deutsch und Englisch, keine fest eingebauten UI-Texte.

## 13. Nutzerflüsse

### 13.1 Neues Spiel

1. Nutzer mit Modul- und Erstellberechtigung wählt „Neues Spiel“.
2. Das Modul erstellt ein Core-Projekt und den Game-Studio-Marker atomar; Teilfehler werden kompensiert.
3. Minimalworkflow und Agentenpaket werden eingerichtet.
4. Der Nutzer erstellt den Game Brief.
5. Optional bindet ein Projekt-Admin eine kompatible Workstation.
6. Der Core-Projektagent der projektbesitzenden HydraHive-Instanz erzeugt einen Branch/Worktree und einen ersten kleinen Prototyp.
7. Build/Test/Beobachtung laufen über den Game-Runner.
8. Das Modul zeigt Evidenz und eine Playtestentscheidung.

### 13.2 Bestehendes Projekt übernehmen

1. Ein Projekt-Admin wählt eine lokal registrierte Workstation und einen dort bestätigten Workspace-Handle.
2. `game.project.inventory` sammelt statische Fakten, ohne Engine oder Projektskripte auszuführen.
3. Der Bericht erkennt Engine, Version, Sprachen, Plugins, Projektmarker und vorhandene Dokumente.
4. Der Nutzer prüft die Zuordnung und bestätigt Engineprofil und Trust Mode.
5. Der Agentenworkflow `game-adopt` erstellt einen nummerierten Ergänzungsplan.
6. Bestehende Artefakte werden nie regeneriert; nur Lücken werden vorgeschlagen.

### 13.3 Archiv untersuchen

1. Ein Archiv wird ausschließlich auf der Workstation ausgewählt und lokal registriert.
2. Der Workspace beginnt in `inventory_only`.
3. Die statische Inventarisierung listet Containerinhalt unter harten Limits, ohne Inhalte auf dem HydraHive-Host zu entpacken.
4. Symlinks, Traversalpfade, Sonderdateien, verschachtelte Archive und Bombenindikatoren werden gemeldet.
5. Der Server erhält standardmäßig nur Zusammenfassung, Hashes, erkannte Marker und Dateizählungen.
6. Vollständige Dateinamen werden nur nach ausdrücklicher Freigabe übertragen.
7. Der Bericht empfiehlt `revive`, `reuse_parts`, `keep_archived` oder `not_assessed`; er migriert nichts.
8. Erst eine Nutzerentscheidung erzeugt eine Arbeitskopie und optional ein neues Git-Repository.

### 13.4 Playtest

1. Ein Build oder Export wird in der Sandbox ausgeführt.
2. `game.project.run_observe` startet ausschließlich ein geprüftes Ergebnis, nicht das Editorprojekt.
3. Der Runner erfasst Startstatus, definierte Smoke-Checks und mindestens einen Screenshot.
4. Ein Mensch ergänzt Spielgefühl, Verständlichkeit und beobachtete Probleme.
5. Der Bericht trennt Bugs, Designprobleme, Balance und Polishing.
6. Ein sichtbares Feature wird ohne Evidenz als `NOT_ASSESSED` behandelt.

## 14. Engine-Profile

### 14.1 Gemeinsamer Adaptervertrag

Jeder Adapter implementiert:

```text
detect(workspace) -> EngineDetection
inventory(workspace, privacy) -> InventoryReport
validate(workspace, profile) -> ValidationReport
build(workspace, target, profile) -> ArtifactManifest
test(workspace, suite, profile) -> TestReport
run_observe(artifact, scenario, limits) -> ObservationReport
export(workspace, preset, profile) -> ArtifactManifest
```

Adapter erhalten keine freien Argumentlisten. Ziele, Profile, Suites, Szenarien und Presets stammen aus zuvor inventarisierten und serverseitig validierten IDs.

### 14.2 Godot-Profil

Statische Erkennung:

- `project.godot`;
- `config_version` und Featuretags;
- GDScript, C#, GDExtension und Shader;
- Addons und Editor-Plugins;
- vorhandene Exportpresets und Tests.

Typisierte Ausführung:

- Headless-Import/Validierung;
- projektdefinierte, zuvor inventarisierte Testsuite;
- Build/Export über existierendes Preset;
- Start eines exportierten Builds für Beobachtung.

Sicherheitsregeln:

- `@tool`, Editor-Plugins, C#-Build und native GDExtensions gelten als ausführbarer Code;
- keine Engine-Ausführung im `inventory_only`-Modus;
- keine automatische Godot-3-/Godot-4-Konvertierung;
- Importcache ist joblokal und nicht kanonisch.

### 14.3 Unreal-Profil

Statische Erkennung:

- `.uproject` und `EngineAssociation`;
- Source-Module, Targets, Plugins und Descriptoren;
- C++-, Blueprint-, GAS-, Replication- und UMG/CommonUI-Indikatoren;
- Build-, Test-, Cook- und Packaging-Konfigurationen;
- Marketplace-/Drittanbieter-Pluginhinweise.

V0.1-Ausführung:

- Unreal bleibt in V0.1 im Trust Mode `inventory_only`.
- Build, Test, Cook/Package und Beobachtung sind sichtbar, aber mit einer Erklärung zur fehlenden administrativ bestätigten Windows-VM deaktiviert.
- Diese Aktionen werden erst in einer Folgeversion nach einem nachgewiesenen Windows-VM-Sandbox-Runner freigegeben.

Sicherheitsregeln:

- `.uasset` und `.umap` werden nicht als Text bearbeitet;
- `Build.cs`, `Target.cs`, Plugins, Python und AutomationTool gelten als ausführbarer Code;
- V0.1 verändert keine Blueprints automatisiert;
- kein automatisches Upgrade der Unreal-Version;
- Windows-Unreal-Jobs benötigen eine isolierte Windows-VM oder einen gleichwertig nachgewiesenen Sandbox-Runner; ein normaler Desktopprozess reicht nicht.

## 15. Workstation-Capabilities

Ein kompatibler Runner meldet mindestens:

```json
{
  "provider": "game-runtime/v1",
  "game_runtime_protocol": 1,
  "runner_version": "1.0.0",
  "isolation_profile_id": "linux-microvm-v1|windows-vm-v1",
  "policy_digest": "sha256:...",
  "sandbox": {
    "kind": "linux-microvm|windows-vm",
    "network_default": "off",
    "ephemeral": true,
    "resource_limits": true,
    "process_tree_cancel": true,
    "host_device_passthrough": false
  },
  "engines": [
    {
      "id": "godot|unreal",
      "versions": ["..."],
      "operations": ["inventory", "validate", "build", "test", "run_observe", "export"],
      "observation": {
        "boot_smoke": true,
        "virtual_display": true,
        "software_or_virtual_gpu": true,
        "host_gpu_passthrough": false
      }
    }
  ],
  "artifact_upload": {
    "supported": true,
    "max_bytes": 2147483648
  }
}
```

Diese **NodeCapabilities** enthalten nur Sandboxarten, Engineinstallationen, Plattformen, Runner-/Policy-Versionen und unterstützte Operationen. Ziele, Testsuites, Exportpresets, Plugins und Szenarien sind projektspezifisch und stehen ausschließlich in einem `InventorySnapshot`, gebunden an `game_resource_id`, Generation und `source_commit_sha|source_snapshot_digest`. Jeder ausführende Job referenziert dessen `inventory_snapshot_id`; veraltete oder zum Quellstand unpassende Snapshots werden abgelehnt.

Eine vom Node selbst gemeldete Capability schaltet keine Ausführung frei. Der Master dispatcht nur an ein beim Enrollment administrativ freigegebenes `isolation_profile_id` mit allowlistetem Runnerstand und bekanntem `policy_digest`. Abweichungen führen zu `job_rejected`.

Absolute Rootpfade, Benutzernamen, Secrets und lokale Tool-Kommandos werden nicht als öffentliche Capability übertragen.

## 16. Jobmodell und Protokoll

### 16.1 Erforderliche Core-Erweiterung

Die bestehende Compute-Queue unterstützt nur Container/VM/Node und Eigentümersicht nach `created_by`. Vor Game Studio müssen additiv ergänzt werden:

- projektgebundene Jobs mit `project_id`;
- `resource_kind='game_workspace'`;
- projektrollenbasierte Sicht und Cancel-Berechtigung;
- typisierte Game-Operationen im Master und Runner;
- strukturierte Phasenereignisse zusätzlich zum numerischen Fortschritt;
- jobgebundene Artefakt-Upload-Sitzungen;
- den fest registrierten Provider `game-runtime/v1` mit streng versionierten Payload-Schemas und Unknown-Field-Rejection;
- die Core-Ressource `compute_game_workspaces`, über die Projekt, Node, Workspace-Handle, Generation, Runner und Isolation vor Signierung geprüft werden.

Core verantwortet Ressource, Projektberechtigung, Node-Zuordnung, Lease, Signatur, Cancel und Jobzustand. Das Modul verantwortet Workflow, Engineprofil und die fachliche Run-Projektion. Der Runner verantwortet ausschließlich Schema-/Signaturprüfung, isolierte Ausführung und Ergebnisbildung.

### 16.2 Erlaubte V0.1-Operationen

```text
game.workspace.inspect
game.project.inventory
game.project.validate
game.project.build
game.project.test
game.project.run_observe
game.project.export
```

Cancel bleibt eine Control-Plane-Operation und wird nicht als frei wählbare Runner-Operation modelliert.

### 16.3 Gemeinsamer Job-Envelope

Zusätzlich zu den bestehenden signierten Feldern enthält der kanonische Auftrag:

```json
{
  "provider": "game-runtime/v1",
  "project_id": "<core-project-id>",
  "game_resource_id": "<core-game-resource-id>",
  "workspace_handle": "<opaque-local-id>",
  "workspace_generation": 3,
  "source_commit_sha": "<40-or-64-hex-commit>",
  "source_snapshot_digest": null,
  "inventory_snapshot_id": "<snapshot-id>",
  "operation": "game.project.validate",
  "engine": "godot",
  "engine_version": "4.5.1",
  "toolchain_digest": "sha256:...",
  "profile_id": "debug-desktop",
  "input_revision": 12,
  "limits": {
    "timeout_seconds": 900,
    "cpu_cores": 4,
    "memory_mb": 8192,
    "disk_mb": 16384,
    "pids": 256,
    "network": "off"
  }
}
```

Es gibt keine Felder für Shell, Hostpfad, beliebige Argumente, Umgebungsvariablen, Mounts oder Secrets. Genau eines von `source_commit_sha` und `source_snapshot_digest` ist gesetzt. Der Runner prüft Repositoryidentität, Clean-Status, Submodule/LFS, Quellhash, Toolchain und Inventory Snapshot vor dem Start; Abweichungen führen zu `source_revision_conflict`.

Der Quellstand wird als read-only Lower Layer in eine joblokale Copy-on-write-Überlagerung oder vollständige temporäre Kopie gestaged. Godot und Unreal dürfen dort Importcache, `Intermediate`, `Saved` und generierte Dateien schreiben. Scratch, Cache und Output sind getrennt und größenbegrenzt; nur allowlistete Outputs werden gesammelt. Das Overlay wird nie in den lokalen Clone zurückgeschrieben.

### 16.4 Operation-Payloads

- `inspect`: `privacy = summary|full_names`, keine Engine-Ausführung.
- `inventory`: `scan_profile_id`, `include_hashes`, harte Datei-/Byte-/Zeitlimits; erzeugt einen quellengebundenen `InventorySnapshot`.
- `validate`: `validation_profile_id` aus demselben Inventory Snapshot.
- `build`: `target_id`, `configuration_id`; beide aus demselben Inventory Snapshot.
- `test`: `suite_id` aus demselben Inventory Snapshot; keine freie Testkommandozeile.
- `run_observe`: `artifact_id`, `scenario_id = boot_smoke`, `evidence = screenshot|video`. Das Artefakt muss aus einem erfolgreichen Build-/Export-Run desselben Projekts, derselben Game-Ressource und Generation stammen. Der Auftrag bindet erwarteten Hash und unveränderlichen lokalen Handle; der Runner prüft Projekt, Ressource, Generation, Handle und Hash unmittelbar vor Start und meldet sonst `artifact_provenance_mismatch`.
- `export`: `preset_id` aus demselben Inventory Snapshot, `destination = workstation|server_upload`.

V0.1 kennt nur das fest definierte Beobachtungsszenario `boot_smoke`: verpacktes Ergebnis in einer VM mit virtuellem Display und Software- oder virtueller GPU starten, auf Prozess-/Fenster-/Frame-Bereitschaft warten, einen Screenshot erfassen und den Prozess kontrolliert beenden. Es gibt keine freien Eingabeskripte und kein Host-GPU-Passthrough.

### 16.5 Zustände und Ereignisse

Run-Zustände:

```text
created → queued → leased → running → succeeded
                               ├────→ failed
                               ├────→ cancelled
                               └────→ expired
```

Phasenereignisse verwenden stabile Codes, zum Beispiel:

```text
preparing_sandbox
staging_input
validating_project
building
running_tests
launching_artifact
capturing_evidence
collecting_artifacts
uploading
cleaning_up
```

Die UI zeigt nur dann Prozentwerte, wenn der Runner einen echten Nenner kennt. Andernfalls zeigt sie Phase und vergangene Dauer.

### 16.6 Idempotenz und Wiederaufnahme

V0.1 garantiert **At-least-once Delivery mit Deduplizierung**, nicht magische Exactly-once-Ausführung:

- `job_id` identifiziert die logische Operation; `attempt_id` einen Ausführungsversuch.
- Jeder Job besitzt einen eindeutigen Idempotency-Key über Projekt, Game-Ressource, Operation, Quellstand, Inputrevision und Nutzeraktion.
- Der Runner persistiert angenommene, laufende und abgeschlossene `job_id`s für die konfigurierte Retentionsfrist.
- Ein Duplikat eines laufenden Jobs wird nicht erneut gestartet; abgeschlossene Ergebnisse kommen aus persistentem Core-/Runner-Storage.
- Ein abgelaufener Build wird bei unbekanntem Ausgang nicht automatisch erneut gestartet.
- Ein bewusstes neues Build erhält eine neue `job_id`.
- Workspace-Generation, Quellstand und Inputrevision verhindern Ausführung gegen veraltete Ressourcen.
- Cancel setzt zuerst den Jobstatus, beendet dann den vollständigen Runner-Prozessbaum und markiert unvollständige Artefakte als verworfen.

## 17. Artefaktvertrag

### 17.1 Manifest

Jeder erfolgreiche Run liefert ein kleines, strukturiertes Manifest:

```json
{
  "artifacts": [
    {
      "artifact_ref": "<runner-local-uuid>",
      "kind": "report",
      "logical_name": "validation-report.json",
      "media_type": "application/json",
      "size_bytes": 12345,
      "sha256": "...",
      "retention": "project",
      "transfer": "upload"
    }
  ],
  "summary": {
    "result": "pass|concerns|not_assessed|fail",
    "warnings": 2,
    "errors": 0
  }
}
```

### 17.2 Upload

Der Upload ist ein zweiphasiges Protokoll:

1. Der Runner sendet während des laufenden Jobs ein `artifact_offer` mit `artifact_ref`, Art, normalisiertem logischen Namen, deklarierter Größe, SHA-256 und Retention.
2. Der Server prüft Projekt, Job, Quota, Art, Größe und Anzahl, erzeugt die serverseitige `artifact_id` und stellt ein kurzlebiges, einmaliges, daran gebundenes Uploadrecht aus.
3. Der Runner streamt die Datei. Der Node darf den Zielpfad nicht bestimmen.
4. Der Server prüft tatsächliche Größe, Hash und Inhaltsklasse und veröffentlicht atomar.
5. Erst nachdem alle als erforderlich markierten Artefakte angenommen wurden, darf der Job `succeeded` melden. Teiluploads fehlgeschlagener oder abgebrochener Jobs bleiben temporär und werden automatisch entfernt.

`logical_name` und `media_type` gelten als nicht vertrauenswürdig. Der Server bestimmt den effektiven Medientyp über feste Allowlist und Magic Bytes; die Node-Angabe bleibt Metadatum. HTML, SVG, XML, JavaScript, unbekannte Formate und ausführbare Inhalte werden nie inline vom authentifizierten HydraHive-Origin ausgeliefert, sondern nur mit `Content-Disposition: attachment`, `Content-Type: application/octet-stream` und `X-Content-Type-Options: nosniff`. Vorschauen verwenden serverseitig erzeugte passive Derivate oder einen getrennten cookielosen Origin mit restriktiver Sandbox-CSP. Logs, JSON, Markdown und Reports werden nur als escapeter Text oder über strukturierte Renderer dargestellt. Downloadnamen werden serverseitig normalisiert und dürfen keine Header- oder Pfadsyntax enthalten.

Archive werden serverseitig als opaque Datei gespeichert und nicht automatisch entpackt. Symlinks, Geräte, FIFOs und Sparse-/Bombenindikatoren werden abgewiesen.

### 17.3 Größen und Aufbewahrung

V0.1-Defaults:

| Klasse | Standardgrenze | Verhalten |
|---|---:|---|
| Bericht/Log | 10 MiB | serverseitig speichern |
| Screenshot | 25 MiB | serverseitig speichern |
| Video | 250 MiB | explizite Übertragung |
| Build/Export | 2 GiB | explizite Übertragung und Projektquota |

Größere Builds bleiben auf der Workstation und werden über einen opaken Handle referenziert. Quoten sind serverseitig konfigurierbar.

## 18. Agententeam

V0.1 installiert höchstens fünf Rollen:

| Rolle | Verantwortung | Darf nicht |
|---|---|---|
| Game Producer | Umfang, Meilensteine, nächste Schritte, Abhängigkeiten | Gameplay allein festlegen |
| Game Designer | Core Loop, Regeln, Balance, Spielerlebnis | Enginecode ohne Auftrag ändern |
| Gameplay Programmer | Umsetzung, Architektur, Tests | Designlücken still erraten |
| Engine Specialist | genau Godot oder Unreal, Builds und Enginekonventionen | andere Engine als Primärquelle behandeln |
| Game QA | Testfälle, echte Ausführung, Evidenz, Playtestberichte | bestandene Tests mit gutem Spielgefühl gleichsetzen |

Pro Projekt wird genau der passende Engine Specialist aktiviert. Weitere Upstream-Rollen wie Art, Audio, Narrative, Live Ops oder Economy sind spätere optionale Pakete.

## 19. Kuratiertes Skillpaket

V0.1 bietet neun nutzerorientierte Workflows:

| HydraHive-Skill | Zweck | Upstream-Inspiration |
|---|---|---|
| `game-start` | Einstieg, Minimalmodus, Projektart wählen | `start`, `setup-engine` |
| `game-adopt` | Brownfield-Audit und nummerierter Ergänzungsplan | `adopt`, `project-stage-detect`, `reverse-document` |
| `game-archive-audit` | sichere statische Archiv-Inventarisierung | eigener HydraHive-Workflow |
| `game-brief` | einseitiger Pitch, Zielgruppe, Gefühl, Kernmechanik | `brainstorm`, `quick-design` |
| `game-prototype` | eine falsifizierbare Hypothese, harter Zeit-/Umfangsrahmen | `prototype` |
| `game-vertical-slice` | kleiner vollständiger Spielausschnitt | `vertical-slice` |
| `game-scope-check` | ursprünglichen und aktuellen Umfang vergleichen | `scope-check` |
| `game-playtest` | Ausführung, Beobachtung, Befunde und Evidenz | `playtest-report`, `smoke-check` |
| `game-release-check` | reproduzierbarer Build, Tests, Lizenz- und Paketprüfung | `qa-plan`, `release-checklist` |

### 19.1 Kollaborationsregel

Jeder Workflow:

1. liest den bestehenden Kontext;
2. trennt Beobachtung von Annahme;
3. zeigt höchstens vier Optionen mit Trade-offs;
4. lässt kreative und irreversible Entscheidungen beim Nutzer;
5. schreibt nur nach bestätigtem Zielpfad oder innerhalb eines vorab genehmigten orchestrierten Runs;
6. überschreibt keine vorhandenen Design- oder Quelldateien still;
7. liefert konkrete Akzeptanzkriterien und Evidenz.

### 19.2 Upstream-Lizenzierung

Das Modul enthält `UPSTREAM.md` mit:

- Repository-URL und geprüftem Commit;
- MIT-Copyright-Hinweis von Donchitos;
- Liste kopierter oder substanziell adaptierter Dateien/Ideen;
- HydraHive-spezifischen Änderungen;
- Hinweis, dass Upstream keine fertigen Spiele mitliefert.

Die vollständige MIT-Lizenz bleibt bei jeder substantiellen Übernahme erhalten. Upstream-Hooks werden nicht pauschal importiert.

## 20. API V0.1

Alle Routen liegen unter `/api/modules/game-studio`.

Alle unter einem Projekt adressierten Kindobjekte werden atomar über den zusammengesetzten Schlüssel aus `project_id` und Objekt-ID geladen und verändert. Dies gilt für Ressourcen/Bindings, Dokumente, Runs, Events und Artefakte. Die Kenntnis einer Objekt-ID ist kein Berechtigungsnachweis. Gehört das Kindobjekt nicht zum Projekt aus der URL, antwortet die API mit 404; ein globaler Lookup mit erst nachträglichem Projektvergleich ist unzulässig. Dasselbe Scoping gilt für Agententools, interne Service-Aufrufe und alle in Job-Payloads referenzierten IDs.

### 20.1 Projekte

```text
GET    /projects
POST   /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
POST   /projects/{project_id}/archive
```

- Liste und Lesen benötigen Projektrolle `read`.
- Anlegen benötigt `game-studio.create_project`.
- normale Metadatenänderung benötigt `write` plus `base_revision`.
- Enginewechsel, Binding und Archivierung benötigen `admin`.

### 20.2 Bindings und Capabilities

```text
GET    /projects/{project_id}/bindings
POST   /projects/{project_id}/bindings
PATCH  /projects/{project_id}/bindings/{binding_id}
DELETE /projects/{project_id}/bindings/{binding_id}
GET    /projects/{project_id}/capabilities
```

Diese Modulrouten projizieren die Core-Ressource `compute_game_workspaces`; sie führen keine zweite Binding-Tabelle. Binding-Änderungen benötigen Projektrolle `admin`. `workspace_handle` muss zuvor lokal auf der Workstation bestätigt und für genau diesen Projektprincipal freigegeben worden sein.

### 20.3 Dokumente

```text
GET  /projects/{project_id}/documents
GET  /projects/{project_id}/documents/{document_id}
PUT  /projects/{project_id}/documents/{document_id}
GET  /projects/{project_id}/documents/{document_id}/versions
POST /projects/{project_id}/documents/{document_id}/restore
```

Schreiben benötigt `write`, `base_revision` und `base_sha256`. Konflikte liefern 409, nicht Last-Write-Wins.

### 20.4 Runs und Jobs

```text
GET  /projects/{project_id}/runs
POST /projects/{project_id}/runs
GET  /projects/{project_id}/runs/{run_id}
POST /projects/{project_id}/runs/{run_id}/cancel
GET  /projects/{project_id}/runs/{run_id}/events
```

Erlaubte Workflow-/Operationskombinationen werden serverseitig validiert. Der anfragende Nutzer wird aus der Authentifizierung genommen, nie aus dem Requestbody.

### 20.5 Artefakte und Audit

```text
GET    /projects/{project_id}/artifacts
GET    /projects/{project_id}/artifacts/{artifact_id}
GET    /projects/{project_id}/artifacts/{artifact_id}/download
DELETE /projects/{project_id}/artifacts/{artifact_id}
GET    /projects/{project_id}/events
```

Lesen benötigt `read`, Löschen `write`; Release-Artefakte benötigen `admin` zum Löschen.

## 21. Sicherheit und Threat Model

### 21.1 Zu schützende Werte

- Quellcode, unveröffentlichte Spielideen und Assets;
- Projektmitgliedschaften und personenbezogene Daten;
- Git-, LLM-, Signier-, Plattform- und HydraHive-Secrets;
- HydraHive-Host, Workstation und andere Projekte;
- Build- und Release-Artefakte;
- Audit- und Herkunftsnachweise.

### 21.2 Angreifer und Risiken

V0.1 nimmt an, dass ein Projekt enthalten kann:

- absichtlich schädliche Buildskripte oder Plugins;
- kompromittierte Marketplace-/Drittanbieter-Plugins;
- Godot-`@tool`-Skripte oder native GDExtensions;
- Unreal-`Build.cs`, `Target.cs`, Python, Plugins oder AutomationTool-Code;
- Archive mit Traversal, Symlinks, Bomben oder Sonderdateien;
- indirekte Prompt-Injection in Projektdateien, Dokumentation, Logs, Asset-Metadaten oder Archivinhalten;
- manipulierte Logs, Artefaktnamen, Medientypen oder Browserinhalte;
- ein berechtigtes Projektmitglied, das auf ein fremdes Projekt zugreifen will.

### 21.3 Verbindliche Muss-Regeln

1. Kein Game-Job verwendet `execution.mode=host`.
2. Fehlende Isolation führt zu `job_rejected`; es gibt keinen Fallback.
3. Shared-Kernel-Container gelten nicht als ausreichende Grenze. Inventar, Validierung, Build, Test, Beobachtung und Export laufen ausschließlich in Linux-MicroVM oder Windows-VM mit eigenem Kernel.
4. Eine selbst gemeldete Node-Capability genügt nicht. Der Master dispatcht nur an administrativ freigegebene Isolation Profile mit allowlistetem Runnerstand und `policy_digest`.
5. Hostgeräte, Docker-/Incus-Sockets und Host-GPU-Passthrough sind in V0.1 unzulässig.
6. Die Sandbox erhält keine HydraHive-, Git-, LLM-, Cloud-, SSH- oder Vault-Secrets.
7. Das Environment wird aus einer Positivliste aufgebaut und nicht vom Host geerbt.
8. Netzwerk ist standardmäßig aus und nur in einer späteren, explizit allowlisteten Operation zulässig.
9. Kein Mount von HydraHive-Daten, Home, `/etc/hydrahive2`, SSH, Docker, Incus oder Credential-Stores.
10. Der Quellstand ist read-only Lower Layer; Copy-on-write-Overlay, Scratch, Cache und Output sind joblokal und begrenzt.
11. Die Sandbox sieht keine Geschwisterprojekte.
12. CPU, RAM, Disk, Inodes, PIDs, Dateianzahl, Laufzeit und Outputgröße sind hart begrenzt.
13. Cancel und Timeout beenden alle Kindprozesse.
14. Jobs sind signiert, node-, projekt-, ressourcen-, workspace-, generation-, provider-, quellen-, lease- und idempotenzgebunden.
15. Pfade werden nicht durch `resolve()` plus späteren zweiten Zugriff abgesichert, sondern über sichere Descriptor-/Handle-basierte Operationen oder einen isolierten Staging-Root.
16. Der bestehende globale Samba-Account ist kein Transport für Game-Studio-Projekte.
17. Jede REST-Route und jedes Agententool verwendet denselben Core-Projektguard.
18. Nichtmitglieder erhalten 404, zu schwache Mitglieder 403.
19. Kindobjekte und Jobreferenzen werden durchgängig auf dasselbe Projekt, dieselbe Game-Ressource und relevante Generation beschränkt.
20. Absolute Workstation-Pfade und Secrets erscheinen weder in UI, Events, Logs noch Agentenkontext.
21. Node-gelieferte Namen, Medientypen, Logs und Reports gelten als aktive Angreifereingaben und dürfen im authentifizierten HydraHive-Origin keine ausführbaren Inhalte erzeugen.
22. Artifact Uploads sind einmalig, kurzlebig, projekt-/jobgebunden und hashgeprüft.
23. Archive werden auf dem Server nicht automatisch entpackt.
24. Originalarchive werden nie direkt verändert.
25. Kritische Aktionen benötigen eine sichtbare Nutzerbestätigung und werden auditiert.

### 21.4 Trust Modes

- `inventory_only`: ausschließlich statische, limitierte Analyse; keine Engine, kein Build, keine Plugins.
- `sandboxed`: typisierte Engine-Jobs in nachgewiesener Sandbox.

Ein Projekt wird niemals automatisch von `inventory_only` auf `sandboxed` hochgestuft.

## 22. Datenschutz und Datenminimierung

- Inventarisierung überträgt standardmäßig nur Engineerkennung, Versionsmarker, Anzahl/Größe, Hashes und aggregierte Dateitypen.
- Vollständige Dateinamen und Pfade benötigen eine bewusste Freigabe.
- Lokale absolute Pfade bleiben auf der Workstation.
- Logs werden vor Übertragung auf Secrets und lokale Identifikatoren geprüft.
- Rohlogs besitzen eine kurze Standardaufbewahrung; strukturierte Berichte bleiben projektdauerhaft.
- Löschung eines serverseitigen Artefakts löscht keine lokale Originaldatei auf der Workstation.

## 23. Fehler- und Konfliktmodell

Stabile Fehlercodes, unter anderem:

```text
project_not_found
project_read_only
binding_not_ready
workspace_generation_conflict
source_revision_conflict
artifact_provenance_mismatch
job_rejected
engine_not_detected
engine_version_mismatch
sandbox_unavailable
operation_not_supported
inventory_limit_exceeded
archive_unsafe
job_transition_invalid
job_timeout
job_cancelled
artifact_too_large
artifact_hash_mismatch
quota_exceeded
version_conflict
```

Fehlerantworten enthalten keine absoluten Pfade, Kommandos oder Secrets. UI-Texte werden aus Codes und sicheren Parametern lokalisiert.

## 24. Beobachtbarkeit und Audit

Für jeden Run sichtbar:

- wer ihn gestartet hat;
- Projekt, Binding, Engineprofil und Inputrevision;
- aktuelle Phase und vergangene Dauer;
- Workstationstatus ohne sensible Hostdetails;
- strukturierte Warnungen und Fehler;
- erzeugte Artefakte und Prüfsummen;
- Cancel-/Retry-/Freigabeereignisse.

Metriken:

- Jobs nach Operation/Status/Engine;
- Laufzeit und Queuezeit;
- Abbruch-, Timeout- und Retryrate;
- übertragene Artefaktbytes;
- Sandbox- und Capability-Fehler;
- Workstation-Erreichbarkeit.

Es werden keine freien Shellkommandos geloggt, weil V0.1 keine annimmt.

## 25. Implementierungsetappen

### Etappe A — Core-Voraussetzungen

- Compute-Jobs projektbezogen machen.
- Core-Ressource `compute_game_workspaces` und Provider `game-runtime/v1` einführen.
- projektrollenbasierte Jobansicht und Cancel ergänzen.
- strukturierte Phasenereignisse ergänzen.
- sichere zweiphasige Artifact-Upload-Sitzungen bereitstellen.
- administrativ freigegebene Isolation Profile, Runnerstände und Policy-Digests abbilden.
- Workstation-Enrollment und sofortigen Widerruf für diesen Anwendungsfall verifizieren.

### Etappe B — Modulgrundlage

- Manifest, Migrationen und Registrierung.
- Core-Projektanlage mit kompensierendem Cleanup.
- Projekt-, Dokument-, Run-, Artefakt- und Eventstore sowie Projektion der Core-Game-Ressource.
- einheitlicher `read|write|admin`-Guard.
- Orphan-Markierung für gelöschte Core-Projekte.

### Etappe C — Oberfläche und Minimalworkflow

- Projektübersicht und drei Einstiege.
- Projektkopf, geführter Weg und Werkbank.
- Dokumentbearbeitung mit Revisionen.
- Job- und Artefaktansichten.
- Deutsch/Englisch, Tastatur- und Mobile-Abnahme.

### Etappe D — Workstation Game-Runner

- lokale Workspace-Registrierung mit opaken Handles.
- signierte Jobprüfung, Unknown-Field-Rejection und feste Operation-Allowlist.
- Linux-MicroVM-/Windows-VM-Lifecycle, Copy-on-write-Staging, Limits, Cancel und Cleanup.
- administrativ bestätigte Isolation Profile und Policy-Digests.
- statische Inventarisierung und sicherer Archivscanner.
- Godot-Adapter mit vollständiger Ausführung über den nachgewiesenen Linux-MicroVM-Runner.
- Unreal-Erkennung und Inventarisierung im `inventory_only`-Modus; ausführender Unreal-Adapter erst nach nachgewiesenem Windows-Sandbox-Gate in einer Folgeversion.

### Etappe E — Agenten- und Skillpaket

- fünf kuratierte Rollen.
- neun HydraHive-Workflows.
- Toolrechte nach Projektrolle und Engineprofil.
- `UPSTREAM.md`, MIT-Hinweise und Anpassungsnachweis.

### Etappe F — Abnahme mit realen Projekten

- frisches kleines Godot-Projekt;
- bestehendes Godot-Projekt;
- frisches kleines Unreal-Projekt im `inventory_only`-Modus;
- bestehendes Unreal-Projekt im `inventory_only`-Modus;
- sicher präpariertes Archiv mit Traversal/Symlink/Bombenindikatoren;
- später Tills offline archivierte Projekte als zusätzliche Brownfield-Fälle.

## 26. Vorgesehene Dateien

### Modulrepository

```text
game-studio/
├── manifest.json
├── UPSTREAM.md
├── SPEC.md                         # freigegebene Kopie dieser Spec
├── migrations/
│   ├── 001_game_studio.sql
│   └── 002_game_studio_indexes.sql
├── backend/
│   ├── __init__.py
│   ├── access.py
│   ├── models.py
│   ├── store.py
│   ├── files.py
│   ├── projects.py
│   ├── resources.py              # Projektion der Core-Game-Ressource
│   ├── runs.py
│   ├── artifacts.py
│   ├── routes.py
│   └── tools.py
├── frontend/
│   ├── index.tsx
│   ├── GameStudioPage.tsx
│   ├── api.ts
│   ├── types.ts
│   ├── project/
│   ├── guided/
│   ├── workbench/
│   ├── jobs/
│   └── artifacts/
├── skills/
└── tests/
```

Produktivdateien werden nach Verantwortung aufgeteilt und bleiben ungefähr unter 200 Zeilen.

### Core-/Node-Repository

Betroffen sind mindestens:

```text
core/src/hydrahive/compute/models.py
core/src/hydrahive/compute/jobs.py
core/src/hydrahive/compute/game_resources.py
core/src/hydrahive/compute/providers/game_runtime_v1.py
core/src/hydrahive/api/routes/compute_jobs.py
core/src/hydrahive/db/migrations/              # zwei neue additive, fortlaufend nummerierte Migrationen
node-agent/src/hydrahive_node/jobs.py
node-agent/src/hydrahive_node/game_runtime/
frontend/src/features/cockpit/admin/                 # nur Runner-/Node-Capabilities
```

Die konkrete Implementierung erhält vor Codebeginn einen separaten atomaren TDD-Plan.

## 27. Teststrategie

### 27.1 Modulbackend

- Projektrollenmatrix für jede Route und jedes Tool;
- Nichtmitglied 404, Read-only-Schreibversuch 403;
- Cross-Project-Mismatch für jede Ressourcen-, Dokument-, Run-, Event- und Artefakt-ID;
- optimistische Revisionen und 409-Konflikte;
- kompensierendes Cleanup bei fehlgeschlagener Projektanlage;
- Orphan-Markierung;
- relative Pfade, Hashes, atomare Writes und Quoten;
- keine Secrets oder absoluten Pfade in Antworten/Events.

### 27.2 Frontend

- drei Einstiegsflüsse;
- deaktivierte Engineaktionen ohne Capability mit Begründung;
- Jobs, Cancel und strukturierte Fehler;
- semantische Tabs, Dialogfokus und Tastatursteuerung;
- 320-px-Layout;
- deutsche und englische Texte;
- Artefaktvorschau und Speicherort;
- Stored-XSS-Gegenproben mit HTML/SVG/XML, gefälschtem Medientyp, manipuliertem Dateinamen sowie HTML in Logs und Reports.

### 27.3 Runner und Sicherheit

- ungültige Signatur, Node-, Projekt-, Ressourcen-, Generation-, Quellstand- und Lease-Bindung;
- unbekannte Operation und zusätzliche Payloadfelder fail-closed;
- kein Host-Fallback und keine Shared-Kernel-Container;
- selbst gemeldete oder veränderte Capabilities, unbekannte Policy-Digests und Hostgeräte schalten keine Game-Jobs frei;
- keine Host-Secrets im Environment oder Dateisystem;
- kein Netzwerk/DNS/lokale Dienste;
- kein Zugriff auf Geschwisterprojekte;
- Prompt-Injection in Repository-/Log-/Archivdateien kann weder Worktree noch Toolgrenzen verlassen und keine direkte Ausführung auslösen;
- Dirty Worktree, falscher Commit/Snapshot, Submodule/LFS-Abweichung und veralteter Inventory Snapshot werden abgelehnt;
- Copy-on-write-Overlay erlaubt Engine-Schreibpfade, ohne den lokalen Clone zu verändern;
- `run_observe` weist fremde, veraltete, ausgetauschte oder hashabweichende Artefakte ab;
- Cancel/Timeout beendet Kindprozesse;
- CPU/RAM/Disk/Inode/PID-Limits;
- Archive Traversal, Symlink, Sonderdatei, Verschachtelung und Bombe;
- Artifact-Hash/Größe/Quota/Einmaligkeit und zweiphasiger Upload;
- Crash und idempotente Wiederaufnahme.

### 27.4 Engine-Abnahme

Godot:

- statische Erkennung ohne Ausführung;
- `@tool`-/Plugin-/GDExtension-Projekt bleibt in Sandbox;
- Headless-Validierung, Test, Export und Screenshot;
- Versionskonflikt ohne automatische Konvertierung.

Unreal:

- statische Erkennung ohne Laden binärer Assets als Text;
- `Build.cs`-/Plugin-/Automation-Code bleibt in Windows-Sandbox;
- Target-Build, Test, Package und Screenshot eines verpackten Builds;
- Versionskonflikt ohne automatische Konvertierung.

## 28. V0.1-Akzeptanzkriterien

V0.1 ist abgenommen, wenn:

1. Ein berechtigter Nutzer ein Game-Studio-Projekt atomar anlegen kann.
2. `read`, `write` und `admin` serverseitig für alle Routen und Tools korrekt gelten.
3. Nichtmitglieder keine Projektmetadaten, Jobs oder Artefakte erkennen können.
4. Ein neues, bestehendes und archiviertes Projekt als getrennte Flüsse funktionieren.
5. Ohne Workstation der Planungsmodus vollständig nutzbar ist und Engineaktionen begründet deaktiviert sind.
6. Eine kompatible Workstation über einen opaken Handle gebunden werden kann, ohne Hostpfad im Server zu speichern.
7. Statische Inventarisierung keine Engine und keinen Projektcode ausführt.
8. Kein Game-Job direkt auf HydraHive-/Workstation-Host oder in einem Shared-Kernel-Container läuft.
9. Der Master nur administrativ bestätigte Isolation Profile, Runnerstände und Policy-Digests akzeptiert.
10. Jeder ausführende Job an einen unveränderlichen Commit/Snapshot und passenden Inventory Snapshot gebunden ist.
11. Godot-Validierung, Test, Export und Screenshot mit einem kleinen Referenzprojekt funktionieren.
12. Unreal-Projekte in V0.1 statisch inventarisiert werden; Build/Test/Package bleiben bis zum nachgewiesenen Windows-VM-Runner sichtbar begründet deaktiviert.
13. Jobs signiert, projektgebunden, dedupliziert, abbrechbar und nach Reconnect nachvollziehbar sind.
14. Fortschritt als echte Phase und nur bei vorhandenem Nenner als Prozent erscheint.
15. Berichte, Logs, Screenshots und Artefakte mit Hash, Größe, Herkunft und Run verknüpft sind.
16. Artifact Uploads kurzlebig, einmalig, quota- und hashgeprüft sind.
17. Archive mit Traversal, Symlinks oder Bombenindikatoren sicher abgewiesen werden.
18. Aktive HTML/SVG/XML-Inhalte, manipulierte Medientypen und Logs im HydraHive-Origin keine Stored XSS auslösen.
19. Ein sichtbares Feature ohne gestartetes Spiel und Evidenz `NOT_ASSESSED` erhält.
20. Agenten bestehende Artefakte bei Adoption nicht still regenerieren oder überschreiben.
21. Deutsch/Englisch, Tastaturbedienung, Fokus und 320-px-Layout geprüft sind.
22. `UPSTREAM.md` und MIT-Hinweise jede substantielle Übernahme nachvollziehbar machen.
23. Modul-, Core-, Node-, Security- und E2E-Testläufe grün sind.

## 29. Bewusst vertagte Erweiterungen

Nach V0.1 separat zu entscheiden:

- optionale Art-, Audio-, Narrative- und Technical-Art-Pakete;
- Blender- und DCC-Adapter;
- Steam-/itch.io-/Store-Releaseadapter;
- Telemetrie aus veröffentlichten Spielen;
- dedizierte Assetbibliothek mit Lizenzverwaltung;
- Multi-Node-Buildfarm und automatische Platzierung;
- Live-Multiplayer- und Latenztests;
- Godot-/Unreal-Migrationsassistenten;
- verknüpfte Projekte für Portierungen oder gemeinsame Franchises;
- öffentliche Template-/Marketplace-Veröffentlichung.

Diese Punkte sind nicht Teil der V0.1-Abnahme und dürfen deren Umfang nicht erweitern.

## 30. Freigabeempfehlung

Die Umsetzung wird in der Reihenfolge **Core-Sicherheit → Modulgrundlage → UI → Runner → Engineadapter → Agentenpaket → reale Brownfield-Abnahme** geplant. Der erste Produktivcode darf erst beginnen, wenn:

- diese Spezifikation fachlich freigegeben ist;
- die Sandboxstrategie für Godot/Linux konkret nachgewiesen ist;
- projektgebundene Compute-Jobs und Artifact Uploads als Core-Vertrag beschlossen und als separate Vorarbeit eingeplant sind;
- ein atomarer TDD-Implementierungsplan mit getrennten PRs vorliegt.

Unreal-Ausführung ist kein V0.1-Blocker: Sie bleibt bis zum separat nachgewiesenen Windows-VM-Sandbox-Runner im `inventory_only`-Modus.
