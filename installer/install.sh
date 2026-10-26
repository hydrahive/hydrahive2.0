#!/usr/bin/env bash
# HydraHive2 — Installer für Ubuntu / Debian.
#
# Voraussetzungen: läuft als root (sudo). Frische VM oder bestehender Server,
# Repo wurde nach /opt/hydrahive2 geklont (oder dieser Pfad existiert).
#
# Usage:
#   sudo ./install.sh                    # Kern ohne Fragen (Backend, Oberfläche, PostgreSQL, nginx, HydraLink)
#   sudo ./install.sh --with=voice,vms   # Kern + genannte Zusatz-Module
#   sudo ./install.sh --all              # Kern + alle Zusatz-Module (bisheriges Verhalten, ohne Local Media)
#   sudo ./install.sh --reconfigure      # Zusatz-Module einzeln abfragen
#   sudo HH_HOST=192.168.1.10 ./install.sh
#
# Zusatz-Module (Tailscale, Voice, Container, VMs, Samba, WhatsApp, Local Media) sind bei neuen Installationen
# AUS und lassen sich später im Admin-Cockpit → System → Zusatz-Module nachinstallieren
# (docs/specs/installer-core-first.md). Die Auswahl steht in /etc/hydrahive2/install.conf; ENV-Variablen vor dem
# Aufruf gewinnen über install.conf (z.B. sudo -E HH_INSTALL_VOICE=yes ./install.sh).
#
# Was passiert:
#   1. apt-Dependencies (System-Python >= 3.12, node, nginx)
#   2. System-User 'hydrahive' anlegen
#   3. Verzeichnisse /var/lib/hydrahive2 + /etc/hydrahive2
#   4. Python-venv im Repo, hydrahive-core via pip install -e
#   5. Frontend bauen (npm install + run build)
#   6. WhatsApp-Bridge: npm-Module installieren
#   7. systemd-Service installieren + starten
#   8. (optional) nginx-Reverse-Proxy
set -euo pipefail

# --------------------------------------------------------------- Konfiguration
HH_REPO_DIR_EXPLICIT="${HH_REPO_DIR:-}"   # vom User gesetzt? (leer = Auto-Detect)
HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
HH_HOST="${HH_HOST:-127.0.0.1}"
HH_PORT="${HH_PORT:-8001}"
# HH_INSTALL_*-Defaults: NICHT hier setzen — die Auswahl (lib/install-choices.sh) setzt Zusatz-Module auf „no“,
# Kern-Teile (PostgreSQL, nginx, HydraLink) bleiben leer = an.

# --------------------------------------------------------------- Helfer
log() { printf "\033[1;36m[hh2-install]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-install]\033[0m %s\n" "$*" >&2; exit 1; }
# Wie err(), aber ohne Abbruch — für Fehler, die die Installation nicht
# wertlos machen, aber sichtbar bleiben müssen.
err_soft() { printf "\033[1;31m[hh2-install]\033[0m %s\n" "$*" >&2; }
AGENTLINK_FAILED=0

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."

INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"

# Repo-Root robust ermitteln: der Installer liegt IMMER unter <repo>/installer/.
# Damit funktioniert ./install.sh aus jedem Clone-Pfad — nicht nur /opt/hydrahive2.
DETECTED_REPO_DIR="$(dirname "$INSTALLER_DIR")"

if [ -n "$HH_REPO_DIR_EXPLICIT" ]; then
  # HH_REPO_DIR wurde explizit per ENV gesetzt → respektieren, nur prüfen.
  [ -d "$HH_REPO_DIR" ] || err "HH_REPO_DIR=$HH_REPO_DIR existiert nicht."
elif [ "$DETECTED_REPO_DIR" != "$HH_REPO_DIR" ]; then
  # Repo liegt nicht am kanonischen Ziel. Der systemd-Service läuft als
  # '$HH_USER'-User; /root und private Home-Dirs sind Mode 700 → der Service
  # könnte das Repo nicht lesen. Darum nach $HH_REPO_DIR verschieben und von
  # dort neu starten (re-exec). mv && exec in EINER Zeile: bash hat das Kommando
  # dann vollständig im Speicher, bevor das Skript-File unter ihm wegbewegt wird.
  if [ -e "$HH_REPO_DIR" ]; then
    err "Repo unter $DETECTED_REPO_DIR erkannt, aber $HH_REPO_DIR existiert bereits.
     Bitte 'rm -rf $HH_REPO_DIR' (wenn kaputt/leer) ODER
     'HH_REPO_DIR=$DETECTED_REPO_DIR ./install.sh' aus $INSTALLER_DIR starten."
  fi
  log "Repo unter $DETECTED_REPO_DIR erkannt — verschiebe nach $HH_REPO_DIR (world-readable für den $HH_USER-Service) und starte neu ..."
  mkdir -p "$(dirname "$HH_REPO_DIR")"
  export HH_REPO_DIR
  mv "$DETECTED_REPO_DIR" "$HH_REPO_DIR" && exec "$HH_REPO_DIR/installer/$(basename "$0")" "$@"
fi

[ -d "$HH_REPO_DIR" ] || err "Repo-Verzeichnis $HH_REPO_DIR existiert nicht."

export HH_REPO_DIR HH_USER HH_DATA_DIR HH_CONFIG_DIR HH_HOST HH_PORT INSTALLER_DIR

# --------------------------------------------------------------- Auswahl der Zusatz-Module
# Kern (immer): Backend, Oberfläche, PostgreSQL, nginx, HydraLink. Zusatz-Module bei neuen Installationen AUS
# (docs/specs/installer-core-first.md). Reihenfolge: ENV > install.conf > --with/--all > „no“.
#
# Flags:
#   --reconfigure   Zusatz-Module einzeln abfragen (Standard jeweils „N“)
#   --with=a,b      genannte Zusatz-Module mitinstallieren (tailscale voice containers vms samba whatsapp local_media)
#   --all           alle Zusatz-Module außer Local Media (bisheriges Verhalten)
#   --no-prompt     (bleibt aus Kompatibilität; es wird ohnehin nicht mehr gefragt)
# >>> Auswahl (Block wird in core/tests/test_install_sh_core_first.py echt ausgeführt)
INSTALL_CONF="$HH_CONFIG_DIR/install.conf"
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
  HH_INSTALL_LOCAL_MEDIA
)

RECONFIGURE=0
for arg in "$@"; do
  case "$arg" in
    --reconfigure) RECONFIGURE=1 ;;
  esac
done

is_tty() { [ -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; }

# shellcheck source=lib/install-choices.sh
source "$INSTALLER_DIR/lib/install-choices.sh"
hh_choices_parse_args "$@" || err "Ungültige Option (siehe oben)."

load_install_conf() {
  [ "$RECONFIGURE" = "1" ] && return 0
  [ -f "$INSTALL_CONF" ] || return 0
  log "Lade gespeicherte Auswahl aus $INSTALL_CONF"
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

save_install_conf() {
  mkdir -p "$HH_CONFIG_DIR"
  {
    echo "# HydraHive2 install.conf — automatisch generiert"
    echo "# Zusatz-Module nachinstallieren: Admin-Cockpit → System → Zusatz-Module (oder install.sh --reconfigure)."
    local v
    for v in "${CONF_VARS[@]}"; do
      if [ -n "${!v:-}" ]; then echo "$v='${!v}'"; fi
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
  # prompt_component VAR Default-y/n "Frage" — nur bei --reconfigure mit Terminal
  local var="$1" def="$2" question="$3"
  [ -n "${!var:-}" ] && return 0
  if ask_yn "$question" "$def"; then export "$var=yes"; else export "$var=no"; fi
}

load_install_conf
if [ "$RECONFIGURE" = "1" ] && is_tty; then
  printf "\n\033[1;36m── HydraHive2 Zusatz-Module ──\033[0m\n" >/dev/tty
  printf "\033[1;36m   Kern (Oberfläche, PostgreSQL, nginx, HydraLink) wird immer installiert.\033[0m\n" >/dev/tty
  printf "\033[1;36m   Alles hier lässt sich auch später im Admin-Cockpit nachinstallieren.\033[0m\n\n" >/dev/tty
  prompt_component HH_INSTALL_TAILSCALE  n "Tailscale (VPN-Mesh) installieren?"
  if [ "${HH_INSTALL_TAILSCALE}" = "yes" ] && [ -z "${HH_TAILSCALE_AUTHKEY:-}" ]; then
    printf "  Tailscale Auth-Key (leer = später manuell verbinden): " >/dev/tty
    read -r HH_TAILSCALE_AUTHKEY </dev/tty || HH_TAILSCALE_AUTHKEY=""
  fi
  prompt_component HH_INSTALL_VOICE      n "Voice-Stack (Whisper-STT in LXC + mmx-TTS)? [groß: ~30 min]"
  prompt_component HH_INSTALL_CONTAINERS n "Container-Manager (incus) installieren?"
  prompt_component HH_INSTALL_VMS        n "VM-Manager (QEMU/KVM + websockify) installieren?"
  prompt_component HH_INSTALL_SAMBA      n "Samba für Projekt-Workspace-Shares?"
  prompt_component HH_INSTALL_WHATSAPP   n "WhatsApp-Bridge installieren?"
  # ~33 GB Download, braucht NVIDIA-GPU ab 12 GB Grafikspeicher.
  prompt_component HH_INSTALL_LOCAL_MEDIA n "Lokale Bild-/Videogenerierung (ComfyUI, NVIDIA ab 12 GB)? [groß: ~33 GB]"
fi
hh_choices_apply_defaults
save_install_conf
# <<< Auswahl

export HH_INSTALL_TAILSCALE HH_TAILSCALE_AUTHKEY \
       HH_INSTALL_POSTGRES HH_INSTALL_VOICE HH_INSTALL_CONTAINERS \
       HH_INSTALL_VMS HH_INSTALL_AGENTLINK HH_INSTALL_NGINX \
       HH_INSTALL_SAMBA HH_INSTALL_WHATSAPP HH_INSTALL_LOCAL_MEDIA

# --------------------------------------------------------------- Vorab-Prüfung
# shellcheck source=lib/preflight.sh
source "$INSTALLER_DIR/lib/preflight.sh"
hh_apt_retries
hh_preflight_dns || err "Abbruch vor der Installation: keine Namensauflösung (Hinweise oben)."

# --------------------------------------------------------------- Module
log "Phase 1: System-Dependencies"
bash "$INSTALLER_DIR/modules/00-deps.sh"

# Automatische Sicherheitsupdates + Dienst-Neustarts danach (docs/specs/system-updates.md).
# shellcheck source=lib/system-upgrade.sh
source "$INSTALLER_DIR/lib/system-upgrade.sh"
hh_ensure_auto_updates

log "Phase 2: System-User"
bash "$INSTALLER_DIR/modules/10-user.sh"

log "Phase 3: Verzeichnisse + Permissions"
bash "$INSTALLER_DIR/modules/20-paths.sh"

log "Phase 4: Python-venv + Backend"
bash "$INSTALLER_DIR/modules/30-python.sh"

log "Phase 4b: llmfit für lokale Modellbewertung"
if ! bash "$INSTALLER_DIR/modules/35-llmfit.sh"; then
  err_soft "llmfit-Installation fehlgeschlagen — Ollama-Verwaltung funktioniert, Hardware-Fit bleibt vorerst unbekannt."
fi

log "Phase 4d: graphify für den Code-Graph"
# shellcheck source=lib/graphify.sh
source "$INSTALLER_DIR/lib/graphify.sh"
ensure_graphify

# Local Media nur auf ausdrücklichen Wunsch (Standard nein). Der Marker sorgt
# dafür, dass update.sh die Runtime danach weiter pflegt. Ein Fehler bricht
# die Installation nicht ab; nachholen geht im System-Fenster.
if [ "${HH_INSTALL_LOCAL_MEDIA:-no}" = "yes" ]; then
  log "Phase 4c: Local Media Runtime (ComfyUI)"
  if bash "$INSTALLER_DIR/modules/72-local-media.sh"; then
    date +%s > "$HH_CONFIG_DIR/local-media.enabled"
  else
    err_soft "Local Media Runtime nicht eingerichtet — später im System-Fenster nachholen."
  fi
else
  log "Phase 4c: Local Media übersprungen (HH_INSTALL_LOCAL_MEDIA=no, nachträglich im System-Fenster)"
fi

log "Phase 5: Frontend"
bash "$INSTALLER_DIR/modules/40-frontend.sh"

log "Phase 5b: Browser-Werkzeug für Agenten"
# shellcheck source=lib/dev-browser.sh
source "$INSTALLER_DIR/lib/dev-browser.sh"
ensure_dev_browser

if [ "${HH_INSTALL_WHATSAPP:-no}" != "no" ]; then
  log "Phase 6: WhatsApp-Bridge"
  bash "$INSTALLER_DIR/modules/45-whatsapp.sh"
else
  log "Phase 6: WhatsApp-Bridge übersprungen (HH_INSTALL_WHATSAPP=no)"
fi

if [ "${HH_INSTALL_SAMBA:-no}" != "no" ]; then
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

if [ "${HH_INSTALL_VMS:-no}" != "no" ]; then
  log "Phase 9: VM-Manager (QEMU/KVM + websockify)"
  bash "$INSTALLER_DIR/modules/65-vms.sh"
else
  log "Phase 9: VM-Manager übersprungen (HH_INSTALL_VMS=no)"
fi

if [ "${HH_INSTALL_CONTAINERS:-no}" != "no" ]; then
  log "Phase 10: Container-Manager (incus + dir-Storage)"
  bash "$INSTALLER_DIR/modules/70-containers.sh"
else
  log "Phase 10: Container-Manager übersprungen (HH_INSTALL_CONTAINERS=no)"
fi

if [ "${HH_INSTALL_VOICE:-no}" != "no" ]; then
  log "Phase 10b: Voice-Stack (Wyoming-STT-LXC + mmx-TTS)"
  bash "$INSTALLER_DIR/modules/55-voice.sh"
else
  log "Phase 10b: Voice-Stack übersprungen (HH_INSTALL_VOICE=no)"
fi

if [ "${HH_INSTALL_AGENTLINK:-yes}" != "no" ]; then
  log "Phase 11: HydraLink (AgentLink) — Pflichtkomponente"
  # Kein hartes Abbrechen: eine sonst fehlerfreie Installation soll nutzbar
  # bleiben. Der Fehlschlag wird stattdessen laut protokolliert und in der
  # Abschlussübersicht wiederholt — AgentLink ist Pflicht, ein stilles
  # Übergehen wäre irreführend.
  if ! bash "$INSTALLER_DIR/modules/75-agentlink.sh"; then
    AGENTLINK_FAILED=1
    err_soft "HydraLink-Installation FEHLGESCHLAGEN — Agenten können sich nicht
     gegenseitig beauftragen (ask_agent fehlt). Details oben im Log.
     Nachholen mit: sudo bash $INSTALLER_DIR/modules/75-agentlink.sh"
  fi
else
  AGENTLINK_FAILED=1
  log "Phase 11: HydraLink übersprungen (HH_INSTALL_AGENTLINK=no) — ask_agent steht NICHT zur Verfügung"
fi

log "Phase 12: Tailscale"
if [ "${HH_INSTALL_TAILSCALE:-no}" != "no" ]; then
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
kv "Zusatz-Module:" "Admin-Cockpit → System → Zusatz-Module"
kv_hint "oder:" "sudo bash $INSTALLER_DIR/install.sh --reconfigure"

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

if is_yes "${HH_INSTALL_TAILSCALE:-no}"; then
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

if is_yes "${HH_INSTALL_VOICE:-no}"; then
  section "Voice-Stack"
  kv "STT-Container:" "hydrahive2-stt (incus)"
  kv "STT-Port:" "127.0.0.1:10300 (Wyoming-Faster-Whisper)"
  kv "TTS:" "mmx-CLI (MiniMax) — als hydrahive-User"
  kv "STT-Logs:" "incus exec hydrahive2-stt -- journalctl -u wyoming-whisper -f"
  INSTALLED+=("voice")
else
  SKIPPED+=("voice")
fi

if is_yes "${HH_INSTALL_VMS:-no}"; then
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

if is_yes "${HH_INSTALL_CONTAINERS:-no}"; then
  section "Container-Manager (incus)"
  kv "Status:" "incus list"
  kv "Storage:" "default (dir-Storage)"
  INSTALLED+=("containers")
else
  SKIPPED+=("containers")
fi

if [ "${AGENTLINK_FAILED:-0}" = "1" ]; then
  section "HydraLink (AgentLink) — FEHLT"
  kv "Status:" "NICHT INSTALLIERT — Agenten können sich nicht beauftragen"
  kv "Folge:" "ask_agent steht nicht zur Verfügung"
  kv "Nachholen:" "sudo bash $INSTALLER_DIR/modules/75-agentlink.sh"
  SKIPPED+=("agentlink (FEHLGESCHLAGEN)")
elif is_yes "${HH_INSTALL_AGENTLINK:-yes}"; then
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

if is_yes "${HH_INSTALL_SAMBA:-no}"; then
  section "Samba (Projekt-Workspace-Shares)"
  kv "Config-Verzeichnis:" "/etc/samba/hh-projects.d/"
  kv "Status:" "systemctl status smbd"
  kv "Hinweis:" "Pro Projekt automatisch per API angelegt"
  INSTALLED+=("samba")
else
  SKIPPED+=("samba")
fi

if is_yes "${HH_INSTALL_WHATSAPP:-no}"; then
  section "WhatsApp-Bridge"
  kv "Pfad:" "$HH_REPO_DIR/core/src/hydrahive/communication/whatsapp/bridge"
  kv "Hinweis:" "Pairing über die Web-UI (Settings → WhatsApp)"
  INSTALLED+=("whatsapp")
else
  SKIPPED+=("whatsapp")
fi

if [ -f "$HH_CONFIG_DIR/local-media.enabled" ]; then
  section "Lokale Bild-/Videogenerierung"
  kv "ComfyUI:" "127.0.0.1:8188 (Docker hydra-comfyui)"
  kv "Entfernen:" "System-Fenster → Lokale Bild-/Videogenerierung"
  INSTALLED+=("local-media")
else
  SKIPPED+=("local-media")
fi

if [ ${#SKIPPED[@]} -gt 0 ]; then
  section "Nicht installiert (Zusatz-Module)"
  printf "  \033[2;37m%s\033[0m\n" "${SKIPPED[*]}"
  kv_hint "Nachinstallieren:" "Admin-Cockpit → System → Zusatz-Module"
  kv_hint "oder:" "sudo bash $INSTALLER_DIR/install.sh --reconfigure"
  if hh_is_wsl; then
    kv_hint "WSL:" "VMs, Container und Voice laufen unter WSL meist nicht"
  fi
fi

if [ -n "$RE_INSTALL_HINT" ]; then
  printf "\n\033[1;33m  %s\033[0m\n" "$RE_INSTALL_HINT"
fi
printf "\n"
