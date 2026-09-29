# AgentLink: Absicherung

Stand: 29.09.2026. Gehört zu Task 3bd963b2.

## Ausgangslage

AgentLink (HydraLink, `/opt/hydralink`) ist der lokale Vermittler für Aufträge
zwischen Agenten. HydraHive spricht ihn über `http://127.0.0.1:9000` an.
AgentLink selbst hat **keine Anmeldung**. nginx gibt ihn für das Dashboard unter
`/agentlink/`, `/agentlink/api/` und `/agentlink/ws` frei.

## 1. Signierte States (#472)

- HydraHive signiert jeden State, den es sendet (`agentlink/signing.py`).
- Verfahren: HMAC-SHA256 über id, Absender, Ziel, reason, Aufgabe und Kontext.
- Der Schlüssel ist aus `secret_key` abgeleitet (Zweck `hydrahive-agentlink-state-v1`).
- Die Signatur steht im letzten reason-Segment `|hh-sig:v1:<hex>`, weil AgentLink
  reason unverändert speichert und fremde Felder verwirft.
- `handoff_receiver` nimmt nur signierte Aufträge an. Jeder State startet
  höchstens einen Lauf.
- `resolve_pending` nimmt nur signierte Antworten an.

## 2. Dashboard nur für Admins (b2)

HydraHive hält das Login im Browser in `sessionStorage`. Bei einer Navigation
nach `/agentlink/` wird es nicht mitgeschickt. Deshalb gibt es ein eigenes Cookie.

- **Ausstellen:** `POST /api/agentlink/dashboard-session` ist nur für Admins und
  setzt das Cookie `hh_agentlink`.
  - Attribute: HttpOnly, Secure, SameSite=Strict, Path=/agentlink/, 8 Stunden gültig.
  - Inhalt: user_id und Ablauf, signiert mit eigenem Zweck
    (`hydrahive-agentlink-dashboard-v1`).
  - Es ist kein Login-Token und öffnet keine HydraHive-API.
- **Prüfen:** `GET /api/agentlink/dashboard-auth` antwortet mit 204 oder 401.
  - Geprüft werden Signatur und Ablauf.
  - Außerdem muss der Nutzer noch existieren und immer noch Admin sein.
- **nginx** (`installer/modules/60-nginx.sh`):
  - Alle drei `/agentlink/`-Wege haben `auth_request /_hh_agentlink_auth`.
  - Die Prüf-Location ist `internal`.
  - Ohne gültiges Cookie leitet `/agentlink/` auf `/` um, API und WebSocket
    antworten mit 401.
- **Update:** `update.sh` schreibt die nginx-Config neu, wenn der Marker
  `hh_agentlink_auth` fehlt.
- **Frontend:** In der AgentLinkCard sehen nur Admins den Button
  „Dashboard öffnen“. Er holt erst das Cookie und öffnet dann den Tab.

## Nicht abgedeckt

AgentLink selbst bleibt ohne Anmeldung. Direkt auf `127.0.0.1:9000` kommt nur,
wer auf dem Server selbst etwas ausführen kann. Das sind seit #470 nur Admins
oder Nutzer mit Freigabe `core.shell`.
