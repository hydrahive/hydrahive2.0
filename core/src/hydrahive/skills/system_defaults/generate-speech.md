---
name: generate-speech
description: Text in gesprochene Sprache umwandeln (TTS) mit gpt-audio über das generate_speech-Tool — Stimmenwahl, Sprachen, typische Fehler.
when_to_use: Wenn der User Text vorgelesen haben will, eine Sprachausgabe, einen Voiceover, eine Audio-Ansage oder TTS möchte.
tools_required: [generate_speech]
---

# Sprache generieren mit gpt-audio

Das Tool `generate_speech` wandelt Text in gesprochene Sprache über OpenRouter (gpt-audio). Das Ergebnis erscheint direkt im Chat als Audio-Player (WAV).

## Stimmen

| Stimme | Charakter |
|--------|-----------|
| `alloy` (default) | neutral, ausgewogen |
| `echo` | ruhig, klar |
| `fable` | warm, erzählend |
| `onyx` | tief, markant |
| `nova` | hell, freundlich |
| `shimmer` | weich |

Wähl die Stimme nach Kontext — `onyx` für Ansagen, `fable` fürs Vorlesen, `alloy` wenn egal.

## Sprache

gpt-audio spricht **mehrsprachig** — einfach den Text in der Zielsprache übergeben. Der Text **ist** das, was gesprochen wird (keine Anweisung, sondern der Inhalt). Für Deutsch deutschen Text geben, für Englisch englischen.

## Ablauf

1. Text in der gewünschten Sprache zusammenstellen (das wird 1:1 gesprochen).
2. `generate_speech(text=..., voice=...)` aufrufen. `model` nur setzen wenn ein anderes als das zentral konfigurierte gewünscht ist.
3. Die Audiodatei wird gespeichert und im Chat angezeigt — kurz beschreiben was du erzeugt hast.

## Hinweise & Grenzen

- Nur der **Text** wird gesprochen — keine Lautschrift, keine SSML-Tags nötig.
- Längere Texte = längere Audios; bei sehr langem Text in sinnvolle Stücke teilen.
- Sagt das Tool **"bitte erneut versuchen"** (kein Audio / Stream vorzeitig beendet): seltene Provider-Flakiness, **einmal** unverändert erneut aufrufen. Zweimal hintereinander erfolglos: dem User melden.
- Andere API-Fehler (ungültiges Modell, Key fehlt): nicht wiederholen, dem User melden.
