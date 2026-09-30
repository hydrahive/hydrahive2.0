# Agent-Editor: Modellauswahl ohne Limit, nach Anbieter gruppiert

Task 19687316. Freigabe Till am 30.09.2026: kein Limit, Gruppen, Anbieter-Filter.

## Befund (30.09.2026, live über die API, nur lesend)

- `GET /api/llm/models?modality=chat` liefert 694 Modelle: openrouter 465, openai 128,
  nvidia 73, openai-codex 14, anthropic 13, ollama 1.
- Der Picker für das Hauptmodell im Agent-Editor (`features/agents/_ModelTab.tsx`) schneidet
  seit 8514fc30 (31.05.2026) nach dem Filtern bei 100 Einträgen ab. Ohne Suche fehlen
  OpenRouter und OpenAI-Codex ganz, von OpenAI sind 13 von 128 sichtbar.
- Die anderen Modell-Picker (Chat, Zahnfee, Buddy, Standard-Modelle, Fallback-Auswahl)
  haben kein Limit und sind nicht betroffen.

## Änderung

- Neue reine Funktion `groupModels(catalog, { query, onlyFree, provider })` in
  `features/agents/_modelGroups.ts`:
  - filtert nach Suche (id und Label, ohne Groß/klein), „nur gratis“ und Anbieter,
  - gruppiert nach `provider`, Gruppen alphabetisch nach Anzeigename, Modelle nach id,
  - hat **kein** Limit.
  - `providersOf(catalog)` liefert die Anbieter mit Anzahl für den Filter.
- `providerName` wandert aus `llm/ModelSelect.tsx` nach `llm/_llm_providers.ts` und wird
  in beiden Pickern genutzt.
- Picker im Agent-Editor:
  - Suchfeld, Anbieter-Filter (Dropdown „Alle Anbieter“ + je Anbieter mit Anzahl), „nur gratis“.
  - Liste mit `<optgroup>` je Anbieter.
  - Trefferzahl („123 von 694 Modellen“) statt des alten Hinweises „max 100 angezeigt“.
  - Das aktuell gespeicherte Modell bleibt als „(aktuell)“ wählbar, auch wenn es herausgefiltert ist.
- Texte über i18n (`agents.json`, de/en).

## Tests (vitest)

- Ohne Filter ist aus jedem Anbieter mindestens ein Modell enthalten, auch bei mehr als
  100 Modellen vor dem letzten Anbieter.
- Summe der Gruppen = Anzahl der Modelle (nichts fällt weg).
- Suche, „nur gratis“ und Anbieter-Filter wirken, auch kombiniert.
- Reihenfolge der Gruppen nach Anzeigename.
- `providersOf` zählt richtig.
