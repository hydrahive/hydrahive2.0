# Plan E5: Module auf Template-Rollen umstellen

Spec: `docs/specs/agent-templates.md` Kap. 3.2, 7. Voraussetzung: E2 live (Kern-API `template=`).
Repo: `hydrahive2-modules` (je Modul eigener PR + Versionssprung), dazu ein Kern-PR für die API.

## Ziel

Kein Modul nennt mehr einen festen Modellnamen. Module fragen eine **Rolle** an
(`modul-schreiber`, `modul-schnell` oder ein eigenes Template), bekommen damit Kette + Failover.

## Kern-Teil (zuerst)

- `core/src/hydrahive/llm/client.py` – `complete(..., template: str | None = None)` und
  `stream(..., template=None)`: Kette aus `templates.resolve_role(template)`, Failover nach E1-Regeln
  (eigene kleine Schleife, gleiche Kategorien, kein Streaming-Wechsel nach gesendetem Text).
  `model=` bleibt erlaubt (Rückwärtskompatibilität), erzeugt aber eine Log-Warnung
  „Modul X nutzt festes Modell“.
- Unbekanntes Template → `chat`-Systemtemplate + Warnung, kein Fehler.
- `core/src/hydrahive/agents/config.py` `create(template=…)` (aus E3) steht Modulen zur Verfügung.
- Modul-Manifest (`manifest.json`) optional `"templates": [{"id": "storyteller-ghostwriter",
  "label": "…", "base": "modul-schreiber"}]` → der Kern legt beim Installieren ein eigenes Template an,
  falls es fehlt (Kopie von `base`), Admin kann es danach anpassen. Deinstallation lässt es stehen.
- Tests: `test_llm_client_template.py`, `test_module_manifest_templates.py`.
- CI-Prüfung `scripts/check_fixed_models.py`: grep nach `llm_model="` / `model="claude-` /
  `model="openai-codex/` usw. in `modules/` und `hydrahive2-modules`, Ausnahmen per Kommentar
  `# feste-modell-id: Grund`.

## Module (je eigener PR, Reihenfolge nach Risiko)

| # | Modul | heute | künftig | Stellen |
|---|---|---|---|---|
| 1 | vibe | `claude-haiku-4-5` fest, sonst `default_model()` | `modul-schnell` | Agent anlegen, Auswahl |
| 2 | hydralabor | `claude-haiku-4-5`, `managed_by` | eigenes `labor` (base `modul-schnell`) | `set_managed` + `create(template=)` |
| 3 | legal | `claude-sonnet-4-6` fest + `get_default("chat")` | `modul-schreiber` | Agent + `complete` |
| 4 | storyteller | 7 Helfer `claude-sonnet-4-6` | `storyteller-ghostwriter` (base `modul-schreiber`) | 7 Agent-Anlagen |
| 5 | game-studio | `default_model()` | `modul-schreiber` | Agent |
| 6 | deepresearch | eigene Läufe / `default_model()` | `recherche` | Läufe |
| 7 | studio | `default_model()` + `complete` | `modul-schnell` | 4 Stellen |
| 8 | atelier | `complete`/`stream` ohne Modell | `modul-schnell` | 3 Stellen |
| 9 | telephony | `complete` | `modul-schnell` | 1 Stelle |
| 10 | haushaltsbuch | `stream` | `modul-schnell` | 1 Stelle |
| 11 | boardgames | `complete` | `modul-schnell` | 1 Stelle |

Je Modul gleicher Ablauf:
- [ ] Test im Modul: Aufruf übergibt `template=…`, nicht `model=`; bestehende Agenten des Moduls
      werden beim Start auf das Template umgestellt (einmalig, idempotent).
- [ ] RED → Umsetzung → GREEN.
- [ ] `min_core_version` in `manifest.json` auf die Kern-Version mit E5-Kern-Teil.
- [ ] Versionssprung (Minor), Changelog-Zeile, PR.
- [ ] Nach Merge: Update über den Modul-Hub auf hydratest, Funktion einmal echt ausprobieren.

Hinweis: `voice` nennt `"anthropic/claude-x"` nur in `voice/tests/test_llm.py` (Testdaten), nicht zur Laufzeit
(geprüft 14.11.). Kein Umbau nötig; `check_fixed_models.py` nimmt `*/tests/` aus.

## Akzeptanzkriterien
- [ ] `check_fixed_models.py` meldet nach allen PRs keine Treffer ohne Begründung.
- [ ] Fällt das Primärmodell eines Modul-Templates aus, antwortet das Modul über die Kette.
- [ ] Module mit altem Kern (ohne `template=`) starten nicht kaputt: `min_core_version` verhindert die
      Installation, Fehlermeldung verständlich.

## Nicht in diesem Plan
- Medien-Modelle (Bild, Musik, TTS, STT, Video) und Embedding – bleiben eigene Einstellungen.
