#!/bin/bash
# macOS: Container über Colima + Incus (Plan docs/plans/mac-containers.md). Gegenstück zu modules/70-containers.sh.
#
# Incus läuft in einer kleinen Linux-VM (Colima, Apple Virtualization). Colima richtet den `incus`-Befehl am Mac so
# ein, dass er die VM anspricht – der Kern nutzt ihn wie unter Linux (containers/incus_client.py).
#
# Werkzeuge kommen als fertige Dateien von GitHub, nicht aus Homebrew: Homebrew hat für Intel-Macs keine fertigen
# Pakete von lima/colima/incus mehr und würde sie aus dem Quellcode bauen. Jede Datei wird gegen die hier fest
# hinterlegte SHA-256 geprüft – passt eine nicht, bricht das Skript ab, bevor etwas installiert ist.
#
# Läuft aus install-mac.sh (als Nutzer, sudo bei Bedarf), update-mac.sh und dem Zusatz-Module-Runner (beide root).
# Idempotent. Abschalten: nicht aufrufen (Standard aus, HH_INSTALL_CONTAINERS=yes schaltet ein).
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

HH_USER="${HH_USER:?HH_USER fehlt}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
HH_CT_ROOT="${HH_CT_ROOT:-/usr/local/lib/hydrahive2/containers}"
HH_CT_PLIST="${HH_CT_PLIST:-/Library/LaunchDaemons/io.hydrahive.colima.plist}"
HH_CT_DOWNLOAD="${HH_CT_DOWNLOAD:-https://github.com}"
COLIMA_HOME="${COLIMA_HOME:-$HH_DATA_DIR/colima}"
PROFILE="hydrahive"

COLIMA_VERSION="0.10.3"
LIMA_VERSION="2.2.1"
INCUS_VERSION="7.0.2"

as_root() { [ "$(id -u)" -eq 0 ]; }
as_user() { if as_root; then sudo -u "$HH_USER" env "PATH=$PATH" "HOME=$(_home)" "COLIMA_HOME=$COLIMA_HOME" "$@"; else "$@"; fi; }
priv() { if as_root; then "$@"; else sudo "$@"; fi; }
_home() { local h; h="$(dscl . -read "/Users/$HH_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}' || true)"; echo "${h:-/Users/$HH_USER}"; }

# --- Architektur + feste Prüfsummen (Release-Dateien der Projekte, Stand 21.10.2026) -----------------------
case "${HH_CT_ARCH:-$(uname -m)}" in
  arm64)
    COLIMA_FILE="colima-Darwin-arm64"
    COLIMA_SHA="980ad8bf61a4ca370243f4cb41401a61276dcd2c2502bee7b9b86f9250169f34"
    LIMA_FILE="lima-${LIMA_VERSION}-Darwin-arm64.tar.gz"
    LIMA_SHA="9e9eacce88f37e185c346bad73aa6136f738d8cdf8c3bb23cd42b071824bc66e"
    INCUS_FILE="bin.macos.incus.aarch64"
    INCUS_SHA="12aa325c9437223bbdcb8da754e0aafdff948fc168f7537140460f20267762c8" ;;
  x86_64)
    COLIMA_FILE="colima-Darwin-x86_64"
    COLIMA_SHA="3082737fe8a98afda11cba7d9a20b6e56fe80c6153464beda04bec630758770b"
    LIMA_FILE="lima-${LIMA_VERSION}-Darwin-x86_64.tar.gz"
    LIMA_SHA="6b776e4bc41f358e6ee01fefcc78e2eb26f11635a0fcff632234af77a566c6c4"
    INCUS_FILE="bin.macos.incus.x86_64"
    INCUS_SHA="a67f1507e299d1995d69ad4cf5d73f2fc81319aab8fc95102dc741f52370e092" ;;
  *) echo "Container: unbekannte Mac-Architektur $(uname -m)" >&2; exit 1 ;;
esac
# Nur Tests: eigene Prüfsummen für Schein-Dateien (nie in Installationen gesetzt).
COLIMA_SHA="${HH_CT_TEST_COLIMA_SHA:-$COLIMA_SHA}"
LIMA_SHA="${HH_CT_TEST_LIMA_SHA:-$LIMA_SHA}"
INCUS_SHA="${HH_CT_TEST_INCUS_SHA:-$INCUS_SHA}"

# --- Größe der VM: Wünsche, gedeckelt auf die Hälfte von Kernen und Arbeitsspeicher -----------------------
host_cpus="$(sysctl -n hw.ncpu 2>/dev/null || echo 2)"
host_gb="$(( $(sysctl -n hw.memsize 2>/dev/null || echo 8589934592) / 1073741824 ))"
CPU="${HH_CONTAINERS_CPU:-2}"
MEM="${HH_CONTAINERS_MEMORY:-4}"
DISK="${HH_CONTAINERS_DISK:-60}"
[ "$CPU" -gt $(( host_cpus / 2 )) ] && CPU=$(( host_cpus / 2 ))
[ "$CPU" -lt 1 ] && CPU=1
[ "$MEM" -gt $(( host_gb / 2 )) ] && MEM=$(( host_gb / 2 ))
[ "$MEM" -lt 2 ] && MEM=2

VER_DIR="$HH_CT_ROOT/colima-${COLIMA_VERSION}_lima-${LIMA_VERSION}_incus-${INCUS_VERSION}"
BIN="$HH_CT_ROOT/bin"

fetch() {  # fetch URL ZIEL SHA256
  local url="$1" dst="$2" sha="$3" got
  curl -fsSL --retry 3 -o "$dst" "$url"
  got="$(shasum -a 256 "$dst" | awk '{print $1}')"
  if [ "$got" != "$sha" ]; then
    rm -f "$dst"
    echo "Prüfsumme falsch für $(basename "$url") (erwartet $sha, erhalten $got) – Abbruch" >&2
    exit 1
  fi
}

# --- 1) Werkzeuge (nur wenn diese Versionen fehlen) -------------------------------------------------------
if [ ! -x "$VER_DIR/bin/colima" ] || [ ! -x "$VER_DIR/bin/incus" ] || [ ! -x "$VER_DIR/lima/bin/limactl" ]; then
  log "Lade Colima $COLIMA_VERSION, Lima $LIMA_VERSION, Incus $INCUS_VERSION"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  fetch "$HH_CT_DOWNLOAD/abiosoft/colima/releases/download/v$COLIMA_VERSION/$COLIMA_FILE" "$tmp/colima" "$COLIMA_SHA"
  fetch "$HH_CT_DOWNLOAD/lima-vm/lima/releases/download/v$LIMA_VERSION/$LIMA_FILE" "$tmp/lima.tgz" "$LIMA_SHA"
  fetch "$HH_CT_DOWNLOAD/lxc/incus/releases/download/v$INCUS_VERSION/$INCUS_FILE" "$tmp/incus" "$INCUS_SHA"
  priv mkdir -p "$VER_DIR/bin" "$VER_DIR/lima"
  priv tar -xzf "$tmp/lima.tgz" -C "$VER_DIR/lima"
  priv install -m 0755 "$tmp/colima" "$VER_DIR/bin/colima"
  priv install -m 0755 "$tmp/incus" "$VER_DIR/bin/incus"
  # Gatekeeper: aus dem Netz geladene Dateien tragen ggf. die Quarantäne-Markierung.
  priv xattr -dr com.apple.quarantine "$VER_DIR" 2>/dev/null || true
else
  log "Container-Werkzeuge bereits vorhanden ($VER_DIR)"
fi
# Ein bin-Ordner für den Kern (PATH der plist): colima, incus, limactl der aktuellen Version.
priv mkdir -p "$BIN"
priv ln -sfn "$VER_DIR/bin/colima" "$BIN/colima"
priv ln -sfn "$VER_DIR/bin/incus" "$BIN/incus"
for f in "$VER_DIR"/lima/bin/*; do priv ln -sfn "$f" "$BIN/$(basename "$f")"; done
priv chown -R "$HH_USER" "$HH_CT_ROOT"
export PATH="$BIN:$PATH"

# --- 2) VM einmal anlegen bzw. starten ------------------------------------------------------------------------
priv mkdir -p "$COLIMA_HOME" "$HH_LOG_DIR"
priv chown -R "$HH_USER" "$COLIMA_HOME"
# Läuft die VM schon unter dem Dienst (Update), bleibt sie unberührt – kein Neustart der Container.
DAEMON_UP=""
if [ -f "$HH_CT_PLIST" ] && as_user colima status "$PROFILE" >/dev/null 2>&1; then
  DAEMON_UP=1
fi
start_vm() {
  as_user colima start "$PROFILE" --runtime incus --vm-type vz --cpu "$CPU" --memory "$MEM" --disk "$DISK" \
    --network-address
}
if ! as_user colima status "$PROFILE" >/dev/null 2>&1; then
  log "Starte Container-VM ($CPU Kerne, $MEM GB, $DISK GB) – beim ersten Mal einige Minuten"
  # Erster Start: Colima richtet Incus ein; die SSH-Sitzung für den Socket kennt die neue Gruppe manchmal noch
  # nicht → „error starting incus … EOF“. Ein zweiter Start klappt (Befund 21.10.2026, Test-Mac).
  if ! start_vm; then
    log "Erster Start unvollständig – starte die VM einmal neu"
    as_user colima stop "$PROFILE" >/dev/null 2>&1 || true
    start_vm || { echo "Container-VM startet nicht – siehe Ausgabe oben" >&2; exit 1; }
  fi
fi

# --- 3) NAT-Netz wie auf Servern ohne br0 (installer/lib/container-nat.sh) ----------------------------------
if as_user incus network show hhnat0 >/dev/null 2>&1; then
  log "NAT-Netz hhnat0 vorhanden"
else
  log "NAT-Netz hhnat0 anlegen (10.10.0.1/24)"
  as_user incus network create hhnat0 ipv4.address=10.10.0.1/24 ipv4.nat=true ipv6.address=none \
    ipv4.dhcp.ranges=10.10.0.200-10.10.0.250
fi

# --- 4) Dienst: startet die VM beim Hochfahren, ohne Anmeldung -----------------------------------------------
# Die VM gehört dem Dienst. Läuft sie aus Schritt 2 noch außerhalb, endet `colima start --foreground` sofort mit
# „already running“ und launchd startet es alle 10 s neu (Befund 21.10.2026). Darum dann vorher anhalten.
if [ -z "$DAEMON_UP" ] && as_user colima status "$PROFILE" >/dev/null 2>&1; then
  log "VM an den Dienst übergeben"
  as_user colima stop "$PROFILE" >/dev/null 2>&1 || true
fi
log "Schreibe $HH_CT_PLIST"
priv tee "$HH_CT_PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.colima</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BIN/colima</string>
        <string>start</string>
        <string>$PROFILE</string>
        <string>--foreground</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$BIN:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>HOME</key>
        <string>$(_home)</string>
        <key>COLIMA_HOME</key>
        <string>$COLIMA_HOME</string>
    </dict>
    <key>UserName</key>
    <string>$HH_USER</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ExitTimeOut</key>
    <integer>120</integer>
    <key>StandardOutPath</key>
    <string>$HH_LOG_DIR/hydrahive2-colima.log</string>
    <key>StandardErrorPath</key>
    <string>$HH_LOG_DIR/hydrahive2-colima.log</string>
</dict>
</plist>
EOF
priv chmod 644 "$HH_CT_PLIST"
if [ -z "$DAEMON_UP" ]; then
  priv launchctl unload "$HH_CT_PLIST" >/dev/null 2>&1 || true
  priv launchctl load "$HH_CT_PLIST"
fi
# Warten, bis der Dienst die VM wieder hochgefahren hat – danach erwartet der Kern einen erreichbaren incus.
i=0
until as_user incus info >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt "${HH_CT_WAIT:-90}" ]; then
    echo "Container-VM antwortet nach dem Start durch den Dienst nicht – siehe $HH_LOG_DIR/hydrahive2-colima.log" >&2
    exit 1
  fi
  sleep 2
done

# --- 5) Wunsch merken (update-mac.sh pflegt das Modul dann mit; Cockpit zeigt „gewünscht“) ------------------
CONF="$HH_CONFIG_DIR/install.conf"
if ! grep -q '^HH_INSTALL_CONTAINERS=yes' "$CONF" 2>/dev/null; then
  # Ohne `sed -i` (BSD und GNU verstehen es verschieden): alte Zeile weg, neue anhängen, Datei ersetzen.
  { grep -v '^HH_INSTALL_CONTAINERS=' "$CONF" 2>/dev/null || true; echo "HH_INSTALL_CONTAINERS=yes"; } > "$COLIMA_HOME/.install.conf.new"
  priv install -m 0640 "$COLIMA_HOME/.install.conf.new" "$CONF"
  rm -f "$COLIMA_HOME/.install.conf.new"
  priv chown "$HH_USER" "$CONF"
fi

log "Container bereit (Incus in der VM $PROFILE)"
