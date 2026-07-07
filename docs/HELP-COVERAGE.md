# Hilfe-Doku — Lückenliste & Fahrplan

> Stand der In-App-Hilfe (HelpDrawer + `frontend/src/i18n/help/<lang>/<topic>.md`).
> Ziel: jede Nav-Seite und jedes Modul hat (1) einen HelpButton, (2) einen
> ausführlichen, einsteigerfreundlichen Deep-Dive-Artikel, (3) ein registriertes
> Loader-Topic. Feld-Tooltips sind Phase 3.
>
> Legende: ✅ vorhanden · 🟡 dünn/unvollständig · ❌ fehlt

## Technische Basis
- Artikel: `frontend/src/i18n/help/de/<topic>.md` + `.../en/<topic>.md`
- Loader-Typ `HelpTopic` in `frontend/src/i18n/help/loader.ts` — **muss jedes Topic kennen** (aktuell nur 7!)
- Einbau je Seite: `<HelpButton topic="…" />` (aus `@/i18n/HelpButton`)
- Handbuch-Übersicht: `frontend/src/i18n/locales/{de,en}/help.json` → `manual.topics`

## Kern-Nav (NAV_ITEMS)

| Seite | Pfad | Artikel | HelpButton | Loader-Topic | Prio |
|-------|------|---------|-----------|--------------|------|
| Dashboard | /dashboard | ✅ (dünn, 1.4k) | ✅ | ✅ | hoch |
| Buddy | / | ✅ | ✅ | ✅ | **sehr hoch** (Startseite) |
| Werkstatt | /werkstatt | 🟡 (chat.md passt teils) | ✅ (im ChatHeader) | ✅ (chat) | **sehr hoch** |
| Agenten | /settings/agents | ✅ (3.6k) | ✅ (Empty-State) | ✅ | hoch |
| Projekte | /settings/projects | ✅ (3.1k) | ✅ (Empty-State) | ✅ | hoch |
| Communication | /communication | ✅ | ✅ | ✅ | mittel |
| Teamchat | /teamchat | ✅ | ✅ | ✅ | mittel |
| Butler | /butler | ✅ | ✅ | ✅ | mittel |
| Zahnfee | /zahnfee | ❌ | ❌ | ✅ | niedrig (admin) |
| Skills | /skills | ✅ | ✅ | ✅ | mittel |
| MCP | /mcp | ✅ (3.9k) | ✅ | ✅ | hoch |
| Plugins | /plugins | ❌ | ❌ | ✅ | niedrig (admin) |
| VMs | /vms | ❌ | ❌ | ✅ | mittel |
| Container | /containers | ❌ | ❌ | ✅ | mittel |
| Federation | /federation | ❌ | ❌ | ✅ | niedrig |
| Streaming | /streaming | ❌ | ❌ | ✅ | niedrig |
| Datamining | /datamining | ✅ | ✅ | ✅ | mittel |
| Memory | /memory | ✅ | ✅ | ✅ | mittel |
| VMs | /vms | ✅ | ✅ | ✅ | mittel |
| Container | /containers | ✅ | ✅ | ✅ | mittel |
| System | /settings → System | ✅ (2.3k) | ✅ | ✅ | hoch |
| LLM | /settings → LLM | ✅ (3.3k) | ✅ | ✅ | hoch |
| Hilfe/Handbuch | /help | (Meta) | — | — | — |

## Settings-Hub (Zahnrad → /settings, keine eigenen Nav-Items)
| Bereich | Artikel | Prio |
|---------|---------|------|
| Credentials | ✅ (Artikel + Button) | hoch (Keys/Secrets — kritisch für Einstieg) |
| Extensions | ❌ | niedrig |
| Module (Verwaltung) | ❌ | mittel |
| Benutzer/Users | ✅ (Artikel + Button) | mittel |
| Einstellungen (Mail, SearXNG, …) | ❌ | mittel |

## Module (frontend/src/modules/*)
| Modul | Pfad | Artikel | Prio |
|-------|------|---------|------|
| Atelier | /atelier | ✅ (Artikel + Button, Button im modules-Repo) | mittel (groß, viel Erklärbedarf) |
| Patientenakte | /akte | ✅ (Artikel + Button, Button im modules-Repo) | mittel |
| Cryptoboard | /cryptoboard | ❌ | niedrig |
| Notizbuch | /notizbuch | ❌ | niedrig |
| Scratchpad | /scratchpad | ❌ | niedrig |
| Deepresearch | /deepresearch | ❌ | niedrig |
| Homeassistant | /homeassistant | ❌ | niedrig |
| Archiver | /archiver | ❌ | niedrig |
| Blueprint | /blueprint | ❌ | niedrig |
| Boardgames/Minigames | /boardgames, /minigames | ❌ | sehr niedrig (Spiele) |
| Musicplayer | /musicplayer | ❌ | niedrig |
| Tasks | (Widget) | ❌ | niedrig |

## Zusammenfassung (Stand: Deep-Dive-Chargen 1–9 — ABGESCHLOSSEN)
- **Loader** kennt jetzt **alle** geplanten Topics (Typ + Glob) — neue Artikel greifen sofort.
- **Neu geschrieben (de+en, ausführlich)**: onboarding, buddy, credentials, butler,
  skills, memory, datamining, communication, teamchat, atelier → **10 neue Artikel-Paare**.
- **HelpButtons neu**: Buddy, Credentials, Butler, Skills, Memory, Datamining,
  Communication, Teamchat, Atelier (modules-Repo), Agenten+Projekte (Empty-State).
- Bestehende Artikel (dashboard, agents, projects, llm, mcp, system, chat) unverändert;
  Dashboard weiterhin dünn → Kandidat für Überarbeitung.

## Status: VOLLSTÄNDIG ✅ (Chargen 1–9)
Alle Nav-Seiten und Module haben jetzt einen Deep-Dive-Artikel (de+en) **und**
einen HelpButton (gelber Blob). Erledigt in Chargen:
- **1–5**: onboarding, buddy, credentials, butler, skills, memory, datamining,
  communication, teamchat, atelier + Agenten/Projekte-Buttons.
- **6**: vms, containers, users, patientenakte.
- **Dashboard** überarbeitet (war dünn → Widget-Beschreibung).
- **7**: cryptoboard, notizbuch, scratchpad, deepresearch.
- **8**: homeassistant, archiver, blueprint, boardgames, minigames, musicplayer,
  tasks, videoeditor.
- **9**: zahnfee, plugins, federation, streaming, extensions.

Bestehende Artikel aus der Frühzeit: agents, projects, llm, mcp, system, chat.

### Nur noch optional offen
- **Werkstatt**: chat.md deckt es ab; ggf. werkstatt-spezifische Ergänzung.
- **Phase 3**: Feld-Tooltips an unklaren Eingabefeldern (eigenes, größeres Thema).
- Modul-Verwaltung (Settings-Bereich Module) — hat kein eigenes Topic; die
  Modul-Liste selbst ist über die Modul-Seite dokumentiert.

## Fahrplan (Original)
1. ✅ **Loader + HelpTopic-Typ** auf alle Topics erweitern.
2. ✅ **Onboarding-Artikel** „Erste Schritte".
3. ✅ **Sehr hoch + hoch**: Buddy, Credentials (Agenten/Projekte-Buttons ergänzt; LLM/MCP/System/Dashboard bestanden schon).
4. 🟡 **Mittel**: Communication, Teamchat, Butler, Skills, Datamining, Memory, Atelier ✅ · VMs, Container, Module-Verwaltung, Users, Akte offen.
5. **Niedrig**: Rest.
6. 🟡 **HelpButton** überall nachrüsten (Kern-Seiten erledigt).
7. **Phase 3**: Feld-Tooltips an unklaren Eingabefeldern.
