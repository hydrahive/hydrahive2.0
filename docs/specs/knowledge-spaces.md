# Wissensräume für Agenten (E1/E2)

Stand 09.10.2026 · Task b17f9e38 · baut auf E0 (`docs/specs/datamining-access.md`, PR #528/#529) auf ·
Status: **freigegeben (Till, 09.10.)** – Fragen §4 beantwortet.

## 1. Ziel
Ein Admin legt fest, aus welchen **Projekten, Gruppen und Nutzern** ein Agent Wissen lesen darf, und wie
**sensibel** dieses Wissen sein darf. Beispiel Till:
- Familien-Agent: Wissen aller Mitglieder der Gruppe „Familie“ und ihrer Projekte, aber ohne Gesundheit.
- RoM-Agent (Git, Discord): nur das RoM-Projekt, nie privat, nie Gesundheit.
- Buddy: alles des eigenen Nutzers.

Heute (E0) gibt es dafür `knowledge_access {scope, projects, sensitive}` – nur per API, nur Projekte, nur
„sensibel ja/nein“, und die Sperre erkennt nur zwei Gesundheits-Werkzeuge.

## 2. Bausteine

### 2.1 Schutzstufe je Sitzung (E1)
Stufe hängt an der **Sitzung**, nicht an einzelnen Ereignissen (eine Sitzung über Gesundheit ist komplett
sensibel). Höchste Stufe aller in der Sitzung benutzten Werkzeuge gilt.

| Stufe | Bedeutung | Werkzeuge |
|---|---|---|
| `normal` | Standard | – |
| `privat` | Persönliches (Finanzen, Mail) | `read_mail`, `send_mail`, `query_portfolio` (Cryptoboard). Haushaltsbuch: hat heute keine Agent-Werkzeuge (a7951f29) – meldet sich per Manifest, sobald es welche bekommt. Kurse/Analyse (`query_crypto_price/_analysis`) sind öffentlich → `normal`. |
| `gesundheit` | Akte, Health | `query_fhir_data`, `query_health_data` |

- **E1a – dynamisch, ohne neue Tabelle:** Bei jeder Suche bestimmt der Filter die Sitzungen je Stufe aus
  `events.tool_name` (Index `events_tool`). Gemessen 09.10.: 8 Sitzungen privat+gesundheit, 0,001 s. Kein
  Bestandslauf, keine Migration, nie veraltet.
- Liste Werkzeug → Stufe: Kern (`db/_mirror_scope.py`) + Modul-Manifest `"sensitive_tools": {"tool": "privat"}`,
  damit Module selbst melden. Unbekannte Stufe im Manifest → Modul-Fehler beim Laden.
- **E1b (später, bei Bedarf):** Tabelle `session_sensitivity` für Handarbeit (Admin/Nutzer stuft eine Sitzung
  hoch, nur Admin herab). Wird dann zusätzlich zur Werkzeug-Erkennung geprüft.
- Ersetzt die E0-Sperre (`sensitive`) durch Stufen.

### 2.2 Wissensraum je Agent (E2)
`knowledge_access` wird erweitert:
```json
{"scope": "project" | "user",
 "projects": ["<id>", ...],          // wie E0
 "groups": ["<gruppen-id>", ...],    // NEU: alle Nutzer der Gruppe + deren Projekte
 "max_level": "normal" | "privat" | "gesundheit"}   // ersetzt sensitive
```
- Nutzerfilter: eigener Nutzer **+ Mitglieder der Gruppen**. Andere Nutzer nur, wenn sie in einer Gruppe
  sind – kein „alle Nutzer“.
- **Von Gruppenmitgliedern nur Projekt-Sitzungen, nie ihre Buddy-Chats** (Sitzungen ohne Projekt bzw. von
  Master-Agenten). Entscheidung Till 09.10. Der eigene Buddy-Chat bleibt für `scope: user` sichtbar.
- Projekte: Projekt des Laufs + `projects` + Projekte, in denen ein Gruppenmitglied Mitglied ist (nur bei
  `scope: project`; bei `scope: user` alles der erlaubten Nutzer).
- Standard: Projekt/Spezialist `max_level: normal`; Buddy/Master `gesundheit` (nur eigener Nutzer).
- **Außenwirkung begrenzt die Stufe hart**: Hat ein Agent Werkzeuge mit Außenwirkung, gilt höchstens
  `normal`, egal was eingestellt ist. Liste im Kern: `discord_*` (schreibend), `send_mail`, `shell_exec`
  (kann git push/curl – Entscheidung Till 09.10.), `web_browser`, `fetch_url`/`plugin__http-tester__request`
  mit POST, Föderation (`ask_agent` an `…@server`). Die Oberfläche zeigt den Grund an.
  Ausnahme: Buddy/Master behalten ihre Stufe für den **eigenen** Nutzer (sie sind der Nutzer selbst);
  Gruppen-Wissen bekommen sie nur bis `normal`.
- `sensitive: true` aus E0 wird beim Lesen als `max_level: gesundheit` verstanden (keine Migration nötig).

### 2.3 Wo das Wissen gilt
Gleiche Sicht für: `datamining_*`-Werkzeuge (heute), Karten im Prompt (`top_cards_for`, heute nur eigener
Agent – bleibt Standard, Räume erweitern optional), später Kristalle (d666b036) und Auftrags-Wissen bei
`ask_agent` (3994f6b1 Hebel 3).

**Kartensuche (Recall C, `search_cards`)** – Nachtrag 09.10., Task ddb1ff35: filterte vorher nur nach Nutzer,
ein Projekt-Agent bekam per Ähnlichkeit auch Karten anderer Agenten (auch aus Buddy-Sitzungen mit
Gesundheits-/Privat-Werkzeugen). Regel jetzt (Till, 09.10.):
- **eigene Karten** des Agenten: immer (wie `top_cards_for`),
- **fremde Karten**: nur, wenn ihre Sitzung in der Sicht liegt (`_mirror_scope.where`),
- ohne Sicht und ohne Agent: keine Treffer, nie ungefiltert.
Die Vektorsuche läuft mit `hnsw.iterative_scan = relaxed_order` (nur in der Transaktion): ohne fielen bei
enger Sicht Treffer weg (gemessen 16 Agenten × 3 Fragen: 53 statt 93 Treffer, gleiche Laufzeit).

### 2.4 Oberfläche (E2)
Agent-Editor, Reiter „Werkzeuge“ unter dem Schalter Langzeitgedächtnis: Bereich **„Wissen“** (nur Admin):
Projekte wählen, Gruppen wählen, Stufe wählen; Hinweis „wegen Discord/Shell höchstens normal“; Zähler
„sieht ca. N Einträge“ (Count über die Sicht, gecacht).

## 3. Etappen
- **E1a** Schutzstufe dynamisch: Werkzeug→Stufe-Liste (Kern + Manifest `sensitive_tools`), Filter in
  `_mirror_scope` auf Stufen (`max_level`), `sensitive` aus E0 weiter verstanden. Messen gegen echte DB.
- **E1b** (bei Bedarf) Tabelle für Hand-Hochstufung.
- **E2a** `groups` + `max_level` + Außenwirkungs-Grenze in `_mirror_scope`, Prüfung, Tests.
- **E2b** Oberfläche im Agent-Editor + Zähler.
- **E3** Kristalle/Karten/Auftrags-Wissen nutzen dieselbe Sicht (eigene Specs).

## 4. Entscheidungen (Till, 09.10.)
1. `privat` = Haushaltsbuch, Mail, Cryptoboard (Portfolio) – „reicht erst mal“.
2. Familien-/Gruppen-Wissen **ohne Buddy-Chats** der Mitglieder, nur deren Projekte.
3. `shell_exec` zählt als Außenwirkung.
