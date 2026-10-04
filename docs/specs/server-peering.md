# Server-Kopplung: HydraHive ↔ HydraHive über Tailscale

**Stand:** 04.10.2026 · **Status:** Design, freigegeben in Grundrichtung (Option C, Rechte-Modell 2)
**Task:** 6883a1bc · **Verwandt:** SPEC.md §Tailscale-Integration, `agentlink-security.md`, `workstation-client.md`

## Problem

SPEC.md verspricht: „Verbindung mehrerer HydraHive2-Server untereinander via
HydraLink über Tailscale-IPs“. Das geht heute nicht. Live-Test 04.10.2026
zwischen .2 und dem VPS (hydrahive-vps, 100.89.239.63):

1. **Kein Netzweg.** AgentLink lauscht nur auf `127.0.0.1:9000`. Über nginx
   `/agentlink/` braucht es seit #469–#474 ein Admin-Cookie → 401.
2. **Signatur passt nicht.** `agentlink/signing.py` leitet den HMAC-Schlüssel aus
   dem eigenen `secret_key` ab. Ein State des anderen Servers wird verworfen:
   „ohne gültige Signatur verworfen“ (VPS-Log, State 9ee0112e).
3. **Gleiche Instanz-ID.** Beide Server abonnieren `agent:hydrahive`.

AgentLink selbst hat keine Anmeldung. Ihn ins Netz zu hängen, würde die
Härtung aus #469–#474 zurückdrehen.

## Entscheidung: Option C – HydraHive spricht direkt mit HydraHive

Verworfen:
- **A) Gemeinsamer AgentLink:** AgentLink müsste ins Netz und eine eigene
  Anmeldung bekommen. Fällt der eine Server aus, ist der andere taub.
- **B) In fremden AgentLink posten:** gleiches Netz-/Anmeldeproblem, zweimal.

Gewählt: AgentLink bleibt lokal. HydraHive bekommt einen Server-zu-Server-Endpunkt
hinter nginx (443). Aufträge zwischen Servern sind mit Ed25519 signiert.

## Rechte-Modell (Entscheidung Till: Variante 2)

Ein Partner-Server darf **nur freigegebene Agenten** beauftragen. Der Admin wählt
pro Partner aus, welche Agenten erreichbar sind. Ohne Freigabe: Ablehnung.

## Ablauf

### Kopplung (einmalig, Admin auf beiden Seiten)

1. Jeder Server hat ein eigenes Ed25519-Schlüsselpaar.
   - Privat: `$HH_DATA_DIR/peering/server_ed25519` (0600, nur Service-User).
   - Wird beim ersten Start erzeugt. Nie über die API ausgeliefert.
2. Admin A: **Föderation → Server koppeln** → zeigt einen **Kopplungscode**
   (Name, Tailscale-URL, öffentlicher Schlüssel, Fingerprint), kopierbar.
3. Admin B fügt den Code ein → B speichert A als Partner, Status
   **„wartet auf Bestätigung“**, und zeigt seinen eigenen Kopplungscode.
4. Admin A fügt Bs Code ein. Beide zeigen den **Fingerprint der Gegenseite**;
   der Admin vergleicht und bestätigt. Erst dann ist der Partner **aktiv**.
5. Pro Partner: Liste der **freigegebenen Agenten** (Start: leer).

Kein gemeinsames Geheimnis, kein Passwort über die Leitung.

### Auftrag

1. `ask_agent(agent_id="<agent>@<partner>")` auf Server A.
   - `@`-Routing gibt es schon (`_execute_federated`). Erweiterung: Ist
     `<partner>` ein gekoppelter HydraHive-Server, geht es über den neuen Weg,
     sonst wie bisher `/remote/chat`.
2. A baut einen Auftrag und signiert ihn mit seinem privaten Schlüssel:
   `POST https://<partner>/api/peering/tasks`
   - Inhalt: Auftrags-ID (UUID), Absender-Server, Ziel-Agent, Aufgabe, Kontext,
     Profil, Zeitstempel, Ablauf (max. 5 min).
   - Header: `X-HH-Peer`, `X-HH-Signature` (Ed25519 über die kanonische JSON-Form).
3. B prüft in dieser Reihenfolge, jede Ablehnung ohne Details nach außen:
   - Absender ist gekoppelt und aktiv
   - Signatur gültig
   - Zeitstempel frisch, Auftrags-ID noch nie gesehen (Replay-Schutz)
   - Ziel-Agent ist für diesen Partner freigegeben
4. B legt den Auftrag lokal in seinen eigenen AgentLink, signiert mit seinem
   **eigenen** HMAC wie heute. Der bestehende `handoff_receiver` bleibt unverändert.
   Antwort sofort: `202 accepted` mit Auftrags-ID.
5. Ist der Lauf fertig, schickt B die Antwort signiert zurück:
   `POST https://<A>/api/peering/replies` → A prüft genauso und löst den
   wartenden `ask_agent`.

### Session auf B

- Läuft unter dem Besitzer des Ziel-Agenten (wie heute im `handoff_receiver`).
- Titel/Metadaten zeigen klar: „Auftrag von Server <A>“.
- Kosten fallen auf B an.

## Sicherheit

- Endpunkte `/api/peering/*` nur erreichbar über **Tailscale-Interface**
  (nginx `allow 100.64.0.0/10; deny all;`) **und** nur mit gültiger Signatur.
  Kein Cookie, kein JWT.
- Größenlimit für Aufträge (z. B. 1 MB), Rate-Limit pro Partner.
- Partner sperren = sofort keine Annahme mehr. Schlüsselwechsel = neu koppeln.
- Audit: Jeder angenommene/abgelehnte Auftrag ins `errors_log`/Audit.
- AgentLink bleibt auf `127.0.0.1`. `signing.py` bleibt pro Server.

## Datenmodell (neue Migration)

`federation_peers`
- `id`, `name`, `url`, `public_key`, `fingerprint`
- `status` (`pending` | `active` | `blocked`), `created_at`, `confirmed_at`, `last_seen`

`federation_peer_agents`
- `peer_id`, `agent_id` (Freigaben, Variante 2)

`federation_peer_tasks`
- `task_id`, `peer_id`, `direction` (`in`/`out`), `local_state_id`, `status`, `created_at`
- Dient Replay-Schutz und Zuordnung der Antwort.

## Oberfläche

**Föderation** bekommt einen zweiten Bereich **„Server“** neben den Workstations:
- Server koppeln (Code anzeigen / Code einfügen), Fingerprint-Vergleich
- Je Partner: Status, letzte Verbindung, freigegebene Agenten (Auswahl), sperren, entfernen

## Nicht-Ziele (vorerst)

- Datenabgleich zwischen Servern (Projekte, Memory, Dateien) – siehe `workstation-client.md`
- Mehr als Agenten-Aufträge (z. B. Tools des anderen Servers direkt aufrufen)
- Kopplung ohne Tailscale über das offene Internet

## Akzeptanzkriterien

1. .2 und VPS koppeln über die Oberfläche, Fingerprints stimmen.
2. Auf .2: `ask_agent("<freigegebener Agent>@hydrahive-vps")` → Antwort kommt zurück.
3. Nicht freigegebener Agent → klare Ablehnung, kein Lauf auf dem VPS.
4. Gefälschte Signatur, abgelaufener oder wiederholter Auftrag → abgelehnt, kein Lauf.
5. `/api/peering/*` von außerhalb des Tailnets → 403.
6. Partner gesperrt → sofort abgelehnt.
7. Bestehende lokale `ask_agent`-Aufträge laufen unverändert (Regressionstest).

## Etappen

1. Schlüsselpaar + Datenmodell + Kopplung (API + Oberfläche)
2. Auftrag senden/annehmen + Antwort zurück + Freigaben
3. nginx-Beschränkung, Rate-Limit, Audit
4. Live-Abnahme .2 ↔ VPS
