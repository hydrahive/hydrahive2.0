# Instanzname und Agent-Identität

**Stand:** 05.10.2026 · **Status:** Entwurf, Entscheidungen offen (siehe unten) · **Task:** be1b6200
**Verwandt:** `server-peering.md`, `agentlink-security.md`

## Problem

Seit es zwei HydraHive-Server gibt (.2 = „hydrahome“, VPS), fallen drei Dinge auf:

1. **Kein Server kennt seinen Namen.** `HH_AGENTLINK_AGENT_ID` ist überall
   `hydrahive`. Agenten raten, auf welchem Server sie laufen (VPS-Buddy:
   „hydrahive2“, echter Host `srv2034108`).
2. **Commits sind anonym.** Im hydrahive2-Repo (letzte 30 Commits): 19×
   „Hydrahive DEV Agent“ (eine feste Git-Einstellung im Repo, gleich für jeden
   Agenten), 11× GitHub-Merges. Welcher Agent was gemacht hat, ist nicht zu sehen.
3. **Datamining ist pro Server getrennt.** Der VPS hat seit 04.10. ein eigenes
   Datamining. Till möchte alles auf .2 durchsuchen.
   Menge: .2 hat 524.541 Einträge (8,4 GB), letzte 7 Tage 28.424 Einträge
   ≈ 3,6 MB Text/Tag. Der Traffic ist unkritisch.

## Kern: ein Instanzname pro Server

- Neue Einstellung **`instance_name`** (Admin → System), Standard = Hostname.
  Erlaubt `[a-z0-9-]{1,32}`.
- Wird verwendet für:
  - Kopplungscode (Vorschlag für den Namen, den der Partner sieht)
  - Commit-Autor (siehe unten)
  - Herkunft im Datamining
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

**Vorschlag A (empfohlen):** Der VPS schickt seine Datamining-Einträge über die
Server-Kopplung an .2.

- Neuer Endpunkt `POST /api/peering/datamining` (signiert, wie Aufträge).
- Nur wenn der Partner auf .2 das Recht **„Datamining empfangen“** hat.
- Jeder Eintrag bekommt `origin = <instance_name des Absenders>`.
- Versand gebündelt (z. B. alle 60 s, max. 500 Einträge oder 1 MB je Paket),
  Wiederaufnahme nach Unterbrechung über eine Merkmarke.
- Auf .2 ein Filter „Herkunft“ in der Datamining-Suche.

**Vorschlag B:** .2 fragt das Datamining des VPS bei Bedarf live ab.
Kein Kopieren, aber jede Suche hängt am VPS, und die Ergebnisse sind nicht in
einer Liste.

## Offene Entscheidungen (Till)

1. Datamining: **A** (VPS schickt an .2) oder **B** (live abfragen)?
2. Bei A: Behält der VPS sein eigenes Datamining zusätzlich (Standard: ja)?
3. Bei A: Auch rückwärts (.2 → VPS) oder nur in eine Richtung?
4. Instanzname für .2: `hydrahome` (wie in der Kopplung) übernehmen?

## Akzeptanzkriterien

1. `instance_name` einstellbar, Standard Hostname, im Systemprompt sichtbar.
2. Ein Commit über `shell_exec` trägt Agent-Name und Instanzname als Autor.
3. Bei A: Neuer Eintrag auf dem VPS ist binnen 2 Minuten auf .2 suchbar,
   mit Herkunft „VPS“. Ohne Recht „Datamining empfangen“ → 403.

## Etappen

1. Instanzname + Systemprompt + Kopplungscode-Vorschlag
2. Commit-Autor in `shell_exec`
3. Datamining-Versand (nach Entscheidung)
