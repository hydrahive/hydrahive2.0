# Voice (TTS/STT)

Das Voice-Subsystem deckt zwei Richtungen ab: **STT** (Speech-to-Text, eingehende Sprache → Text) und **TTS** (Text-to-Speech, Text → gesprochene Audio). Es wird von drei Konsumenten genutzt: dem Web-Frontend (Mikrofon-Aufnahme + Vorlese-Button), dem WhatsApp-Adapter (Sprachnachrichten verstehen + als Voice-Note antworten) und dem Discord-Adapter (Voice-Antwort). Zusätzlich gibt es zwei **agenten-facing Tools** (`generate_speech`, `transcribe_audio`), die NICHT über das lokale Voice-Subsystem laufen, sondern über OpenRouter — diese sind hier zur Abgrenzung mit dokumentiert.

Architektur-Kern: `core/src/hydrahive/voice/` ist die einzige Stelle, die das `mmx`-CLI als Subprozess startet und die Wyoming-Container (STT Port 10300, TTS Port 10200) anspricht. Die HTTP-Routen (`api/routes/tts.py`, `api/routes/stt.py`) sind dünne Wrapper. Wyoming-Wire-Framing ist in einer Datei geteilt (`_wyoming.py`).

---

## WAS

### TTS-Provider (4 Stück, aus dem Frontend wählbar)

- **`browser`** — Web Speech API (`SpeechSynthesisUtterance`), rein clientseitig, kein Backend-Call, kein Key. Default-Provider. Quelle: `useVoiceOutput.ts`.
- **`minimax`** — Cloud-TTS über das `mmx`-CLI (MiniMax). Roh-MP3. Stimme z.B. `German_FriendlyMan`. Braucht installiertes `mmx`-CLI + ffmpeg + MiniMax-API-Key in `llm.json`.
- **`local`** — Lokales Piper-TTS über Wyoming (incus-Container Port 10200). Feste Container-Stimme (default `de_DE-thorsten-medium`), kein Cloud-Key. Gibt WAV zurück.
- **`openrouter`** — TTS über OpenRouter `/audio/speech` mit dem zentralen `media_models.tts`-Modell (Default `hexgrad/kokoro-82m`). Voice modellabhängig. Gibt WAV oder MP3 zurück. Braucht OpenRouter-Key.

### STT-Provider (1 Stück, fest verdrahtet)

- **Wyoming faster-whisper** (incus-Container Port 10300, Modell `small`). Einziger STT-Pfad für Frontend-Mikrofon UND WhatsApp-Sprachnachrichten. Auto-Language-Detect oder expliziter ISO-Code.

### API-Endpoints

- **`POST /api/tts`** — Synthese. Body `{text, voice, provider}`. Auth required. Daily-Quota-Gate. Routet je nach `provider` → `synthesize_local` / `synthesize_openrouter` / `synthesize_mp3`. Gibt rohe Audio-Bytes mit passendem `media_type` zurück. (`api/routes/tts.py:59`)
- **`GET /api/tts/voices`** — Stimmen-Liste. Query `language` (default `german`) + `provider` (default `minimax`). Für `openrouter` → `media_models.voices_for(tts-Modell)`; für `minimax` → `mmx speech voices`. Auth required. (`api/routes/tts.py:37`)
- **`POST /api/stt`** — Transkription. Multipart `audio`-File. Auth required. Liest Bytes, leitet MIME ab, ruft `transcribe_bytes`. Gibt `{text}` zurück. (`api/routes/stt.py:19`)

### Agenten-facing Tools (separater OpenRouter-Pfad, NICHT lokales Voice-Subsystem)

- **`generate_speech`** — TTS-Tool für Agenten. Wrapper um `_openrouter_media.synthesize_speech`. Speichert Audio in `ctx.workspace/generated/<uuid>.<ext>`, Chat zeigt Player. Kategorie `media`. (`core/src/hydrahive/tools/generate_speech.py`)
- **`transcribe_audio`** — STT-Tool für Agenten über OpenRouter (`_openrouter_transcribe.transcribe_file`), Modell aus `media_models["transcribe"]` (Default `openai/whisper-large-v3`). Explizit getrennt vom lokalen Wyoming-Container (Docstring: „Whisper über lokalen Wyoming-Container … dieses Tool ist für Agenten-Use-Cases"). (`core/src/hydrahive/tools/transcribe_audio.py`)

### Public-API-Funktionen des Voice-Moduls

- **`voice.tts.synthesize_mp3(text, voice)`** — Roh-MP3 von `mmx` (MiniMax). Für `/api/tts` ohne Konvertierung. (`voice/tts.py:51`)
- **`voice.tts.synthesize_local(text, voice)`** — Piper (Wyoming Port 10200) → `(wav_bytes, "audio/wav")`. (`voice/tts.py:86`)
- **`voice.tts.synthesize_openrouter(text, voice)`** — OpenRouter → `(audio_bytes, media_type)`. (`voice/tts.py:155`)
- **`voice.tts.synthesize_to_ogg(text, voice)`** — MP3 (via MiniMax) → OGG/Opus + Sekunden + Waveform als `VoiceClip` für WhatsApp/Discord-Voice-Notes. (`voice/tts.py:202`)
- **`voice.tts.list_voices(language)`** — Stimmen von `mmx speech voices` als JSON-Liste. (`voice/tts.py:175`)
- **`voice.tts.is_available()`** — `True` wenn `mmx` UND `ffmpeg` im PATH. (`voice/tts.py:36`)
- **`voice.stt.transcribe_bytes(audio, mime, language)`** — Public-STT-API: beliebiges Audio → 16kHz Mono PCM (via ffmpeg) → Wyoming → Text. (`voice/stt.py:94`)

### Frontend-Hooks & Komponenten

- **`useVoiceInput(onResult)`** — Mikrofon-Aufnahme-Hook. State `idle|recording|transcribing|error`, `toggle()`-Funktion. MediaRecorder → Blob → `/api/stt` → `onResult(text)`. (`useVoiceInput.ts:26`)
- **`useVoiceOutput()`** — Vorlese-Hook. `{speaking, error, speak, stop}`. Modul-Singleton (nur EIN aktives TTS app-weit). (`useVoiceOutput.ts:155`)
- **`MessageInput.tsx`** — Chat-Eingabefeld mit Mikrofon-Button (Mic/MicOff-Icon, Recording-Puls, Transcribing-amber). Transkript wird ans Textfeld angehängt. (`MessageInput.tsx:26`, Button `:98-111`)
- **`TTSSettings.tsx`** — Profil-Seite: Provider-Auswahl (4 Buttons) + Stimmen-Dropdown (für minimax/openrouter). Schreibt `localStorage`. Mount in `ProfilePage.tsx:56`. (`TTSSettings.tsx`)
- **`_WhatsAppVoiceSection.tsx`** — WhatsApp-Filter-Panel: STT-Sprache-Dropdown, „Antworten als Sprachnachricht"-Checkbox, MiniMax-Stimmen-Dropdown. Mount in `WhatsAppFilterPanel.tsx:110`. (`_WhatsAppVoiceSection.tsx`)
- **Vorlese-Buttons** (Volume2/VolumeX) in: `_ChatBubbleThread.tsx:149`, `_Thread.tsx:131`, `_BuddyThread.tsx:128`. Alle nutzen `tts.speaking ? tts.stop() : tts.speak(fullText)`.
- **`BuddyPage.tsx`** — Maskottchen-Animation reagiert auf TTS: `mascotState = tts.speaking ? "speaking" : chat.busy ? "working" : "idle"`. (`BuddyPage.tsx:37`)

### Config-Flags / Settings

- **`localStorage["hh_tts_provider"]`** (`TTS_PROVIDER_KEY`) — gewählter TTS-Provider im Frontend. (`useVoiceOutput.ts:6`)
- **`localStorage["hh_tts_voice"]`** (`TTS_VOICE_KEY`) — gewählte Stimme im Frontend, default `German_FriendlyMan`. (`useVoiceOutput.ts:7`)
- **WhatsAppConfig.`respond_as_voice`** (bool, default `False`) — Antwort als Voice-Note. (`whatsapp/config.py:28`)
- **WhatsAppConfig.`voice_name`** (str, default `German_FriendlyMan`) — MiniMax-Stimme für WA-Voice-Antwort. (`whatsapp/config.py:29`)
- **WhatsAppConfig.`stt_language`** (str, default `""`) — STT-Sprache eingehender WA-Voice; `""`/`auto` ⇒ Whisper-Auto-Detect. (`whatsapp/config.py:31`)
- **ENV `TTS_DAILY_CAP`** — Override des täglichen TTS-Limits (default 200). (`voice/_quota.py:51`)
- **ENV `HH_INSTALL_VOICE`** (`yes`/`no`) — Voice-Stack beim Install überspringen. (`installer/modules/55-voice.sh:18`)
- **ENV `HH_PIPER_VOICE`** — Piper-Container-Stimme (default `de_DE-thorsten-medium`). (`installer/modules/55-voice.sh:231`)

---

## WIE

### STT-Datenfluss (Frontend-Mikrofon)

1. User klickt Mic-Button in `MessageInput` → `voice.toggle()`.
2. **Recording-Start** (`useVoiceInput.ts:46-105`): Prüft `MediaRecorder`-Support + `window.isSecureContext` (Mikrofon braucht HTTPS/localhost). `getUserMedia({audio:true})`. `pickMime()` wählt ersten unterstützten MIME aus `PREFERRED_MIMES` (webm/opus → webm → mp4 → ogg/opus — iOS Safari kann nur mp4, Android bevorzugt webm). `recorder.start(250)` → `ondataavailable` alle 250ms (iOS feuert sonst evtl. nie). State → `recording`.
3. **Recording-Stop**: erneuter Klick → `requestData()` + `stop()`, State → `transcribing`. Safety-Timeout 1500ms falls `onstop` nicht feuert → manuell `transcribe()`.
4. **`transcribe()`** (`useVoiceInput.ts:107`): Chunks → Blob mit MIME-Typ. Datei-Endung abgeleitet (`m4a`/`ogg`/`webm`). FormData `audio` → `POST /api/stt` mit Bearer-Token. Bei Erfolg `onResult(text)`, State → `idle`. Bei Fehler State → `error` (2s, dann `idle`).
5. **Backend** (`api/routes/stt.py:19`): liest Bytes, leere Datei → 400. MIME aus `content_type` (split `;`). `transcribe_bytes(data, mime)`.
6. **`transcribe_bytes`** (`voice/stt.py:94`): `_to_pcm` (ffmpeg → 16kHz Mono s16le PCM, Timeout 30s) → `_wyoming_transcribe`.
7. **`_wyoming_transcribe`** (`voice/stt.py:33`): TCP-Connect `127.0.0.1:10300` (Connect-Timeout 15s cold-start). Wyoming-Sequenz: `transcribe` (mit/ohne language) → `audio-start` (rate 16000, width 2, channels 1) → `audio-chunk`* (1s-Chunks = 32000 Bytes) → `audio-stop`. Liest bis `transcript`-Event (gibt `text` strip zurück) oder `error` (RuntimeError). Total-Timeout 120s.
8. Fehler-Mapping in der Route: `ConnectionRefused/OSError` → 503, `TimeoutError` → 504, `RuntimeError` → 422.

### STT-Datenfluss (WhatsApp eingehend)

1. WA-Bridge POSTet `/api/communication/whatsapp/incoming` mit `media_type` (`audio`/`audio_failed`), `media_data` (base64), `media_mime`, `media_error`. (`communication_whatsapp_incoming.py:40`)
2. Rate-Limit + Bridge-Secret-Verify. Body-Validation: ohne `text` UND ohne Audio → 400. (`:46-64`)
3. **Pre-Filter** (`wa_filter.evaluate` mit `skip_keyword=True`) — VOR Transkription, um Audio gar nicht erst zu dekodieren wenn Sender geblockt. (`:69`)
4. **`process_voice`** (`_wa_voice.py:11`): `audio_failed` → freundliche Fehlermeldung („nochmal oder als Text"). `audio` + `media_data` → base64-decode → `transcribe_bytes(bytes, mime, language=stt_lang)`. `stt_lang` aus `cfg.stt_language` (außer `auto`/leer). Leeres Transkript → Fehlermeldung. Connect/OS/Timeout → Service-nicht-erreichbar-Meldung. Sonstige Exception → generische Fehlermeldung. Returns `(transcript|None, error_msg|None)`.
5. Bei `voice_error_msg`: Bridge sendet Fehlertext zurück, Response `{voice_error:True}`. (`:82-89`)
6. Bei Transkript: `text = transcript`. Dann **2. Filter-Durchlauf** mit echtem Text (Keyword-Check etc.). (`:90-97`)
7. `IncomingEvent` mit `voice_mode: cfg.respond_as_voice` in Metadata → `handle_incoming(event)` → `answer`.

### TTS-Datenfluss (Frontend Vorlesen)

1. Vorlese-Button → `tts.speak(fullText)` → `speakGlobal`. (`useVoiceOutput.ts:67`)
2. **`stopAll()` zuerst** — invalidiert laufende speaks (`speakRequestId++`), pausiert `activeAudio`, revoked Object-URL, cancelt `speechSynthesis`. Modul-Singleton: mehrere MessageBubbles teilen `activeAudio`/`activeAudioUrl` → nie doppelte Stimmen. (`:48`)
3. `provider = getTTSProvider()`. `myId = ++speakRequestId` (Race-Guard).
4. **provider ∈ {local, minimax, openrouter}** (`:73`): Bearer-Token. `voice = provider==="local" ? "" : getTTSVoice()` (Piper nutzt Container-Stimme). `POST /api/tts {text, voice, provider}`. Nach jedem `await` Race-Check `myId !== speakRequestId`. Response-Blob → ObjectURL → `new Audio` → `play()`. `onended`/`onerror` räumen auf + setzen `speaking=false`. `play()`-`AbortError` ist KEIN echter Fehler (Quelle während Start entfernt). KEIN Fallback auf Browser-TTS — „entweder/oder, nie beides". (`:122`)
5. **provider === browser** (`:126`): Voices-Loading-Race — nach Reload ist `getVoices()` oft leer → einmal auf `voiceschanged` warten (Fallback-Timeout 500ms). `SpeechSynthesisUtterance` mit lang `de-DE`, rate 1.0. `onstart/onend/onerror` setzen global `speaking` (mit `myId`-Guard).

### TTS-Backend-Routing (`/api/tts`)

1. **mmx-Gate** NUR für `minimax` (`local`/`openrouter` brauchen kein mmx). (`tts.py:65`)
2. **Quota** (`_quota.check_and_increment(username)`): bei `allowed=False` → 429, KEIN Subprozess-Start. (`tts.py:69`)
3. Routing nach `provider`: `local`→`synthesize_local`, `openrouter`→`synthesize_openrouter`, sonst (`minimax`)→`synthesize_mp3` (`audio/mpeg`). (`tts.py:77-83`)
4. **Fehler-Mapping** `_runtime_to_coded`: „timeout"→504, „fehlt"→503, sonst→502. Unerwartete Exception → 502 (nie rohes 500, weil TTS an externen Diensten hängt). (`tts.py:28`, `:86`)

### `synthesize_local` (Piper, Wyoming Port 10200)

- Spiegelbild von `_wyoming_transcribe`. TCP `127.0.0.1:10200`. (`voice/tts.py:86`)
- **Whitespace-Kollaps**: `" ".join(text.split())` — wyoming-piper splittet an `\n` in Segmente, leere Segmente (Absatz-Leerzeilen) → 0 Audio → Fehler „# channels not specified". Mehrzeilige Nachrichten brachen so. (`:104`)
- **Voice-Filter**: Voice nur weiterreichen wenn sie zum Piper-Muster `^[a-z]{2,3}_[A-Z]{2}-` passt (z.B. `de_DE-thorsten-medium`). Sonst Container-Default → verhindert 502 wenn Fremd-Voice (MiniMax `German_FriendlyMan`) durchschlägt. (`_PIPER_VOICE_RE`, `:83`, `:109`)
- Sequenz: `synthesize{text,voice?}` → `audio-start` (rate/channels) → `audio-chunk`* → `audio-stop`. Sammelt PCM → `pcm16_to_wav`. `error`-Event mit „channel" → freundliche Meldung „Text enthält nichts Vorlesbares". Connect-Timeout 15s, Total-Timeout 120s, `OSError` → RuntimeError „Piper nicht erreichbar".

### `synthesize_openrouter` + geteilter `synthesize_speech`

- `voice/tts.py:155` → `_openrouter_media.synthesize_speech(text, voice, model, key)`.
- **`synthesize_speech`** (`_openrouter_media.py:116`): `voices_for(model)` → Voice-Auflösung: angeforderte unbekannte Voice → `voices[0]` + `note`; leer → `voices[0]`. POST `/audio/speech` mit `response_format:"pcm"` (universell). Content-Type mpeg/mp3 → durchreichen als `mp3`; sonst PCM → `parse_pcm_content_type` (rate/channels aus Header) → `pcm16_to_wav` als `wav`. 120s-Timeout. Returns `(data, ext, voice_used, note)`.
- **GETEILT** mit Agenten-Tool `generate_speech` — eine Synthese-Stelle.

### TTS → WhatsApp Voice-Note (`synthesize_to_ogg` + Senden)

1. `handle_incoming` liefert `answer` → `send_voice_or_text`. (`_wa_voice.py:64`)
2. **Metadaten-Guard**: wenn `respond_as_voice` UND `_looks_like_metadata(answer)` (≥2 Regex-Treffer auf `.mp3`/`dauer`/`KB`/`sek`-Muster) → Antwort sieht wie Datei-Metadaten aus → Fallback auf Text, Return `True` (`voice_metadata_fallback`). (`communication_whatsapp_incoming.py:34`, `_wa_voice.py:75`)
3. **Voice-Pfad**: `synthesize_to_ogg(answer, voice_name)` → `VoiceClip`. `ch.send_audio(...)` mit base64-OGG + `seconds` + `waveform_b64`. Bei Exception → Text-Fallback. (`_wa_voice.py:84-103`)
4. **`synthesize_to_ogg`** (`voice/tts.py:202`): braucht ffmpeg. `synthesize_mp3` (MiniMax) → MP3 → ffmpeg `libopus 16kHz mono 32k` → OGG. `probe_seconds` (ffprobe) + `waveform_from_audio` (64-Byte RMS) → `VoiceClip`.
5. **`send_audio`** (`whatsapp/adapter.py:65`): POST an Bridge `/send/{username}` mit `audio_base64`, `seconds`, `waveform_base64`.
6. **Bridge** (`bridge/index.js:67`): `audio_base64` → Buffer, `seconds`/`waveform` als opts → `sendAudio(user, to, buf, opts)`. seconds+waveform sorgen dafür dass WhatsApp es als echte Voice-Note (Welle + Sekunden) rendert, nicht als Datei mit Download-Icon.

### Waveform-Algorithmus (`waveform_from_audio`)

- ffmpeg → 8kHz Mono s16le PCM. (`_audio_utils.py:32`)
- 64 Buckets: pro Bucket RMS = `sqrt(Σ s² / n)`, skaliert `min(100, int(rms/327.67))`. 64 Bytes je 0-100. Fehler/leer → `bytes(64)` (Nullen).

### Quota-Zustandsmaschine (`_quota.check_and_increment`)

- JSON `<data_dir>/.tts_quota.json`, pro User `{date, count}`. (`voice/_quota.py`)
- Reset bei Tageswechsel (ISO-Datum UTC). Unter Threading-Lock: lädt, vergleicht Datum (neu → count 0), `count >= cap` → `(False, used, cap)` OHNE Increment, sonst increment + atomarer Save (temp+rename) → `(True, used+1, cap)`.

---

## WO

### Voice-Modul (`core/src/hydrahive/voice/`)

- `voice/__init__.py:1` — Modul-Docstring (STT Wyoming-Whisper + TTS-Helpers).
- `voice/tts.py:29` — `@dataclass VoiceClip(ogg_bytes, seconds, waveform)`.
- `voice/tts.py:36` — `is_available()` (mmx + ffmpeg).
- `voice/tts.py:40` — `_mmx_key()` (aus `llm.json` via `llm_client._get_minimax_key`).
- `voice/tts.py:51` — `synthesize_mp3(text, voice)` — `mmx speech synthesize`, Timeout 60s.
- `voice/tts.py:80-83` — `PIPER_HOST/PIPER_PORT=10200`, `_PIPER_VOICE_RE`.
- `voice/tts.py:86` — `synthesize_local(text, voice)`.
- `voice/tts.py:155` — `synthesize_openrouter(text, voice)`.
- `voice/tts.py:175` — `list_voices(language)` — `mmx speech voices`, Timeout 15s.
- `voice/tts.py:202` — `synthesize_to_ogg(text, voice)` — MP3→OGG/Opus.
- `voice/stt.py:18-19` — `STT_HOST/STT_PORT=10300`.
- `voice/stt.py:21` — `_MIME_EXT`-Tabelle.
- `voice/stt.py:28` — `_normalize_mime(m)`.
- `voice/stt.py:33` — `_wyoming_transcribe(pcm, language)`.
- `voice/stt.py:70` — `_to_pcm(audio, mime)` (ffmpeg → 16kHz Mono s16le).
- `voice/stt.py:94` — `transcribe_bytes(audio, mime, language)` — Public API.
- `voice/_wyoming.py:12` — `send_event(writer, etype, data, payload)`.
- `voice/_wyoming.py:28` — `recv_event(reader)` → `(type, data, payload)`.
- `voice/_audio_utils.py:15` — `probe_seconds(path)` (ffprobe, default 1).
- `voice/_audio_utils.py:32` — `waveform_from_audio(path)` (64-Byte RMS).
- `voice/_quota.py:20` — `DEFAULT_DAILY_CAP=200`, `:21` `_LOCK`.
- `voice/_quota.py:24` — `_path()` (`<data_dir>/.tts_quota.json`).
- `voice/_quota.py:50` — `get_cap()` (ENV `TTS_DAILY_CAP`).
- `voice/_quota.py:58` — `check_and_increment(username)`.

### Routen

- `api/routes/tts.py:17` — Router-Prefix `/api/tts`.
- `api/routes/tts.py:19` — `DEFAULT_VOICE = "German_FriendlyMan"`.
- `api/routes/tts.py:22` — `SpeakIn` (text 1-10000, voice ≤80, provider ≤20, default `minimax`).
- `api/routes/tts.py:28` — `_runtime_to_coded(e)`.
- `api/routes/tts.py:37` — `GET /voices`.
- `api/routes/tts.py:59` — `POST ""` (`synthesize`).
- `api/routes/stt.py:16` — Router-Prefix `/api/stt`.
- `api/routes/stt.py:19` — `POST ""` (`transcribe`).
- `api/routes/_wa_voice.py:11` — `process_voice(...)`.
- `api/routes/_wa_voice.py:64` — `send_voice_or_text(...)`.
- `api/routes/communication_whatsapp_incoming.py:23` — `_METADATA_HINTS`-Regex.
- `api/routes/communication_whatsapp_incoming.py:34` — `_looks_like_metadata(answer)`.
- `api/routes/communication_whatsapp_incoming.py:40` — `POST /api/communication/whatsapp/incoming`.
- `api/routes/communication_whatsapp_incoming.py:76` — `process_voice`-Aufruf.
- `api/routes/communication_whatsapp_incoming.py:113` — `send_voice_or_text`-Aufruf.

### Router-Registrierung

- `api/main.py:52` — `from ...routes.stt import router as stt_router`.
- `api/main.py:58` — `from ...routes.tts import router as tts_router`.
- `api/main.py:126` — `app.include_router(stt_router)`.
- `api/main.py:127` — `app.include_router(tts_router)`.

### Key-Quellen & Media-Modelle

- `llm/client.py:49` — `_get_minimax_key(cfg)` → `get_provider_key(cfg, "minimax")`.
- `llm/_config.py:57` — `get_provider_key(config, provider_id)`.
- `llm/_config.py:64` — `openrouter_key()` (SSOT alle Media-Tools).
- `llm/media_models.py:32` — `DEFAULTS` (`tts: hexgrad/kokoro-82m`, `transcribe: openai/whisper-large-v3`).
- `llm/media_models.py:69` — `get_media_model(category)`.
- `llm/media_models.py:96` — `list_speech_models()` (Live TTS-Modelle + Voices, 5-Min-Cache).
- `llm/media_models.py:122` — `voices_for(model)`.
- `llm/media_models.py:130` — `first_voice(model)`.
- `llm/media_models.py:138` — `_TRANSCRIBE_FALLBACK`.
- `llm/media_models.py:145` — `list_transcribe_models()`.

### Geteilte OpenRouter-Media-Helfer

- `tools/_openrouter_media.py:93` — `pcm16_to_wav(pcm, sample_rate, channels)` (auch von `synthesize_local` genutzt!).
- `tools/_openrouter_media.py:104` — `parse_pcm_content_type(content_type)`.
- `tools/_openrouter_media.py:116` — `synthesize_speech(text, voice, model, key)`.
- `tools/_openrouter_media.py:85` — `save_bytes(raw, dest_dir, ext)`.

### Agenten-Tools

- `tools/generate_speech.py:74` — `TOOL` (name `generate_speech`, category `media`).
- `tools/transcribe_audio.py` — `transcribe_audio`-Tool (OpenRouter-Pfad, getrennt von Wyoming).
- `tools/_openrouter_transcribe.py` — `transcribe_file`, `openrouter_key`.

### WhatsApp-Config & Adapter

- `communication/whatsapp/config.py:20` — `@dataclass WhatsAppConfig`.
- `communication/whatsapp/config.py:28-31` — `respond_as_voice`, `voice_name`, `stt_language`.
- `communication/whatsapp/config.py:61-63` — Lese-Defaults.
- `communication/whatsapp/adapter.py:65` — `send_audio(username, to, audio_b64, *, seconds, waveform_b64)`.
- `communication/whatsapp/bridge/index.js:67-72` — Bridge-Audio-Send (`audio_base64`/`seconds`/`waveform_base64` → `sendAudio`).

### Discord-Adapter (Voice)

- `communication/discord/adapter.py:121` — `if current_cfg.respond_as_voice`.
- `communication/discord/adapter.py:123-126` — `synthesize_to_ogg` + `discord.File(io.BytesIO(clip), ...)` ← **BUG, siehe Offene Enden**.

### Frontend

- `frontend/src/features/chat/useVoiceInput.ts:8` — `PREFERRED_MIMES`.
- `frontend/src/features/chat/useVoiceInput.ts:16` — `pickMime()`.
- `frontend/src/features/chat/useVoiceInput.ts:26` — `useVoiceInput(onResult)`.
- `frontend/src/features/chat/useVoiceInput.ts:107` — `transcribe()`.
- `frontend/src/features/chat/useVoiceOutput.ts:4` — `type TTSProvider`.
- `frontend/src/features/chat/useVoiceOutput.ts:6-8` — `TTS_PROVIDER_KEY`, `TTS_VOICE_KEY`, `DEFAULT_VOICE`.
- `frontend/src/features/chat/useVoiceOutput.ts:10` — `getTTSProvider()`.
- `frontend/src/features/chat/useVoiceOutput.ts:15` — `getTTSVoice()`.
- `frontend/src/features/chat/useVoiceOutput.ts:21-26` — Modul-Singleton-State (`activeAudio`, `activeAudioUrl`, `speakRequestId`, `listeners`, `errorListeners`, `errorTimer`).
- `frontend/src/features/chat/useVoiceOutput.ts:39` — `ttsErrorMessage(res)`.
- `frontend/src/features/chat/useVoiceOutput.ts:48` — `stopAll()`.
- `frontend/src/features/chat/useVoiceOutput.ts:67` — `speakGlobal(text, lang)`.
- `frontend/src/features/chat/useVoiceOutput.ts:155` — `useVoiceOutput()`.
- `frontend/src/features/chat/MessageInput.tsx:26` — Hook-Verdrahtung.
- `frontend/src/features/chat/MessageInput.tsx:98-111` — Mic-Button.
- `frontend/src/features/profile/TTSSettings.tsx` — Provider/Voice-Settings UI.
- `frontend/src/features/profile/ProfilePage.tsx:56` — `<TTSSettings />`.
- `frontend/src/features/communication/_WhatsAppVoiceSection.tsx` — WA-Voice-Settings.
- `frontend/src/features/communication/WhatsAppFilterPanel.tsx:110` — `<WhatsAppVoiceSection />`.
- `frontend/src/features/chat/_ChatBubbleThread.tsx:149` — Vorlese-Button.
- `frontend/src/features/chat/_Thread.tsx:131` — Vorlese-Button.
- `frontend/src/features/buddy/_BuddyThread.tsx:128` — Vorlese-Button.
- `frontend/src/features/buddy/BuddyPage.tsx:36-37` — Maskottchen-`speaking`-State.

### Installer

- `installer/modules/55-voice.sh:23` — `CT_NAME="hydrahive2-stt"`, `:24` `STT_PORT=10300`.
- `installer/modules/55-voice.sh:30-34` — mmx-CLI-Install (npm-global).
- `installer/modules/55-voice.sh:38-62` — mmx-Auth aus `llm.json` (Provider `minimax`).
- `installer/modules/55-voice.sh:87` — `ensure_container_net` (br0 bevorzugt, NAT-Fallback).
- `installer/modules/55-voice.sh:144` — Wyoming-Whisper systemd (`--model small --uri tcp://0.0.0.0:10300`).
- `installer/modules/55-voice.sh:179` — STT-Proxy-Device (`127.0.0.1:10300`).
- `installer/modules/55-voice.sh:229-231` — `CT_TTS="hydrahive2-tts"`, `TTS_PORT=10200`, `PIPER_VOICE`.
- `installer/modules/55-voice.sh:276` — wyoming-piper systemd.
- `installer/modules/55-voice.sh:293` — TTS-Proxy-Device (`127.0.0.1:10200`).

### Tests

- `core/tests/test_tts_local.py` — 10 Tests (Piper PCM→WAV, ConnectionRefused, Newline-Kollaps, leerer Text, error-Event, channels-Fehler, kein Audio, Voice-Filter setzen/ignorieren).
- `core/tests/test_tts_openrouter.py` — 6 Tests (Bytes + media_type, mp3-media_type, ohne Key raises).
- `core/tests/test_wyoming_framing.py` — 3 Tests (send/recv-Framing).

---

## WARUM

### Nicht-offensichtliche Verdrahtung & Invarianten

- **`voice/tts.py` ist die EINZIGE Stelle, die `mmx` als Subprozess startet.** `api/routes/tts.py` ist ein dünner Wrapper. Wer mmx-Aufrufe woanders einbaut, bricht die Co-Location.
- **Zwei spiegelbildliche Wyoming-Clients** (STT `_wyoming_transcribe`, TTS `synthesize_local`) teilen sich `_wyoming.py` als einzige Framing-Stelle. Wer am Wire-Format dreht, muss beide testen.
- **MiniMax-Key hat EINE Quelle**: `llm.json` Provider `minimax`. Sowohl `voice/tts.py:_mmx_key` als auch der Installer (`55-voice.sh:41-51`, Python-Inline) lesen daraus. Kein zweiter Config-Ort. Installer macht zusätzlich `mmx auth login` als `$HH_USER`, weil das Backend `$HH_HOME/.mmx` liest — das CLI hält seinen eigenen Auth-State.
- **OpenRouter-Key**: SSOT `llm/_config.openrouter_key()` (`providers[].id=="openrouter"`). Geteilt von Vorlese-TTS, Tools, media_models.
- **`pcm16_to_wav` cross-modul**: `synthesize_local` (Voice) importiert `tools._openrouter_media.pcm16_to_wav`. Voice hängt also an einem Tools-Helfer — wer `_openrouter_media.py` umbaut, kann lokales TTS brechen.
- **`response_format:"pcm"` ist universell** bei OpenRouter — die Sample-Rate steht im Content-Type-Header. Deshalb `parse_pcm_content_type` + WAV-Wrap. mp3-liefernde Modelle werden durchgereicht.
- **Voice-Auflösung mit Fallback**: unbekannte Voice → erste verfügbare + `note`. Verhindert harte Fehler wenn Frontend/Config eine alte Voice-ID hält.
- **Modul-Singleton im Frontend** (`useVoiceOutput`): nur EIN aktives `<audio>`/`speechSynthesis` app-weit, weil mehrere MessageBubbles denselben Hook nutzen — sonst überlappende Stimmen. `speakRequestId` ist der Race-Guard, der nach jedem `await` geprüft wird.
- **KEIN Browser-Fallback bei Server-TTS-Fehler** — bewusst „entweder/oder, nie beides". Ein fehlgeschlagenes MiniMax-TTS liest NICHT plötzlich mit der Browser-Stimme vor.
- **`play()`-AbortError ist kein Fehler** — wird vom Browser geworfen, wenn die Audio-Quelle während des Starts entfernt wird (erneuter Klick/stop/Unmount).
- **Quota gated VOR dem Subprozess** — bei `allowed=False` darf kein mmx/ffmpeg/Container-Call laufen (Kosten + Last). Reihenfolge in der Route ist load-bearing: mmx-Gate → Quota → Synthese.
- **Pre-Filter VOR STT bei WhatsApp** — Audio wird nicht dekodiert/transkribiert wenn der Sender geblockt ist (`skip_keyword=True` Durchlauf), dann 2. Filter mit echtem Text (für Keyword-Gate). Spart Kosten + verhindert, dass geblockte Sender STT-Last erzeugen.
- **Metadaten-Guard für WA-Voice** — wenn die LLM-Antwort wie Datei-Metadaten aussieht (≥2 Regex-Treffer auf `.mp3`/`Dauer`/`KB`/`sek`), wird sie als Text statt Voice gesendet. Schützt davor, dass ein Agent versehentlich Datei-Infos vorgelesen bekommt.

### Gotchas / was bricht wenn man X anfasst

- **Piper-Voice-Filter** (`_PIPER_VOICE_RE`): nur locale-präfixierte Namen (`de_DE-...`) werden an Piper geschickt. Eine MiniMax-Voice (`German_FriendlyMan`) würde sonst durchschlagen und 502 erzeugen. Frontend schickt für `local` bewusst leere Voice (`useVoiceOutput.ts:77`).
- **Newline-Kollaps in `synthesize_local`** zwingend: ohne `" ".join(text.split())` erzeugen Leerzeilen 0 Audio („# channels not specified"). Mehrzeilige Nachrichten brachen historisch.
- **MIME-Normalisierung**: `audio/ogg;codecs=opus` muss zu `audio/ogg` gestrippt werden (`_normalize_mime` + Route-split), sonst greift `_MIME_EXT` nicht und ffmpeg bekommt `.bin`.
- **Secure-Context-Pflicht**: Mikrofon braucht HTTPS oder localhost — `useVoiceInput` prüft `window.isSecureContext`. Auf nacktem HTTP-Zugriff (LAN-IP) versagt die Aufnahme stumm-by-design (State `error`).
- **iOS-Quirks**: nur `audio/mp4`, `start(250)` nötig, `requestData()` vor `stop()`, Safety-Timeout falls `onstop` nie feuert. Am MIME-Picker oder Timing zu drehen kann iOS-Aufnahme killen.
- **Cold-Start-Timeouts**: Wyoming-Connect 15s, Total 120s — die incus-Container brauchen beim ersten Call (Modell-Load) lange. Kürzere Timeouts brechen kalte Container.
- **`get_media_model("tts")`** liefert für `media_models.tts` den nackten Slug (führendes `openrouter/` wird gestrippt) — OpenRouter `/audio/speech` will den nackten Slug.
- **`list_speech_models` 5-Min-Cache**: neu in OpenRouter freigeschaltete Stimmen/Modelle erscheinen bis zu 5 Min verzögert.

---

## Datenmodell

### Dateien / persistenter State

- **`<data_dir>/.tts_quota.json`** — pro User `{date: "YYYY-MM-DD", count: int}`. Atomarer Save via temp+rename. (`voice/_quota.py`)
- **`$HH_CONFIG_DIR/whatsapp/<username>.json`** — WhatsAppConfig inkl. `respond_as_voice`, `voice_name`, `stt_language`. (`whatsapp/config.py`)
- **`/etc/hydrahive2/llm.json`** — Provider-Liste; `minimax`-Key (für mmx) + `openrouter`-Key (für OpenRouter-TTS). `media_models.{tts,transcribe}`.
- **`$HH_HOME/.mmx/`** — mmx-CLI-Auth-State (vom Installer befüllt).
- **Container-State**: `/var/lib/wyoming` (Whisper), `/var/lib/piper` (Piper-Modelle).

### Frontend localStorage

- `hh_tts_provider` — `"browser"|"local"|"minimax"|"openrouter"`.
- `hh_tts_voice` — Voice-ID-String, default `German_FriendlyMan`.

### Datenklassen / Schemas

- **`VoiceClip`** (`voice/tts.py:29`): `ogg_bytes: bytes`, `seconds: int` (≥1), `waveform: bytes` (64 Bytes, je 0-100).
- **`WhatsAppConfig`** (`whatsapp/config.py:20`): u.a. `respond_as_voice: bool`, `voice_name: str`, `stt_language: str`.
- **`SpeakIn`** (`api/routes/tts.py:22`): `text` (1-10000), `voice` (≤80, default `German_FriendlyMan`), `provider` (≤20, default `minimax`).
- **`TTSProvider`** (TS, `useVoiceOutput.ts:4`): `"browser"|"local"|"minimax"|"openrouter"`.

### Config-Konstanten

- `DEFAULT_DAILY_CAP = 200` (`_quota.py:20`).
- `DEFAULT_VOICE = "German_FriendlyMan"` (`tts.py:19` Backend, `useVoiceOutput.ts:8` Frontend).
- `STT_PORT = 10300`, `PIPER_PORT/TTS_PORT = 10200`.
- `DEFAULTS.tts = "hexgrad/kokoro-82m"`, `DEFAULTS.transcribe = "openai/whisper-large-v3"` (`media_models.py:32`).
- Wyoming-Whisper-Modell `small`, Piper-Voice `de_DE-thorsten-medium`.

### Env-Vars

- `TTS_DAILY_CAP` — Override Daily-Cap.
- `HH_INSTALL_VOICE` (`yes`/`no`).
- `HH_PIPER_VOICE`.
- `HH_USER`, `HH_HOME` (Installer-Kontext).

### Wyoming-Events (Wire-Protokoll)

- STT senden: `transcribe`, `audio-start`, `audio-chunk` (Payload), `audio-stop`.
- STT empfangen: `transcript` (`{text}`), `error` (`{text}`).
- TTS (Piper) senden: `synthesize` (`{text, voice?}`).
- TTS empfangen: `audio-start` (`{rate, channels}`), `audio-chunk` (Payload), `audio-stop`, `error`.

### WhatsApp-Incoming-Payload (Voice-relevant)

`target_username`, `external_user_id`, `text`, `is_group`, `participant`, `media_type` (`audio`/`audio_failed`), `media_data` (base64), `media_mime`, `media_error`, `sender_name`.

---

## Offene Enden

- **Discord-Voice ist KAPUTT (Bug).** `communication/discord/adapter.py:124-126`: `clip = await synthesize_to_ogg(...)` gibt einen `VoiceClip`-Dataclass zurück, aber Zeile 126 macht `io.BytesIO(clip)` — `BytesIO` braucht `bytes`, kein `VoiceClip`. Das wirft `TypeError` und landet im `except` → es wird IMMER Text statt Voice gesendet. Korrekt wäre `io.BytesIO(clip.ogg_bytes)`. (WhatsApp nutzt `clip.ogg_bytes`/`.seconds`/`.waveform` korrekt, Discord nicht.)

- **Zwei `stt.py`-Dateien, identischer Inhalt, doppelte Verantwortung-Optik.** `api/routes/stt.py` (Route) und `voice/stt.py` (Logik) — das ist gewollt getrennt, aber der Route-File-Docstring „delegiert an hydrahive.voice.stt" und der Voice-File teilen den Namen. Kein Bug, aber Verwechslungsgefahr beim Grep.

- **Zwei STT-Pfade, zwei TTS-Pfade — bewusst, aber leicht zu verwechseln.** Lokal (Wyoming Container) für Frontend/WhatsApp vs. OpenRouter (`generate_speech`/`transcribe_audio`) für Agenten. Es gibt keine gemeinsame Abstraktion — wer „STT" sucht, findet vier verschiedene Einstiege.

- **`first_voice` (`media_models.py:130`) — Konsument prüfen.** Definiert „für Tool-Default", aber im Voice-Subsystem wird stattdessen die Voice-Auflösung in `synthesize_speech` (`_openrouter_media.py:132`) gemacht. Mögliche Redundanz / toter Pfad je nach Tool-Nutzung.

- **`list_transcribe_models` Fallback-Pflaster.** Kommentar sagt explizit „OpenRouter unterstützt `?input_modalities=audio` nicht zuverlässig" → `_TRANSCRIBE_FALLBACK`-Hardcode-Liste. Drift-Risiko: neue/entfernte Whisper-Varianten bei OpenRouter spiegeln sich nicht automatisch.

- **`_WhatsAppVoiceSection` lädt 10 Sprachen parallel** (`langs`-Array, je ein `/api/tts/voices`-Call) nur um eine deduplizierte MiniMax-Voice-Liste zu bauen. 10 Backend-Calls bei jedem Aktivieren von „respond_as_voice". Funktioniert, aber ineffizient (N+1-artig).

- **Quota gilt nur für `/api/tts`** (Frontend-Vorlesen), NICHT für WhatsApp-/Discord-Voice-Antworten (die rufen `synthesize_to_ogg` direkt, an der Quota vorbei). Wer Kosten deckeln will, muss das wissen — der WA-Voice-Pfad ist ungedeckelt.

- **Quota ist global pro Username, nicht pro Provider.** Ein `browser`-TTS zählt nicht (kein Backend-Call), aber `local` (kostenloses Piper) zählt genauso gegen das Limit wie `minimax`/`openrouter`. Das Limit existiert wegen Cloud-Kosten, trifft aber auch den kostenlosen lokalen Pfad.

- **`probe_seconds`/`waveform_from_audio` degradieren still** zu `1`/`bytes(64)` wenn ffprobe/ffmpeg fehlt oder fehlschlägt. Eine WhatsApp-Voice-Note hätte dann falsche Dauer + flache Welle, aber würde trotzdem gesendet — kein lauter Fehler.

- **Migrations-Reste im Installer** (`55-voice.sh`): Docker→incus-Migration mit Rollback-Logik. Wenn auf einem System nie Docker lief, ist der ganze `old_docker_running`-Block toter Code-Pfad (harmlos, aber Ballast). Hinweis-Logs verweisen auf ein separates `installer/migrations/voice-docker-to-incus.sh`.

- **`audio/ogg;codecs=opus` in `PREFERRED_MIMES`** (Frontend) als letzte Option — wird aber von kaum einem Browser für `MediaRecorder` unterstützt; faktisch dekorativ.

- **Sprachauswahl-Drift Frontend↔Backend.** `_WhatsAppVoiceSection` bietet nur 5 STT-Sprachen (de/en/fr/es/it) im Dropdown, `transcribe_bytes` akzeptiert aber jeden ISO-Code. Auto-Detect deckt den Rest ab, aber die UI-Liste ist eine willkürliche Teilmenge.
