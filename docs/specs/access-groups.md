# Freigaben und Gruppen — wer darf was nutzen und teilen

Status: **Entwurf, Grundrichtung freigegeben (Till, 29.09.2026)**
Task: 5760df8d · Betroffene Befunde: 1333b295 (Home Assistant), 65762134 (Voice),
472a28a7 (VMs/Container), 4c14b933 (Föderation), b461b999 + Ticket #48 (Archiver),
1b69b1c9 (OpenTor), 9111b283 (Blueprint, nur Etappe 2)

## 1. Problem

HydraHive kennt heute nur zwei Rollen: `admin` und `user`. Jeder angemeldete Nutzer
darf fast jedes Modul und fast jede Core-Funktion vollständig nutzen. Die Handbuch-
Prüfung vom 29.09.2026 hat gezeigt, was das bedeutet:

| Funktion | Heute | Folge |
|---|---|---|
| Home Assistant | jeder Nutzer und jeder Buddy (`default_agent_tools`) | ganzes Haus schaltbar, ohne Rückfrage |
| Voice | jeder Nutzer | Verlauf der Box lesen, im Namen des Besitzers sprechen |
| VMs und Container | jeder Nutzer | unbegrenzt Maschinen, Bridged ins LAN |
| Föderation | jeder Agent | Admin-Workstation fernsteuern |
| Archiver | jeder Nutzer | root-rsync auf beliebige Pfade |

Gleichzeitig fehlt Teamarbeit: Eine VM, ein Blueprint-Board oder die Voicebox im
Wohnzimmer gehören genau einer Person. Mitbenutzen geht nicht.

## 2. Ziel

1. **Pro Nutzer freigeben:** Der Admin legt fest, wer eine Funktion nutzen darf.
2. **Gruppen:** Statt jede Person einzeln einzutragen, gibt der Admin einer Gruppe
   frei (z. B. „Familie“, „Dev-Team“).
3. **Teilen:** Wer eine Sache besitzt (VM, Board, Voicebox …), teilt sie selbst mit
   Nutzern oder Gruppen.
4. **Einheitlich:** Ein Mechanismus im Core für Core-Funktionen und alle Module.
   Kein Modul baut sich seine eigene Rechte-Logik.

## 3. Entscheidungen (Till, 29.09.2026)

- Freigaben **pro Nutzer**, zusätzlich **Gruppen** für Teamarbeit.
- **Gruppen und Funktions-Freigaben verwaltet nur der Admin.**
- **Eigene Sachen teilt der Besitzer selbst** mit Nutzern oder Gruppen.
- Gewählter Ansatz: Core-Gruppen + eine gemeinsame Freigabe-Tabelle (Option B),
  in Etappen. Verworfen: nur Einzelfreigaben (A, kein Teilen), Projekte als Gruppen
  (C, passt nicht für Haus-Funktionen und löst „darf das Modul?“ nicht).

## 4. Bestand (Stand 29.09.2026)

- **Nutzer:** `users.json` im Config-Verzeichnis, stabile `user_id`, Rolle
  `admin`/`user`. `require_principal` löst die aktuelle Rolle je Anfrage auf.
- **Gruppen im Core:** keine. Eigene Konzepte in Modulen:
  Tickets (`module_ticket_teams`, Rollen member/lead), Haushaltsbuch (Haushalte
  mit Mitgliedern und Einladungen), Projekte (`members` mit read/write/admin).
- **Manifest `permissions`:** wird in `modules/manifest.py` geparst, aber nirgends
  ausgewertet.
- **Gate-Punkte, die es schon gibt:**
  - Alle Modul-Router hängen in `api/main.py → mount_module_routers()` unter
    `/api/modules/<id>`. Dort kann eine Prüfung für alle Module auf einmal sitzen.
  - Die Werkzeuge eines Laufs entstehen in `runner/runner.py` über
    `scope_tools()` und `schemas_for()`. Ausgeführt wird in
    `runner/dispatcher.py → execute_tool()` mit `ctx.user_id`.
  - Das Menü filtert in `frontend/src/shared/nav-config.ts` nach `roles`.
- **Werkzeug → Modul:** Modul-Tools werden in `api/lifespan.py` aus
  `REGISTRY[m].ctx.tools` registriert. Die Modul-ID ist dort bekannt, wird aber
  nicht am Tool gespeichert.

## 5. Begriffe

- **Funktion (Capability):** etwas, das man freigeben kann. Schreibweise
  `bereich.name`, z. B. `module.homeassistant`, `homeassistant.control`,
  `core.vms`, `core.federation`.
- **Sache (Ressource):** ein einzelnes Objekt mit Besitzer, z. B. eine VM, ein
  Board, eine Voicebox, eine Workstation. Schreibweise `typ:id`.
- **Wer (Subjekt):** `user:<user_id>` oder `group:<group_id>`.
- **Stufe:** `use` (benutzen) oder `manage` (verwalten, inkl. weiter teilen bei Sachen).

## 6. Datenmodell (Core-DB, eine Migration)

```sql
CREATE TABLE access_groups (
    id          TEXT PRIMARY KEY,          -- uuid7
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_by  TEXT NOT NULL,             -- user_id
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE access_group_members (
    group_id   TEXT NOT NULL REFERENCES access_groups(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL,
    added_by   TEXT NOT NULL,
    added_at   TEXT NOT NULL,
    PRIMARY KEY (group_id, user_id)
);

-- Funktions-Freigaben (nur Admin schreibt)
CREATE TABLE access_capability_grants (
    capability   TEXT NOT NULL,            -- z. B. 'module.homeassistant'
    subject_type TEXT NOT NULL CHECK (subject_type IN ('user','group','everyone')),
    subject_id   TEXT NOT NULL DEFAULT '', -- leer bei 'everyone'
    level        TEXT NOT NULL CHECK (level IN ('use','manage')),
    granted_by   TEXT NOT NULL,
    granted_at   TEXT NOT NULL,
    PRIMARY KEY (capability, subject_type, subject_id)
);

-- Geteilte Sachen (Besitzer oder Admin schreibt)
CREATE TABLE access_resource_shares (
    resource_type TEXT NOT NULL,           -- 'vm', 'container', 'blueprint_board', …
    resource_id   TEXT NOT NULL,
    owner_id      TEXT NOT NULL,           -- user_id des Besitzers
    subject_type  TEXT NOT NULL CHECK (subject_type IN ('user','group')),
    subject_id    TEXT NOT NULL,
    level         TEXT NOT NULL CHECK (level IN ('use','manage')),
    shared_by     TEXT NOT NULL,
    shared_at     TEXT NOT NULL,
    PRIMARY KEY (resource_type, resource_id, subject_type, subject_id)
);

CREATE TABLE access_audit (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    at         TEXT NOT NULL,
    actor_id   TEXT NOT NULL,
    action     TEXT NOT NULL,              -- grant, revoke, share, unshare, group_*
    target     TEXT NOT NULL,              -- capability oder typ:id oder group:id
    detail     TEXT NOT NULL DEFAULT ''
);
```

Alle Verweise auf Nutzer über die stabile `user_id`, nie über den Namen.
Wird ein Nutzer gelöscht, entfernt der Core seine Mitgliedschaften, Freigaben und
Teilungen. Das geschieht in `api/routes/users.py → delete_user()`, direkt neben
dem bereits vorhandenen Löschen seiner Agenten. Sachen, die er besessen hat,
verlieren damit auch alle Teilungen.

## 7. Regeln

1. **Admins dürfen alles.** Keine Prüfung für Rolle `admin`.
2. **Funktion:** Ein Nutzer darf eine Funktion nutzen, wenn es eine Freigabe für
   `everyone`, für ihn selbst oder für eine seiner Gruppen gibt. Die höchste
   Stufe gewinnt.
3. **Nicht deklarierte Funktion = für alle freigegeben.** Nur was ein Modul oder der
   Core als Funktion anmeldet, wird überhaupt geprüft. So brechen Module ohne
   Angaben nicht.
4. **Sache:** Zugriff hat der Besitzer, ein Admin und jeder, mit dem die Sache
   geteilt ist (direkt oder über eine Gruppe). Teilen darf, wer `manage` hat.
5. **Funktion vor Sache:** Eine geteilte VM nützt nur, wer auch `core.vms` darf.
   Beim Teilen warnt die Oberfläche, wenn der Empfänger die Funktion nicht hat.
6. **Agenten erben die Rechte ihres Besitzers.** Ein Buddy von Nutzer X bekommt
   nur Werkzeuge, deren Funktion X nutzen darf, und nur Sachen, auf die X
   Zugriff hat. Maßgeblich ist `ctx.user_id` des Laufs.
7. **Fail-closed bei Fehlern:** Kann die Prüfung nicht entscheiden (DB-Fehler),
   wird abgelehnt und protokolliert.

## 8. Wie Module und Core Funktionen anmelden

Manifest (neu, ersetzt das bisher ungenutzte `permissions`):

```json
"capabilities": [
  { "id": "module.homeassistant", "label": "Home Assistant nutzen",
    "default": "admin_only" },
  { "id": "homeassistant.control", "label": "Geräte schalten",
    "default": "admin_only", "tools": ["ha_call_service"] }
]
```

- `id` beginnt mit `module.<modul-id>` für die Modul-Grundfreigabe, weitere
  Funktionen mit `<modul-id>.<name>`.
- `default` bestimmt den Anfangszustand beim ersten Laden:
  `everyone` (legt eine `everyone`-Freigabe an) oder `admin_only` (legt nichts an).
- `tools` ordnet Werkzeuge einer Funktion zu. Tools ohne Zuordnung hängen an
  `module.<id>`.
- Das alte Feld `permissions` wird weiter gelesen und ignoriert (Kompatibilität).

Core-Funktionen stehen in einer Liste im Core (`access/capabilities.py`), z. B.
`core.vms`, `core.containers`, `core.federation`, `core.shell`.

Core-Werkzeuge hängen nur dann an einer Funktion, wenn die Core-Liste sie
nennt (`tools=`). `core.shell` nennt `shell_exec` und `web_browser`. Dazu
kommen alle Plugin-Werkzeuge (`plugin__…`), weil Plugins im Server-Prozess
laufen und keine Workspace-Grenze prüfen. Alle übrigen Core-Werkzeuge
(`file_read`, `fetch_url` …) bleiben ungeprüft, sie haben eigene Grenzen.

## 9. Durchsetzung

| Ebene | Wo | Wie |
|---|---|---|
| Modul-Schnittstellen | `mount_module_routers()` | `include_router(..., dependencies=[require_capability("module.<id>")])` |
| Feinere Modul-Funktionen | im Modul | `Depends(require_capability("homeassistant.control"))` |
| Core-Schnittstellen | Router von VMs, Container, Föderation … | `dependencies=[require_capability("core.vms")]` |
| Werkzeuge im Lauf | `runner.py` nach `scope_tools()` | Werkzeuge ohne Freigabe des Besitzers herausfiltern |
| Werkzeuge bei Ausführung | `dispatcher.execute_tool()` | zweite Prüfung, falls ein Tool trotzdem aufgerufen wird |
| Sachen | Routen der jeweiligen Sache | `require_resource_access(typ, id, level)` statt reiner Besitzer-Prüfung |
| Menü | `nav-config.ts` + Modul-Nav | `/api/access/me` liefert die freigegebenen Funktionen, Menü blendet den Rest aus |
| Modul-Routen im Browser | `App.tsx` | nicht freigegebene Modul-Routen zeigen „Kein Zugriff“ statt der Seite |

`require_capability` baut auf `require_principal` auf (aktuelle Rolle, stabile
`user_id`). Ergebnis pro Anfrage zwischenspeichern, damit nicht jede Route die DB
mehrfach fragt.

Werkzeug → Funktion: `register_module_tools()` merkt sich zu jedem Tool die
Modul-ID (neues Feld `Tool.module_id`, beim Registrieren gesetzt). Daraus und aus
dem Manifest-Feld `tools` ergibt sich die Funktion.

## 10. Oberfläche

**Admin → Benutzer → neuer Reiter „Gruppen“**
Gruppen anlegen, umbenennen, löschen, Mitglieder hinzufügen und entfernen.

**Admin → neuer Bereich „Freigaben“**
Tabelle: Zeilen = Funktionen (gruppiert nach Core und Modul), Spalten = „Alle“,
Gruppen, einzelne Nutzer. Je Zelle: –, benutzen, verwalten. Admins stehen nicht
in der Tabelle (dürfen immer).

**Bei jeder teilbaren Sache: Knopf „Teilen“**
Dialog: Nutzer oder Gruppe wählen, Stufe wählen, Liste der bisherigen Teilungen
mit Entfernen. Warnung, wenn der Empfänger die nötige Funktion nicht hat.

**Profil (`/profile`, gibt es schon) → neuer Abschnitt „Meine Freigaben“**
Nur lesend: welche Funktionen ich habe und was mit mir geteilt ist.

## 11. Übergang (bestehende Installationen)

Damit nichts plötzlich verschwindet:

1. Beim ersten Start mit der Migration bekommt **jede heute vorhandene Funktion
   eine `everyone`-Freigabe**, außer den heiklen Funktionen aus Abschnitt 12.
2. Die heiklen Funktionen starten mit **`admin_only`**. Der Admin gibt sie danach
   gezielt frei.
3. Der Admin sieht nach dem Update einen Hinweis im Cockpit: „Neue Freigaben:
   diese Funktionen sind jetzt nur für Admins. Hier freigeben.“
4. Agenten-Konfigurationen werden **nicht** umgeschrieben. Der Filter wirkt zur
   Laufzeit. Ein Tool, das der Besitzer nicht mehr darf, steht zwar noch in der
   Liste, wird aber nicht angeboten. Der Agent-Editor zeigt es ausgegraut mit
   Hinweis.

## 12. Anfangszustand der heiklen Funktionen

| Funktion | Start | Warum |
|---|---|---|
| `homeassistant.control` (ha_call_service) | admin_only | schaltet echte Geräte |
| `module.voice` | admin_only | Verlauf der Box, Sprechen im fremden Namen |
| `core.vms`, `core.containers` | admin_only | Host-Ressourcen, Bridged ins LAN |
| `core.federation` | admin_only | fremde Rechner fernsteuern |
| `core.shell` (shell_exec, web_browser, Plugins) | admin_only | läuft als Dienst-User ohne Sandbox, liest Serverdateien und Schlüssel (Task 3bd963b2) |
| `module.archiver` | admin_only | root-Zugriff auf Dateisystem (bis Ticket #48) |
| `module.opentor` | admin_only | rechtlich heikle Recherche |
| `module.homeassistant` (lesen) | everyone | reine Anzeige |

Alles andere startet mit `everyone`.

## 13. Etappen

**Etappe 1: Funktions-Freigaben**
Tabellen, Gruppen-Verwaltung (Admin), Freigabe-Tabelle (Admin),
`require_capability`, Modul-Router-Gate, Core-Gate für VMs/Container/Föderation,
Werkzeug-Filter im Runner und Dispatcher, `/api/access/me`, Menü-Filter,
Manifest-Feld `capabilities` für Home Assistant, Voice, Archiver, OpenTor,
Übergang nach Abschnitt 11. Deckt 1333b295, 472a28a7, 4c14b933 und den
Rechte-Teil von 65762134 und b461b999 ab.

**Etappe 2: Sachen teilen**
`access_resource_shares`, `require_resource_access`, Teilen-Dialog. Zuerst für
VMs/Container, Voicebox (setzt Voice-Registry S1 voraus), Föderations-Workstations,
Blueprint-Boards. Danach weitere Module nach Bedarf.

**Etappe 3: Bestehende Gruppenkonzepte anbinden (optional)**
Tickets-Teams und Haushalte können Core-Gruppen als Mitgliederquelle nutzen.
Bis dahin laufen sie unverändert weiter.

Unabhängig davon und sofort machbar (nicht Teil dieser Spec):
Blueprint-Agenten-Werkzeug (9111b283), Rückfrage bei kritischen Home-Assistant-
Domains (lock, alarm_control_panel, cover) in 1333b295.

## 14. Sicherheit

- Alle Schreibwege für Gruppen und Funktions-Freigaben: `require_admin_principal`.
- Teilen: nur Besitzer, Nutzer mit `manage` auf der Sache oder Admin.
- Jede Änderung landet in `access_audit`.
- Prüfungen immer über `user_id`, nie über den Namen. Umbenennen eines Nutzers
  ändert keine Rechte.
- API-Keys (`hhk_`) unterliegen denselben Prüfungen wie der Nutzer, dem sie gehören.
- Tests prüfen jede Durchsetzungs-Ebene aus Abschnitt 9 einzeln (siehe 16).

## 15. Offene Punkte

1. Soll es neben `use`/`manage` später eine Stufe `read` geben (nur ansehen)?
   Vorschlag: erst bei Bedarf.
2. Kontingente (Anzahl VMs, RAM …) gehören sachlich zu 472a28a7 und kommen als
   eigene Spec nach Etappe 1.
3. Dürfen Nutzer eigene Gruppen anlegen (z. B. zum Teilen)? Heute: nein, nur Admin.
4. Föderation: Workstations als teilbare Sache in Etappe 2 oder nur Funktion?

## 16. Akzeptanzkriterien Etappe 1

- Nicht-Admin ohne `module.homeassistant` → 403 auf `/api/modules/homeassistant/*`,
  Menüpunkt unsichtbar, Seite zeigt „Kein Zugriff“.
- Nicht-Admin in Gruppe „Familie“ mit Freigabe → Zugriff.
- Buddy eines Nutzers ohne `homeassistant.control` bekommt `ha_call_service` nicht
  angeboten. Ein trotzdem erzwungener Aufruf wird im Dispatcher abgelehnt.
- Nicht-Admin ohne `core.vms` → 403 auf `POST /api/vms`.
- Admin hat immer Zugriff, unabhängig von Einträgen.
- Nach dem Update auf eine bestehende Installation: alle nicht heiklen Funktionen
  unverändert nutzbar, heikle nur für Admins, Hinweis im Cockpit sichtbar.
- Modul ohne `capabilities` im Manifest verhält sich wie heute.
- Jede Änderung an Gruppen und Freigaben steht im Audit.
- Löschen eines Nutzers entfernt seine Mitgliedschaften und Freigaben.
- Volle Test-Suite grün, Tests laufen gegen isolierte DB (`leak=0`).
