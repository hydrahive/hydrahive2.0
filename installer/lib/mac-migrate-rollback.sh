#!/bin/bash
# macOS: Rückweg nach abgebrochenem Umzug auf das Dienst-Konto (Etappe 3, docs/plans/mac-service-user.md).
# Aufruf aus mac-migrate-service-user.sh (root), wenn ein Schritt nach dem Anhalten der Dienste scheitert.
#
# Befund 22.10.2026 (.186): Abbruch beim Datenbank-Import ließ einen halben Umzug zurück – Dateien gehörten dem Konto,
# die Dienst-Dateien noch dem alten Nutzer, nichts lief. Jetzt: neue Dienste anhalten, Besitz zurück, Dienst-Dateien
# aus der Sicherung zurück, alte Dienste starten (Datenbank zuerst). Das Konto und der neue Datenbank-Ordner bleiben
# liegen – das nächste Update versucht den Umzug erneut. Den Update-Dienst selbst nie anfassen (läuft gerade).
# Env: HH_OLD_USER, HH_SVC_USER, HH_BACKUP; Pfade wie mac-migrate-service-user.sh.
set -uo pipefail
log() { printf "  · %s\n" "$*"; }

OLD="${HH_OLD_USER:?HH_OLD_USER fehlt}"
SVC="${HH_SVC_USER:?HH_SVC_USER fehlt}"
BACKUP="${HH_BACKUP:?HH_BACKUP fehlt}"
PLIST_DIR="${HH_PLIST_DIR:-/Library/LaunchDaemons}"
HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HL_DIR="${HH_HL_DIR:-/opt/hydralink}"
HL_CONFIG_DIR="${HH_HL_CONFIG_DIR:-/usr/local/etc/hydralink}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
LABELS="postgres colima backend agentlink agentlink-frontend voice-stt voice-tts"

if [ -z "$OLD" ] || [ "$OLD" = "root" ]; then
  echo "Rückweg abgebrochen: alter Nutzer '$OLD' ungültig" >&2
  exit 1
fi
log "Rückweg: HydraHive läuft wieder als $OLD"

for label in $LABELS; do launchctl bootout "system/io.hydrahive.$label" 2>/dev/null; done

for d in "$HH_REPO_DIR" "$HH_DATA_DIR" "$HH_CONFIG_DIR" "$HL_DIR" "$HL_CONFIG_DIR"; do
  [ -e "$d" ] && chown -R "$OLD" "$d"
done
[ -d "$HH_DATA_DIR/tailscale" ] && chown -R root "$HH_DATA_DIR/tailscale"
# Neuer Datenbank-Ordner bleibt beim Konto (postgres startet nur als Besitzer) – für den nächsten Versuch.
[ -d "$HH_DATA_DIR/postgres" ] && chown -R "$SVC" "$HH_DATA_DIR/postgres"
for f in "$HH_LOG_DIR"/hydrahive2*.log "$HH_LOG_DIR"/agentlink*.log; do
  [ -f "$f" ] || continue
  case "$f" in *-update.log|*-addon.log|*-tailscaled.log) continue ;; esac
  chown "$OLD" "$f"
done

for label in $LABELS; do
  src="$BACKUP/plists/io.hydrahive.$label.plist"
  [ -f "$src" ] && cp -p "$src" "$PLIST_DIR/io.hydrahive.$label.plist"
done
for label in $LABELS; do
  p="$PLIST_DIR/io.hydrahive.$label.plist"
  [ -f "$p" ] && launchctl bootstrap system "$p" 2>/dev/null
  [ "$label" = "postgres" ] && sleep 3   # Datenbank vor AgentLink/Backend
done
log "Alter Stand wiederhergestellt (Sicherung: $BACKUP)"
exit 0
