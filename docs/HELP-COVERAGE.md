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
| Buddy | / | ❌ | ❌ | ❌ | **sehr hoch** (Startseite) |
| Werkstatt | /werkstatt | 🟡 (chat.md passt teils) | ✅ (im ChatHeader) | ✅ (chat) | **sehr hoch** |
| Agenten | /settings/agents | ✅ (3.6k) | ❌ | ✅ | hoch |
| Projekte | /settings/projects | ✅ (3.1k) | ❌ | ✅ | hoch |
| Communication | /communication | ❌ | ❌ | ❌ | mittel |
| Teamchat | /teamchat | ❌ | ❌ | ❌ | mittel |
| Butler | /butler | ❌ | ❌ | ❌ | mittel |
| Zahnfee | /zahnfee | ❌ | ❌ | ❌ | niedrig (admin) |
| Skills | /skills | ❌ | ❌ | ❌ | mittel |
| MCP | /mcp | ✅ (3.9k) | ✅ | ✅ | hoch |
| Plugins | /plugins | ❌ | ❌ | ❌ | niedrig (admin) |
| VMs | /vms | ❌ | ❌ | ❌ | mittel |
| Container | /containers | ❌ | ❌ | ❌ | mittel |
| Federation | /federation | ❌ | ❌ | ❌ | niedrig |
| Streaming | /streaming | ❌ | ❌ | ❌ | niedrig |
| Datamining | /datamining | ❌ | ❌ | ❌ | mittel |
| Memory | /memory | ❌ | ❌ | ❌ | mittel |
| System | /settings → System | ✅ (2.3k) | ✅ | ✅ | hoch |
| LLM | /settings → LLM | ✅ (3.3k) | ✅ | ✅ | hoch |
| Hilfe/Handbuch | /help | (Meta) | — | — | — |

## Settings-Hub (Zahnrad → /settings, keine eigenen Nav-Items)
| Bereich | Artikel | Prio |
|---------|---------|------|
| Credentials | ❌ | hoch (Keys/Secrets — kritisch für Einstieg) |
| Extensions | ❌ | niedrig |
| Module (Verwaltung) | ❌ | mittel |
| Benutzer/Users | ❌ | mittel |
| Einstellungen (Mail, SearXNG, …) | ❌ | mittel |

## Module (frontend/src/modules/*)
| Modul | Pfad | Artikel | Prio |
|-------|------|---------|------|
| Atelier | /atelier | ❌ | mittel (groß, viel Erklärbedarf) |
| Patientenakte | /akte | ❌ | mittel |
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

## Zusammenfassung
- **49 Bereiche** (34 Features + 15 Module), aber nur **7 Artikel** und **5 HelpButtons**.
- Loader kennt nur **7 Topics** → technische Erweiterung nötig, bevor neue Artikel greifen.
- Bestehende Artikel sind teils **zu dünn** (Dashboard 1.4k) → im Deep-Dive überarbeiten.

## Fahrplan
1. **Loader + HelpTopic-Typ** auf alle Topics erweitern (sonst 404 für neue Artikel).
2. **Onboarding-Artikel** „Erste Schritte" — roter Faden für neue User.
3. **Sehr hoch + hoch**: Buddy, Werkstatt, Agenten, Projekte, LLM, Credentials, Dashboard, MCP, System (überarbeiten/neu).
4. **Mittel**: Communication, Teamchat, Butler, Skills, Datamining, Memory, VMs, Container, Module-Verwaltung, Users, Atelier, Akte.
5. **Niedrig**: Rest.
6. **HelpButton** überall nachrüsten.
7. **Phase 3**: Feld-Tooltips an unklaren Eingabefeldern.
