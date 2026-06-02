# Feature Map: Voice — STT, TTS, Voice-Mode

> **Modul:** `core/src/hydrahive/voice/` + `frontend/src/features/chat/`  
> **Was:** Sprach-Eingabe (STT) und Sprach-Ausgabe (TTS) im Chat. Voice-Mode für Hands-Free-Betrieb.  
> **Warum:** Freisprechmodus — ohne Tastatur mit dem Agenten reden.

---

## STT — Speech-to-Text (Eingabe)

```
Frontend:
  useVoiceInput.ts:
    → MediaRecorder (Browser-API)
    → Mikrofon aufnehmen → WebM/Opus
    → POST /api/voice/transcribe {audio: Blob}
    → Text in MessageInput einfügen

Backend:
  api/routes/voice.py:
    → Audio-Datei temporär speichern
    → tools/transcribe_audio.py → Whisper
    → {text: "..."} zurück
```

---

## TTS — Text-to-Speech (Ausgabe)

```
Frontend:
  useVoiceOutput.ts:
    → Wenn Voice-Mode aktiv: nach jeder Antwort
    → POST /api/voice/tts {text: "...", voice: "nova"}
    → Audio-URL zurück
    → HTML5 Audio Player → abspielen

Backend:
  api/routes/voice.py:
    → tools/generate_speech.py
    → MP3 generieren + speichern
    → {url: "/files/generated/<uuid>.mp3"} zurück
```

---

## Voice-Mode

Voice-Mode = durchgehender STT+TTS-Betrieb:
```
User spricht → STT → Text → Agent → TTS → Antwort
     ↑_____________________________________________|
              Hands-free loop
```

Aktivierung: Mikrofon-Button im Chat halten = Voice-Mode an.
Deaktivierung: erneuter Klick oder Tastendruck.

---

## Backend-Dateien

| Datei | Verantwortung |
|---|---|
| `voice/__init__.py` | Voice-Modul-Init |
| `api/routes/voice.py` | Endpoints: `/api/voice/transcribe`, `/api/voice/tts` |
| `tools/transcribe_audio.py` | STT-Tool (Whisper) |
| `tools/generate_speech.py` | TTS-Tool |

---

## Frontend-Dateien

| Datei | Verantwortung |
|---|---|
| `chat/useVoiceInput.ts` | STT-Hook: Aufnehmen, Transcribe, in Input einfügen |
| `chat/useVoiceOutput.ts` | TTS-Hook: Text → Audio, Abspielen |
| `chat/MessageInput.tsx` | Mikrofon-Button (hält STT an, aktiviert Voice-Mode) |

---

## Voice-Mode-Hint als System-Prompt

Wenn Voice-Mode aktiv: `extra_system`-Block wird an Runner übergeben:
```
[Voice Mode Active]
Du antwortest jetzt als Sprachausgabe. Halte Antworten kurz und 
natürlich klingend. Keine Markdown-Formatierung, keine langen Listen.
```

Dieser Block geht als `extra_system` rein (NICHT als User-Message),
damit Agents ihn nicht als Prompt-Injection missdeuten.

---

## Buddy-Konfiguration

Buddies haben Voice-Settings:
```json
{
  "voice_enabled": true,
  "voice_model": "openai/tts-1",
  "voice_name": "nova",
  "voice_auto_play": true,   // Antworten automatisch abspielen
  "voice_wakeword": "Hey Seven" // geplant
}
```

---

## Verwandte Subsysteme

- **→ Multimodal** (`27-multimodal.md`): `generate_speech`, `transcribe_audio` Tools
- **→ Buddy** (`09-buddy.md`): Buddy-Voice-Settings
- **→ Chat UI** (`19-frontend-chat.md`): Voice-Buttons im MessageInput
