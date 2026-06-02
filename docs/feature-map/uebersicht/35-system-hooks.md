# Feature Map: System-Hooks & Background-Tasks

> **Modul:** `core/src/hydrahive/hooks/`  
> **Was:** Event-gesteuerte Hintergrundprozesse. Sync, Cleanup, Monitoring.  
> **Warum:** Dinge die regelmäßig passieren müssen ohne User-Interaktion.

---

## Hook-Typen

### 1. Event-Hooks
Werden bei bestimmten Ereignissen ausgelöst:

| Hook | Trigger | Aufgabe |
|---|---|---|
| `session_end` | Session abgeschlossen | Datamining-Sync |
| `agent_error` | Agent wirft Exception | Error-Logging, Alert |
| `user_login` | User eingeloggt | Last-Login updaten |
| `tool_call` | Jeder Tool-Call | Rate-Limit-Update |
| `compaction` | Compaction passiert | Compaction in Mirror schreiben |

### 2. Background-Tasks (APScheduler)
Regelmäßig laufend:

| Task | Intervall | Aufgabe |
|---|---|---|
| `cleanup_expired_tokens` | 1h | Abgelaufene JWT-Tokens aufräumen |
| `cleanup_sessions` | 24h | Alte leere Sessions löschen |
| `mirror_sync` | 5min | Neue Events in Mirror synchronisieren |
| `vm_health_check` | 1min | Laufende VMs prüfen |
| `cleanup_temp_files` | 1h | Temporäre generierte Dateien aufräumen |
| `samba_sync` | on_change | Samba-Config neu schreiben wenn Projekte geändert |

---

## Dateien

```
hooks/
├── __init__.py          # Hook-Registry
├── base.py              # BaseHook-Klasse
├── event_hooks.py       # Event-Hook-Registrierung
├── scheduler.py         # APScheduler-Setup
├── tasks/
│   ├── cleanup.py       # Cleanup-Tasks
│   ├── mirror_sync.py   # Datamining-Sync
│   ├── vm_health.py     # VM-Health-Check
│   └── samba_sync.py    # Samba-Config-Sync
└── datamining-sync/     # Spezialisierter Sync-Hook
    ├── __init__.py
    └── sync.py
```

---

## Hook-Registrierung

```python
# event_hooks.py
@hook_registry.on("session_end")
async def on_session_end(session_id: str, **kwargs):
    await mirror_sync.sync_session(session_id)

@hook_registry.on("agent_error") 
async def on_agent_error(error: Exception, session_id: str, **kwargs):
    await error_logger.log(error, session_id)
```

---

## APScheduler-Konfiguration

```python
# scheduler.py
scheduler = AsyncIOScheduler()
scheduler.add_job(cleanup_expired_tokens, "interval", hours=1)
scheduler.add_job(mirror_sync_all, "interval", minutes=5)
scheduler.start()  # wird in main.py gestartet
```

---

## Verwandte Subsysteme

- **→ Datamining** (`16-datamining.md`): Mirror-Sync ist wichtigster Hook
- **→ DB** (`03-db.md`): Cleanup-Tasks räumen DB auf
- **→ VMs** (`23-vms.md`): VM-Health-Check-Task
- **→ Samba** (`28-samba.md`): Samba-Sync-Task
