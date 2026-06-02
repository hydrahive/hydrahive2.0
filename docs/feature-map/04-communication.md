# Communication (Mail/WhatsApp/Discord/Matrix)

> Feature-Landkarte des Subsystems `communication/` — Messenger- und Mail-Kanäle, über die
> externe Kontakte mit dem HydraHive2-Agenten-System reden. Drei real implementierte Kanäle:
> **WhatsApp** (Baileys-Node-Bridge + Python-Adapter), **Discord** (discord.py in-process),
> **E-Mail** (IMAP-Poll + SMTP-Reply). **Telegram** und **Matrix** existieren NUR als Strings
> (Trigger-Dropdown, Docstrings, Migrations-Kommentar) — kein Backend-Code. Sektion deckt:
> Kanäle, incoming/outgoing, Agent-Glue, Sender-Rahmung, @lid/JID-Auflösung, Voice-Nachrichten.

---

## WAS

### Kern-Foundation (kanal-agnostisch)

- **`IncomingEvent` (dataclass)** — Datenmodell einer eingehenden Nachricht aus *irgendeinem* Kanal.
  Felder: `channel`, `external_user_id`, `target_username` (HH-User dem das Konto gehört), `text`,
  `sender_name`, `media_type` (z.B. `"audio/ogg"`), `media_data` (base64), `metadata` (dict).
  (`communication/base.py:15`)
- **`ChannelStatus` (dataclass)** — Zustand eines Kanals für einen User, den die UI rendert. Felder:
  `connected`, `state` (`disconnected`/`waiting_qr`/`connecting`/`connected`/`error`), `detail`
  (menschlich, z.B. `"+49…"` oder Fehlertext), `qr_data_url` (QR als data-URL), `metadata`.
  (`communication/base.py:30`)
- **`Channel` (Protocol)** — Interface das jeder Adapter implementieren muss: Attribute `name`,
  `label`; Coroutinen `status(username)`, `connect(username)`, `disconnect(username)`,
  `send(username, to, text)`. `@runtime_checkable`. (`communication/base.py:42`)
- **Channel-Registry** — Modul-Singleton `_REGISTRY: dict[str, Channel]`. Funktionen:
  `register(channel)`, `get(name)`, `all_channels()`, `names()` (sortiert). Befüllt beim Backend-Start
  in `lifespan`. (`communication/registry.py`)
- **`handle_incoming(event)`** — zentraler Eingangsrouter: Butler-Pass zuerst, sonst Master-Agent.
  Returnt Antwort-String oder `None`. (`communication/router.py:24`)
- **`find_or_create(...)`** — Find-or-create für persistente Channel-Sessions; eine Session pro
  `(agent_id, channel, external_user_id)`. (`communication/_session_lookup.py:13`)
- **Agent-Glue** — `run_master_for_event`, `run_agent_for_event`, `_run_agent`, `_build_agent_input`,
  `_operator_directive_block`, `_find_master`, `NoMasterError`. (`communication/_agent_glue.py`)

### WhatsApp-Kanal

- **`WhatsAppAdapter` (Channel-Impl)** — spricht per HTTP mit der Baileys-Bridge.
  Methoden: `status`, `connect`, `disconnect`, `send` (Text, mit Egress-Redaction), `send_audio`
  (Sprachnachricht/ptt mit `seconds`+`waveform`), `aclose`, `_http` (lazy httpx-Client mit
  `X-HH-Bridge-Secret`-Header). (`communication/whatsapp/adapter.py`)
- **`BridgeProcess` (Lifecycle)** — startet/stoppt den Node-Subprozess (`node index.js`), pumpt dessen
  stdout/stderr (pino-NDJSON) in den Python-Logger. `start()` prüft Node-Verfügbarkeit + `node_modules`,
  gibt `False` zurück wenn nicht installiert (Kanal registriert sich dann nicht).
  (`communication/whatsapp/process.py:65`)
- **`ensure_secret(secret_file)`** — lädt oder generiert (beim ersten Mal) das Shared-Secret
  (`secrets.token_urlsafe(32)`, chmod 0600). (`communication/whatsapp/process.py:22`)
- **`_pump(stream, level)`** — Bridge-Logs → Python-Logger, mit pino-Level-Mapping `_PINO_TO_PY`.
  (`communication/whatsapp/process.py:36`)
- **`WhatsAppConfig` (dataclass)** — Pro-User-Filter-Config. Felder: `private_chats_enabled`,
  `group_chats_enabled`, `require_keyword`, `owner_numbers`, `allowed_numbers`, `blocked_numbers`,
  `respond_as_voice`, `voice_name` (Default `"German_FriendlyMan"`), `stt_language`.
  (`communication/whatsapp/config.py:19`)
- **WA-Config `load`/`save`/`_normalize_numbers`** — JSON pro User unter
  `$HH_CONFIG_DIR/whatsapp/<safe>.json`; Nummern werden ge-whitespace-strippt, `+`-Prefix entfernt,
  dedupliziert. (`communication/whatsapp/config.py:45`)
- **WA-Filter `evaluate(...)`** — Annahme-Logik mit `FilterResult(accepted, reason, is_owner)`.
  Reihenfolge: owner → blocked → group/private → allowlist → keyword. `skip_keyword`-Flag für
  Pre-Filter vor STT. (`communication/whatsapp/filter.py:43`)
- **Node-Bridge HTTP-Service (`index.js`)** — Loopback-HTTP (127.0.0.1, Default-Port 8767).
  Routen: `GET /healthz`, `POST /connect/:user`, `POST /disconnect/:user`, `GET /status/:user`,
  `POST /send/:user` (Text *oder* `audio_base64`). Konstant-zeitige Secret-Auth (außer `/healthz`).
  (`communication/whatsapp/bridge/index.js`)
- **Bridge `sock.js`** — Baileys-Socket-Lifecycle: `connect`, `disconnect`, `send`, `sendAudio`,
  `getStatus`, `handleMessage`. Enthält @lid-JID-Auflösung + Loop-Marker. (`.../bridge/lib/sock.js`)
- **Bridge `auth.js`** — `authStateFor(user)` / `clearAuth(user)` (Multi-File-Auth-State pro User).
- **Bridge `push.js`** — `pushIncoming(payload)` → POST an `/api/communication/whatsapp/incoming`.
- **Bridge `qr.js`** — `qrToDataUrl(qrString)` (QR → data-URL via `qrcode`).
- **Bridge `log.js`** — pino-Logger (`logger`) + separater `baileysLogger` (Level `warn`).

### Discord-Kanal

- **`DiscordAdapter` (Channel-Impl)** — pro User eigener `discord.Client` im FastAPI-asyncio-Loop
  (kein externer Prozess). Methoden: `status`, `connect`, `disconnect`, `send` (mit Egress-Redaction),
  `auto_reconnect_all` (Startup), `aclose` (Shutdown), `_run_client`. In-Client-Events: `on_ready`,
  `on_message`. (`communication/discord/adapter.py`)
- **`DiscordConfig` (dataclass)** — Pro-User-Config. Felder: `bot_token`, `dm_enabled`,
  `mention_enabled`, `require_keyword`, `allowed_user_ids`, `blocked_user_ids`, `allowed_channel_ids`,
  `respond_as_voice`, `voice_name`. (`communication/discord/config.py:18`)
- **Discord-Config `load`/`save`/`_normalize_ids`** — JSON pro User unter
  `$HH_CONFIG_DIR/discord/<safe>.json`. (`communication/discord/config.py:42`)
- **Discord-Filter `evaluate(...)`** — `FilterResult(accepted, reason)`. Reihenfolge: blocked →
  dm/mention → user-allowlist → channel-allowlist → keyword. (`communication/discord/filter.py:25`)

### E-Mail-Kanal (Schicht 1)

- **Mail-Watcher `run_loop(stop)`** — pollt IMAP im Intervall, dispatcht jede neue Mail über
  `handle_incoming`, antwortet per SMTP. Startup-Delay 15s. (`communication/mail/watcher.py:64`)
- **`_process(mail, cfg)`** — Self-Mail-Loop-Schutz, baut `IncomingEvent(channel="email", is_owner=False)`,
  ruft `handle_incoming`, schickt Reply mit `Re:`-Subject + Threading-Header. (`mail/watcher.py:37`)
- **`_mail_cfg()`** — sammelt alle IMAP/SMTP-Settings in ein dict. (`mail/watcher.py:22`)
- **`poll_unseen(cfg, folder, seen)`** — IMAP-Poll: holt UNSEEN-Mails readonly, dedupt gegen
  `seen`-Set, dekodiert MIME-Header, extrahiert `text/plain`-Body (auf 4000 Zeichen gekappt), max 50
  pro Poll. Liefert `list[MailMessage]`. (`communication/mail/imap_poll.py:66`)
- **`MailMessage` (dataclass)** — `message_id`, `from_addr`, `from_name`, `to`, `subject`, `date`,
  `body`. (`mail/imap_poll.py:22`)
- **`send_reply(cfg, ...)`** — SMTP-Versand mit `In-Reply-To`/`References`-Threading-Headern,
  optional STARTTLS + Login. (`communication/mail/smtp_send.py:12`)
- **`load_seen`/`save_seen`** — Dedup-State (verarbeitete Message-IDs) als JSON, max 2000 IDs.
  (`communication/mail/_seen.py`)

### API-Endpoints (alle unter `/api/communication`)

- **`GET /channels`** — registrierte Kanäle als `[{name, label}]`. Auth: `require_auth`.
  (`api/routes/communication.py:12`)
- **`GET /whatsapp/status`** — Status für den eingeloggten User. (`communication_whatsapp_routes.py:31`)
- **`POST /whatsapp/connect`** — Connect (triggert QR/Reconnect). (`...whatsapp_routes.py:40`)
- **`POST /whatsapp/disconnect`** — Disconnect (Logout). (`...whatsapp_routes.py:49`)
- **`GET /whatsapp/config`** — WA-Filter-Config. (`...whatsapp_routes.py:59`)
- **`PUT /whatsapp/config`** — WA-Filter-Config speichern. (`...whatsapp_routes.py:65`)
- **`POST /whatsapp/incoming`** — **unauthentifizierter** Inbound-Endpoint *von der Bridge*
  (geschützt per Shared-Secret-Header + Rate-Limit). Filter, Voice-STT, Dispatch, Voice/Text-Reply.
  (`api/routes/communication_whatsapp_incoming.py:40`)
- **`GET /discord/status`** — Discord-Status. (`communication_discord_routes.py:38`)
- **`POST /discord/connect`** — Discord-Bot connecten. (`...discord_routes.py:47`)
- **`POST /discord/disconnect`** — Discord-Bot trennen. (`...discord_routes.py:56`)
- **`GET /discord/config`** — Config (Token maskiert als `***`). (`...discord_routes.py:66`)
- **`PUT /discord/config`** — Config speichern (Token-Maske `***` ⇒ alten Token behalten).
  (`...discord_routes.py:72`)
- Mail hat **keine** HTTP-Endpoints — rein Env-konfiguriert + Hintergrund-Loop.

### Voice/STT-Helfer (WA)

- **`process_voice(...)`** — Audio decodieren → STT (`transcribe_bytes`) → Transkript oder
  benutzerfreundliche Fehlermeldung. Behandelt `audio_failed` (Download-Fail) und STT-Unerreichbarkeit.
  (`api/routes/_wa_voice.py:11`)
- **`send_voice_or_text(...)`** — Antwort als Voice (TTS → `send_audio`) oder Text; Metadaten-Fallback
  + Text-Fallback bei TTS-Fehler. (`api/routes/_wa_voice.py:64`)
- **`_looks_like_metadata(answer)`** / `_METADATA_HINTS` (Regex) — heuristik um zu erkennen, ob die
  LLM-Antwort wie Datei-Metadaten aussieht (≥2 Treffer) → kein Voice. (`...whatsapp_incoming.py:23`)

### Frontend-UI

- **`CommunicationPage`** — Übersichtsseite, lädt `/communication/channels`, rendert WhatsApp- und
  Discord-Karte (oder „nicht verfügbar"-Platzhalter). i18n-Namespace `communication`.
  (`frontend/.../CommunicationPage.tsx`)
- **`WhatsAppCard`** — Status-Dot, QR-Bild (`waiting_qr`), Connect/Disconnect, Telefon-Detail; pollt
  `status` alle 1500 ms während `connecting`/`waiting_qr`. (`frontend/.../WhatsAppCard.tsx`)
- **`WhatsAppFilterPanel`** — private/group-Toggle, Keyword, owner/allowed/blocked-Nummern-Textareas,
  Voice-Section, Save. (`frontend/.../WhatsAppFilterPanel.tsx`)
- **`WhatsAppVoiceSection`** (`_WhatsAppVoiceSection.tsx`) — STT-Sprach-Dropdown (`stt_language`),
  „Antworten als Sprachnachricht"-Toggle, MiniMax-Stimmen-Picker (lädt `/api/tts/voices` über mehrere
  Sprachen). (`frontend/.../_WhatsAppVoiceSection.tsx`)
- **`DiscordCard`** — wie WhatsAppCard, ohne QR (pollt alle 3000 ms). (`frontend/.../DiscordCard.tsx`)
- **`DiscordFilterPanel`** — Bot-Token (password, maskiert `***`), dm/mention-Toggle, Keyword,
  user/channel-ID-Listen, Voice-Toggle, Save. (`frontend/.../DiscordFilterPanel.tsx`)
- **`communicationApi`** (`api.ts`) — typisierter Client: `channels`, `discord.{status,connect,
  disconnect,getConfig,putConfig}`, `whatsapp.{...}`. (`frontend/.../api.ts:41`)
- **Nav/Route** — Sidebar-Eintrag `/communication` (Icon `MessageCircle`, group `working`, Farbe
  `lime`); Route in `App.tsx:74`. (`frontend/src/shared/nav-config.ts:37`, `App.tsx:74`,
  `shared/colors.ts:20`)

### Config-Flags / Voice-Mode-Schalter

- `respond_as_voice` (WA + Discord) — Antwort als Voice-Note rendern.
- `stt_language` (WA) — Sprache der eingehenden Sprachnachrichten (`""`/`"auto"` ⇒ Whisper-Auto-Detect).
- `voice_name` (WA + Discord) — MiniMax-Stimme.
- `require_keyword`, `private_chats_enabled`/`group_chats_enabled` (WA), `dm_enabled`/`mention_enabled`
  (Discord) — Annahme-Gates.
- `voice_mode` (Event-Metadata) — durchgereicht an den Agent-Run als Voice-Mode-System-Hinweis.

### Butler-Trigger (verwandt, nicht in `communication/`)

- **`message_received`-Trigger** — Butler-Flow-Trigger „Nachricht eingegangen" mit Channel-Param
  (Optionen: `all`, `whatsapp`, `telegram`, `discord`, `matrix`). `telegram`/`matrix` sind
  **Dropdown-Strings ohne Backend-Kanal**. (`butler/registry/triggers/message_received.py`)

---

## WIE

### Eingehende Nachricht — gemeinsamer Pfad (`handle_incoming`)

Jeder Kanal baut ein `IncomingEvent` und ruft `handle_incoming(event)`:

1. **Guard** — leeres `text` *und* kein `media_type` ⇒ `None`. (`router.py:31`)
2. `voice_reply = event.metadata["voice_mode"]` extrahieren. (`router.py:34`)
3. **Butler-Pass zuerst** — `dispatch_for_channel(target_username, channel, text, contact_id,
   contact_label)`. Baut `TriggerEvent(event_type="message", is_known=False, …)`, läuft alle Flows des
   Owners, sammelt die erste `stop_default`-Action. Returnt `Decision`. (`router.py:38`, `dispatch.py:34`)
4. Bei `decision.stop_default`:
   - `reply_text` gesetzt ⇒ den Text direkt zurückgeben (Master übersprungen).
   - `reply_via_agent` gesetzt ⇒ `run_agent_for_event(agent_id, event, prefix, voice_reply)`.
   - sonst (ignore/queue) ⇒ `None` (schweigen). (`router.py:49–67`)
5. **Default: Master-Agent** — `run_master_for_event(event, voice_reply)`. `NoMasterError` ⇒ Event
   verworfen + Warnung; andere Exceptions ⇒ geloggt, `None`. (`router.py:69–78`)

### Agent-Run (`_agent_glue._run_agent`)

1. **Session find-or-create** — `_session_lookup.find_or_create(agent_id, user_id, channel,
   external_user_id, title_hint)`. Query: jüngste Session mit gleichem `(agent_id, channel,
   external_user_id)`; sonst neu mit `uuid7()`, `status='active'`. (`_session_lookup.py:22`)
2. **Input bauen** (`_build_agent_input`) — **zwei bewusst getrennte Schichten**:
   - **USER-TURN**: Sender-Rahmungs-Zeile `[<Channel> <Einzel-/Gruppen-Chat> von <Sender> —
     <Vertrauensstufe>]`. *Ohne* Betreiber-Vorgabe und *nicht* owner: zusätzlich ein
     Datenschutz-Block (kein Besitzer-Name, keine internen Fähigkeiten, keine privaten Daten, stell
     dich als allgemeiner KI-Assistent vor, keine System-Aktionen). Dann die eigentliche `event.text`.
   - **SYSTEM (`extra_system`)**: bei `prefix` (Butler-Vorgabe) ein `_operator_directive_block`
     (vertrauenswürdiger Betreiber-Block, Vorrang über Persona, mit Sicherheits-Boden für Fremde);
     bei `voice_reply` der `_VOICE_MODE_SYSTEM_HINT`. (`_agent_glue.py:67`)
3. **Runner** — `session_run_guard(session.id)` (Concurrency-Lock) → `runner_run(session.id,
   user_text, extra_system=extra_system)`. Async-Stream wird konsumiert: `MessageStart` reset,
   `TextDelta` akkumuliert, `TextBlock` flush, `Done` final, `Error` ⇒ raise. (`_agent_glue.py:139`)
4. `SessionAlreadyRunning` ⇒ Run wird geskippt (`RuntimeError`). (`_agent_glue.py:172`)
5. **Egress-Engstelle** — `redaction.scrub("\n\n".join(...))`: jeder lebende Secret-Wert wird vor
   Rückgabe Richtung externer Kontakt entfernt. (`_agent_glue.py:178`)

### WhatsApp incoming (Bridge → Backend)

```
WhatsApp → Baileys-Socket (messages.upsert) → handleMessage (sock.js)
  → pushIncoming (push.js, POST /api/communication/whatsapp/incoming + Secret-Header)
  → wa_incoming (Backend)
```

`wa_incoming` (`...whatsapp_incoming.py:40`) Schritt für Schritt:

1. **Rate-Limit** — `check_rate("wa-incoming:<client-ip>")`; bei Überschreitung 429 + `Retry-After`.
2. **Secret-Auth** — `verify_secret(x_hh_bridge_secret, ensure_secret(secret_file))` (konstant-zeitig,
   fail-closed); sonst 401.
3. **Pflichtfelder** — `target_username`, `external_user_id`; ohne `text` *und* nicht audio ⇒ 400.
4. **Sender-für-Filter** — bei Gruppen der `participant`, sonst `external_user_id`.
5. **Pre-Filter** — `wa_filter.evaluate(..., text="", skip_keyword=True)`: blockt owner/block/group/
   allowlist *bevor* STT läuft (spart Ressourcen, kein Info-Leak). Reject ⇒ `{ok, filtered}`.
6. **Voice/STT** — `process_voice(...)`: bei `media_type=="audio"` decodieren + `transcribe_bytes`
   (mit `stt_language` falls gesetzt). Fehler ⇒ Fehlermeldung wird per `ch.send` an den Sender
   geschickt, return `{ok, voice_error}`. Erfolg ⇒ `text = transcript`.
7. **Post-Filter** — `wa_filter.evaluate(..., text)` (jetzt *mit* Keyword-Check). Reject ⇒ filtered.
8. **Event + Dispatch** — `IncomingEvent(channel="whatsapp", metadata={is_group, is_owner,
   participant, voice_mode=respond_as_voice})` → `handle_incoming` → `answer`.
9. **Antwort senden** — `send_voice_or_text(...)`:
   - `respond_as_voice` + `_looks_like_metadata(answer)` ⇒ Text-Fallback, return
     `{ok, voice_metadata_fallback}`.
   - sonst: `respond_as_voice` ⇒ `synthesize_to_ogg(answer, voice_name)` → `VoiceClip(ogg_bytes,
     seconds, waveform)` → `ch.send_audio(..., seconds, waveform_b64)`; bei TTS-Fehler Text-Fallback.
   - kein Voice ⇒ `ch.send(...)` (Text).

### WhatsApp outgoing + @lid/JID-Auflösung (`sock.js`)

- `send(user, to, text)` hängt **`LOOP_MARKER`** (Zero-Width-Space `​`) an jeden Text an;
  `handleMessage` ignoriert eingehende Texte, die den Marker enthalten ⇒ Echo-/Loop-Schutz.
  (`sock.js:13`, `:103`, `:171`)
- `sendAudio` setzt `ptt: true`, `mimetype: "audio/ogg; codecs=opus"`, optional `seconds`+`waveform`
  ⇒ echte Voice-Note-Darstellung (Welle + Sekunden) statt Datei-Icon. (`sock.js:174`)
- **@lid-Auflösung** (Baileys v7): bei `@lid`-Adressierung liefert WhatsApp die Telefon-JID als
  `remoteJidAlt` mit. Antwort-JID-Fallback-Kette: `remoteJidAlt` (v7) → `senderPn` (älter) → rohe JID.
  Für Gruppen analog `participantAlt`/`participantPn`. **An die rohe `@lid` zu senden erzeugt beim
  Empfänger „Auf diese Nachricht wird gewartet" (undecryptable).** (`sock.js:109–121`)
- **Connection-State-Machine**: `qr` ⇒ `waiting_qr` (+ data-URL); `open` ⇒ `connected` (+ Telefon aus
  `sock.user.id`); `close` ⇒ `disconnected`, Socket aus Map. Bei `loggedOut` ⇒ Auth löschen +
  `explicitlyDisconnected`. Sonst Auto-Reconnect (200 ms bei `restartRequired`, sonst 2000 ms).
  (`sock.js:48–74`)
- **Messages parallel** verarbeitet (`Promise.all`) damit eine kaputte Voice den Batch nicht stallt.
  (`sock.js:80`)

### Discord-Pfad (in-process)

1. **Connect** — `disconnect` (idempotent) → `load(username)` (ohne Token ⇒ `disconnected`) →
   Intents (`dm_messages`, `guild_messages`, `message_content`) → `discord.Client` → Events
   registrieren → `_run_client` als Task → 3 s warten → Status. (`adapter.py:43`)
2. **`on_message`** — Bot-/Self-Nachrichten skippen; nur DM *oder* Bot-Mention. `load(username)`
   (frische Config) → `evaluate(...)`. Bot-Mention-Tokens (`<@id>`/`<@!id>`) aus Text strippen.
   `IncomingEvent(channel="discord", external_user_id=channel.id, metadata={author_id, is_dm,
   guild_id})` → `handle_incoming`. Bei `respond_as_voice` TTS → `discord.File(.ogg)`, sonst Text.
   (`adapter.py:69`)
3. **`send`** — `redaction.scrub`, `fetch_channel(int(to))`, `channel.send(text)`. (`adapter.py:158`)
4. **`auto_reconnect_all`** — beim Startup alle `discord/*.json` mit Token reconnecten.
   (`adapter.py:167`)
5. **`_run_client`** — `client.start(token)`; `LoginFailure` ⇒ `error`-Status; CancelledError still;
   finally Client schließen. (`adapter.py:189`)

### E-Mail-Pfad

1. **`run_loop`** — Startup-Delay 15 s → Schleife: `load_seen` → `poll_unseen` (in Thread) → pro
   Mail `seen.add` + `_process` → `save_seen` wenn neue Mails → `wait_for(stop, interval)`.
   (`watcher.py:64`)
2. **`_process`** — Self-Mail-Check (`from_addr == smtp_from/imap_user` ⇒ skip, Loop-Schutz) →
   `IncomingEvent(channel="email", is_owner=False, is_group=False, subject)` → `handle_incoming` →
   bei Antwort `send_reply` (in Thread) mit `Re:`-Subject (kein doppeltes `Re: Re:`) + `In-Reply-To`.
   (`watcher.py:37`)
3. **Absender immer extern** (`is_owner=False`) ⇒ Datenschutz-Block der Sender-Rahmung greift
   automatisch.

### Startup/Shutdown-Verdrahtung (`lifespan`)

- **Mail**: bei `settings.mail_enabled` ⇒ `mail_watcher.run_loop` als Task (`mail_stop`-Event).
  (`lifespan.py:137`)
- **Discord**: bei `settings.discord_enabled` ⇒ `DiscordAdapter()` → `register_channel` →
  `auto_reconnect_all`-Task. (`lifespan.py:177`)
- **WhatsApp**: bei `settings.whatsapp_enabled` ⇒ `ensure_secret` → `BridgeProcess(...)` →
  `bridge.start()`; nur bei Erfolg `WhatsAppAdapter(bridge_url, secret)` → `register_channel` →
  `_whatsapp_auto_reconnect`-Task (reconnectet alle User mit `auth/creds.json`). (`lifespan.py:183`)
- **Shutdown**: `discord_adapter.aclose()`, `wa_adapter.aclose()`, `wa_bridge.stop()`,
  `mail_stop.set()` + Task-Join mit Timeout. (`lifespan.py:204`)
- **Router-Mount** (`main.py:108–110`): `communication_router`, `communication_whatsapp_router`
  (`= _routes_router + _incoming_router`), `communication_discord_router`.

---

## WO

### Foundation / Router / Glue
- `communication/__init__.py` — Public API (re-exports). `communication/__init__.py:8`
- `communication/base.py:15` — `IncomingEvent`; `:30` — `ChannelStatus`; `:42` — `Channel` Protocol.
- `communication/registry.py:14` — `_REGISTRY`; `:17` `register`; `:24` `get`; `:28` `all_channels`;
  `:32` `names`.
- `communication/router.py:24` — `handle_incoming`.
- `communication/_session_lookup.py:13` — `find_or_create`.
- `communication/_agent_glue.py:26` — `_VOICE_MODE_SYSTEM_HINT`; `:45` `_operator_directive_block`;
  `:67` `_build_agent_input`; `:108` `NoMasterError`; `:112` `_find_master`; `:119`
  `run_master_for_event`; `:130` `run_agent_for_event`; `:139` `_run_agent`; `:178` Egress-`scrub`.

### WhatsApp (Python)
- `communication/whatsapp/__init__.py:2` — Exports.
- `communication/whatsapp/adapter.py:13` — `WhatsAppAdapter`; `:29` `status`; `:48` `connect`; `:53`
  `disconnect`; `:56` `send`; `:65` `send_audio`; `:82` `aclose`.
- `communication/whatsapp/config.py:19` — `WhatsAppConfig`; `:45` `load`; `:67` `save`; `:77`
  `_normalize_numbers`.
- `communication/whatsapp/filter.py:19` — `FilterResult`; `:26` `_digits_only`; `:32` `_matches_any`;
  `:43` `evaluate`.
- `communication/whatsapp/process.py:19` — `BRIDGE_DIR`; `:22` `ensure_secret`; `:33` `_PINO_TO_PY`;
  `:36` `_pump`; `:65` `BridgeProcess`; `:82` `start`; `:114` `stop`.

### WhatsApp (Node-Bridge)
- `communication/whatsapp/bridge/index.js:18` `authorized`; `:38` HTTP-Server; `:46` `/healthz`;
  `:52`–`:78` Routen.
- `communication/whatsapp/bridge/lib/sock.js:13` `LOOP_MARKER`; `:15` `getStatus`; `:26` `connect`;
  `:48` `connection.update`; `:76` `messages.upsert`; `:92` `handleMessage`; `:109` @lid-Auflösung;
  `:158` `disconnect`; `:168` `send`; `:174` `sendAudio`.
- `communication/whatsapp/bridge/lib/auth.js:11` `authStateFor`; `:17` `clearAuth`.
- `communication/whatsapp/bridge/lib/push.js:6` `pushIncoming`.
- `communication/whatsapp/bridge/lib/qr.js:3` `qrToDataUrl`.
- `communication/whatsapp/bridge/lib/log.js:16` `logger`; `:24` `baileysLogger`.
- `communication/whatsapp/bridge/package.json:15` — Baileys `7.0.0-rc13`, pino, qrcode; `engines.node
  >=20`.

### Discord
- `communication/discord/__init__.py:2` — Export.
- `communication/discord/adapter.py:27` `DiscordAdapter`; `:36` `status`; `:43` `connect`; `:62`
  `on_ready`; `:68` `on_message`; `:143` `disconnect`; `:158` `send`; `:167` `auto_reconnect_all`;
  `:184` `aclose`; `:189` `_run_client`.
- `communication/discord/config.py:18` `DiscordConfig`; `:42` `load`; `:64` `save`; `:74`
  `_normalize_ids`.
- `communication/discord/filter.py:19` `FilterResult`; `:25` `evaluate`.

### Mail
- `communication/mail/__init__.py` — Docstring (Schicht-1-Erklärung).
- `communication/mail/watcher.py:22` `_mail_cfg`; `:37` `_process`; `:64` `run_loop`; `:19`
  `_STARTUP_DELAY`.
- `communication/mail/imap_poll.py:18` `_MAX_PER_POLL`; `:19` `_BODY_BUDGET`; `:22` `MailMessage`;
  `:33` `_decode`; `:42` `_split_from`; `:47` `_extract_body`; `:66` `poll_unseen`.
- `communication/mail/smtp_send.py:12` `send_reply`.
- `communication/mail/_seen.py:15` `_MAX_SEEN`; `:18` `load_seen`; `:27` `save_seen`.

### API-Routes + Helfer
- `api/routes/communication.py:9` Router (`/api/communication`); `:12` `GET /channels`.
- `api/routes/communication_whatsapp.py` — Aggregator (`_routes_router` + `_incoming_router`).
- `api/routes/communication_whatsapp_routes.py:17` `_status_dict`; `:22` `_config_dict`; `:31`–`:79`
  Endpoints.
- `api/routes/communication_whatsapp_incoming.py:23` `_METADATA_HINTS`; `:34` `_looks_like_metadata`;
  `:40` `wa_incoming`.
- `api/routes/communication_discord.py` — Aggregator.
- `api/routes/communication_discord_routes.py:16` `_TOKEN_MASK`; `:19` `_status_dict`; `:24`
  `_config_dict`; `:38`–`:89` Endpoints.
- `api/routes/_wa_voice.py:11` `process_voice`; `:64` `send_voice_or_text`.

### Auth/Rate-Limit-Middleware (für WA-incoming)
- `api/middleware/secret_compare.py:13` `verify_secret` (hmac.compare_digest, fail-closed).
- `api/middleware/inbound_ratelimit.py:13` `WINDOW_SECONDS=60`; `:14` `DEFAULT_LIMIT=120`; `:23`
  `check_rate`; `:42` `reset`.
- `api/middleware/client_ip.py:13` `TRUSTED_PROXIES`; `:16` `client_ip` (X-Forwarded-For nur hinter
  Loopback-Proxy).

### Lifespan + Settings
- `api/lifespan.py:40` `_whatsapp_auto_reconnect`; `:137`–`:142` Mail-Start; `:177`–`:181`
  Discord-Start; `:183`–`:198` WhatsApp-Start; `:204`–`:209` Shutdown.
- `api/main.py:23`–`:25` Imports; `:108`–`:110` `include_router`.
- `settings/_services.py:91` `_CommunicationMixin`; `:97` `backend_internal_url`; `:101`
  `discord_enabled`; `:105` `discord_config_dir`; `:109` `whatsapp_enabled`; `:113`
  `whatsapp_data_dir`; `:117` `whatsapp_bridge_port`; `:121` `whatsapp_bridge_url`; `:125`
  `whatsapp_bridge_secret_file`.
- `settings/_mail.py` — `_MailMixin`: `mail_enabled`, `mail_owner_username`, `mail_poll_interval`,
  `mail_seen_ids`, `mail_imap_*`, `mail_smtp_*`, `mail_from`.

### DB
- `db/migrations/002_communication.sql` — `ALTER TABLE sessions ADD COLUMN channel`,
  `external_user_id`; Index `idx_sessions_channel(channel, external_user_id, agent_id)`.
- `db/sessions.py:13` `Session`; `:25` `from_row`.

### Frontend
- `frontend/src/features/communication/CommunicationPage.tsx`
- `frontend/src/features/communication/api.ts:3` `ChannelState`; `:10` `ChannelStatus`; `:17`
  `WhatsAppConfig`; `:29` `DiscordConfig`; `:41` `communicationApi`.
- `frontend/src/features/communication/WhatsAppCard.tsx:9` `POLL_MS=1500`.
- `frontend/src/features/communication/WhatsAppFilterPanel.tsx`
- `frontend/src/features/communication/_WhatsAppVoiceSection.tsx`
- `frontend/src/features/communication/DiscordCard.tsx:9` `POLL_MS=3000`.
- `frontend/src/features/communication/DiscordFilterPanel.tsx`
- `frontend/src/App.tsx:74` Route; `frontend/src/shared/nav-config.ts:37` Nav; `shared/colors.ts:20`
  Farbe; `i18n/index.ts:77/88/108` Namespace `communication`.
- `i18n/locales/{de,en}/communication.json` — UI-Strings.

### Trigger (verwandt)
- `butler/registry/triggers/message_received.py` — `message_received`-Trigger (`channel`-Param mit
  `telegram`/`matrix` als reine Dropdown-Strings).

### Voice-Abhängigkeiten (außerhalb)
- `voice/tts.py:30` `VoiceClip`; `:202` `synthesize_to_ogg`. `voice/stt.py:94` `transcribe_bytes`.
- `credentials/redaction.py:65` `scrub`.

### Tests
- `core/tests/test_mail_watcher.py` — `_seen`-Roundtrip, `poll_unseen` (parse/dedup/unconfigured),
  `_process` (Re-Subject, Re-Prefix-Idempotenz, Self-Mail-Skip, agent-silent).

---

## WARUM

### Nicht-offensichtliche Verdrahtung & Invarianten

- **Zwei-Schichten-Input ist Injection-Härtung, nicht Kosmetik.** Eine Identitäts-/Persona-Anweisung
  (Betreiber-Vorgabe) im *User-Turn* würde ein injection-resistenter Agent (Opus 4.8) als eingeschleuste
  Nachricht des *Absenders* werten und korrekt ablehnen. Deshalb wandert sie als
  `_operator_directive_block` in `extra_system` (System-Schicht = echte Betreiber-Config). Die
  Sender-Rahmung + Datenschutz-Block bleiben im User-Turn, weil sie *über* den Sender informieren, nicht
  *als* Sender anweisen. Wer diese Trennung auflöst, bricht entweder die Vorgaben-Befolgung oder die
  Injection-Resistenz. (`_agent_glue.py:45–105`)
- **Sender-Rahmung ist ein HH1-Port.** Ohne die `[Channel … von … — Vertrauensstufe]`-Zeile antwortet
  der Agent dem *Owner* statt dem externen Sender (Bug aus HydraHive1). Der Datenschutz-Block greift
  *nur* wenn `is_owner=False` *und* keine Betreiber-`prefix` gesetzt ist — mit Vorgabe übernimmt diese
  die Regelung (Persona + was geteilt wird), plus Sicherheits-Boden für Fremde.
- **`is_owner` ist kanal-spezifisch.** WhatsApp leitet es aus `wa_filter.evaluate` (owner_numbers) ab;
  Mail setzt es **hart auf `False`** (jede Mail = Fremder); Discord setzt es gar nicht ⇒ default `False`.
  Discord hat also nie eine „Owner"-Vertrauensstufe.
- **Egress-Redaction an der Draht-Grenze, doppelt.** `_run_agent` scrubt die finale Antwort
  (`_agent_glue.py:178`), *und* jeder Adapter scrubt zusätzlich in `send`/`send_audio`
  (`whatsapp/adapter.py:58`, `discord/adapter.py:160`). Begründung: das LLM könnte an einen Secret-Wert
  über einen anderen Pfad gekommen sein; die Draht-Grenze ist die letzte Engstelle. **Mail-Reply
  scrubt NICHT erneut** — verlässt sich allein auf die `_run_agent`-Engstelle (siehe Offene Enden).
- **Loop-Marker (`​`) ist Pflicht für den Echo-Schutz.** Die Bridge hängt ihn an jeden
  ausgehenden Text und filtert eingehende Texte mit Marker raus. Würde man ihn aus `send` entfernen,
  könnten Agent-Antworten (die der Bot selbst sieht) eine Endlosschleife auslösen. Greift **nur bei
  Text**, nicht bei Voice-Notes (`fromMe`-Check fängt die meisten Self-Messages separat ab).
- **@lid-Auflösung ist die Lösung des „Auf diese Nachricht wird gewartet"-Bugs.** Senden an die rohe
  `@lid` erzeugt undecryptable Messages. Fix = Baileys v7 + `remoteJidAlt`. Wer die Fallback-Kette
  `remoteJidAlt → senderPn → rawJid` ändert oder Baileys downgradet, bricht WhatsApp-Antworten an
  @lid-adressierte Kontakte. (Bekannter Befund in MEMORY; verifiziert 2026-06-02.)
- **Pairing-Identitäts-Invariante** (aus MEMORY): WhatsApp pro HH-User — Pairing-User == Butler-User ==
  Agent-Owner müssen zusammenpassen, sonst findet `_find_master(target_username)` keinen Master.
- **Bridge-Loopback ist KEIN Trust-Boundary.** Da HH2 untrusted Agent-Tools (`shell_exec`) auf
  demselben Host ausführt, muss jeder Bridge-Request (außer `/healthz`) das Shared-Secret tragen —
  beidseitig konstant-zeitig (`crypto.timingSafeEqual` bzw. `hmac.compare_digest`), fail-closed.
  (Issue #180/#181) (`index.js:18`, `secret_compare.py`)
- **Pre-Filter vor STT spart Ressourcen *und* verhindert Info-Leak.** `skip_keyword=True` prüft
  owner/block/group/allowlist *bevor* teure STT läuft. Nach STT zweiter `evaluate`-Lauf nur noch für den
  Keyword-Check (owner/block sind dann schon ok). (`filter.py:43`, `...whatsapp_incoming.py:69/93`)
- **Voice-Mode-System-Hint deckt mehrere LLM-Failure-Modes ab**: eigene TTS-/`mmx`-/`shell_exec`-Calls,
  Markdown, Pfade/Datei-Metadaten, Emojis, zu lange Antworten. Ergänzend die `_looks_like_metadata`-
  Heuristik als Backstop, die bei ≥2 Metadaten-Treffern auf Text-Reply fällt (TTS würde sonst
  „17 Komma 3 Megabyte" vorlesen). (`_agent_glue.py:26`, `...whatsapp_incoming.py:23`)
- **Frischer Config-Load in `on_message`/`wa_incoming`** (statt einmal beim Connect): Filter-/Voice-
  Änderungen im Frontend wirken sofort, ohne Reconnect. (`discord/adapter.py:81`)
- **Discord `connect` ist idempotent** (ruft erst `disconnect`), `auto_reconnect_all` und
  `_whatsapp_auto_reconnect` laufen als verzögerte Tasks (2 s) damit Bridge/Loop HTTP-ready sind.
- **Token-Maske `***`**: Discord-`config`-Endpoint maskiert den Bot-Token nach außen; `PUT` mit `***`
  ⇒ alten Token behalten (kein versehentliches Überschreiben mit der Maske). WhatsApp braucht das nicht
  (kein Token, QR-basiert). (`...discord_routes.py:24/77`)

### Was bricht, wenn man X anfasst

- **`channel`/`external_user_id`-Spalten oder den Index** ⇒ Session-Kontinuität pro Sender geht
  verloren (jede Nachricht startet neue Session) bzw. `find_or_create` wird langsam.
- **`run()`-Stream-Events** (`MessageStart`/`TextDelta`/`TextBlock`/`Done`/`Error`) umbenennen ⇒
  `_run_agent` sammelt keine Antwort mehr.
- **`/whatsapp/incoming` ohne Secret/Rate-Limit** ⇒ offener Kosten-DoS (jeder kann Agent-Runs + STT
  triggern).
- **`HH_INTERNAL_URL`/`backend_internal_url` falsch** ⇒ Bridge kann `pushIncoming` nicht erreichen,
  eingehende WhatsApp-Nachrichten verschwinden still.

---

## Datenmodell

### DB (SQLite, Core)
Eigene Tabellen hat das Subsystem nicht — es erweitert `sessions`:
- `sessions.channel TEXT` — Kanalname (`"whatsapp"`/`"discord"`/`"email"`), NULL für UI-Sessions.
- `sessions.external_user_id TEXT` — externer Sender (JID/Channel-ID/Mail-Adresse).
- Index `idx_sessions_channel(channel, external_user_id, agent_id) WHERE channel IS NOT NULL`.
  (`db/migrations/002_communication.sql`)

### Persistente Config (JSON-Dateien, keine DB)
- `$HH_CONFIG_DIR/whatsapp/<safe_username>.json` — `WhatsAppConfig` (private/group/keyword/
  owner/allowed/blocked-numbers/respond_as_voice/voice_name/stt_language).
- `$HH_CONFIG_DIR/discord/<safe_username>.json` — `DiscordConfig` (bot_token/dm/mention/keyword/
  allowed/blocked-user-ids/allowed-channel-ids/respond_as_voice/voice_name).
- `$HH_CONFIG_DIR/whatsapp_bridge.secret` — Shared-Secret (chmod 0600).
- `$HH_DATA_DIR/whatsapp/<username>/auth/creds.json` (+ keys) — Baileys-Multi-File-Auth-State pro User.
- `$HH_DATA_DIR/mail/seen_ids.json` — Dedup-State (max 2000 Message-IDs).

### Events / Datenstrukturen
- `IncomingEvent` (channel, external_user_id, target_username, text, sender_name, media_type,
  media_data, metadata). Metadata-Keys: `is_owner`, `is_group`, `voice_mode`, `participant` (WA),
  `subject` (Mail), `author_id`/`is_dm`/`guild_id` (Discord).
- `ChannelStatus` (connected, state, detail, qr_data_url, metadata).
- `Decision` (matched, reply_text, reply_via_agent, reply_prefix, stop_default) — Butler→Router.
- `TriggerEvent` (event_type="message", channel, contact_id, contact_label, is_known, message_text,
  owner) — Router→Butler.
- `VoiceClip` (ogg_bytes, seconds, waveform[64 Bytes]) — TTS→`send_audio`.
- `MailMessage` (message_id, from_addr, from_name, to, subject, date, body).
- `FilterResult` (WA: accepted/reason/is_owner; Discord: accepted/reason).

### Bridge-HTTP-Payload (`/whatsapp/incoming`)
`target_username`, `external_user_id`, `participant`, `is_group`, `sender_name`, `text`,
`media_type` (`"audio"`/`"audio_failed"`/null), `media_mime`, `media_data` (base64), `media_error`.
Header `X-HH-Bridge-Secret`.

### Settings / Env-Vars
| Env-Var | Setting | Default | Zweck |
|---|---|---|---|
| `HH_WA_ENABLED` | `whatsapp_enabled` | `1` | WhatsApp-Kanal an |
| `HH_WA_BRIDGE_PORT` | `whatsapp_bridge_port` | `8767` | Bridge-Loopback-Port |
| `HH_INTERNAL_URL` | `backend_internal_url` | `http://127.0.0.1:<port>` | Backend-URL für Bridge-Push |
| (abgeleitet) | `whatsapp_bridge_url` | `http://127.0.0.1:<port>` | Adapter→Bridge |
| (abgeleitet) | `whatsapp_data_dir` | `<data_dir>/whatsapp` | Auth-State |
| (abgeleitet) | `whatsapp_bridge_secret_file` | `<config_dir>/whatsapp_bridge.secret` | Shared-Secret |
| `HH_WA_DATA_DIR`* | — | — | Bridge-seitiger Auth-Dir (vom Backend gesetzt) |
| `HH_WA_BRIDGE_SECRET`* | — | — | Bridge-seitiges Secret (vom Backend gesetzt) |
| `HH_WA_BACKEND_URL`* | — | — | Bridge-seitige Backend-URL (vom Backend gesetzt) |
| `HH_WA_BRIDGE_LOG_LEVEL`* | — | `info` | Bridge-pino-Level |
| `HH_WA_BRIDGE_BAILEYS_LEVEL`* | — | `warn` | Baileys-Logger-Level |
| `HH_DISCORD_ENABLED` | `discord_enabled` | `1` | Discord-Kanal an |
| (abgeleitet) | `discord_config_dir` | `<config_dir>/discord` | Per-User-Config |
| `HH_MAIL_ENABLED` | `mail_enabled` | `0` | Mail-Watcher an |
| `HH_MAIL_OWNER` | `mail_owner_username` | `admin` | dessen Butler/Master verarbeitet Mail |
| `HH_MAIL_POLL_INTERVAL` | `mail_poll_interval` | `60` | Poll-Sekunden |
| `HH_MAIL_IMAP_HOST` | `mail_imap_host` | `""` | IMAP-Host |
| `HH_MAIL_IMAP_PORT` | `mail_imap_port` | `993` | IMAP-Port |
| `HH_MAIL_IMAP_USER` | `mail_imap_user` | `""` | IMAP-User |
| `HH_MAIL_IMAP_PASSWORD` | `mail_imap_password` | `""` | IMAP-Passwort |
| `HH_MAIL_IMAP_FOLDER` | `mail_imap_folder` | `INBOX` | IMAP-Ordner |
| `HH_MAIL_SMTP_HOST` | `mail_smtp_host` | `""` | SMTP-Host |
| `HH_MAIL_SMTP_PORT` | `mail_smtp_port` | `587` | SMTP-Port |
| `HH_MAIL_SMTP_USER` | `mail_smtp_user` | `""` | SMTP-User |
| `HH_MAIL_SMTP_PASSWORD` | `mail_smtp_password` | `""` | SMTP-Passwort |
| `HH_MAIL_SMTP_TLS` | `mail_smtp_use_tls` | `1` | STARTTLS |
| `HH_MAIL_FROM` | `mail_from` | `=smtp_user` | Absender-Adresse |
\* = nur in der Bridge-Subprozess-Env gesetzt (von `BridgeProcess.start`, nicht im Settings-Singleton).

### Konstanten
- `LOOP_MARKER = "​"` (`sock.js:13`)
- `_MAX_PER_POLL = 50`, `_BODY_BUDGET = 4000` (`imap_poll.py`)
- `_MAX_SEEN = 2000` (`_seen.py`)
- `_STARTUP_DELAY = 15` (mail), Auto-Reconnect-Delay `2` s (WA/Discord), Discord-connect-warten `3` s.
- Rate-Limit `WINDOW_SECONDS=60`, `DEFAULT_LIMIT=120` (`inbound_ratelimit.py`).
- Frontend-Poll: WA `1500` ms, Discord `3000` ms.
- Default-Voice `"German_FriendlyMan"`.

---

## Offene Enden

- **`messaging/__init__.py` ist leer** — toter Platzhalter-Namespace `hydrahive/messaging/`, kein
  Code, von niemandem importiert. Kandidat zum Löschen.
- **Telegram & Matrix sind Phantom-Kanäle.** Sie tauchen auf als: Dropdown-Optionen im
  `message_received`-Trigger (`telegram`, `matrix`), in Docstrings (`base.py`, `mail/__init__.py`),
  und im Migrations-Kommentar (`002_communication.sql`) — **es gibt keinen Adapter, keine Route, kein
  Setting**. Ein Butler-Flow mit Channel `telegram`/`matrix` kann nie matchen (kein Kanal feuert je
  ein Event mit `channel="telegram"`). Drift zwischen UI-Versprechen und Backend-Realität.
- **Mail-Reply scrubt nicht doppelt.** WhatsApp/Discord scrubben in `send`/`send_audio` zusätzlich;
  `mail.watcher._process` schickt die `handle_incoming`-Antwort direkt an `send_reply` ohne erneutes
  `redaction.scrub`. Verlässt sich allein auf die `_run_agent`-Egress-Engstelle. Inkonsistenz zum
  Adapter-Pattern (kein akuter Leak, aber asymmetrisch).
- **Mail = eine globale Mailbox.** Bewusst Schicht 1 (`HH_MAIL_*` global, einem `mail_owner_username`
  zugeordnet). Per-Buddy-Postfächer und KAS-Provisioning sind explizit NICHT gebaut (MEMORY:
  „Schicht 2 (Addi pro Buddy), KAS-Provisioning-Plugin" als Backlog). Wartet laut MEMORY noch auf
  Tills Deploy + echtes Postfach für E2E.
- **Mail hat keinen `target_username`-Filter / kein Filter-UI.** Anders als WA/Discord gibt es für
  Mail keine `*Config`-Datei, keine Allow/Block-Listen, kein Keyword — jede Nicht-Self-Mail wird
  verarbeitet. Einziges Gate ist der Self-Mail-Loop-Schutz.
- **Mail-Watcher hat keine Voice-Verarbeitung** (offensichtlich), aber auch keine Attachments — nur
  `text/plain`-Body (HTML-only-Mails ⇒ leerer Body ⇒ Guard verwirft das Event).
- **Discord-Adapter hat keinen eingehenden Voice-Pfad.** `respond_as_voice` (TTS raus) existiert, aber
  eingehende Discord-Voice-Messages werden nicht transkribiert (nur WhatsApp hat den STT-Pfad). Discord
  `IncomingEvent` setzt nie `media_type`.
- **`ChannelStatus.metadata` wird nie befüllt/genutzt** — Feld existiert in der dataclass, kein Adapter
  schreibt rein, keine UI liest es. Toter Slot.
- **`DiscordConfig`/`WhatsAppConfig` save mutiert das übergebene Objekt** (`cfg.owner_numbers = ...`
  vor dem Schreiben) — verletzt das Immutability-Prinzip aus den Projektregeln (CLAUDE.md), low impact.
- **WhatsApp-`status` mappt `qr_data_url` durch, Discord-`_status_dict` setzt es hart `None`** — die
  geteilte `ChannelStatus`-Form trägt ein WA-only-Feld; kleine Modell-Unsauberkeit.
- **Tests nur für Mail.** `test_mail_watcher.py` deckt `_seen`/`poll_unseen`/`_process`. Für
  WhatsApp-Filter/@lid-Auflösung, Discord-Filter, `handle_incoming`-Routing, `_build_agent_input`-
  Schichtung und die Voice-Helfer gibt es **keine** Unit-Tests im gefundenen Suchraum — kritische,
  injection-relevante Logik (Sender-Rahmung, Betreiber-Vorgabe) ist ungetestet.
- **`_PINO_TO_PY`-Pump erwartet pino-NDJSON**; der Kommentar verweist auf „Legacy-Output … sollte nach
  #31 keiner mehr sein" — Hinweis auf abgeschlossene, aber im Code noch verteidigte Migration.
- **Bridge-`disconnect` ruft `s.sock.logout()`** (serverseitiger Logout, löscht Pairing), während die
  HTTP-Route `/disconnect` das auch tut — ein versehentlicher Disconnect erzwingt also neues
  QR-Pairing, kein „nur Verbindung trennen". Bewusst? Unklar, potenzielle UX-Falle.
