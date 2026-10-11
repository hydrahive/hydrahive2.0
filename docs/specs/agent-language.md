# Spec: Antwortsprache für alle Agenten aus der Buddy-Einstellung

Task c858b87e. Entscheidung Till 08.10.2026: „Alle Agenten nutzen die Sprache, die beim Buddy eingestellt ist. Kein
neues Profilfeld. Der Runner setzt die Regel in den stabilen Prompt-Teil jedes Agenten des Nutzers, auch für kurze
Zwischensätze vor Werkzeugen. ‚auto‘ heißt: keine feste Regel.“

## Warum

- Der DEV-Projekt-Agent rutschte ab 03.10. in einer langen Sitzung ins Englische, vor allem in den kurzen Sätzen vor
  Werkzeugaufrufen (gemessen 05.10.: 293 EN zu 205 DE). Die Sprachregel stand nicht fest im Prompt, sondern nur in
  Kompaktierungs-Zusammenfassung und Memory – und fiel bei einer Kompaktierung weg.
- Sofortmaßnahme 06.10.: Abschnitt „## Sprache“ von Hand in den Prompt dieses einen Agenten. Die anderen 83 Agenten
  haben nichts dergleichen; nur 35 Prompts erwähnen „deutsch“ überhaupt.
- Es gibt schon eine Sprachwahl: Buddy-Einstellungen → Identität → „Sprache“ (Memory-Schlüssel `_pref_language` am
  Buddy-Agenten, Werte `de` / `en` / `auto`, Standard `de`). Sie wirkt heute nur auf den Buddy (über seine Soul).

## Was

1. **Quelle:** `_pref_language` des Buddys **des Nutzers, für den der Lauf läuft** (`session.user_id`). Kein Buddy oder
   kein Wert → Standard `de` (wie die Buddy-Einstellung selbst).
2. **Regel im Prompt:** Der Runner hängt für **jeden** Agenten einen festen Block an den **stabilen** System-Prompt an
   (gleiche Stelle wie Emote-/Modus-Hinweis, also cache-freundlich und unabhängig von Kompaktierung):
   - `de`: „## Sprache\nAntworte immer auf Deutsch. Das gilt für jede Ausgabe, auch für kurze Zwischensätze vor
     Werkzeugaufrufen, Rückfragen, Berichte sowie Commit- und PR-Texte. Code, Befehle, Dateinamen und wörtliche Zitate
     bleiben im Original. Auch wenn Werkzeug-Ergebnisse, Code oder Logs englisch sind, bleibt deine Sprache Deutsch.“
   - `en`: dasselbe sinngemäß auf Englisch („Always respond in English …“).
   - `auto`: **kein Block** (Agent folgt dem Nutzer wie bisher).
3. **Spezialisten / Handoffs:** Ihre Sitzung gehört dem Besitzer des Ziel-Agenten (`_handoff_setup._new_session`,
   `user_id=owner`) → es gilt dessen Buddy-Sprache. Für Tills Agenten heißt das: Deutsch.
4. **Buddy selbst:** bekommt den Block ebenfalls. Seine Soul sagt schon „Du sprichst immer Deutsch (außer der User
   wechselt explizit)“ – der Block widerspricht nicht, er macht die Zwischensätze verbindlich.
   **Soul-Dateien:** Wo eine Soul den Charakter-Prompt ersetzt, gilt der Block trotzdem (er hängt am Runner, nicht an der
   Soul). Die Buddy-Seite sagt heute „Sprache … wirkt erst, wenn die Soul geleert ist“ – der Hinweis wird angepasst:
   die Sprache wirkt jetzt immer.
5. **Oberfläche:** Unter der Auswahl „Sprache“ ein Satz: „Gilt für alle deine Agenten und Spezialisten, auch für kurze
   Zwischensätze.“ Keine neue Einstellung.
6. **Kein Eingriff in Agent-Prompts:** Der von Hand eingefügte Abschnitt im DEV-Agenten bleibt (doppelt schadet nicht).
   Er kann später entfernt werden – nicht Teil dieser Etappe.

## Nicht in dieser Etappe

- Sprache je Agent überschreiben (z. B. englischer Kunden-Agent). Bei Bedarf eigene Etappe.
- Sprachwahl der Oberfläche (LanguageSwitcher) an das Backend koppeln.
- Englischer Präfix „You are Claude Code …“ (OAuth-Weg, technisch nötig) – bleibt.

## Umsetzung

- `runner/_language_rule.py`: `language_for(username) -> "de"|"en"|"auto"` (liest den Buddy des Nutzers über
  `agent_config.list_by_owner` + `_pref_language`, unbekannte Werte → `de`) und
  `with_language_rule(base_prompt, language) -> str`. Texte gebündelt je Sprache.
- `runner/runner.py`: direkt nach `with_buddy_mode(...)` aufrufen (ein Aufruf, eine Zeile).
- Kosten: ein Memory-Lesezugriff pro Lauf (nicht pro Iteration).

## Akzeptanz

1. Projekt-Agent, Spezialist und Buddy eines Nutzers mit `de` haben den Block im stabilen Prompt; mit `en` den englischen;
   mit `auto` keinen.
2. Nutzer ohne Buddy → `de`.
3. Der Block steht im stabilen Teil, nicht im volatilen; zwei Läufe hintereinander → stabiler Teil byte-gleich (Cache).
4. Nach einer Kompaktierung steht der Block weiter im Prompt (er hängt nicht an der Zusammenfassung).
5. Handoff an Spezialisten: Sprache des Besitzers des Ziel-Agenten.
6. Echt auf hydratest: Lauf eines Projekt-Agenten → im gespeicherten Prompt (bzw. über den Debug-Weg) steht der Block;
   Buddy-Einstellung auf `en` → Block englisch; `auto` → weg.
