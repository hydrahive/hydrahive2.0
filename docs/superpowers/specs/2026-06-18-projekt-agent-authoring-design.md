# Feature 1: Projekt-Agent-Authoring (Spezialisten + Skills)

> Status: Entwurf · 2026-06-18 · Approach 2 (geteilte Projekt-Skill-Bibliothek)
> Scope: Feature 1 von 2. Feature 2 (Vorlagen/Cross-User-Sharing) ist separat, danach.

## Ziel

Der **Projekt-Agent** kann sein Projekt selbst gestalten: Spezialisten anlegen/konfigurieren
und Skills bauen/zuweisen — alles **projekt-gebunden**. Damit formt er das Projekt nach den
Wünschen des Users und den Anforderungen, ohne dass ein Admin jeden Spezialisten manuell anlegt.

Analog Claude Code (SPEC Z. 23: „Agenten arbeiten wie Claude Code, nicht wie ein gesperrter
Chatbot"), aber hart begrenzt durch die `project_id`.

## Architektur

Der Projekt-Agent erhält einen kleinen Satz Authoring-Tools. Spezialisten und Skills entstehen
projekt-gebunden; Skills leben in einer neuen Projekt-Bibliothek, die alle Agenten des Projekts
automatisch sehen. Delegation funktioniert sofort (Auto-Eintrag in `allowed_specialists` +
gefixter AgentLink-Loopback, siehe [[project_hh2_subagent_zombies]]).

## Komponenten

### Neuer `project`-Skill-Scope

| Datei | Änderung |
|---|---|
| `skills/models.py` | `SkillScope` += `"project"`; bei project-Scope hält `owner` die `project_id` |
| `skills/_paths.py` | `project_dir(pid) → data_dir/projects/<pid>/skills/`; `dir_for()` erweitern |
| `skills/loader.py` | `list_for_agent()`: hat der Agent eine `project_id`, werden Projekt-Skills dazugemischt |
| `api/routes/skills.py` | Scope `"project"` zulassen, Auth = Projekt-Mitglied/Owner |

`save_skill`/`get_skill`/`delete_skill` laufen über den vorhandenen `(scope, owner)`-Pfad mit.

### Neue Tools (nur Projekt-Agenten)

Je ein Tool pro Datei (HH2-Stil), gemeinsamer Guard + Tools-Subset-Helfer in
`tools/_project_authoring.py`:

| Tool | Zweck |
|---|---|
| `create_specialist` | type=specialist, `project_id`+`owner` erzwungen, tools ⊆ Erzeuger, Auto-Eintrag in `allowed_specialists` |
| `configure_specialist` | Eigenen Projekt-Spezialisten ändern (Modell, Tools ⊆ Erzeuger, System-Prompt, Beschreibung, `status`) |
| `list_specialists` | Spezialisten des eigenen Projekts auflisten (schließt die Discovery-Lücke) |
| `write_skill` | Skill anlegen/bearbeiten — Default Projekt-Scope; optional Agent-Scope eines Spezialisten |
| `delete_skill` | Projekt-/Agent-Skill im eigenen Projekt löschen |

Registrierung: `tools/__init__.py` REGISTRY + `agents/_defaults.py` `DEFAULT_TOOLS["project"]`.

## Sicherheits-Enforcement (hart verdrahtet)

- Guard: Aufrufer muss `type=="project"` **mit** `project_id` sein — sonst Fehler.
- `project_id` + `owner` werden **erzwungen** → kein Fremdprojekt, kein globaler Agent.
- **Tools des Spezialisten ⊆ Tools des Erzeugers**; Authoring-Tools sind **nicht zuweisbar**
  (gefiltert) + intern durch den `type`-Guard blockiert (defense-in-depth).
- Skills nur `project`/`agent`-Scope des eigenen Projekts — **nie `system`/`user`**.
- Spezialist löschen: **nein** — nur `status=disabled` (umkehrbar, CLAUDE.md Regel #6).

## Datenfluss

```
create_specialist("rust-reviewer", tools=[file_read, list_skills, load_skill])
  → config.create(type=specialist, project_id=P, owner=U, tools⊆)
  → project_config: allowed_specialists += id
write_skill("rust-review", scope=project, body=…)        # Projekt-Bibliothek
ask_agent("rust-reviewer", "review X")                    # Loopback (gefixt)
  → Spezialist läuft, sieht Projekt-Skill automatisch, load_skill("rust-review")
```

## Tests (TDD, zuerst)

- Projekt-Scope: save/get/list + `list_for_agent` mischt Projekt-Skills nur für Agenten
  **dieses** Projekts dazu, nicht für fremde.
- `create_specialist`: erzwingt project_id/owner/type, Tools-Subset-Check, Auto-`allowed_specialists`,
  lehnt Nicht-Projekt-Aufrufer ab.
- `write_skill`: erzwingt Projekt-Scope, lehnt `system`/Fremdprojekt ab.
- `configure_specialist`/`delete_skill`: Cross-Projekt-Zugriff wird abgelehnt.

## Nicht in v1 (bewusst, YAGNI)

- Master-Selbstverwaltung (nur Projekt-Agent)
- Spezialist hart löschen (nur disabled)
- UI zum Anzeigen/Bearbeiten der Projekt-Skills (kleiner Nachzug; Agent-Pfad ist der Kern)
- Vorlagen / Cross-User-Sharing = **Feature 2**, eigener Durchgang

## SPEC.md

Neue Kernfähigkeit → braucht laut CLAUDE.md Regel #8 eine **SPEC-Ergänzung als eigener
Standalone-Commit** mit Tills ausdrücklichem OK. Vorschlag: kurzer Absatz unter Projekt-Agent
(„kann projekt-gebunden Spezialisten + Skills erzeugen"). SPEC.md wird NICHT ohne Freigabe angefasst.
