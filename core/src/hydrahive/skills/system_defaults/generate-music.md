---
name: generate-music
description: Musik mit Lyria 3 über das generate_music-Tool erzeugen — gutes Prompting, Modellwahl, typische Fehler.
when_to_use: Wenn der User Musik, einen Song, einen Soundtrack, Hintergrundmusik oder ein Audio-Stück generieren möchte.
tools_required: [generate_music]
---

# Musik generieren mit Lyria 3

Das Tool `generate_music` erzeugt Musik aus einem Text-Prompt über OpenRouter (Google Lyria 3). Das fertige Stück erscheint direkt im Chat als Audio-Player.

## Modellwahl

| Modell | Wofür |
|--------|-------|
| `google/lyria-3-pro-preview` (default) | Vollständige Stücke, höhere Qualität |
| `google/lyria-3-clip-preview` | Kurze Clips, schneller — für Ideen/Jingles |

Nimm `pro` wenn der User ein richtiges Stück will, `clip` für schnelle Skizzen oder kurze Loops.

## Prompting

**Auf Englisch promten** — Lyria versteht Englisch am besten. Beschreibe konkret:

- **Genre/Stil**: "lo-fi hip hop", "epic orchestral", "synthwave", "acoustic folk"
- **Stimmung**: "melancholic", "upbeat", "tense", "dreamy"
- **Instrumente**: "piano and strings", "808 drums, warm bass", "fingerpicked guitar"
- **Tempo/Energie**: "slow 70 BPM", "driving uptempo", "building crescendo"
- **Kontext** (optional): "for a meditation app", "boss fight music"

### Gute Prompts

```
warm lo-fi hip hop beat, mellow Rhodes piano, soft vinyl crackle, relaxed 80 BPM, study vibe
epic orchestral battle theme, soaring brass, pounding timpani, choir, building intensity
dreamy synthwave, analog pads, nostalgic lead melody, steady 100 BPM, retro 80s feel
```

### Schwache Prompts (vermeiden)

- "mach gute Musik" — kein Genre, keine Stimmung
- "ein Lied" — viel zu vage
- Songtexte/Lyrics — Lyria erzeugt **Instrumentalmusik**, keine gesungenen Texte

## Ablauf

1. Frag bei vagen Wünschen **einmal** nach (Genre + Stimmung reichen oft).
2. Übersetze den Wunsch in einen konkreten englischen Prompt.
3. Ruf `generate_music(prompt=..., model=...)` auf.
4. Das Stück wird gespeichert und im Chat angezeigt — beschreibe kurz was du erzeugt hast.

## Kosten & Grenzen

- Lyria 3 ist aktuell im **Preview kostenlos**.
- Generierung dauert spürbar (Streaming, ~10–60s) — nicht doppelt abschicken.
- Instrumental only, keine Vocals/Lyrics.
- Bei "Audio output requires stream" o.ä. Fehlern: das ist ein API-Problem, nicht dein Prompt — dem User melden, nicht blind wiederholen.
