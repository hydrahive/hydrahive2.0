# Umsetzungsplan: Tool- und Skill-Katalog

**Ziel:** Ein Agent mit `tool_mode: catalog` bekommt nur einen kleinen Kern an Tools in den Prompt, findet weitere per `find_tools`/`find_skills` und ruft sie per `run_tool` auf – ohne dass sich die Tool-Liste im Lauf ändert; Unteragenten bekommen pro Auftrag Tools aus einem Freigabe-Pool.
**Ansatz:** Zuerst eine zentrale Rechenstelle für die wirksamen Tools (alle Prüfer nutzen sie), dann `run_tool` als Auspacken VOR allen Prüfungen, dann Katalog und Suche, dann der Prompt-Umbau hinter dem Schalter, zuletzt Pool/Zuweisung und Messung. `classic` bleibt Bit für Bit wie heute.
**Technik:** Python 3.12+/3.14 (Kern), SQLite (Konfig), Postgres-Spiegel mit pgvector 0.8.1 (optional), bestehendes Embed-Modell aus der LLM-Konfig.
**Spec:** `docs/specs/tool-skill-katalog.md` (freigegeben 26.11.2026, PR #779). Abschnittsverweise (§, E, D, S, K) beziehen sich darauf.

## Globale Vorgaben

- **Prompt-Cache bricht nie im Lauf** (E4, Till „Cache brechen geht gar nicht“): Die an das Modell geschickte Tool-Liste ist innerhalb eines Laufs byte-gleich; der Prompt-Block mit Kern/Kategorien ist innerhalb eines Laufs byte-gleich.
- **`tool_mode` fehlt oder ist `classic` → Verhalten exakt wie heute** (K7). Kein bestehender Test darf sich ändern müssen.
- **Rechte erweitern sich nie über den Katalog** (§3, S1–S7): Katalog = Suchhilfe. Jede Freigabe läuft durch `effective_tool_names` (Aufgabe 1).
- Oberflächentexte de + en; Fehlermeldungen an das Modell Deutsch.
- Neue Migrationen ohne eigenes BEGIN/COMMIT (`db/migrations/067_…`).
- Ohne Postgres/Embed-Modell: Wortsuche (K9); kein Fehler, kein Start-Abbruch.
- MCP bleibt in Stufe 1 klassisch (D3): MCP-Tools werden nie über den Katalog geführt.

## Review-Fokus

1. **Agent ruft `run_tool` mit einem Tool, das er direkt hat** (z. B. `run_tool("file_read", …)`): muss genauso laufen wie direkt, inkl. Bestätigung – kein Doppel-Eintrag in `tool_calls`. → Test in Aufgabe 2.
2. **Modell erfindet Argumente, die das Schema des inneren Tools nicht hat**: klare Fehlermeldung mit dem Schema, kein Absturz, kein Aufruf. → Test in Aufgabe 2.
3. **Umschalten `catalog` → `classic` mitten in einer bestehenden Sitzung**: nächster Lauf wieder volle Liste, kein Fehler durch vorgemerkte Tools. → Test in Aufgabe 5.
4. **Ein Tool wird nach dem Indexieren entfernt (Modul deinstalliert)**: `find_tools` darf es nicht mehr anbieten, `run_tool` lehnt mit „nicht mehr vorhanden“ ab. → Test in Aufgabe 3.
5. **Sehr lange Buddy-Sitzung sammelt vorgemerkte Tools**: Obergrenze greift (älteste zuerst raus), Kern bleibt. → Test in Aufgabe 5.

---

## Etappe 1 – Rechte-Grundlage (ein Auftrag, ≈ 20 min)

### Aufgabe 1: `effective_tool_names` – eine Stelle für die wirksamen Tools (S6)

**Dateien:**
- Neu: `core/src/hydrahive/agents/effective_tools.py`
- Ändern: `core/src/hydrahive/runner/runner.py:137-143` (nutzt die neue Funktion), `core/src/hydrahive/db/_mirror_scope.py` (Außen-Einstufung), `core/src/hydrahive/api/routes/agent_knowledge.py:50`
- Test: `core/tests/test_effective_tools.py`

**Schnittstellen:**
- Liefert: `effective_tool_names(agent: dict, *, username: str, project: dict | None, pool: list[str] | None = None) -> list[str]`
  Reihenfolge fest (S6): `agent["tools"]` ∪ `pool` → Kategorien auflösen (`resolve_categories`, Aufgabe 4; bis dahin Identität) → `scope_tools(project, …)` → `access_filter_tools(username, …)`. Reihenfolge der Namen stabil (Config-Reihenfolge, dann Pool in Eingabereihenfolge, Duplikate raus).
- Liefert: `possible_tool_names(agent: dict) -> set[str]` – Config ∪ Pool des Agenten **ohne** Projekt-/Besitzer-Filter, für die Gedächtnis-Einstufung (D4: nach möglicher Freigabe).

- [ ] **Schritt 1: Tests schreiben (rot)**
  `test_classic_gleich_wie_heute` (gleiche Liste wie der bisherige Runner-Code für 3 Agenten-Configs aus Fixtures), `test_container_projekt_filtert_pool` (Pool-Tool außerhalb `CONTAINER_ALLOWED` fällt raus), `test_besitzer_filter_gilt_fuer_pool` (Tool mit Capability ohne Freigabe fällt raus), `test_reihenfolge_stabil`, `test_moegliche_tools_fuer_aussen_einstufung` (Pool enthält `send_mail` → `has_outward_tools(possible_tool_names(a))` True).
- [ ] **Schritt 2:** rot laufen lassen: `cd core && PYTHONPATH=src pytest tests/test_effective_tools.py -q`
- [ ] **Schritt 3:** Funktionen umsetzen; Runner Zeile 137–143 ruft `effective_tool_names` (MCP-Teil bleibt daneben unverändert); `_mirror_scope` und `agent_knowledge` nutzen `possible_tool_names`.
- [ ] **Schritt 4:** grün + bestehende Tests: `pytest tests/test_effective_tools.py tests/test_project_container_tools.py tests/test_project_secrets_scope.py tests/test_datamining_agent_scope.py tests/test_agent_knowledge_route.py -q`
- [ ] **Schritt 5:** Commit + Push, PR „feat(agents): effective_tool_names als zentrale Freigabe (Katalog Etappe 1)“. Review: hydrahive-reviewer + **hydrahive-security-reviewer**.

---

## Etappe 2 – `run_tool` (ein Auftrag)

### Aufgabe 2: `run_tool` wird VOR allen Prüfungen ausgepackt (E4, S1)

**Dateien:**
- Neu: `core/src/hydrahive/tools/run_tool.py` (Schema + Beschreibung; `execute` wird nie direkt erreicht)
- Neu: `core/src/hydrahive/runner/_run_tool_unwrap.py`
- Ändern: `core/src/hydrahive/runner/_runner_tools.py:70` (erste Zeile in der Schleife: auspacken), `core/src/hydrahive/db/tools.py` + Aufruf in `runner/dispatcher.py:54` (Herkunft `via` in `tool_calls.metadata`, keine neue Spalte)
- Test: `core/tests/test_run_tool.py`

**Schnittstellen:**
- Nutzt: `effective_tool_names` (Aufgabe 1) – die Freigabe des Laufs ist `allowed_tools`.
- Liefert: `unwrap_run_tool(tool_use: dict, allowed_tools: list[str]) -> tuple[dict, str | None]` → (ausgepackter `tool_use` mit `name=inner`, `input=args`, `via="run_tool"` | unverändert, Fehlertext | None). Fehler, wenn innerer Name ∈ {`run_tool`, `find_tools`, `find_skills`}, nicht in `allowed_tools`, oder `args` nicht zum Schema passt. Validierung **ohne neue Abhängigkeit** (`jsonschema` ist kein deklariertes Kern-Paket): eigene schlanke Prüfung `check_args(schema, args) -> str | None` für `type: object`, `required`, `properties.*.type`, `enum`, unbekannte Felder – mehr nutzen Tool-Schemas nicht. Gegen `REGISTRY[inner].schema` bzw. Plugin-Schema.
- `tool_calls`: Spalte/Metadatum `via` (`run_tool` | NULL); `tool_name` = innerer Name.

- [ ] **Schritt 1: Tests schreiben (rot)** – K10/K11 je Sperrgrund:
  `test_shell_ueber_run_tool_loest_harakiri_aus` (Event `ToolConfirmRequired` mit Grund wie bei direktem `shell_exec`), `test_vault_gesperrt_auch_ueber_run_tool`, `test_run_tool_auf_run_tool_abgelehnt`, `test_container_projekt_run_tool_ausserhalb_allowlist_abgelehnt`, `test_nicht_freigegebenes_tool_abgelehnt`, `test_args_passen_nicht_zum_schema` (Fehler nennt erlaubte Felder, kein Aufruf), `test_tool_calls_zeigt_inneren_namen_und_via`, `test_run_tool_auf_direkt_vorhandenes_tool_wie_direkt` (Review-Fokus 1), `test_agent_tree_erkennt_sperre_ueber_run_tool`.
- [ ] **Schritt 2:** rot laufen lassen.
- [ ] **Schritt 3:** `unwrap_run_tool` umsetzen; in `_runner_tools` als erste Handlung je `tu`, danach unverändert weiter (Bestätigung, `execute_tool`). `run_tool` erscheint im Schema nur, wenn `tool_mode == catalog` (Aufgabe 5) – bis dahin nirgends eingeschaltet.
- [ ] **Schritt 4:** grün + `pytest tests/test_run_tool.py tests/test_runner_harakiri_confirm.py tests/test_tool_confirmation.py tests/test_tool_confirm_wait.py tests/test_dispatcher*.py tests/test_project_container_tools.py -q`
- [ ] **Schritt 5:** Commit + Push, PR. Review: reviewer + **security-reviewer**.

---

## Etappe 3 – Katalog und Suche (zwei Aufträge)

### Aufgabe 3: Katalog-Index und `find_tools` (V5, S7, K2, K3, K9)

**Dateien:**
- Neu: `core/src/hydrahive/catalog/__init__.py`, `catalog/index.py` (Einträge bauen), `catalog/search.py` (Hybrid-Suche), `catalog/_store.py` (Postgres-Tabelle `tool_catalog` mit `embedding vector(dim)` + Fallback im Speicher)
- Neu: `core/src/hydrahive/tools/find_tools.py`
- Test: `core/tests/test_catalog_search.py`, `core/tests/test_find_tools.py`

**Schnittstellen:**
- Liefert: `CatalogEntry(name: str, kind: Literal["tool","skill"], title: str, text: str, category: str, owner_scope: str)` – `name` ist der volle Name inkl. Präfix (S7).
- Liefert: `rebuild_tool_index() -> int` (aus `REGISTRY` + Plugin-Tools; nie MCP), aufgerufen beim Start und nach Modul-/Plugin-Installation; Embeddings im Hintergrund, nie blockierend.
- Liefert: `search(query: str, *, allowed: set[str], kind: str, limit: int = 5) -> list[CatalogEntry]` – filtert **vor** dem Rang auf `allowed` (kein Leck von Beschreibung/Schema gesperrter Tools, S7). Rang = Wortsuche (immer) + Kosinus (wenn Embedding da), zusammengeführt per Reciprocal Rank Fusion.
- `find_tools(query: str)` gibt je Treffer `name`, Kurzbeschreibung, `input_schema` und den Hinweis „Aufruf mit run_tool(name, args)“ zurück.

- [ ] **Schritt 1: Tests (rot)** – `test_zehn_alltagsanfragen_top3` (feste Liste aus 10 Paaren Anfrage→Tool **nur aus Kern-Tools**, damit der Test ohne Module/Plugins läuft, z. B. „Bild erzeugen“→`generate_image`, „Webseite abrufen“→`fetch_url`, „im Internet suchen“→`web_search`, „Mail schicken“→`send_mail`, „Notiz merken“→`write_memory`; einmal mit Fake-Embedding, einmal ohne → beide ≥ 9/10 in Top 3), `test_gesperrtes_tool_nie_im_ergebnis_auch_nicht_beschreibung`, `test_mcp_nie_im_katalog`, `test_entferntes_tool_verschwindet` (Review-Fokus 4), `test_ohne_postgres_wortsuche`.
- [ ] **Schritt 2–4:** rot → umsetzen → grün (`pytest tests/test_catalog_search.py tests/test_find_tools.py -q`).
- [ ] **Schritt 5:** Commit + Push (eigener PR oder zusammen mit Aufgabe 4 – Aufgabe 4 nutzt `catalog.search`).

### Aufgabe 4: Kategorien-Mapping und `find_skills` (S2, D5, K6, K12)

**Dateien:**
- Neu: `core/src/hydrahive/catalog/categories.py` (festes Mapping Kategorie → Tool-Namen, im Kern gepflegt; plus Admin-Bestätigung neuer Zuordnungen)
- Neu: `core/src/hydrahive/tools/find_skills.py`
- Ändern: `catalog/index.py` (Skills je Besitzer/Projekt indexieren über `skills.loader.list_for_agent`)
- Migration: `core/src/hydrahive/db/migrations/067_tool_category_approvals.sql` (Tabelle bestätigter Zuordnungen)
- Test: `core/tests/test_catalog_categories.py`, `core/tests/test_find_skills.py`

**Schnittstellen:**
- Liefert: `resolve_categories(names: list[str]) -> list[str]` – ersetzt `kategorie:<name>` durch die **bestätigten** Tool-Namen (auch in `possible_tool_names`, Aufgabe 1); ausgeschlossen immer: Plugin-/MCP-Tools, Tools mit Capability, `AUTHORING_TOOLS`, `ask_agent`, `OUTWARD_TOOLS`. Wird in `effective_tool_names` (Aufgabe 1) eingehängt.
- Liefert: `find_skills(query)` – nur Skills, die `list_for_agent(agent, owner, project)` liefert (keine fremden).

- [ ] **Schritt 1: Tests (rot)** – `test_kategorie_mit_aussen_tool_macht_agent_nach_aussen` (K15: `possible_tool_names` löst Kategorien auf → Gedächtnis-Stufe höchstens `normal`; da `OUTWARD_TOOLS` nie über Kategorien frei werden (S2), prüft der Test zusätzlich, dass eine Kategorie ein Außen-Tool gar nicht enthalten kann), `test_nachtraeglich_zugeordnet_nicht_frei_bis_bestaetigt`, `test_plugin_mit_kategorie_nicht_frei`, `test_ausschluesse_nie_ueber_kategorie` (je eine Gruppe), `test_find_skills_keine_fremden_skills`, `test_skill_top3_fuer_fuenf_anfragen`.
- [ ] **Schritt 2–5:** rot → umsetzen → grün → Commit/Push, PR (Aufgabe 3+4). Review: reviewer + **security-reviewer** (Kategorien sind eine Freigabe).

---

## Etappe 4 – Prompt hinter dem Schalter (ein Auftrag)

### Aufgabe 5: `tool_mode: catalog` im Runner und Prompt (V2, V4, V6, E4, K1, K4, K7)

**Dateien:**
- Ändern: `core/src/hydrahive/agents/config.py` (Feld `tool_mode`, Standard `classic`; Validierung), `core/src/hydrahive/runner/runner.py:137-145` (Schema-Liste je Modus), `core/src/hydrahive/runner/system_prompt.py:_stable_section` (catalog: Kern-Zeilen + Kategorien-Zeilen statt voller Skill-Tabelle)
- Neu: `core/src/hydrahive/runner/_catalog_mode.py`
- Test: `core/tests/test_catalog_mode.py`

**Schnittstellen:**
- Nutzt: `effective_tool_names` (1), `resolve_categories` (4).
- Liefert: `CORE_TOOLS: tuple[str, ...] = ("shell_exec", "file_read", "file_write", "file_patch", "todo_write", "find_tools", "find_skills", "run_tool", "load_skill", "ask_agent", "read_memory", "write_memory", "search_memory")`
- Liefert: `catalog_schema_names(effective: list[str], pinned: list[str], remembered: list[str]) -> list[str]` = (`CORE_TOOLS` ∩ effective, dann pinned ∩ effective, dann remembered ∩ effective), Reihenfolge stabil. `find_tools`/`find_skills`/`run_tool` sind im catalog-Modus immer enthalten (sie erweitern keine Rechte).
- `remembered`: per `run_tool` in dieser Sitzung benutzte Tools, gespeichert in `session.metadata["catalog_remembered"]` (übersteht Kompaktierung), Obergrenze `REMEMBER_MAX = 15` (älteste raus); wirksam erst **beim nächsten Lauf** (E4).

- [ ] **Schritt 1: Tests (rot)** – `test_classic_payload_unveraendert` (K7: Schema-Liste und System-Prompt eines classic-Agenten identisch zu vorher – Snapshot vor der Änderung erzeugen), `test_catalog_schickt_nur_kern_pinned_remembered` (K1), `test_tool_liste_im_lauf_byte_gleich_trotz_run_tool` (K4: drei LLM-Aufrufe eines Laufs mit `find_tools`+`run_tool` → identische `tools`), `test_remembered_erst_naechster_lauf`, `test_remembered_obergrenze` (Review-Fokus 5), `test_umschalten_catalog_classic_mitten_in_sitzung` (Review-Fokus 3), `test_kern_erweitert_keine_rechte` (D6: Agent ohne `shell_exec` bekommt es auch im catalog nicht).
- [ ] **Schritt 2–4:** rot → umsetzen → grün (`pytest tests/test_catalog_mode.py tests/test_system_prompt*.py tests/test_runner*.py -q` – 16 Dateien, lokal ok).
- [ ] **Schritt 5:** Commit + Push, PR. Review: reviewer.

---

## Etappe 5 – Pool und Zuweisung (ein bis zwei Aufträge)

### Aufgabe 6: Freigabe-Pool, Besitzer-Freigabe, Zuweisung in `ask_agent` (E1, E3, E5, S3, S5, K5, K13, K14, K16)

**Dateien:**
- Migration: `db/migrations/068_tool_pools.sql` – Tabellen `owner_tool_grants(username, tool_or_category)` (vom Admin), `agent_tool_pools(agent_id, tool_or_category)`, `project_tool_pools(project_id, tool_or_category)`
- Neu: `core/src/hydrahive/agents/tool_pools.py`
- Neu/Ändern: API `core/src/hydrahive/api/routes/agent_tool_pools.py` (+ Admin-Route für Besitzer-Freigabe), `tools/_ask_agent_schema.py` (Felder `tools`, `skills`), `tools/_ask_agent_prepare.py`, `runner/_handoff_setup.py` (Zuweisung an den Lauf des Unteragenten)
- Frontend: Agenten-Einstellungen „Freigabe-Pool“, Admin → Nutzer „Besitzer-Freigabe“ (de/en)
- Test: `core/tests/test_tool_pools.py`, `core/tests/test_ask_agent_assign.py`

**Schnittstellen:**
- Nutzt: `effective_tool_names(…, pool=…)` (1).
- Liefert: `pool_for(agent: dict, project: dict | None) -> list[str]` = Agenten-Pool ∩ Projekt-Pool (Projekt-Pool leer = keine Einschränkung), ohne `AUTHORING_TOOLS` und `ask_agent` (S3); `set_agent_pool(actor: str, agent_id: str, items: list[str])` – nur `owner` oder Admin, jedes Item ⊆ `owner_tool_grants(owner)` außer Admin (E5) → sonst `PermissionError` (API 403).
- `ask_agent(tools=[…])`: zugewiesen = `tools ∩ pool_for(ziel)`; Rest → Fehler mit Grund; föderiertes Ziel mit `tools`/`skills` → Fehler (S5). Zuweisung **kommt dazu** (D2), gilt nur für diesen Auftrag.
- `create_specialist`/`configure_specialist` unverändert (`bounded_tools` mit Config-Tools, S3).

- [ ] **Schritt 1: Tests (rot)** – `test_pool_ohne_authoring_und_ask_agent`, `test_unteragent_mit_zugewiesenem_x_legt_spezialisten_ohne_x_an` (K13), `test_write_mitglied_setzt_pool_403`, `test_nicht_admin_ausserhalb_besitzer_freigabe_403`, `test_ohne_besitzer_freigabe_nichts_vergebbar`, `test_admin_ungedeckelt`, `test_wirksam_agenten_pool_schnitt_projekt_pool`, `test_foederiertes_ziel_mit_tools_fehler`, `test_zuweisung_ausserhalb_pool_abgelehnt_mit_grund`, `test_zuweisung_kommt_dazu_gilt_nur_fuer_auftrag`.
- [ ] **Schritt 2–4:** rot → umsetzen → grün.
- [ ] **Schritt 5:** Commit + Push; bei Zeitnot Backend (Migration, Pools, ask_agent) und Frontend als zwei PRs. Review: reviewer + **security-reviewer**.

---

## Etappe 6 – Messung und Erprobung

### Aufgabe 7: Messung gesucht/gefunden/benutzt (V7, K8)

**Dateien:** Neu `core/src/hydrahive/catalog/metrics.py`; Ändern `tools/find_tools.py`, `tools/find_skills.py`, `_run_tool_unwrap.py` (Ereignis schreiben); API-Route `GET /api/catalog/metrics?session_id=` (Admin/Besitzer). Test: `core/tests/test_catalog_metrics.py`.
- Je Sitzung: Anfragen, Treffer (Namen), per `run_tool` benutzt, „gesucht, nichts benutzt“. Speicherung in SQLite (Migration `069_catalog_events.sql`).
- [ ] Tests: `test_metrik_sucht_findet_benutzt`, `test_gesucht_nichts_benutzt_markiert`. Commit/PR, Review reviewer.

### Aufgabe 8: Erprobung auf .4 (V8) – kein Code

- Ein Test-Agent (neu, Kopie des Projekt-Agenten) auf `catalog`; 5 typische Aufträge laufen lassen.
- Messen aus `llm_calls`: Grundlast je Aufruf vorher/nachher, Cache-Anteil, und ob eine geänderte Tool-Liste **beim nächsten Nutzer-Zug** spürbar Cache kostet (Annahme aus E4 nachprüfen).
- Aus Aufgabe 7: wie oft „gesucht, nichts benutzt“ → Beschreibungen nachschärfen.
- Ergebnis als Notiz an Task 2da6ec55; Umschalten weiterer Agenten nur mit Tills OK.

---

## Reihenfolge und Aufträge

| Auftrag | Aufgaben | Abhängig von | Security-Review |
|---|---|---|---|
| 1 | 1 | – | ja |
| 2 | 2 | 1 | ja |
| 3 | 3 | 1 | – |
| 4 | 4 | 3 | ja |
| 5 | 5 | 1, 2, 3, 4 | – |
| 6 | 6 (ggf. geteilt) | 1, 5 | ja |
| 7 | 7 | 2, 3 | – |
| – | 8 (Buddy, mit Till) | alle | – |

Jeder Auftrag: eigener Worktree `_work/wt/katalog-<n>`, Commit + Push nach jedem Teilstück, PR mit grüner CI, Merge per Merge-Commit durch den Buddy nach Review.
