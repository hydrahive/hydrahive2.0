#!/bin/bash
# macOS: Tailscale ohne App – `tailscaled` als Dienst (Plan docs/plans/mac-tailscale.md). Gegenstück zu
# installer/modules/80-tailscale.sh (Linux).
#
# Die Tailscale-App verlangt beim ersten Start eine Freigabe am Bildschirm (Systemerweiterung/VPN). Die offizielle
# Variante „open source tailscaled“ (tailscale.com/kb/1065/macos-variants) läuft ohne Oberfläche, vor der Anmeldung
# und ohne Freigabe. Fertige Mac-Dateien gibt es dafür nicht: Go (feste Version + SHA-256) wird in einen
# Wegwerf-Ordner geladen und baut tailscale/tailscaled in fester Version (~1 min).
#
# Ist die Tailscale-App schon installiert, macht das Skript nichts – beide gleichzeitig vertragen sich nicht.
# Läuft aus install-mac.sh, update-mac.sh und dem Zusatz-Module-Runner. Idempotent.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

HH_USER="${HH_USER:?HH_USER fehlt}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
HH_TS_ROOT="${HH_TS_ROOT:-/usr/local/lib/hydrahive2/tailscale}"
HH_TS_PLIST="${HH_TS_PLIST:-/Library/LaunchDaemons/io.hydrahive.tailscaled.plist}"
HH_TS_APP="${HH_TS_APP:-/Applications/Tailscale.app}"
HH_GO_DOWNLOAD="${HH_GO_DOWNLOAD:-https://go.dev/dl}"
TS_STATE_DIR="$HH_DATA_DIR/tailscale"

TS_VERSION="1.104.2"
GO_VERSION="1.27.3"

priv() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

if [ -d "$HH_TS_APP" ]; then
  log "Tailscale-App ist installiert – nutze sie (keine zweite Installation, beide vertragen sich nicht)"
  exit 0
fi

case "${HH_TS_ARCH:-$(uname -m)}" in
  arm64)  GO_FILE="go${GO_VERSION}.darwin-arm64.tar.gz"
          GO_SHA="dd3908cf20959d798c1e06ebe5b72213f0505ce01373b40ce3110975a6cd99c2" ;;
  x86_64) GO_FILE="go${GO_VERSION}.darwin-amd64.tar.gz"
          GO_SHA="b6f8e931e4ab497fcde6da8ae4499a58f9d258e55c8a80824a516eae5950a750" ;;
  *) echo "Tailscale: unbekannte Mac-Architektur $(uname -m)" >&2; exit 1 ;;
esac
GO_SHA="${HH_TS_TEST_GO_SHA:-$GO_SHA}"   # nur Tests

VER_DIR="$HH_TS_ROOT/$TS_VERSION"
BIN="$HH_TS_ROOT/bin"

# --- 1) Bauen, wenn diese Version fehlt ------------------------------------------------------------------------
if [ ! -x "$VER_DIR/tailscaled" ] || [ ! -x "$VER_DIR/tailscale" ]; then
  log "Baue Tailscale $TS_VERSION (Go $GO_VERSION, etwa eine Minute)"
  work="$(mktemp -d)"
  # Go legt den Modul-Cache schreibgeschützt an – zum Aufräumen erst Schreibrechte geben.
  trap 'chmod -R u+w "$work" 2>/dev/null; rm -rf "$work"' EXIT
  curl -fsSL --retry 3 -o "$work/go.tgz" "$HH_GO_DOWNLOAD/$GO_FILE"
  got="$(shasum -a 256 "$work/go.tgz" | awk '{print $1}')"
  if [ "$got" != "$GO_SHA" ]; then
    echo "Prüfsumme falsch für $GO_FILE (erwartet $GO_SHA, erhalten $got) – Abbruch" >&2
    exit 1
  fi
  tar -xzf "$work/go.tgz" -C "$work"
  mkdir -p "$work/out"
  env -i HOME="$work" PATH="$work/go/bin:/usr/bin:/bin" GOPATH="$work/gopath" GOCACHE="$work/gocache" \
    GOBIN="$work/out" GOTOOLCHAIN=local GOFLAGS=-trimpath CGO_ENABLED=1 \
    "$work/go/bin/go" install \
      -ldflags "-X tailscale.com/version.longStamp=$TS_VERSION-hydrahive -X tailscale.com/version.shortStamp=$TS_VERSION" \
      "tailscale.com/cmd/tailscale@v$TS_VERSION" "tailscale.com/cmd/tailscaled@v$TS_VERSION"
  priv mkdir -p "$VER_DIR"
  priv install -m 0755 "$work/out/tailscale" "$VER_DIR/tailscale"
  priv install -m 0755 "$work/out/tailscaled" "$VER_DIR/tailscaled"
  NEW_BUILD=1
else
  log "Tailscale $TS_VERSION bereits gebaut"
  NEW_BUILD=""
fi
priv mkdir -p "$BIN"
priv ln -sfn "$VER_DIR/tailscale" "$BIN/tailscale"
priv ln -sfn "$VER_DIR/tailscaled" "$BIN/tailscaled"

# --- 2) Dienst (root – tailscaled braucht das utun-Gerät) --------------------------------------------------------
priv mkdir -p "$TS_STATE_DIR" "$HH_LOG_DIR"
priv chmod 700 "$TS_STATE_DIR"
log "Schreibe $HH_TS_PLIST"
priv tee "$HH_TS_PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.tailscaled</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BIN/tailscaled</string>
        <string>--state=$TS_STATE_DIR/tailscaled.state</string>
        <string>--statedir=$TS_STATE_DIR</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HH_LOG_DIR/hydrahive2-tailscaled.log</string>
    <key>StandardErrorPath</key>
    <string>$HH_LOG_DIR/hydrahive2-tailscaled.log</string>
</dict>
</plist>
EOF
priv chmod 644 "$HH_TS_PLIST"
running=""
priv launchctl list 2>/dev/null | awk '$3 == "io.hydrahive.tailscaled" && $1 ~ /^[0-9]+$/' | grep -q . && running=1
if [ -n "$NEW_BUILD" ] || [ -z "$running" ]; then
  priv launchctl unload "$HH_TS_PLIST" >/dev/null 2>&1 || true
  priv launchctl load "$HH_TS_PLIST"
fi

# --- 3) HydraHive darf tailscale bedienen (up/logout/status ohne sudo) ------------------------------------------
i=0
until priv "$BIN/tailscale" status --json >/dev/null 2>&1 || priv "$BIN/tailscale" status 2>&1 | grep -q -i "logged out\|NeedsLogin"; do
  i=$((i + 1))
  if [ "$i" -gt "${HH_TS_WAIT:-30}" ]; then
    echo "tailscaled antwortet nicht – siehe $HH_LOG_DIR/hydrahive2-tailscaled.log" >&2
    exit 1
  fi
  sleep 1
done
priv "$BIN/tailscale" set --operator="$HH_USER"
log "Bediener: $HH_USER"

# --- 4) Wunsch merken ------------------------------------------------------------------------------------------
CONF="$HH_CONFIG_DIR/install.conf"
if ! grep -q '^HH_INSTALL_TAILSCALE=yes' "$CONF" 2>/dev/null; then
  tmp_conf="$(mktemp)"
  { grep -v '^HH_INSTALL_TAILSCALE=' "$CONF" 2>/dev/null || true; echo "HH_INSTALL_TAILSCALE=yes"; } > "$tmp_conf"
  priv install -m 0640 "$tmp_conf" "$CONF"
  rm -f "$tmp_conf"
  priv chown "$HH_USER" "$CONF"
fi

log "Tailscale bereit – anmelden im Cockpit (Einstellungen → System → Tailscale)"
