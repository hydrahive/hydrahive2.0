# Live-Agent-Aktivität in der Pixel-Leiste

> Status: Entwurf · 2026-06-18 · Approach 1 (Registry + SSE) · Scope: Chat-Leiste mit „Chat ↔ Alle"-Umschalter

## Ziel

Die Pixel-Männchen-Leiste (`/pixel`) zeigt **echten Live-Status pro Agent** statt aus der Nachrichten-Historie der aktuellen Session abgeleitet. Delegierte Spezialisten (laufen in eigenen Handoff-Sessions) animieren in Echtzeit mit ihrem aktuellen Tool und **verschwinden, wenn sie wirklich idle sind**.

Behebt die Grenze aus [[project_hh2_subagent_zombies]]-Folge: der Monitor leitete alles aus der aktuellen Session ab und konnte den Status delegierter Spezialisten gar nicht sehen.

## Architektur

In-Memory-Aktivitäts-Registry im Backend, vom Runner bei Run-Start / Tool-Wechsel / Run-Ende aktualisiert, über einen globalen SSE-Kanal gepusht. Frontend-Hook abonniert, speist den Monitor mit zwei Scopes. Single-Process (wie `runner/concurrency.py`).

## Komponenten

### Backend

| Datei | Inhalt |
|---|---|
| `runner/activity.py` *(neu)* | `AgentActivity` (session_id, agent_id, name, owner, project_id, current_tool, started_at) + Registry-Singleton `start()/set_tool()/stop()/snapshot(owner)`. Bei jeder Änderung → Broadcaster-Signal (Muster `api/_session_broadcast.py`). TTL-Prune (Einträge älter als 15 min) gegen verwaiste Ghosts. |
| `runner/runner.py` | 3 Hooks: Run-Start → `start(session, agent)`; je `tool_use_start` → `set_tool(session, tool)`; `finally` → `stop(session)`. Deckt Chat, Delegation (handoff_receiver) und Kanäle ab — alle laufen durch `runner.run`. |
| `api/routes/agent_activity.py` *(neu)* | `GET /api/agents/activity/stream` (auth) → initiale `snapshot(owner)`, dann bei jedem Signal neue Owner-gefilterte Momentaufnahme. Nur eigene Agenten. |

Snapshot-statt-Delta: bei jeder Änderung die volle (kleine) Momentaufnahme senden, Frontend ersetzt seine Karte. KISS.

### Frontend

| Datei | Inhalt |
|---|---|
| `features/chat/useAgentActivity.ts` *(neu)* | Abonniert die SSE, hält die Live-Karte laufender Agenten, Reconnect bei Abriss. |
| `ChatPage.tsx` | Neuer `pixelScope: "chat" | "all"`. „all" = alle laufenden Agenten; „chat" = aktiver Agent + laufende Agenten passend zu `ask_agent`-Zielen dieser Session. Pixel-Props aus dem Live-Feed statt Nachrichten-Historie. |
| `AgentPixelMonitor.tsx` | Kleiner „Chat ↔ Alle"-Umschalter. Männchen erscheinen/verschwinden mit dem Feed (Entfernen-Logik existiert). „done"-Nachklang ~2,5 s vor dem Ausblenden. |
| `features/chat/_pixelSelect.ts` *(neu)* | Reine Funktion `selectPixelAgents(activity, scope, activeAgentName, askTargets)` → testbar. |

## Datenfluss

```
runner.run: start → set_tool(tool) … → stop   (jeweils broadcast)
   → SSE /agents/activity/stream → useAgentActivity → selectPixelAgents(scope) → AgentPixelMonitor
```

## Fehlerbehandlung

- SSE-Reconnect mit Backoff (wie bestehende Session-Subscription).
- Registry best-effort: verpasstes `stop` (Crash) → TTL-Prune verhindert Dauer-Ghost.

## Tests (TDD)

- Registry: `start/set_tool/stop` → snapshot stimmt; Owner-Filter; TTL-Prune.
- SSE-Endpoint: initiale Momentaufnahme owner-gefiltert; 401 ohne Auth.
- `selectPixelAgents`: beide Scopes (chat/all) unit-getestet.

## Nicht in v1 (YAGNI)

App-weite Leiste · Cross-User/Admin-Sicht · Multi-Worker (Registry single-process) · Delta-Protokoll.
