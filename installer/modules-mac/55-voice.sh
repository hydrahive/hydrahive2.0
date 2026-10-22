#!/bin/bash
# macOS: Spracheingabe (Whisper) und Vorlesen (Piper) ohne Container (Plan docs/plans/mac-voice.md).
# Gegenstück zu installer/modules/55-voice.sh (Linux: zwei Incus-Container).
#
# Beide Dienste laufen direkt auf dem Mac in eigenen venvs (Homebrew-Python 3.12) als LaunchDaemons unter dem
# Dienstnutzer, nur auf 127.0.0.1 – gleiche Ports und Parameter wie unter Linux, der Kern merkt keinen Unterschied.
# Feste Paketversionen: onnxruntime ≥ 1.24 hat keine Intel-Mac-Pakete, av 19 bricht faster-whisper 1.2.1.
# Läuft aus install-mac.sh, update-mac.sh und dem Zusatz-Module-Runner. Idempotent.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

HH_USER="${HH_USER:?HH_USER fehlt}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
HH_VOICE_ROOT="${HH_VOICE_ROOT:-/usr/local/lib/hydrahive2/voice}"
HH_VOICE_STT_PLIST="${HH_VOICE_STT_PLIST:-/Library/LaunchDaemons/io.hydrahive.voice-stt.plist}"
HH_VOICE_TTS_PLIST="${HH_VOICE_TTS_PLIST:-/Library/LaunchDaemons/io.hydrahive.voice-tts.plist}"
HH_VOICE_PROBE="${HH_VOICE_PROBE:-}"

STT_PORT=10300
TTS_PORT=10200
STT_PINS=(wyoming-faster-whisper==3.8.1 faster-whisper==1.2.1 ctranslate2==4.8.3 av==17.1.0
          onnxruntime==1.23.2 pysilero-vad==3.4.0 wyoming==1.10.2)
TTS_PINS=(wyoming-piper==2.5.2 piper-tts==1.8.0 onnxruntime==1.23.2 wyoming==1.10.2)
# Gleicher Diktat-Hinweis wie Linux (modules/55-voice.sh)
STT_PROMPT="Diktat fuer Smart-Home-Befehle und Software-Entwicklung auf Deutsch: Python, git, commit, branch, refactor, pytest, ffmpeg, API-Endpoint. Mit korrekter Zeichensetzung."

# shellcheck source=../lib/mac-roles.sh
source "$(dirname "$0")/../lib/mac-roles.sh"   # priv, hh_conf_get/hh_conf_set

# --- 0) Python 3.12 von Homebrew -------------------------------------------------------------------------------
PY="${HH_VOICE_PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in /opt/homebrew/opt/python@3.12/bin/python3.12 /usr/local/opt/python@3.12/bin/python3.12; do
    if [ -x "$candidate" ]; then PY="$candidate"; break; fi
  done
fi
if [ -z "$PY" ] || [ ! -x "$PY" ]; then
  echo "Voice: Python 3.12 von Homebrew fehlt (brew install python@3.12)" >&2
  exit 1
fi
case "$("$PY" --version 2>&1)" in
  "Python 3.12."*) ;;
  *) echo "Voice: $PY ist nicht Python 3.12 ($("$PY" --version 2>&1))" >&2; exit 1 ;;
esac

# --- 1) venvs mit festen Versionen (nur neu, wenn sich die Liste geändert hat) -----------------------------------
CHANGED=""
ensure_venv() {   # $1=Name  $2..=pip-Argumente
  local name="$1"; shift
  local dir="$HH_VOICE_ROOT/$name" mark="$HH_VOICE_ROOT/$name/.hh-pins" want
  want="$(printf '%s\n' "$@")"
  if [ -f "$mark" ] && [ "$(cat "$mark")" = "$want" ]; then
    log "Voice-$name: Pakete aktuell"
    return 0
  fi
  log "Voice-$name: Pakete installieren (etwa eine Minute)"
  priv mkdir -p "$HH_VOICE_ROOT"
  priv rm -rf "$dir"
  # Schlägt irgendein Schritt fehl (z. B. kein Internet), halben Ordner wegräumen – der nächste Lauf beginnt sauber.
  if ! { priv "$PY" -m venv "$dir" \
         && priv "$dir/bin/pip" install --quiet --disable-pip-version-check --upgrade pip \
         && priv "$dir/bin/pip" install --quiet --disable-pip-version-check "$@"; }; then
    priv rm -rf "$dir"
    echo "Voice-$name: pip install fehlgeschlagen" >&2
    return 1
  fi
  printf '%s\n' "$want" | priv tee "$mark" > /dev/null
  CHANGED="$CHANGED $name"
}
# Nur fertige Pakete; pysilero-vad gibt es für Intel-Macs nur als Quellcode (Xcode-Kommandozeilenwerkzeuge).
# Sichere Array-Schreibweise für /bin/bash 3.2 (tests/test_mac_bash32.py).
ensure_venv stt --only-binary=:all: --no-binary=pysilero-vad ${STT_PINS[@]+"${STT_PINS[@]}"}
ensure_venv tts --only-binary=:all: ${TTS_PINS[@]+"${TTS_PINS[@]}"}

# --- 2) Modelle/Stimmen gehören dem Dienstnutzer ------------------------------------------------------------------
STT_DATA="$HH_DATA_DIR/voice/stt"
TTS_DATA="$HH_DATA_DIR/voice/tts"
priv mkdir -p "$STT_DATA" "$TTS_DATA" "$HH_LOG_DIR"
priv chown -R "$HH_USER" "$STT_DATA"
priv chown -R "$HH_USER" "$TTS_DATA"

# --- 3) Dienste (Dienstnutzer, nur 127.0.0.1) ---------------------------------------------------------------------
xml() { local s="$1"; s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; printf '%s' "$s"; }
write_plist() {   # $1=plist $2=Label $3=Log $4=Ordner (HOME, gehört dem Dienstnutzer) $5..=Programm + Argumente
  local plist="$1" label="$2" logf="$3" home="$4"; shift 4
  local args="" a
  for a in "$@"; do args="$args        <string>$(xml "$a")</string>"$'\n'; done
  priv tee "$plist" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$label</string>
    <key>UserName</key>
    <string>$(xml "$HH_USER")</string>
    <key>ProgramArguments</key>
    <array>
$args    </array>
    <key>WorkingDirectory</key>
    <string>$(xml "$home")</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>$(xml "$home")</string>
        <key>HF_HOME</key>
        <string>$(xml "$home/.cache/huggingface")</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$(xml "$logf")</string>
    <key>StandardErrorPath</key>
    <string>$(xml "$logf")</string>
</dict>
</plist>
EOF
  priv chmod 644 "$plist"
}

STT_LOG="$HH_LOG_DIR/hydrahive2-voice-stt.log"
TTS_LOG="$HH_LOG_DIR/hydrahive2-voice-tts.log"
# HOME = eigener Ordner des Dienstes: huggingface_hub legt dort seinen Cache an. Lag HOME im root-Ordner voice/,
# scheiterte der Modell-Download mit „Permission denied“ (Befund Mac 22.10.2026).
write_plist "$HH_VOICE_STT_PLIST" io.hydrahive.voice-stt "$STT_LOG" "$STT_DATA" \
  "$HH_VOICE_ROOT/stt/bin/wyoming-faster-whisper" --model small --uri "tcp://127.0.0.1:$STT_PORT" \
  --data-dir "$STT_DATA" --compute-type int8 --beam-size 1 --vad-filter --initial-prompt "$STT_PROMPT"
write_plist "$HH_VOICE_TTS_PLIST" io.hydrahive.voice-tts "$TTS_LOG" "$TTS_DATA" \
  "$HH_VOICE_ROOT/tts/bin/python" -m wyoming_piper --voice de_DE-thorsten-medium --uri "tcp://127.0.0.1:$TTS_PORT" \
  --data-dir "$TTS_DATA" --download-dir "$TTS_DATA"

is_running() { priv launchctl list 2>/dev/null | awk -v l="$1" '$3 == l && $1 ~ /^[0-9]+$/' | grep -q .; }
reload() {   # $1=Name $2=Label $3=plist
  if [[ " $CHANGED " == *" $1 "* ]] || ! is_running "$2"; then
    priv launchctl unload "$3" >/dev/null 2>&1 || true
    priv launchctl load "$3"
  fi
}
reload stt io.hydrahive.voice-stt "$HH_VOICE_STT_PLIST"
reload tts io.hydrahive.voice-tts "$HH_VOICE_TTS_PLIST"

# --- 4) Warten, bis Whisper antwortet (erster Start lädt das Modell, ~460 MB) -------------------------------------
whisper_ready() {
  if [ -n "$HH_VOICE_PROBE" ]; then "$HH_VOICE_PROBE" "$STT_PORT"; return; fi
  "$HH_VOICE_ROOT/stt/bin/python" - "$STT_PORT" <<'PY' >/dev/null 2>&1
import socket, sys
with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=2) as s:
    s.settimeout(3)
    s.sendall(b'{"type": "describe"}\n')
    sys.exit(0 if s.recv(64).startswith(b'{"type": "info"') else 1)
PY
}
log "Warte auf die Spracherkennung (beim ersten Start wird das Sprachmodell geladen)"
i=0
until whisper_ready; do
  i=$((i + 1))
  if [ "$i" -gt "${HH_VOICE_WAIT:-300}" ]; then
    echo "Spracherkennung antwortet nicht – siehe $STT_LOG" >&2
    exit 1
  fi
  sleep 1
done

# --- 5) Wunsch merken ------------------------------------------------------------------------------------------
CONF="$HH_CONFIG_DIR/install.conf"
[ "$(hh_conf_get "$CONF" HH_INSTALL_VOICE || true)" = "yes" ] || hh_conf_set "$CONF" HH_INSTALL_VOICE yes

log "Voice bereit – Mikrofon im Chat und Vorlesen funktionieren jetzt"
