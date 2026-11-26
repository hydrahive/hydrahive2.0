# Instanzname und Agent-Identität

**Stand:** 12.10.2026 · **Status:** Entscheidungen getroffen (Till 11./12.10.), wartet auf Freigabe · **Task:** be1b6200
**Verwandt:** `server-peering.md`, `agentlink-security.md`, `datamining-access.md`

## Problem

Seit es zwei HydraHive-Server gibt (.2 = „hydrahome“, VPS), fallen drei Dinge auf:

1. **Kein Server kennt seinen Namen.** `HH_AGENTLINK_AGENT_ID` ist überall
   `hydrahive`. Agenten raten, auf welchem Server sie laufen (VPS-Buddy:
   „hydrahive2“, echter Host `srv2034108`).
2. **Commits sind anonym.** Im hydrahive2-Repo (letzte 30 Commits): 19×
   „Hydrahive DEV Agent“ (eine feste Git-Einstellung im Repo, gleich für jeden
   Agenten), 11× GitHub-Merges. Welcher Agent was gemacht hat, ist nicht zu sehen.
3. **Datamining ist pro Server getrennt.** Der VPS hat seit 04.10. ein eigenes
   Datamining. Ein Agent auf dem einen Server soll auch nachsehen können, was auf
   dem anderen besprochen wurde, und umgekehrt.

## Kern: ein Instanzname pro Server

- Neue Einstellung **`instance_name`** (Admin → System), Standard = Hostname.
  Erlaubt `[a-z0-9-]{1,32}`. **.2 heißt `hydrahome`** (Entscheidung Till).
- Wird verwendet für:
  - Kopplungscode (Vorschlag für den Namen, den der Partner sieht)
  - Commit-Autor (siehe unten)
  - Herkunft bei Datamining-Treffern vom Partner (siehe unten)
  - einen Satz im Systemprompt: „Du läufst auf dem HydraHive-Server
    `<instance_name>` (Host `<hostname>`).“
- **Nicht** für `HH_AGENTLINK_AGENT_ID`: AgentLink bleibt pro Server lokal
  (Server-Kopplung läuft über `/api/peering`). Eine Umbenennung würde laufende
  Hintergrund-Aufträge verwaisen lassen. Kann später folgen.

## Commit-Autor pro Agent

`shell_exec` setzt bei jedem Aufruf:

```
GIT_AUTHOR_NAME     = <Agent-Name> (<instance_name>)
GIT_AUTHOR_EMAIL    = <agent-id>@<instance_name>.hydrahive.local
GIT_COMMITTER_NAME  = (gleich)
GIT_COMMITTER_EMAIL = (gleich)
```

- Umgebungsvariablen haben bei Git Vorrang vor `git config user.*`, die
  repo-lokale Einstellung „Hydrahive DEV Agent“ wird also überstimmt.
- Agent-ID in der E-Mail: eindeutig, auch wenn zwei Agenten gleich heißen.
- Auf GitHub erscheint der Name aus `GIT_AUTHOR_NAME`; die E-Mail ist keinem
  GitHub-Konto zugeordnet, es entstehen keine Benachrichtigungen.

## Datamining über Server

**Entscheidung Till (12.10.):** Es wird **nichts kopiert**. Jeder Server behält
sein eigenes Datamining. Die Server fragen einander **live** ab, in **beide
Richtungen** (.2 ↔ VPS). Ein Abgleich der Datenbanken wäre zu viel.

### Ablauf

1. Agent auf .2 sucht mit einem Datamining-Werkzeug und gibt den Partner an,
   z. B. `datamining_search(query="…", server="hydrahive-vps")`.
   Ohne `server` sucht er wie bisher nur lokal. Es gibt keine Suche über alle
   Server auf einmal, das ist bewusst so.
2. .2 schickt die Anfrage signiert über die bestehende Server-Kopplung:
   `POST https://<partner>/api/peering/datamining` mit Absender-Server,
   Werkzeug (`search` | `semantic` | `timeline` | `today`), Parametern,
   Nutzer, Zeitstempel und Anfrage-ID. Ed25519 wie bei Aufträgen.
3. Der Partner prüft dieselben Dinge wie bei Aufträgen (gekoppelt, aktiv,
   Signatur, frisch, keine Wiederholung) und dazu:
   - Der Partner hat für diesen Server das Recht **„Datamining abfragen“**.
     Standard: aus. Der Admin schaltet es pro Partner ein.
   - **Wessen Daten?** Nur die des gleichnamigen Nutzers auf dem Partner
     (till ↔ till), mit `scope: user`. Projekt-Agenten des Absenders fragen
     mit ihrem Projektbezug nur dann, wenn dasselbe Projekt auf dem Partner
     existiert. Sonst gibt es keine Treffer.
   - **Gesundheitsdaten** (`sensitive`) gibt der Partner nie heraus, auch
     nicht an Buddys.
4. Der Partner führt die Suche lokal aus (dieselbe Funktion wie seine eigenen
   Werkzeuge) und antwortet **direkt** (synchron, kein Auftrag im AgentLink).
   Er liefert höchstens 50 Treffer bzw. 200 kB, jeweils mit
   `server = <instance_name des Partners>`.
5. Beim Agenten erscheinen die Treffer als eigene Liste „vom Server
   `hydrahive-vps`“. Ist der Partner nicht erreichbar (Timeout 15 s), sagt
   das Werkzeug das klar und liefert keinen Fehler-Text als Treffer.

### Grenzen

- Nur über Tailscale, nur signiert, wie alle `/api/peering/*`-Endpunkte.
- Rate-Limit pro Partner (z. B. 30 Anfragen/min).
- Jede beantwortete und jede abgelehnte Anfrage geht ins Audit des Partners
  (Server, Nutzer, Werkzeug, Anzahl Treffer, ohne Suchtext).
- Keine Speicherung der Partner-Treffer auf dem anfragenden Server, außer im
  Verlauf der Sitzung, in der sie abgefragt wurden.

## Entscheidungen (Till)

1. Datamining: **live abfragen**, kein Kopieren (12.10.).
2. Jeder Server behält sein eigenes Datamining (11.10.).
3. Beide Richtungen: .2 fragt den VPS, der VPS fragt .2 (11.10.).
4. Instanzname .2 = `hydrahome` (11.10.).

### Noch offen (vor Etappe 3)

- Nutzer-Zuordnung über Servergrenzen: Reicht „gleicher Nutzername“, oder
  soll der Admin je Partner eine Zuordnung pflegen (till@.2 = till@VPS)?

## Akzeptanzkriterien

1. `instance_name` einstellbar, Standard Hostname, im Systemprompt sichtbar.
2. Ein Commit über `shell_exec` trägt Agent-Name und Instanzname als Autor.
3. Auf .2 findet `datamining_search(…, server="hydrahive-vps")` einen
   Eintrag, der nur auf dem VPS liegt, mit Angabe des Servers. Umgekehrt
   genauso vom VPS aus.
4. Ohne Recht „Datamining abfragen“ → abgelehnt, keine Suche auf dem Partner.
5. Fremde Nutzer und Gesundheitsdaten kommen nie zurück (Test mit Einträgen
   eines anderen Nutzers und mit `query_health_data`).
6. Partner nicht erreichbar → klare Meldung nach höchstens 15 s, lokale
   Suche ohne `server` unverändert.
7. Auf keinem Server entsteht eine Kopie der Partner-Einträge in der
   Datamining-Datenbank.

## Etappen

1. Instanzname + Systemprompt + Kopplungscode-Vorschlag
2. Commit-Autor in `shell_exec`
3. Datamining live abfragen (beide Richtungen)
