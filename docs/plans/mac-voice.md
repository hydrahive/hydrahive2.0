# Plan: Spracheingabe und Vorlesen (Voice) auf dem Mac

Status: **FREIGEGEBEN** (Till 22.10.2026: Variante A, „ok lege los“). Task a7506ebd, Teil von f4a303a9.

## Befund (Intel-Test-Mac .186, 22.10.2026 – danach restlos entfernt)

- Linux: `installer/modules/55-voice.sh` legt zwei Incus-Container an – `hydrahive2-stt` (wyoming-faster-whisper,
  Modell `small`, int8, Port 10300) und `hydrahive2-tts` (wyoming-piper, Stimme `de_DE-thorsten-medium`, Port 10200).
  Der Kern spricht nur `127.0.0.1:10300` / `127.0.0.1:10200` an (`voice/stt.py`, `voice/tts.py`).
- Auf dem Mac gibt es diese Container nicht; das Cockpit zeigt Voice als „nicht auf dem Mac“.
- Beide Dienste laufen **direkt auf macOS** (venv mit Homebrew-Python 3.12), ohne Container:
  - STT: 5,6 s deutsche Sprache → **1,5 s**, Text korrekt (über HydraHives eigenes `stt.transcribe_bytes`).
  - TTS: **0,3 s** je Satz, WAV 22 kHz (über `tts.synthesize_local`).
  - Platz ~1,1 GB (Modell small 464 MB), RAM Whisper ~400 MB. pip ~1 min. ffmpeg liegt schon da (`00-deps.sh`).
- Paket-Fallen:
  - `onnxruntime` ≥ 1.24 hat **keine Intel-Mac-Pakete** → fest **1.23.2** (arm64 + x86_64 vorhanden).
  - `av` 19 bricht `faster-whisper` 1.2.1 („unexpected keyword argument 'metadata_errors'“) → fest **17.1.0**
    (wie Linux-Container).
  - `pysilero-vad` 3.4.0 hat für Intel-Mac nur Quellcode → wird gebaut (Xcode-Kommandozeilenwerkzeuge, ~10 s).

## Ziel

Mac: Einstellungen → Zusatz-Module → **Voice → Installieren** (oder `install-mac.sh --with=voice`). Danach
funktionieren Mikrofon im Chat, Vorlesen und `transcribe_audio` wie unter Linux. Update pflegt Voice mit.
Linux-Installer unangetastet.

## Bauteile

### Installer (nur Mac)
- **neu** `installer/modules-mac/55-voice.sh`
  - Zwei venvs unter `/usr/local/lib/hydrahive2/voice/{stt,tts}` mit Homebrew-Python 3.12, **feste Versionen**:
    `wyoming-faster-whisper==3.8.1 faster-whisper==1.2.1 ctranslate2==4.8.3 av==17.1.0 onnxruntime==1.23.2
    pysilero-vad==3.4.0 wyoming==1.10.2` bzw. `wyoming-piper==2.5.2 piper-tts==1.8.0 onnxruntime==1.23.2
    wyoming==1.10.2`. Nur fertige Pakete (`--only-binary=:all:`), Ausnahme `pysilero-vad`.
  - Versions-Vermerk je venv → zweiter Lauf / Update installiert nichts neu, wenn sich nichts geändert hat.
  - Modelle/Stimmen in `/usr/local/var/hydrahive2/voice/{stt,tts}` (Dienstnutzer).
  - Zwei LaunchDaemons **`io.hydrahive.voice-stt`** / **`io.hydrahive.voice-tts`**: `UserName` = Dienstnutzer
    (kein root), `RunAtLoad`, `KeepAlive`, nur **`tcp://127.0.0.1`**, gleiche Parameter wie Linux
    (STT: `--model small --compute-type int8 --beam-size 1 --vad-filter --initial-prompt …`;
    TTS: `--voice de_DE-thorsten-medium`). Log `/usr/local/var/log/hydrahive2-voice-{stt,tts}.log`.
  - Wartet, bis Whisper auf „describe“ antwortet (erster Start lädt das Modell, ~460 MB).
  - `HH_INSTALL_VOICE=yes` in `install.conf`.
- `install-mac.sh`: Phase „Voice“ nur mit `--with=voice` / `HH_INSTALL_VOICE=yes`.
- `update-mac.sh`: wenn gewünscht → `55-voice.sh` (Versionen nachziehen, Dienste neu laden).
- `lib/mac-addon-ctl.sh`: erlaubt zusätzlich `install voice`.

### Kern
- `system/addons_status.py`: `MAC_INSTALLABLE += voice`; auf dem Mac **kein** `requires: containers` für Voice.
- Keine Änderung an `voice/stt.py` / `voice/tts.py` (gleiche Ports).

### Oberfläche
- Text der Voice-Karte: nicht mehr „läuft in einem Container“ (gilt für Mac nicht).

### Doku
- `INSTALL-macOS(.de).md`: Abschnitt Voice.

## Nicht-Ziele
- whisper.cpp/Metal für Apple Silicon (später, falls zu langsam).
- MiniMax-TTS (mmx) auf dem Mac – bleibt wie bisher (Cloud, optional).

## Reihenfolge (TDD)
1. `55-voice.sh` auf nachgebautem Mac (falsche Python → Abbruch; Versionen fest; zweiter Lauf ohne pip; Dienste als
   Dienstnutzer + nur 127.0.0.1; install.conf). Rote Tests zuerst.
2. Kern + Runner + Update + install-mac.sh (Tests).
3. Mutantenprobe, volle Suite.
4. Live auf .186: Cockpit → Voice installieren, Mikrofon/Transkript, Vorlesen, Neustart ohne Login, Update.
5. Linux-Gegenprobe hydratest (keine Installer-Datei geändert).
