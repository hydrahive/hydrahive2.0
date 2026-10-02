# Buddy: frühere Unterhaltungen wieder aufrufen

Stand: 02.10.2026 · Task 67d4fd30

## 1. Ausgangslage

Till: „Buddy braucht eine Sessionauswahl der vergangenen Sessions … zur Zeit
verschwinden sie bei Neuer Chat im Nirvana.“

Geprüft: Nichts geht verloren. „Neuer Chat“ (`POST /api/buddy/clear`) legt eine
neue Sitzung an, die alte bleibt in der Datenbank. Till hat 78 Buddy-Sitzungen seit
15.05.2026. Es fehlt nur eine Oberfläche, um sie wieder zu öffnen.

Alle Web-Sitzungen heißen gleich („till's Buddy“). Zwei sind sehr groß
(5.525 bzw. 4.749 Nachrichten).

## 2. Wünsche (Till)

- Beim Öffnen immer **am Ende** starten.
- Name = **erste Nachricht** des Nutzers, dazu **Datum**.

## 3. Zwei Fehler, die beim Prüfen aufgefallen sind

Beide stecken in der Auswahl „welche Sitzung zeigt Buddy?“
(`buddy._get_or_create_session`) und müssen mit der Auswahl ohnehin angefasst werden.

**F1 — Kanal-Sitzungen landen im Web-Chat.** Die Auswahl nimmt die jüngste Sitzung
des Buddy-Agenten nach `created_at` — **ohne** die Kanal-Sitzungen (WhatsApp,
Discord, Matrix, Voice) auszuschließen. Bei Till gibt es 6 davon. Schreibt jemand
Buddy erstmals über WhatsApp an, ist ab dann diese WhatsApp-Unterhaltung die
„jüngste“ und erscheint im Web-Chat; was Till im Web schreibt, landet in dieser
Unterhaltung.

**F2 — Buddy verliert seine Sitzung bei vielen anderen Sitzungen.** Die Auswahl
liest `sessions_db.list_for_user(username)`, das nur die **50 zuletzt geänderten**
Sitzungen des Nutzers liefert (Projekte, Automatik, Butler eingeschlossen). Liegt die
Buddy-Sitzung weiter hinten, findet Buddy sie nicht und legt still eine **neue leere**
an. Bei Till gibt es 10 leere Buddy-Sitzungen ohne „Neuer Chat“ davor (Juni/Juli) —
passt zu diesem Muster. Gleiches Problem in `new_session_keeping_project` (übernimmt
dann Projekt/Tiefe/Modus nicht).

## 4. Lösung

### Backend

Neue Abfrage `sessions_db.list_web_for_agent(agent_id, user_id, limit, offset)`:
nur Sitzungen ohne Kanal (`channel` leer/NULL), sortiert nach `updated_at` absteigend,
direkt per SQL gefiltert (kein 50er-Fenster über alle Sitzungen).

`buddy._get_or_create_session` und `new_session_keeping_project` nutzen
eine gemeinsame Funktion „aktuelle Web-Sitzung“: zuerst die **gemerkte** Sitzung
(siehe unten), sonst die jüngste Web-Sitzung nach `created_at`. Behebt F1 und F2.

**Gemerkte Sitzung:** Wählt Till eine frühere Unterhaltung, wird ihre ID im
Agent-Memory des Buddy unter `_active_session` gespeichert (wie `_pref_language`).
`/state`, Senden, Projekt-/Tiefe-Wechsel arbeiten dann mit ihr. „Neuer Chat“ legt eine
neue Sitzung an und merkt sich diese. Ungültige gemerkte IDs (gelöscht, fremder Nutzer,
anderer Agent, Kanal-Sitzung) werden ignoriert und gelöscht.

Endpunkte (`/api/buddy`):
- `GET /sessions?offset=0&limit=30` → `{sessions: [{id, created_at, updated_at,
  first_message, message_count, project_id}], active_id, has_more}`
  - `first_message`: erste **echte** Nutzernachricht: Text-Teil, Befehle (`/…`) und
    Werkzeug-Ergebnisse übersprungen, auf 80 Zeichen gekürzt, Leerraum vereinheitlicht.
    Keine Nutzernachricht → `null` (Anzeige „(noch leer)“).
  - Nur eigene Web-Sitzungen des eigenen Buddy.
- `POST /sessions/{id}/open` → setzt die gemerkte Sitzung, liefert den neuen `/state`.
  404, wenn die Sitzung nicht dem Nutzer gehört, nicht zum Buddy gehört oder ein Kanal ist.
  409, wenn gerade ein Lauf in der aktuellen Sitzung aktiv ist (kein Wechsel mitten im Lauf).

### Frontend

- Im Kopf des Buddy-Chats ersetzt eine Auswahl die bisherige Anzeige
  „Session: 01a0fd92-0209…“: Knopf mit Datum + Anfang der ersten Nachricht der
  aktuellen Unterhaltung, Klick öffnet eine Liste.
- Liste: jüngste zuerst, je Zeile erste Nachricht (gekürzt) + Datum + Anzahl
  Nachrichten; aktuelle markiert; „Weitere laden“ nach 30.
- Wechsel: lädt wie heute nur das Ende (die letzten 400 Nachrichten, `useChat`) →
  große Sitzungen öffnen schnell, Ansicht steht am Ende.
- Während ein Lauf aktiv ist, ist die Auswahl gesperrt.

## 5. Bewusst nicht Teil

- Umbenennen, Löschen, Suchen in der Buddy-Liste (Löschen gibt es im Chat-Bereich).
- Titel automatisch per LLM erzeugen.
- Bessere Titel im Projekt-Chat (Till: „gruselig“) — eigener Punkt, gleiche Vorschau
  ließe sich dort wiederverwenden.

## 6. Tests

Backend (`core/tests/test_buddy_session_picker.py`):
- Liste: nur eigene Web-Sitzungen des Buddy, jüngste zuerst; Kanal-Sitzung, fremder
  Nutzer, anderer Agent nicht enthalten; Anzahl; Seiten (offset/has_more).
- `first_message`: Text aus Block-Liste, Befehl übersprungen, Werkzeug-Ergebnis
  übersprungen, gekürzt, leer → None.
- F1: neueste Sitzung ist eine WhatsApp-Sitzung → `/state` zeigt trotzdem die Web-Sitzung.
- F2: 60 neuere Projekt-Sitzungen → `/state` findet die Buddy-Sitzung, legt keine neue an.
- Öffnen: setzt gemerkte Sitzung, `/state` liefert sie; fremde/Kanal/unbekannte → 404;
  aktiver Lauf → 409.
- „Neuer Chat“ nach dem Öffnen einer alten → neue Sitzung, übernimmt Einstellungen der
  geöffneten, wird gemerkt.
- Gemerkte Sitzung gelöscht → Rückfall auf jüngste, Merker entfernt.

Frontend: tsc, eslint, Vertragstest der Komponente (Quelltext), Browser auf hydratest.
