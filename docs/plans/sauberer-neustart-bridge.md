# Sauberer Neustart: Zeitlimit beim Herunterfahren + WhatsApp-Bridge ohne Waisen

Task 06d38ae9 · 07.10.2026 · Befund Prod (nur lesend) + Nachbau auf hydratest

## Befund
- Jeder Neustart von `hydrahive2` dauert 90 s und endet mit SIGKILL: uvicorn wartet ohne Grenze auf offene
  Verbindungen. `/api/agents/activity/stream` (SSE, Endlosschleife mit Keepalive) ist in jedem offenen Browser-Tab
  offen. Nachgebaut auf hydratest: ohne Stream 0–13 s, mit einem offenen Stream **90 s + SIGKILL**.
- Nach dem SIGKILL läuft der lifespan-Shutdown nie → `wa_bridge.stop()` fehlt. Wegen `KillMode=process` (bewusst,
  VMs/Container) überlebt die Node-Bridge, hält Port 8767; jede neue Bridge stirbt mit `EADDRINUSE`
  (Prod: 166× seit 25.09.; alte Bridge PID 12852 seit 04.10., antwortet 401 auf das aktuelle Secret).
- Gegenprobe hydratest mit `--timeout-graceful-shutdown 10`: Neustart **16 s**, „Cancel 1 running task(s)“,
  lifespan läuft. Die ALTE Bridge (aus dem 90-s-Lauf) blieb trotzdem → Bridge braucht eigene Absicherung.

## Änderungen (eine Ursache = ein Commit)
1. **Zeitlimit** (Linux + Mac): `--timeout-graceful-shutdown 20` an uvicorn in `installer/modules/50-systemd.sh`;
   `update.sh` erkennt alte Unit ohne die Option (`NEEDS_REWRITE`), wie bei `--ws-max-size`. Mac:
   `installer/modules-mac/50-launchd.sh` (Argument im plist) + `update-mac.sh` erkennt alte plist.
   20 s < TimeoutStopSec 90 s → lifespan hat 70 s Luft.
2. **Bridge beendet sich, wenn ihr Backend weg ist** (`bridge/index.js`): stdin wird zur Lebensader – Python startet
   die Bridge mit `stdin=PIPE`; endet der Elternprozess (auch durch SIGKILL), bekommt Node EOF auf stdin →
   `server.close()` + Exit. Schützt bei jedem harten Abbruch, ohne PID-Dateien.
3. **Alte Bridge beim Start ablösen** (`process.py`): Ist der Port belegt, fragt `start()` `/healthz` ab. Antwortet
   eine HydraHive-Bridge, wird sie über eine neue, mit dem Secret geschützte Route `POST /shutdown` beendet (das
   schließt nur Bridges mit gleichem Secret). Antwortet sie nicht/fremd → klare Meldung im Log statt
   EADDRINUSE-Stacktrace, Bridge bleibt aus. Für die eine bestehende Prod-Waise (altes Secret? – prüfen) reicht
   nach dem Update einmalig ein Neustart, weil (2) ab dann greift; die Waise selbst räumt Till ab (`kill 12852`).

## Tests (TDD, zuerst rot)
- `core/tests/test_update_sh_compute_agent.py`-Muster: Unit/plist enthalten die Option; update.sh/update-mac.sh
  erkennen fehlende Option.
- Neu `test_wa_bridge_lifeline.py` (echter Node-Prozess, nur wenn `node` da ist – CI hat Node 20):
  Bridge mit stdin-Pipe starten (ohne baileys: Bridge-Start mit Stub-`lib/sock.js`? → prüfen, ob index.js ohne
  node_modules startet; sonst Lebensader-Logik als eigenes Modul `lib/lifeline.js` testen), stdin schließen →
  Prozess endet < 5 s.
- `process.py`: Port belegt + `/healthz` ok → `/shutdown` mit Secret aufgerufen, danach Start; fremder Dienst → kein
  Start, Log-Meldung. (HTTP gemockt / kleiner Test-Server.)

## Echt prüfen (hydratest)
Neustart mit offenem SSE-Stream < 30 s; Bridge-PID wechselt; kein EADDRINUSE; Waise vom harten Abbruch
(`systemctl kill -s KILL`) beendet sich selbst; Mac: nur Datei-Test (kein Umbau ohne Rückfrage).

## Nicht in diesem PR
Agent-Shell-Kinder überleben Neustarts ebenfalls (vitest seit 15:53). Das ist Absicht von KillMode=process
(VMs/Container), betrifft aber auch Agent-Werkzeuge → eigener Task (Prozessgruppe je shell_exec beim Herunterfahren
beenden).
