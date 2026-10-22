#!/usr/bin/env bash
# HydraHive2 — Installer für macOS (Homebrew).
#
# Voraussetzungen:
#   - macOS 13+ mit Homebrew installiert
#   - Repo nach /opt/hydrahive2 geklont (oder HH_REPO_DIR setzen)
#   - Als normaler User ausführen (sudo-Passwort wird abgefragt)
#
# Usage:
#   ./install-mac.sh
#   HH_HOST=0.0.0.0 ./install-mac.sh
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
# Zwei Rollen (docs/plans/mac-service-user.md):
#   HH_BREW_USER – ruft brew auf (Homebrew gehört dem Mac-Besitzer, verweigert root)
#   HH_USER      – Dienst-Nutzer: Besitzer von Repo/Daten, unter ihm laufen die Dienste. Standard: eigenes, verstecktes
#                  System-Konto _hydrahive – sonst sperrt macOS 15+ alles im Heimnetz („Lokales Netzwerk“).
#                  HH_USER=<Mac-Besitzer> setzen = alter Weg ohne eigenes Konto.
HH_BREW_USER="${HH_BREW_USER:-$(whoami)}"
HH_SERVICE_ACCOUNT=""
[ -z "${HH_USER:-}" ] && HH_SERVICE_ACCOUNT=yes
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_HOST="${HH_HOST:-127.0.0.1}"
HH_PORT="${HH_PORT:-8001}"
HH_INSTALL_NGINX="${HH_INSTALL_NGINX:-yes}"
HH_INSTALL_POSTGRES="${HH_INSTALL_POSTGRES:-yes}"
HH_INSTALL_AGENTLINK="${HH_INSTALL_AGENTLINK:-yes}"
# Container (Colima + Incus): Standard AUS – die VM kostet dauerhaft Arbeitsspeicher. Einschalten mit
# HH_INSTALL_CONTAINERS=yes oder --with=containers; später auch im Cockpit (Einstellungen → Zusatz-Module).
HH_INSTALL_CONTAINERS="${HH_INSTALL_CONTAINERS:-no}"
# Tailscale (ohne App, für Fernzugriff und Server-Kopplung): Standard AUS, --with=tailscale schaltet ein.
HH_INSTALL_TAILSCALE="${HH_INSTALL_TAILSCALE:-no}"
# Voice (Spracheingabe + Vorlesen, ohne Container): Standard AUS – Sprachmodell ~460 MB, ~400 MB RAM. --with=voice.
HH_INSTALL_VOICE="${HH_INSTALL_VOICE:-no}"
for arg in "$@"; do
  case "$arg" in
    --with=*)
      case ",${arg#--with=}," in *,containers,*) HH_INSTALL_CONTAINERS=yes ;; esac
      case ",${arg#--with=}," in *,tailscale,*) HH_INSTALL_TAILSCALE=yes ;; esac
      case ",${arg#--with=}," in *,voice,*) HH_INSTALL_VOICE=yes ;; esac ;;
  esac
done

log() { printf "\033[1;36m[hh2-mac]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-mac]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || err "Nur für macOS."
[ "$HH_BREW_USER" != "root" ] || err "Bitte als normaler Mac-Nutzer starten, nicht als root (Homebrew verweigert root)."
[ -d "$HH_REPO_DIR" ] || err "Repo nicht gefunden: $HH_REPO_DIR"
command -v brew >/dev/null 2>&1 || err "Homebrew fehlt. Installieren: https://brew.sh"

INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"
# Befehle als Dienst-Konto (sudo -u) brauchen einen Ordner, den das Konto lesen darf – sonst getcwd-Fehler,
# wenn der Installer aus dem eigenen Home gestartet wird (Machbarkeit 22.10.2026).
cd /tmp

if [ -n "$HH_SERVICE_ACCOUNT" ]; then
  log "Phase 0: Dienst-Konto (HydraHive läuft nicht als dein Nutzer – sonst sperrt macOS das Heimnetz)"
  HH_USER="$(bash "$INSTALLER_DIR/lib/mac-service-user.sh" | tail -1)" || err "Dienst-Konto konnte nicht angelegt werden."
  [ -n "$HH_USER" ] || err "Dienst-Konto konnte nicht angelegt werden."
else
  log "Phase 0: kein eigenes Dienst-Konto (HH_USER=$HH_USER gesetzt)"
fi
export HH_BREW_USER
export HH_REPO_DIR HH_USER HH_DATA_DIR HH_CONFIG_DIR HH_HOST HH_PORT INSTALLER_DIR HH_INSTALL_AGENTLINK HH_INSTALL_CONTAINERS HH_INSTALL_TAILSCALE HH_INSTALL_VOICE

log "Phase 1: System-Dependencies"
bash "$INSTALLER_DIR/modules-mac/00-deps.sh"

log "Phase 2: Verzeichnisse"
bash "$INSTALLER_DIR/modules-mac/20-paths.sh"
# Merker für update-mac.sh: diese Installation läuft schon unter dem Dienst-Konto (kein Umzug nötig).
if [ -n "$HH_SERVICE_ACCOUNT" ]; then
  ( source "$INSTALLER_DIR/lib/mac-roles.sh" && hh_conf_set "$HH_CONFIG_DIR/install.conf" HH_SERVICE_USER "$HH_USER" )
fi

log "Phase 3: Python-venv + Backend"
bash "$INSTALLER_DIR/modules-mac/30-python.sh"

log "Phase 4: Frontend"
bash "$INSTALLER_DIR/modules-mac/40-frontend.sh"

if [ "${HH_INSTALL_POSTGRES}" != "no" ]; then
  log "Phase 5: PostgreSQL Datamining-Mirror"
  bash "$INSTALLER_DIR/modules-mac/48-postgres.sh"
else
  log "Phase 5: PostgreSQL übersprungen"
fi

log "Phase 6: launchd-Service"
bash "$INSTALLER_DIR/modules-mac/50-launchd.sh"

log "Phase 6b: Update- und Restart-Trigger"
bash "$INSTALLER_DIR/modules-mac/55-launchd-triggers.sh"
bash "$INSTALLER_DIR/lib/mac-addon-trigger.sh"

# AgentLink braucht PostgreSQL (eigene Datenbank im postgresql@16 des Kerns).
if [ "${HH_INSTALL_AGENTLINK}" != "no" ] && [ "${HH_INSTALL_POSTGRES}" != "no" ]; then
  log "Phase 6c: AgentLink (HydraLink)"
  bash "$INSTALLER_DIR/modules-mac/75-agentlink.sh" \
    || log "AgentLink-Installation FEHLGESCHLAGEN – Agenten können sich nicht gegenseitig beauftragen. Nachholen: bash $INSTALLER_DIR/modules-mac/75-agentlink.sh"
else
  log "Phase 6c: AgentLink übersprungen"
fi

if [ "${HH_INSTALL_CONTAINERS}" = "yes" ]; then
  log "Phase 6d: Container (Colima + Incus)"
  if bash "$INSTALLER_DIR/modules-mac/70-containers.sh"; then
    # Backend-PATH um die Container-Werkzeuge erweitern (50-launchd.sh nimmt den Ordner auf, wenn er existiert).
    bash "$INSTALLER_DIR/modules-mac/50-launchd.sh"
  else
    log "Container-Installation FEHLGESCHLAGEN – nachholen im Cockpit (Einstellungen → Zusatz-Module)"
  fi
else
  log "Phase 6d: Container übersprungen (Option: --with=containers)"
fi

if [ "${HH_INSTALL_TAILSCALE}" = "yes" ]; then
  log "Phase 6e: Tailscale (ohne App)"
  if bash "$INSTALLER_DIR/modules-mac/80-tailscale.sh"; then
    bash "$INSTALLER_DIR/modules-mac/50-launchd.sh"          # Backend-PATH mit tailscale
  else
    log "Tailscale-Installation FEHLGESCHLAGEN – nachholen im Cockpit (Einstellungen → Zusatz-Module)"
  fi
else
  log "Phase 6e: Tailscale übersprungen (Option: --with=tailscale)"
fi

if [ "${HH_INSTALL_VOICE}" = "yes" ]; then
  log "Phase 6f: Voice (Spracheingabe + Vorlesen)"
  bash "$INSTALLER_DIR/modules-mac/55-voice.sh" \
    || log "Voice-Installation FEHLGESCHLAGEN – nachholen im Cockpit (Einstellungen → Zusatz-Module)"
else
  log "Phase 6f: Voice übersprungen (Option: --with=voice)"
fi

if [ "${HH_INSTALL_NGINX}" != "no" ]; then
  log "Phase 7: nginx"
  bash "$INSTALLER_DIR/modules-mac/60-nginx.sh"
else
  log "Phase 7: nginx übersprungen"
fi

SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "<ip>")
SERVER_URL="https://${SERVER_IP}"

log "Warte auf den ersten Start (Admin-Passwort) …"
# Die Datei gehört dem Dienst-Konto (0600) – lesen und löschen darf der Installer nur über sudo.
ADMIN_PW="$(sudo env "HH_CONFIG_DIR=$HH_CONFIG_DIR" bash "$INSTALLER_DIR/lib/mac-admin-password.sh")"

printf "\n"
printf "\033[1;32m╔══════════════════════════════════════════════╗\033[0m\n"
printf "\033[1;32m║     HydraHive2 — Installation fertig (Mac)   ║\033[0m\n"
printf "\033[1;32m╠══════════════════════════════════════════════╣\033[0m\n"
printf "\033[1;32m║\033[0m  URL:       \033[1;37m%-33s\033[0m\033[1;32m║\033[0m\n" "$SERVER_URL"
printf "\033[1;32m║\033[0m  Benutzer:  \033[1;37m%-33s\033[0m\033[1;32m║\033[0m\n" "admin"
if [ -n "$ADMIN_PW" ]; then
  printf "\033[1;32m║\033[0m  Passwort:  \033[1;33m%-33s\033[0m\033[1;32m║\033[0m\n" "$ADMIN_PW"
else
  printf "\033[1;32m║\033[0m  Passwort:  \033[1;33m%-33s\033[0m\033[1;32m║\033[0m\n" "(nicht neu – siehe Anleitung)"
fi
printf "\033[1;32m╠══════════════════════════════════════════════╣\033[0m\n"
printf "\033[1;32m║\033[0m  Service:   launchctl list io.hydrahive.backend\033[1;32m ║\033[0m\n"
printf "\033[1;32m╚══════════════════════════════════════════════╝\033[0m\n"
printf "\n"
