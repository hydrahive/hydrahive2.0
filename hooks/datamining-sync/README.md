# Datamining-Sync-Hook

Spiegelt jede Claude-Code-Runde (User, Assistant, Tool-Calls, Tool-Results,
Thinking) live ins HydraHive-Datamining — via `POST /api/sessions/{id}/log`.

## Voraussetzungen (auf dem HydraHive-Server, einmalig)
- User + Agent für diese Instanz angelegt (siehe Implementierungsplan, Prerequisites).
- `HH_PG_MIRROR_DSN` gesetzt (sonst landet nichts im Datamining).

## Verdrahtung in `~/.claude/settings.json`

    {
      "hooks": {
        "Stop": [{
          "command": "python3 /PFAD/zu/hooks/datamining-sync/sync.py"
        }],
        "SubagentStop": [{
          "command": "python3 /PFAD/zu/hooks/datamining-sync/sync.py"
        }]
      }
    }

## Env-Variablen (im Hook-Prozess verfügbar machen)

| Variable | Pflicht | Beispiel |
|---|---|---|
| `HH_BASE_URL` | ja | `https://<hydrahive-host>` |
| `HH_API_KEY` | wenn kein User/Pass | `hhk_...` |
| `HH_USER` / `HH_PASS` | wenn kein Key | `joshua` / `...` |
| `HH_AGENT_ID` | nein (default `claude-code`) | `joshua` |
| `HH_VERIFY_SSL` | nein (default `0`) | `0` |
| `HH_SYNC_STATE_DIR` | nein | `~/.claude/datamining-sync` |

Da Hook-Commands die Umgebung des Claude-Code-Prozesses erben, die `HH_*`-Vars
beim Start setzen (Shell-Profil / Wrapper-Skript), das `sync.py` aufruft.

## Eigenschaften
- **Idempotent:** stabile Transkript-UUID + `INSERT OR IGNORE` → keine Duplikate.
- **Fail-safe:** HydraHive nicht erreichbar → Fehler auf stderr, Session läuft weiter.
- **Offset:** pro CC-Session in `HH_SYNC_STATE_DIR/<session>.json`.

## Secrets-Hinweis
Es wird **alles** gespiegelt — auch Passwörter/Keys, die in eine Session getippt
werden. Optionale Redaction (z.B. `hhk_`/`Bearer`/`HH_PASS`-Muster maskieren)
gehört clientseitig in `transcript.py` und ist hier bewusst noch nicht enthalten.

## Tests

    cd hooks/datamining-sync && python3 -m pytest -q
