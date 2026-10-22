#!/usr/bin/env bash
# HydraHive2 — Self-Update für macOS (launchd-Variante).
# Wird von io.hydrahive.update LaunchDaemon aufgerufen wenn
# $HH_DATA_DIR/.update_request erscheint.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
# Dienstnutzer = Besitzer des Repos (der Installer legt es als dieser Nutzer an).
# Früher fest „admin“ – beim Update von Hand liefen git/pip dann unter dem falschen Nutzer.
HH_USER="${HH_USER:-$(ls -ld "$HH_REPO_DIR" 2>/dev/null | awk '{print $3}')}"
HH_USER="${HH_USER:-admin}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
BACKEND_PLIST="${HH_BACKEND_PLIST:-/Library/LaunchDaemons/io.hydrahive.backend.plist}"
LOG="${HH_UPDATE_LOG:-/usr/local/var/log/hydrahive2-update.log}"

UPDATE_PLIST="${HH_UPDATE_PLIST:-/Library/LaunchDaemons/io.hydrahive.update.plist}"
TRIGGERS_SCRIPT="${HH_TRIGGERS_SCRIPT:-$HH_REPO_DIR/installer/modules-mac/55-launchd-triggers.sh}"

# Über den Knopf startet launchd das Skript und leitet stdout/stderr schon in $LOG (55-launchd-triggers.sh).
# Dann nur auf stdout schreiben – sonst steht jede Zeile doppelt im Verlauf. Im Terminal: Datei + Bildschirm.
# (Der Vergleich `[ /dev/stdout -ef "$LOG" ]` meldet auf macOS „verschieden“, darum die Kennung.)
if [ "${HH_UPDATE_VIA_LAUNCHD:-}" = "1" ]; then
  to_log() { cat; }
else
  to_log() { tee -a "$LOG"; }
fi
log() { printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | to_log; }

# Schlusszeile für das Update-Fenster (frontend/src/shared/_updateLogStatus.ts): genau einmal, auch bei Abbruch.
# Das Fenster wartete sonst bis zu 10 min auf einen neuen Commit (Befund 22.10.2026).
HH_FAIL_REASON=""
fail() { HH_FAIL_REASON="$*"; log "$*"; exit 1; }
_hh_end() {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    printf 'HH-UPDATE-ENDE: ok\n' | to_log
  else
    printf 'HH-UPDATE-ENDE: fehler %s\n' "${HH_FAIL_REASON:-Abbruch (Code $rc) – siehe Log}" | to_log
  fi
}
trap _hh_end EXIT

rm -f "$HH_DATA_DIR/.update_request"
log "Update gestartet"

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"
# Als root (Update-Dienst) verweigert `brew shellenv` – Homebrew-bin dann über den vollen Pfad in den PATH, sonst
# finden npm/node nichts (Befund 21.10.2026: „env: npm: No such file or directory“).
HH_BREW="${HH_BREW:-}"
if [ -z "$HH_BREW" ]; then
  for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [ -x "$candidate" ]; then HH_BREW="$candidate"; break; fi
  done
fi
[ -n "$HH_BREW" ] && PATH="$(dirname "$HH_BREW"):$PATH" && export PATH

cd "$HH_REPO_DIR"
# git immer als Dienstnutzer – als root lehnt git das fremde Repo ab („dubious ownership“, docs/specs/mac-update.md).
sudo -u "$HH_USER" git pull --ff-only 2>&1 | to_log || fail "git pull fehlgeschlagen"

log "Python-Pakete aktualisieren"
sudo -u "$HH_USER" "$HH_REPO_DIR/.venv/bin/pip" install -e "$HH_REPO_DIR/core" >> "$LOG" 2>&1 \
  || fail "pip install fehlgeschlagen"
HEAL="$HH_REPO_DIR/installer/lib/mac-python-heal.sh"
if [ -f "$HEAL" ]; then
  # shellcheck source=lib/mac-python-heal.sh
  source "$HEAL"
  hh_mac_heal_python "$HH_REPO_DIR/.venv/bin" "$HH_USER" "$LOG"
else
  log "Paketprüfung übersprungen ($HEAL fehlt)"
fi

# Frontend neu bauen, wenn der Build nicht zum aktuellen Stand unter frontend/ passt (Vermerk im Build,
# docs/specs/mac-update.md §4) – holt so auch Builds nach, die frühere Updates verpasst haben.
DIST="$HH_REPO_DIR/frontend/dist"
MARK="$DIST/.hh-frontend-rev"
FRONTEND_REV="$(sudo -u "$HH_USER" git log -1 --format=%H -- frontend/ 2>>"$LOG" || true)"
BUILD=""
if [ ! -f "$DIST/index.html" ]; then
  BUILD="kein fertiger Build"
elif [ -z "$FRONTEND_REV" ]; then
  log "Frontend-Stand unbekannt (git) – vorhandener Build bleibt"
elif [ "$(cat "$MARK" 2>/dev/null || true)" != "$FRONTEND_REV" ]; then
  BUILD="neuer Stand"
fi
if [ -n "$BUILD" ]; then
  log "Frontend neu bauen ($BUILD)"
  cd "$HH_REPO_DIR/frontend"
  # npm ci: genau nach package-lock.json, ändert sie nie (npm install schrieb sie um → nächstes git pull scheiterte)
  # PATH mitgeben: sudo setzt secure_path ohne Homebrew → „sudo: npm: command not found“ (Befund 21.10.2026).
  sudo -u "$HH_USER" env "PATH=$PATH" npm ci --no-fund --no-audit >> "$LOG" 2>&1 || fail "npm ci fehlgeschlagen"
  sudo -u "$HH_USER" env "PATH=$PATH" npm run build >> "$LOG" 2>&1 || fail "Frontend-Build fehlgeschlagen"
  [ -n "$FRONTEND_REV" ] && printf '%s\n' "$FRONTEND_REV" | sudo -u "$HH_USER" tee "$MARK" > /dev/null
  cd "$HH_REPO_DIR"
fi

# PostgreSQL lief früher als brew-services-LaunchAgent (startet erst nach der Anmeldung).
# Einmalig auf den LaunchDaemon umstellen – nur wenn HydraHive die Datenbank nutzt.
PG_PLIST="${HH_PG_PLIST:-/Library/LaunchDaemons/io.hydrahive.postgres.plist}"
if [ -s "$HH_CONFIG_DIR/pg_mirror.dsn" ] && [ ! -f "$PG_PLIST" ]; then
  log "PostgreSQL auf LaunchDaemon umstellen (Start ohne Anmeldung)"
  HH_USER="$HH_USER" HH_PG_PLIST="$PG_PLIST" bash "$HH_REPO_DIR/installer/lib/mac-postgres-daemon.sh" 2>&1 | to_log \
    || log "PostgreSQL-Umstellung fehlgeschlagen – Datamining evtl. erst nach Anmeldung (Log oben)"
fi

# Update-Auslöser ohne Kennung (ältere Installation) neu einrichten – gilt ab dem nächsten Update.
if [ -f "$UPDATE_PLIST" ] && ! grep -q "HH_UPDATE_VIA_LAUNCHD" "$UPDATE_PLIST" 2>/dev/null; then
  log "Update-Auslöser neu einrichten (Verlauf ohne doppelte Zeilen ab dem nächsten Update)"
  HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_REPO_DIR="$HH_REPO_DIR" \
    bash "$TRIGGERS_SCRIPT" 2>&1 | to_log || log "Update-Auslöser konnten nicht neu eingerichtet werden"
fi

# Update-Dienst nicht geladen (Folge eines alten Fehlers: der Dienst entlud sich beim Knopf-Update selbst) →
# wieder laden, damit der Knopf im Cockpit wieder funktioniert. Läuft das Update gerade über den Dienst, ist er geladen.
if [ -f "$UPDATE_PLIST" ] && ! launchctl list 2>/dev/null | awk '$3 == "io.hydrahive.update"' | grep -q .; then
  log "Update-Dienst war nicht geladen – Knopf im Cockpit wieder einschalten"
  launchctl load "$UPDATE_PLIST" 2>&1 | to_log || log "Update-Dienst konnte nicht geladen werden"
fi

# AgentLink (HydraLink): fehlte früher auf jedem Mac (Plan docs/plans/mac-agentlink.md). Bei jedem Update
# nachrüsten bzw. aktualisieren – vor dem Backend-Neustart, damit der Kern sich gleich verbindet.
# Ein Fehlschlag bricht das Update nicht ab, wird aber deutlich gemeldet (wie Linux, update.sh).
if [ "${HH_INSTALL_AGENTLINK:-yes}" != "no" ] && [ -s "$HH_CONFIG_DIR/pg_mirror.dsn" ] \
   && [ -f "$HH_REPO_DIR/installer/modules-mac/75-agentlink.sh" ]; then
  log "AgentLink (HydraLink) installieren bzw. aktualisieren"
  if ! HH_USER="$HH_USER" bash "$HH_REPO_DIR/installer/modules-mac/75-agentlink.sh" 2>&1 | to_log; then
    log "AgentLink-Update FEHLGESCHLAGEN – Agenten können sich nicht gegenseitig beauftragen (ask_agent). Nachholen: sudo HH_USER=$HH_USER bash $HH_REPO_DIR/installer/modules-mac/75-agentlink.sh"
  fi
fi

# Zusatz-Module (Container): Auslöser für das Cockpit nachrüsten; gewünschte Container mitpflegen
# (neue Werkzeug-Versionen, Dienst). docs/plans/mac-containers.md.
ADDON_PLIST="${HH_ADDON_PLIST:-/Library/LaunchDaemons/io.hydrahive.addon.plist}"
if [ ! -f "$ADDON_PLIST" ] && [ -f "$HH_REPO_DIR/installer/lib/mac-addon-trigger.sh" ]; then
  log "Zusatz-Module-Auslöser einrichten (Einstellungen → Zusatz-Module)"
  HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" HH_REPO_DIR="$HH_REPO_DIR" \
    bash "$HH_REPO_DIR/installer/lib/mac-addon-trigger.sh" 2>&1 | to_log || log "Zusatz-Module-Auslöser fehlgeschlagen"
fi
if grep -q '^HH_INSTALL_CONTAINERS=yes' "$HH_CONFIG_DIR/install.conf" 2>/dev/null \
   && [ -f "$HH_REPO_DIR/installer/modules-mac/70-containers.sh" ]; then
  log "Container (Colima + Incus) aktualisieren"
  if ! HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" \
       bash "$HH_REPO_DIR/installer/modules-mac/70-containers.sh" 2>&1 | to_log; then
    log "Container-Update FEHLGESCHLAGEN – Container evtl. nicht erreichbar (Log oben)"
  fi
fi

if grep -q '^HH_INSTALL_VOICE=yes' "$HH_CONFIG_DIR/install.conf" 2>/dev/null \
   && [ -f "$HH_REPO_DIR/installer/modules-mac/55-voice.sh" ]; then
  log "Voice (Spracheingabe + Vorlesen) aktualisieren"
  if ! HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" \
       bash "$HH_REPO_DIR/installer/modules-mac/55-voice.sh" 2>&1 | to_log; then
    log "Voice-Update FEHLGESCHLAGEN – Spracheingabe/Vorlesen evtl. gestört (Log oben)"
  fi
fi

if grep -q '^HH_INSTALL_TAILSCALE=yes' "$HH_CONFIG_DIR/install.conf" 2>/dev/null \
   && [ -f "$HH_REPO_DIR/installer/modules-mac/80-tailscale.sh" ]; then
  log "Tailscale (ohne App) aktualisieren"
  if ! HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" \
       bash "$HH_REPO_DIR/installer/modules-mac/80-tailscale.sh" 2>&1 | to_log; then
    log "Tailscale-Update FEHLGESCHLAGEN – Fernzugriff/Kopplung evtl. gestört (Log oben)"
  fi
fi

# nginx-Konfiguration nachziehen, wenn ein Merkmal fehlt (AgentLink-Wege, Kopplung nur aus dem Tailnet,
# Sicherheits-Kopfzeilen, Modul-Sandbox). 60-nginx.sh kommt frisch aus dem git pull oben.
BREW_PREFIX="/usr/local"
[ -x /opt/homebrew/bin/brew ] && BREW_PREFIX="/opt/homebrew"
NGINX_CONF="$BREW_PREFIX/etc/nginx/servers/hydrahive2.conf"
if [ -f "$NGINX_CONF" ]; then
  NEEDS_NGINX=""
  for marker in hh_agentlink_auth hh_peering_tailnet hh_module_sandbox hh_security_headers; do
    grep -q "$marker" "$NGINX_CONF" || NEEDS_NGINX=1
  done
  if [ -n "$NEEDS_NGINX" ]; then
    log "nginx-Konfiguration neu schreiben (AgentLink, Kopplung nur aus dem Tailnet, Sicherheits-Kopfzeilen)"
    HH_USER="$HH_USER" HH_CONFIG_DIR="$HH_CONFIG_DIR" HH_REPO_DIR="$HH_REPO_DIR" \
      HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" \
      bash "$HH_REPO_DIR/installer/modules-mac/60-nginx.sh" 2>&1 | to_log \
      || log "nginx-Umbau fehlgeschlagen – alte Konfiguration bleibt (Log oben)"
  fi
fi

# Alte plists enthalten HH_SECRET_KEY + PG-DSN im Klartext (0644, für alle
# lesbar). Dann neu schreiben lassen: 50-launchd.sh übernimmt den BESTEHENDEN
# Schlüssel aus secret_key, startet über mac-backend-start.sh und lädt neu.
# Das Skript kommt frisch aus dem git pull oben.
# Ohne Zeitlimit beim Herunterfahren hängt uvicorn an offenen SSE-Verbindungen (Task 06d38ae9).
if grep -q "HH_SECRET_KEY\|HH_PG_MIRROR_DSN" "$BACKEND_PLIST" 2>/dev/null \
   || ! grep -q "mac-backend-start.sh" "$BACKEND_PLIST" 2>/dev/null \
   || ! grep -q -- "--timeout-graceful-shutdown" "$BACKEND_PLIST" 2>/dev/null \
   || ! grep -q "HH_LOG_DIR" "$BACKEND_PLIST" 2>/dev/null \
   || { [ -d /usr/local/lib/hydrahive2/containers/bin ] && ! grep -q "/usr/local/lib/hydrahive2/containers/bin" "$BACKEND_PLIST" 2>/dev/null; } \
   || { [ -d /usr/local/lib/hydrahive2/tailscale/bin ] && ! grep -q "/usr/local/lib/hydrahive2/tailscale/bin" "$BACKEND_PLIST" 2>/dev/null; } \
   || { [ -x "${HH_ARM_BREW_PREFIX:-/opt/homebrew}/bin/brew" ] \
        && ! grep -q "${HH_ARM_BREW_PREFIX:-/opt/homebrew}/bin" "$BACKEND_PLIST" 2>/dev/null; }; then
  log "launchd-plist enthält Secrets, keinen Start-Wrapper, kein Zeitlimit oder keinen Log-Ordner — neu schreiben"
  HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" \
    HH_REPO_DIR="$HH_REPO_DIR" HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" \
    HH_BACKEND_PLIST="$BACKEND_PLIST" \
    bash "$HH_REPO_DIR/installer/modules-mac/50-launchd.sh" 2>&1 | to_log \
    || fail "plist-Umbau fehlgeschlagen — Fehler im Log"
  log "Update abgeschlossen"
  exit 0
fi

log "Service neu starten"
launchctl unload "$BACKEND_PLIST" 2>/dev/null || true
sleep 1
launchctl load "$BACKEND_PLIST"

log "Update abgeschlossen"
