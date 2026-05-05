#!/usr/bin/env bash
# HydraHive2 — Installer für Ubuntu / Debian.
#
# Voraussetzungen: läuft als root (sudo). Frische VM oder bestehender Server,
# Repo wurde nach /opt/hydrahive2 geklont (oder dieser Pfad existiert).
#
# Usage:
#   sudo ./install.sh                    # interaktiv (fragt z.B. nach Tailscale)
#   sudo ./install.sh --no-prompt        # keine Fragen, Defaults / ENV / install.conf
#   sudo ./install.sh --reconfigure      # alle Fragen erneut stellen
#   sudo HH_HOST=192.168.1.10 ./install.sh
#
# Antworten werden in /etc/hydrahive2/install.conf gespeichert. Re-Runs
# überspringen Fragen automatisch. ENV-Variablen vor dem Aufruf gewinnen über
# install.conf (z.B. sudo -E HH_INSTALL_TAILSCALE=no ./install.sh).
#
# Was passiert:
#   1. apt-Dependencies (python3.12, node, nginx)
#   2. System-User 'hydrahive' anlegen
#   3. Verzeichnisse /var/lib/hydrahive2 + /etc/hydrahive2
#   4. Python-venv im Repo, hydrahive-core via pip install -e
#   5. Frontend bauen (npm install + run build)
#   6. WhatsApp-Bridge: npm-Module installieren
#   7. systemd-Service installieren + starten
#   8. (optional) nginx-Reverse-Proxy
set -euo pipefail

# --------------------------------------------------------------- Konfiguration
HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
HH_HOST="${HH_HOST:-127.0.0.1}"
HH_PORT="${HH_PORT:-8001}"
# HH_INSTALL_*-Defaults: NICHT hier setzen — sonst überspringt der Wizard die Frage.
# Der Wizard setzt "yes" als Default in NO_PROMPT/no-TTY-Pfad (siehe prompt_component).

# --------------------------------------------------------------- Helfer
log() { printf "\033[1;36m[hh2-install]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-install]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR" ] || err "Repo-Verzeichnis $HH_REPO_DIR existiert nicht."

INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"

export HH_REPO_DIR HH_USER HH_DATA_DIR HH_CONFIG_DIR HH_HOST HH_PORT INSTALLER_DIR

# --------------------------------------------------------------- Pre-Flight Wizard
# Speichert Antworten in $HH_CONFIG_DIR/install.conf — Re-Runs fragen nicht erneut.
# Reihenfolge der Prioritäten: ENV > install.conf > interaktive Frage > Default.
#
# Flags:
#   --reconfigure   alle Fragen erneut stellen (auch wenn install.conf existiert)
#   --no-prompt     keine Fragen stellen, nur ENV / install.conf / Defaults
INSTALL_CONF="$HH_CONFIG_DIR/install.conf"
RECONFIGURE=0
NO_PROMPT=0
for arg in "$@"; do
  case "$arg" in
    --reconfigure) RECONFIGURE=1 ;;
    --no-prompt)   NO_PROMPT=1   ;;
  esac
done

is_tty() { [ -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; }

load_install_conf() {
  [ "$RECONFIGURE" = "1" ] && return 0
  [ -f "$INSTALL_CONF" ] || return 0
  log "Lade gespeicherte Antworten aus $INSTALL_CONF"
  # ENV gewinnt über install.conf — nur leere Variablen aus Datei nachziehen
  local key value
  while IFS='=' read -r key value; do
    case "$key" in ''|\#*) continue ;; esac
    value="${value#\"}"; value="${value%\"}"
    value="${value#\'}"; value="${value%\'}"
    if [ -z "${!key:-}" ]; then
      export "$key=$value"
    fi
  done < "$INSTALL_CONF"
}

CONF_VARS=(
  HH_INSTALL_TAILSCALE
  HH_INSTALL_POSTGRES
  HH_INSTALL_VOICE
  HH_INSTALL_CONTAINERS
  HH_INSTALL_VMS
  HH_INSTALL_AGENTLINK
  HH_INSTALL_NGINX
  HH_INSTALL_SAMBA
  HH_INSTALL_WHATSAPP
)

save_install_conf() {
  mkdir -p "$HH_CONFIG_DIR"
  {
    echo "# HydraHive2 install.conf — automatisch generiert"
    echo "# Bei sudo bash install.sh --reconfigure werden Werte erneut abgefragt."
    local v
    for v in "${CONF_VARS[@]}"; do
      echo "$v='${!v:-}'"
    done
    if [ -n "${HH_TAILSCALE_AUTHKEY:-}" ]; then
      echo "HH_TAILSCALE_AUTHKEY='${HH_TAILSCALE_AUTHKEY}'"
    fi
  } > "$INSTALL_CONF"
  chmod 600 "$INSTALL_CONF"
}

ask_yn() {
  # ask_yn <Frage> <Default y|n> → return 0 für ja, 1 für nein
  local q="$1" def="$2" prompt reply
  [ "$def" = "y" ] && prompt="$q [J/n] " || prompt="$q [j/N] "
  printf "%s" "$prompt" >/dev/tty
  read -r reply </dev/tty || reply=""
  [ -z "$reply" ] && reply="$def"
  case "$reply" in
    y|Y|j|J|yes|Yes|YES|ja|Ja|JA) return 0 ;;
    *) return 1 ;;
  esac
}

prompt_component() {
  # prompt_component VAR Default-y/n "Frage"
  local var="$1" def="$2" question="$3"
  # Bereits gesetzt (ENV oder install.conf): nicht fragen
  [ -n "${!var:-}" ] && return 0
  # Kein TTY oder --no-prompt: Default (rückwärts-kompatibel)
  if ! is_tty || [ "$NO_PROMPT" = "1" ]; then
    if [ "$def" = "y" ]; then export "$var=yes"; else export "$var=no"; fi
    return 0
  fi
  if ask_yn "$question" "$def"; then
    export "$var=yes"
  else
    export "$var=no"
  fi
}

run_wizard() {
  # Sichtbare Trennung zur log-Ausgabe oben
  if is_tty && [ "$NO_PROMPT" != "1" ] && {
       [ "$RECONFIGURE" = "1" ] || [ ! -f "$INSTALL_CONF" ]
     }; then
    printf "\n\033[1;36m── HydraHive2 Komponenten-Auswahl ──\033[0m\n" >/dev/tty
    printf "\033[1;36m   (Enter = Standard / Großbuchstabe)\033[0m\n\n" >/dev/tty
  fi
  prompt_component HH_INSTALL_TAILSCALE  y "Tailscale (VPN-Mesh) installieren?"
  # Tailscale-Auth-Key separat — nur fragen wenn Tailscale gewählt + interaktiv + Key noch leer
  if [ "${HH_INSTALL_TAILSCALE}" = "yes" ] \
     && [ -z "${HH_TAILSCALE_AUTHKEY:-}" ] \
     && is_tty && [ "$NO_PROMPT" != "1" ] \
     && { [ "$RECONFIGURE" = "1" ] || [ ! -f "$INSTALL_CONF" ]; }; then
    printf "  Tailscale Auth-Key (leer = später manuell verbinden): " >/dev/tty
    read -r HH_TAILSCALE_AUTHKEY </dev/tty || HH_TAILSCALE_AUTHKEY=""
  fi
  prompt_component HH_INSTALL_POSTGRES   y "PostgreSQL für Datamining-Mirror installieren?"
  prompt_component HH_INSTALL_VOICE      y "Voice-Stack (Whisper-STT in LXC + mmx-TTS)? [groß: ~30 min]"
  prompt_component HH_INSTALL_CONTAINERS y "Container-Manager (incus) installieren?"
  prompt_component HH_INSTALL_VMS        y "VM-Manager (QEMU/KVM + websockify) installieren?"
  prompt_component HH_INSTALL_AGENTLINK  y "HydraLink (AgentLink) installieren?"
  prompt_component HH_INSTALL_NGINX      y "nginx Reverse-Proxy installieren?"
  prompt_component HH_INSTALL_SAMBA      y "Samba für Projekt-Workspace-Shares?"
  prompt_component HH_INSTALL_WHATSAPP   y "WhatsApp-Bridge installieren?"

  # Voice braucht incus → Containers automatisch erzwingen wenn Voice gewählt
  if [ "${HH_INSTALL_VOICE}" = "yes" ] && [ "${HH_INSTALL_CONTAINERS}" = "no" ]; then
    log "Voice-Stack braucht Container-Manager → HH_INSTALL_CONTAINERS=yes erzwingen"
    HH_INSTALL_CONTAINERS=yes
  fi
}

load_install_conf
run_wizard
save_install_conf

export HH_INSTALL_TAILSCALE HH_TAILSCALE_AUTHKEY \
       HH_INSTALL_POSTGRES HH_INSTALL_VOICE HH_INSTALL_CONTAINERS \
       HH_INSTALL_VMS HH_INSTALL_AGENTLINK HH_INSTALL_NGINX \
       HH_INSTALL_SAMBA HH_INSTALL_WHATSAPP

# --------------------------------------------------------------- Module
log "Phase 1: System-Dependencies"
bash "$INSTALLER_DIR/modules/00-deps.sh"

log "Phase 2: System-User"
bash "$INSTALLER_DIR/modules/10-user.sh"

log "Phase 3: Verzeichnisse + Permissions"
bash "$INSTALLER_DIR/modules/20-paths.sh"

log "Phase 4: Python-venv + Backend"
bash "$INSTALLER_DIR/modules/30-python.sh"

log "Phase 5: Frontend"
bash "$INSTALLER_DIR/modules/40-frontend.sh"

if [ "${HH_INSTALL_WHATSAPP:-yes}" != "no" ]; then
  log "Phase 6: WhatsApp-Bridge"
  bash "$INSTALLER_DIR/modules/45-whatsapp.sh"
else
  log "Phase 6: WhatsApp-Bridge übersprungen (HH_INSTALL_WHATSAPP=no)"
fi

if [ "${HH_INSTALL_SAMBA:-yes}" != "no" ]; then
  log "Phase 7a: Samba (Projekt-Workspace-Shares)"
  bash "$INSTALLER_DIR/modules/47-samba.sh"
else
  log "Phase 7a: Samba übersprungen (HH_INSTALL_SAMBA=no)"
fi

if [ "${HH_INSTALL_POSTGRES:-yes}" != "no" ]; then
  log "Phase 7b: PostgreSQL Datamining-Mirror"
  bash "$INSTALLER_DIR/modules/48-postgres.sh"
else
  log "Phase 7b: PostgreSQL übersprungen (HH_INSTALL_POSTGRES=no)"
fi

log "Phase 7: systemd-Service"
bash "$INSTALLER_DIR/modules/50-systemd.sh"

if [ "${HH_INSTALL_NGINX:-yes}" != "no" ]; then
  log "Phase 8: nginx"
  bash "$INSTALLER_DIR/modules/60-nginx.sh"
else
  log "Phase 8: nginx übersprungen (HH_INSTALL_NGINX=no)"
fi

if [ "${HH_INSTALL_VMS:-yes}" != "no" ]; then
  log "Phase 9: VM-Manager (QEMU/KVM + websockify)"
  bash "$INSTALLER_DIR/modules/65-vms.sh"
else
  log "Phase 9: VM-Manager übersprungen (HH_INSTALL_VMS=no)"
fi

if [ "${HH_INSTALL_CONTAINERS:-yes}" != "no" ]; then
  log "Phase 10: Container-Manager (incus + dir-Storage)"
  bash "$INSTALLER_DIR/modules/70-containers.sh"
else
  log "Phase 10: Container-Manager übersprungen (HH_INSTALL_CONTAINERS=no)"
fi

if [ "${HH_INSTALL_VOICE:-yes}" != "no" ]; then
  log "Phase 10b: Voice-Stack (Wyoming-STT-LXC + mmx-TTS)"
  bash "$INSTALLER_DIR/modules/55-voice.sh"
else
  log "Phase 10b: Voice-Stack übersprungen (HH_INSTALL_VOICE=no)"
fi

if [ "${HH_INSTALL_AGENTLINK:-yes}" != "no" ]; then
  log "Phase 11: HydraLink (AgentLink)"
  bash "$INSTALLER_DIR/modules/75-agentlink.sh"
else
  log "Phase 11: HydraLink übersprungen (HH_INSTALL_AGENTLINK=no)"
fi

log "Phase 12: Tailscale"
if [ "${HH_INSTALL_TAILSCALE:-yes}" != "no" ]; then
  bash "$INSTALLER_DIR/modules/80-tailscale.sh"
else
  log "Tailscale übersprungen (HH_INSTALL_TAILSCALE=no)"
fi

# --------------------------------------------------------------- LLM-Provider-Wizard
# Fragt Provider-Keys ab und schreibt $HH_CONFIG_DIR/llm.json — damit der User
# nach dem ersten Login direkt chatten kann ohne unter /llm rumzuklicken.
# Skippt automatisch bei kein-TTY oder wenn llm.json schon Provider hat.
# shellcheck source=lib/llm-wizard.sh
source "$INSTALLER_DIR/lib/llm-wizard.sh"
# Wizard-Fehler dürfen den Installer nicht crashen — Provider sind später
# unter /llm nachtragbar.
llm_wizard || log "LLM-Wizard mit Fehler beendet — bitte Provider unter https://<server>/llm eintragen"

# Backend-Service neu starten damit der Mtime-Cache der LLM-Config neu lädt.
# (load_config() in core/llm/_config.py cached über mtime — wenn Datei schon
# vor Service-Start existiert hat, ist der Cache evtl. veraltet.)
if [ -f "$HH_CONFIG_DIR/llm.json" ]; then
  systemctl restart hydrahive2.service 2>/dev/null || true
fi

# ----------------------------------------------------------------- Zusammenfassung
# LAN-IP ermitteln — explizit Tailscale-Range (100.64.0.0/10 CGNAT) und
# Loopback ausschließen. `ip route get 1.1.1.1` greift sonst nach Tailscale-
# Interface wenn das Tailnet Subnet-Routes advertised hat.
SERVER_IP=$(hostname -I 2>/dev/null | tr ' ' '\n' \
  | grep -vE '^(127\.|169\.254\.|::1|fe80:|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.)' \
  | head -1)
if [ -z "$SERVER_IP" ]; then
  SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '/src/{print $7; exit}')
fi
SERVER_URL="https://${SERVER_IP:-<server-ip>}"

# Admin-Passwort: erst aus File (zuverlässig), Fallback journalctl seit Service-Start.
# Backend schreibt es nach $HH_CONFIG_DIR/.admin_initial_password sobald
# admin neu angelegt wurde (siehe lifespan.py).
ADMIN_PW=""
PW_FILE="$HH_CONFIG_DIR/.admin_initial_password"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if [ -f "$PW_FILE" ]; then
    ADMIN_PW=$(tr -d '\n' < "$PW_FILE")
    rm -f "$PW_FILE"
    break
  fi
  sleep 2
done
# Fallback: alte Installs ohne Datei oder Service noch nicht warm
if [ -z "$ADMIN_PW" ]; then
  ADMIN_PW=$(journalctl -u hydrahive2 --no-pager -b 2>/dev/null \
    | grep "Passwort:" | tail -1 | awk '{print $NF}')
fi
# Re-Install (admin existiert schon): keine Datei, kein Log → eigene Meldung
RE_INSTALL_HINT=""
if [ -z "$ADMIN_PW" ] && [ -f "$HH_DATA_DIR/sessions.db" ]; then
  RE_INSTALL_HINT="(Re-Install: admin existiert bereits. Passwort-Reset: HH_INITIAL_ADMIN_PASSWORD=neuesPw, dann sessions.db löschen + Service-Restart)"
fi

section() {
  printf "\n\033[1;32m── %s ──\033[0m\n" "$1"
}
kv()      { printf "  \033[1;37m%-22s\033[0m %s\n" "$1" "$2"; }
kv_pw()   { printf "  \033[1;37m%-22s\033[0m \033[1;33m%s\033[0m\n" "$1" "$2"; }
kv_hint() { printf "  \033[2;37m%-22s\033[0m \033[2;37m%s\033[0m\n" "$1" "$2"; }

is_yes() { [ "${1:-yes}" != "no" ]; }

printf "\n\033[1;32m╔══════════════════════════════════════════════╗\033[0m\n"
printf "\033[1;32m║        HydraHive2 — Installation fertig      ║\033[0m\n"
printf "\033[1;32m╚══════════════════════════════════════════════╝\033[0m\n"

section "Login"
kv "URL:" "$SERVER_URL"
kv "Benutzer:" "admin"
if [ -n "$ADMIN_PW" ]; then
  kv_pw "Passwort:" "$ADMIN_PW"
elif [ -n "$RE_INSTALL_HINT" ]; then
  kv "Passwort:" "(Re-Install — siehe unten)"
else
  kv "Passwort:" "(siehe: journalctl -u hydrahive2 -b)"
fi
kv_hint "Browser:" "Zertifikatswarnung mit 'Weiter'"
kv_hint "Wichtig:" "Passwort nach erstem Login ändern!"

section "System"
kv "Service:" "systemctl status hydrahive2"
kv "Logs:" "journalctl -u hydrahive2 -f"
kv "Datenpfad:" "$HH_DATA_DIR"
kv "Configpfad:" "$HH_CONFIG_DIR"
kv "Update-Trigger:" "sudo touch $HH_DATA_DIR/.update_request"
kv "Reconfigure:" "sudo bash $INSTALLER_DIR/install.sh --reconfigure"

INSTALLED=()
SKIPPED=()

if is_yes "${HH_INSTALL_POSTGRES:-yes}"; then
  section "PostgreSQL (Datamining-Mirror)"
  kv "DSN-Datei:" "$HH_CONFIG_DIR/pg_mirror.dsn"
  kv "Hinweis:" "Passwort steht in der DSN-Datei (chmod 600)"
  INSTALLED+=("postgres")
else
  SKIPPED+=("postgres")
fi

if is_yes "${HH_INSTALL_TAILSCALE:-yes}"; then
  section "Tailscale"
  if command -v tailscale >/dev/null 2>&1; then
    TS_STATE=$(tailscale status --json 2>/dev/null \
      | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("BackendState","?"))
except Exception:
    print("?")' 2>/dev/null || echo "?")
    TS_IP=$(tailscale ip -4 2>/dev/null | head -1 || echo "(noch nicht verbunden)")
    kv "Status:" "$TS_STATE"
    kv "Tailnet-IP:" "${TS_IP:-(noch nicht verbunden)}"
    kv "Verbinden:" "sudo tailscale up"
  else
    kv "Status:" "(tailscale-Binary fehlt)"
  fi
  INSTALLED+=("tailscale")
else
  SKIPPED+=("tailscale")
fi

if is_yes "${HH_INSTALL_VOICE:-yes}"; then
  section "Voice-Stack"
  kv "STT-Container:" "hydrahive2-stt (incus)"
  kv "STT-Port:" "127.0.0.1:10300 (Wyoming-Faster-Whisper)"
  kv "TTS:" "mmx-CLI (MiniMax) — als hydrahive-User"
  kv "STT-Logs:" "incus exec hydrahive2-stt -- journalctl -u wyoming-whisper -f"
  INSTALLED+=("voice")
else
  SKIPPED+=("voice")
fi

if is_yes "${HH_INSTALL_VMS:-yes}"; then
  section "VM-Manager"
  kv "VNC-Proxy:" "127.0.0.1:6080 (websockify)"
  kv "Service:" "systemctl status hydrahive2-websockify"
  kv "VM-Disks:" "$HH_DATA_DIR/vms/disks"
  if ! ip link show br0 >/dev/null 2>&1; then
    kv_hint "Achtung:" "br0 fehlt — bash $INSTALLER_DIR/setup-bridge.sh"
  fi
  INSTALLED+=("vms")
else
  SKIPPED+=("vms")
fi

if is_yes "${HH_INSTALL_CONTAINERS:-yes}"; then
  section "Container-Manager (incus)"
  kv "Status:" "incus list"
  kv "Storage:" "default (dir-Storage)"
  INSTALLED+=("containers")
else
  SKIPPED+=("containers")
fi

if is_yes "${HH_INSTALL_AGENTLINK:-yes}"; then
  section "HydraLink (AgentLink)"
  kv "Backend:" "http://127.0.0.1:9000"
  kv "Repo:" "/opt/hydralink"
  INSTALLED+=("agentlink")
else
  SKIPPED+=("agentlink")
fi

if is_yes "${HH_INSTALL_NGINX:-yes}"; then
  section "nginx"
  kv "Status:" "systemctl status nginx"
  kv "Config:" "/etc/nginx/sites-enabled/hydrahive2"
  INSTALLED+=("nginx")
else
  SKIPPED+=("nginx")
fi

if is_yes "${HH_INSTALL_SAMBA:-yes}"; then
  section "Samba (Projekt-Workspace-Shares)"
  kv "Config-Verzeichnis:" "/etc/samba/hh-projects.d/"
  kv "Status:" "systemctl status smbd"
  kv "Hinweis:" "Pro Projekt automatisch per API angelegt"
  INSTALLED+=("samba")
else
  SKIPPED+=("samba")
fi

if is_yes "${HH_INSTALL_WHATSAPP:-yes}"; then
  section "WhatsApp-Bridge"
  kv "Pfad:" "$HH_REPO_DIR/core/src/hydrahive/communication/whatsapp/bridge"
  kv "Hinweis:" "Pairing über die Web-UI (Settings → WhatsApp)"
  INSTALLED+=("whatsapp")
else
  SKIPPED+=("whatsapp")
fi

if [ ${#SKIPPED[@]} -gt 0 ]; then
  section "Übersprungen"
  printf "  \033[2;37m%s\033[0m\n" "${SKIPPED[*]}"
  kv_hint "Nachinstallieren:" "sudo bash $INSTALLER_DIR/install.sh --reconfigure"
fi

if [ -n "$RE_INSTALL_HINT" ]; then
  printf "\n\033[1;33m  %s\033[0m\n" "$RE_INSTALL_HINT"
fi
printf "\n"
