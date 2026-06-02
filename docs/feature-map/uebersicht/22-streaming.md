# Feature Map: Streaming — SSE / Real-time

> **Modul:** `core/src/hydrahive/api/routes/streaming.py` + `api/routes/_sse.py`  
> **Was:** Server-Sent Events. Real-time Message-Streaming vom Runner zum Frontend.  
> **Warum:** LLM-Responses kommen Token für Token — ohne Streaming würde User ewig warten.

---

## Technologie: Server-Sent Events (SSE)

SSE ist HTTP-basiert (kein WebSocket). Der Browser öffnet eine lange HTTP-Verbindung.
Server schickt Events im Format:
```
data: {"type": "text_delta", "text": "Hallo"}\n\n
data: {"type": "text_delta", "text": " Welt"}\n\n
data: {"type": "done"}\n\n
```

---

## Ablauf

```
Frontend: POST /api/chat/sessions/{id}/messages
  {content: "Hallo", stream: true}
  → Response: Content-Type: text/event-stream

Backend: streaming.py
  → Auth-Check
  → runner.run(session_id, user_input) als AsyncGenerator
  → Für jedes Event:
      event = serialize(event)
      yield f"data: {event}\n\n"
  → Nach Done-Event: Stream schließen

Frontend: _chatStream.ts
  → EventSource oder fetch() mit ReadableStream
  → Events parsen und in Chat-State einpflegen
```

---

## Event-Typen

| Event-Type | Beschreibung | Frontend-Reaktion |
|---|---|---|
| `message_start` | Neue Bubble beginnt | Neue leere Bubble anlegen |
| `text_delta` | Partial Text | Text in Bubble appenden |
| `text_block` | Fertig-Text-Block | Bubble finalisieren |
| `tool_use_start` | Tool-Call beginnt | Tool-Card anlegen |
| `tool_use_delta` | Tool-Args streaming | Tool-Args in Card zeigen |
| `tool_result` | Tool-Ergebnis | Ergebnis in Card einfügen |
| `thinking_block` | Extended-Thinking | Thinking-Block (klappbar) |
| `compaction` | Compaction passiert | Compaction-Marker im Thread |
| `token_usage` | Token-Zahlen | Token-Meter updaten |
| `iteration_start` | Neue Runde | (Optional: Iteration-Marker) |
| `done` | Alles fertig | Stream beenden, Bubble finalisieren |
| `error` | Fehler aufgetreten | Fehler-Bubble anzeigen |

---

## Heartbeat

`_sse.py` sendet alle 15s einen Heartbeat-Event:
```
data: {"type": "ping"}\n\n
```
Verhindert Timeout von nginx/Load-Balancer bei langen Tool-Ausführungen.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `api/routes/streaming.py` | Haupt-Endpoint. Auth, Runner starten, SSE-Stream. |
| `api/routes/_sse.py` | SSE-Helper: Event-Format, Heartbeat, Error-Handling |
| `db/streaming.py` | Aktive Streams registrieren (für Cleanup bei Disconnect) |
| `frontend/features/chat/_chatStream.ts` | Client-seitige Stream-Verarbeitung |
| `frontend/features/chat/useChat.ts` | State-Updates aus Stream-Events |

---

## Reconnect-Verhalten

- Wenn Verbindung abbricht: Frontend reconnectet automatisch (EventSource-Standard)
- Backend: Session-State bleibt erhalten
- Laufende Tool-Ausführungen werden fortgesetzt
- Fertige Messages sind bereits in DB → kein Datenverlust

---

## Gleichzeitige Streams

- Pro Session: nur ein aktiver Stream
- Neuer Stream für gleiche Session: alter wird ersetzt
- Mehrere Sessions gleichzeitig: jede hat eigenen Stream

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): Runner liefert Events
- **→ Chat UI** (`19-frontend-chat.md`): Frontend verarbeitet Events
- **→ DB** (`03-db.md`): `streaming`-Tabelle für aktive Streams
