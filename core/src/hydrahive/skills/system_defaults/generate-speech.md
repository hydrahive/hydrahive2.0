---
name: generate-speech
description: Text in gesprochene Sprache umwandeln (TTS) über das generate_speech-Tool — Stimmenwahl, Sprachen, typische Fehler.
when_to_use: Wenn der User Text vorgelesen haben will, eine Sprachausgabe, einen Voiceover, eine Audio-Ansage oder TTS möchte.
tools_required: [generate_speech]
---

# Sprache generieren (TTS)

Das Tool `generate_speech` liest Text **wortwörtlich** vor (echtes TTS über OpenRouters `/audio/speech`). Das Ergebnis erscheint im Chat als Audio-Player.

Der `text` ist genau das, was gesprochen wird — **keine** Anweisung, **keine** Frage. Das Modell antwortet nicht, es liest vor.

## Modell & Stimme

- Das **Modell** ist zentral konfiguriert (LLM-Seite → Media-Modelle → TTS). Du musst es normalerweise nicht angeben.
- Die **Stimme** ist modellabhängig (z.B. kokoro: `af_bella`/`am_adam`; OpenAI-TTS: `alloy`/`nova`/`onyx`/…). Ohne `voice` nimmt das Tool die Standard-Stimme des Modells.
- Gibst du eine Stimme an, die das Modell nicht kennt, **korrigiert das Tool automatisch** auf die Standard-Stimme und sagt es im Ergebnis — kein Fehler. Trotzdem besser eine zum Modell passende Stimme wählen.

## Sprache

Die meisten Modelle sind mehrsprachig — gib den Text einfach in der Zielsprache (deutscher Text → deutsche Aussprache).

## Ablauf

1. Den vorzulesenden Text in der gewünschten Sprache zusammenstellen.
2. `generate_speech(text=...)` aufrufen — `voice` nur wenn gewünscht, `model` nur um den zentralen Default zu übergehen.
3. Die Audiodatei wird gespeichert und im Chat angezeigt — kurz beschreiben was du erzeugt hast.

## Hinweise & Grenzen

- Nur der **Text** wird gesprochen — keine SSML-Tags nötig.
- Längere Texte = längere Audios; sehr langen Text in Stücke teilen.
- „bitte erneut versuchen" (kein Audio): seltene Flakiness, **einmal** erneut. Zweimal erfolglos → dem User melden.
- „Keine Standard-Stimme gefunden": eine `voice` explizit angeben.
- **API-Fehler 404/500** (z.B. Gemini-TTS, Grok-Voice): das Modell ist providerseitig gerade nicht verfügbar — nicht dein Fehler. Ein anderes TTS-Modell wählen (kokoro-82m und gpt-4o-mini-tts laufen zuverlässig) oder dem User melden.
- Andere API-Fehler (ungültiges Modell, Key fehlt): nicht wiederholen, dem User melden.
