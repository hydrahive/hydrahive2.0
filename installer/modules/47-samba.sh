#!/usr/bin/env bash
# Phase 45: Samba für Projekt-Workspace-Shares.
#
# Pro Projekt eine Config in /etc/samba/hh-projects.d/<id>.conf, smb.conf
# inkludiert das Verzeichnis. Ein gemeinsamer Samba-User (default "hh") für
# alle Projekt-Shares — Per-User-Auth ist späteres Refactor.
#
# HH_SKIP_SAMBA=yes überspringt diesen Schritt.
set -euo pipefail

if [ "${HH_SKIP_SAMBA:-no}" = "yes" ]; then
  echo "Samba übersprungen (HH_SKIP_SAMBA=yes)"
  exit 0
fi

SAMBA_USER="${HH_SAMBA_USER:-hh}"
INCLUDES_DIR="${HH_SAMBA_INCLUDES_DIR:-/etc/samba/hh-projects.d}"
PASSWORD_FILE="${HH_SAMBA_PASSWORD_FILE:-${HH_CONFIG_DIR}/samba.password}"

log() { printf "  · %s\n" "$*"; }

# samba installieren falls nicht da
if ! command -v smbd >/dev/null 2>&1; then
  log "Installiere samba"
  DEBIAN_FRONTEND=noninteractive apt-get install -y samba >/dev/null
fi

# includes-dir anlegen, dem hydrahive-User schreibend zugänglich
mkdir -p "$INCLUDES_DIR"
chgrp "$HH_USER" "$INCLUDES_DIR" 2>/dev/null || true
chmod 2775 "$INCLUDES_DIR"

# smb.conf-Patch: ein Aggregator-File _index.conf includen, das vom Backend
# bei jedem enable/disable_share neu geschrieben wird (samba kann keine
# Verzeichnis-Includes, daher dieser Umweg).
INDEX_LINE="include = $INCLUDES_DIR/_index.conf"
ESCAPED="${INCLUDES_DIR//\//\\/}"
# Alte falsche Patches bereinigen: 'include = $DIR' (Verzeichnis), 'config file = $DIR/%u.conf'
if grep -qE "^(config file|include) = ${ESCAPED}(\$|/%u\.conf)" /etc/samba/smb.conf 2>/dev/null; then
  log "Alte hh-projects.d-Patches in smb.conf bereinigen"
  sed -i.bak -E "/^(config file|include) = ${ESCAPED}(\$|\/%u\.conf)/d" /etc/samba/smb.conf
fi
if ! grep -qF "$INDEX_LINE" /etc/samba/smb.conf 2>/dev/null; then
  log "Patch /etc/samba/smb.conf — $INDEX_LINE"
  printf "\n# HydraHive2 — projektgenerierte Shares (Aggregator-Index)\n%s\n" "$INDEX_LINE" >> /etc/samba/smb.conf
fi
# leere _index.conf anlegen falls fehlend
if [ ! -f "$INCLUDES_DIR/_index.conf" ]; then
  touch "$INCLUDES_DIR/_index.conf"
  chgrp "$HH_USER" "$INCLUDES_DIR/_index.conf" 2>/dev/null || true
  chmod 664 "$INCLUDES_DIR/_index.conf"
fi

# Linux-System-User für Samba (force user) — minimal, kein Login-Shell
if ! id "$SAMBA_USER" >/dev/null 2>&1; then
  log "Lege Samba-System-User '$SAMBA_USER' an"
  useradd -r -M -s /usr/sbin/nologin "$SAMBA_USER"
fi

# Samba-User in hydrahive-Gruppe damit er durch /var/lib/hydrahive2 kommt
# (das Top-Level hat 750 hydrahive:hydrahive, ohne diese Membership wird
# jeder Share-Zugriff mit ACCESS_DENIED beim Path-Traversal blockiert).
usermod -a -G "$HH_USER" "$SAMBA_USER" 2>/dev/null || true
# Plus auch andersrum für Backend-Schreibzugriff auf /etc/samba/hh-projects.d
usermod -a -G "$SAMBA_USER" "$HH_USER" 2>/dev/null || true

# Passwort generieren falls nicht da
if [ ! -f "$PASSWORD_FILE" ]; then
  log "Generiere Samba-Passwort → $PASSWORD_FILE"
  python3 -c "import secrets; print(secrets.token_urlsafe(18))" > "$PASSWORD_FILE"
  chmod 600 "$PASSWORD_FILE"
  chown "$HH_USER:$HH_USER" "$PASSWORD_FILE"
fi

# smbpasswd für SAMBA_USER setzen
SMB_PWD="$(cat "$PASSWORD_FILE")"
log "Setze Samba-Passwort für '$SAMBA_USER'"
(echo "$SMB_PWD"; echo "$SMB_PWD") | smbpasswd -a -s "$SAMBA_USER" >/dev/null
smbpasswd -e "$SAMBA_USER" >/dev/null 2>&1 || true

# Workspace-Root als hydrahive-User schreibbar + samba-User lesbar
chown -R "$HH_USER:$SAMBA_USER" "$HH_DATA_DIR/workspaces" 2>/dev/null || true
chmod -R g+rwX "$HH_DATA_DIR/workspaces" 2>/dev/null || true

systemctl enable smbd >/dev/null 2>&1 || true
systemctl restart smbd >/dev/null 2>&1 || true

log "Samba bereit. User: $SAMBA_USER, Passwort in $PASSWORD_FILE"
