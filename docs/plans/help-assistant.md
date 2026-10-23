# Plan: Hilfe-Assistent (Knopf unten rechts, Handbuch, Navigation)

Status: **ENTWURF – zur Freigabe.** Task 696d0823. Till 23.10.2026: „so können wir das machen“.

## Ziel

Auf jeder Seite des Cockpits gibt es unten rechts einen **Hilfe-Knopf**. Ein Klick öffnet ein kleines Chat-Fenster
mit einem **Hilfe-Assistenten**. Das Fenster bleibt beim Seitenwechsel offen, und der Verlauf bleibt erhalten.
Der Assistent kennt das ganze Handbuch, weiß, auf welcher Seite der Nutzer gerade ist, und kann Seiten öffnen
(„Ich bringe dich hin“). Vorbild: der Supportassistent aus HydraHive1.

## Was es schon gibt (wird genutzt, nicht neu gebaut)

| Baustein | Wo |
|---|---|
| Handbuch: 41 Hilfe-Artikel DE + EN (~190 KB) | `frontend/src/i18n/help/<lang>/<topic>.md`, Topics in `help/loader.ts` |
| Benutzerhandbuch (26 KB) | `docs/USER_GUIDE.md` |
| Eigener Agent pro Nutzer mit fester Sitzung | Vorlage Buddy: `core/src/hydrahive/buddy/__init__.py` (`is_buddy`) |
| Chat mit Streaming, Werkzeug-Aufrufe im Stream (`tool_use_start`) | `frontend/src/features/chat/_chatStream.ts` |
| Seitenliste mit Rollen | `frontend/src/shared/nav-config.ts` (`NAV_ITEMS`, `roles`) |
| Schwebendes Fenster unten rechts (Vorlage) | `frontend/src/features/cockpit/MediaAgentPopup.tsx` |
| Äußerer Rahmen, der beim Seitenwechsel bleibt | `frontend/src/shared/layouts/SidebarLayout.tsx` / `TopnavLayout.tsx` |

## Kernentscheidungen

1. **Eigener Agent, nicht Buddy.** Pro Nutzer ein Agent mit Marker `is_help=True` (wie `is_buddy`), eigene
   Lifetime-Sitzung. Er taucht nicht in der Agentenliste auf und ist nicht „primärer“ Agent.
2. **Nur harmlose Werkzeuge:** `help_search` (Handbuch durchsuchen), `help_read` (Artikel lesen), `open_page`
   (Seite öffnen, Etappe 2). Kein Terminal, keine Dateien, kein Web, kein Gedächtnis-Schreiben. Agenten-Tools werden
   beim Anlegen fest auf diese Liste gesetzt.
3. **Modell:** das Standard-Modell aus den LLM-Einstellungen (`default_model`). **Ist keins eingerichtet**, zeigt das
   Fenster statt des Chats einen Hinweis „Für den Hilfe-Assistenten erst eine KI einrichten“ mit Knopf zu `/llm`.
   Kein stiller Rückgriff auf ein fest eingebautes Modell (Buddy macht das heute mit `claude-sonnet-4-6` – das wird
   hier bewusst nicht übernommen).
4. **Handbuch im Backend lesbar:** Die Hilfe-Artikel liegen heute nur im Frontend-Quellcode. Das Backend liest sie
   direkt aus `$HH_REPO_DIR/frontend/src/i18n/help/` und `docs/USER_GUIDE.md` (beides ist auf jeder Installation da,
   weil das Repo komplett geklont wird). Sprache des Nutzers zuerst, sonst Deutsch, sonst Englisch – wie `loadHelp`.
5. **Suche ohne Embeddings:** `help_search` ist eine einfache Wortsuche über Überschriften und Absätze (Treffer mit
   Topic, Überschrift, Auszug). Funktioniert also auch ohne Embedding-Modell (siehe Befund Gedächtnis 23.10.).
6. **Aktuelle Seite als Kontext:** Jede Nachricht aus dem Fenster schickt den aktuellen Pfad mit (z. B.
   `/settings/agents`). Der Runner hängt ihn als kurze Zeile an („Der Nutzer ist gerade auf: …“), plus das passende
   Hilfe-Topic, wenn es eins gibt.
7. **Navigation nur auf erlaubte Seiten (Etappe 2):** `open_page(path)` akzeptiert nur Pfade aus einer festen Liste
   (Navigation + Einstellungs-Seiten + installierte Module). Admin-Seiten nur für Admins. Das Werkzeug selbst tut im
   Backend nichts außer prüfen und `{"open": path}` zurückgeben; die **Oberfläche** sieht den Aufruf im Stream und
   wechselt die Seite. Keine beliebigen URLs, keine externen Links.
8. **Fenster:** im Layout eingehängt (nicht in einzelnen Seiten) → bleibt beim Seitenwechsel offen. Zustand
   (offen/zu, Größe) im Browser gemerkt. Nicht auf der Anmeldeseite. Auf dem Handy als Vollbild-Blatt.

## Dateien

Backend
- `core/src/hydrahive/helpdesk/__init__.py` — `get_or_create_help_agent(username)` (Vorlage Buddy, `is_help`)
- `core/src/hydrahive/helpdesk/_manual.py` — Handbuch laden, Sprache, Wortsuche
- `core/src/hydrahive/helpdesk/_pages.py` — Liste erlaubter Seiten (mit Rollen)
- `core/src/hydrahive/tools/help_search.py`, `help_read.py`, `open_page.py` — die drei Werkzeuge
- `core/src/hydrahive/api/routes/helpdesk.py` — `GET /api/helpdesk/state` (Agent, Sitzung, `model_missing`)
- Runner: Seiten-Kontext für `is_help`-Agenten (kleine Ergänzung wie `_buddy_mode.py`)
- Agentenliste/primärer Agent: `is_help` ausblenden (`agents/primary.py`, Listen-API)

Frontend
- `frontend/src/features/helpdesk/HelpAssistant.tsx` — Knopf + Fenster
- `frontend/src/features/helpdesk/useHelpAssistant.ts` — Zustand, Sitzung, Senden mit aktuellem Pfad
- `frontend/src/features/helpdesk/_openPage.ts` — reagiert auf `open_page` im Stream (Etappe 2)
- Einhängen in `SidebarLayout.tsx` und `TopnavLayout.tsx`
- Texte DE/EN in `i18n/locales/{de,en}/helpdesk.json`, Hilfe-Artikel `help/{de,en}/helpdesk.md`

Tests
- `core/tests/test_helpdesk_agent.py`, `test_helpdesk_manual.py`, `test_helpdesk_tools.py`, `test_helpdesk_pages.py`
- `frontend/src/features/helpdesk/*.test.tsx`

## Etappen

### Etappe 1 – Fenster, Chat, Handbuch
1. Handbuch laden + Wortsuche (`_manual.py`) – Tests: Sprache, Rückfall, Treffer, kein Pfad-Ausbruch bei `help_read`.
2. Werkzeuge `help_search`, `help_read` – Tests: Ausgabe, unbekanntes Topic, Länge begrenzt.
3. Hilfe-Agent anlegen (`is_help`, feste Werkzeuge, Standard-Modell) – Tests: einmal pro Nutzer, Werkzeuge fest,
   `model_missing` wenn kein Standard-Modell, nicht in Agentenliste, nicht primär.
4. `GET /api/helpdesk/state` – Tests: Nutzer sieht nur den eigenen Agenten.
5. Seiten-Kontext im Runner – Test: Pfad landet im Prompt, nur bei `is_help`, Pfad wird gekürzt/gesäubert.
6. Frontend: Knopf + Fenster + Chat, im Layout – Tests: bleibt beim Seitenwechsel offen, Hinweis ohne Modell.

### Etappe 2 – Seiten öffnen
7. `_pages.py` + `open_page` – Tests: nur erlaubte Pfade, Admin-Seiten nur für Admins, unbekannt → Fehler mit Liste.
8. Frontend reagiert auf `open_page` im Stream – Test: Seite wechselt, Fenster bleibt offen, fremde Pfade ignoriert.

### Etappe 3 – Elemente hervorheben (eigener Plan)
`highlight(element)` über `data-help-id`-Markierungen an wichtigen Knöpfen/Feldern. Kommt erst, wenn 1+2 laufen.

## Akzeptanzkriterien

- [ ] Auf jeder Seite unten rechts ein Hilfe-Knopf; Klick öffnet das Fenster; Seitenwechsel lässt es offen samt Verlauf.
- [ ] Ohne Standard-Modell: Hinweis + Knopf zu `/llm`, kein Fehler.
- [ ] Frage „Wie lege ich einen Agenten an?“ → Antwort aus dem Handbuch, mit Nennung des Artikels.
- [ ] Auf `/containers` gefragt „was kann ich hier machen?“ → Antwort passt zur Seite.
- [ ] (Etappe 2) „Bring mich zu den KI-Einstellungen“ → Seite `/llm` öffnet sich, Fenster bleibt offen.
- [ ] Der Hilfe-Agent kann nichts außer lesen und Seiten öffnen (Werkzeugliste fest, Test).
- [ ] Linux und Mac gleich; Suite grün; Live-Test auf hydratest.

## Nicht in diesem Plan
- Elemente hervorheben (Etappe 3, eigener Plan).
- Bedeutungs-Suche im Handbuch (Embeddings) – Wortsuche reicht für ~190 KB.
- Hilfe-Assistent für Module, die eigene Hilfe-Artikel mitbringen (kommt, wenn Module Artikel liefern).
- Sprachein-/ausgabe im Hilfe-Fenster.
