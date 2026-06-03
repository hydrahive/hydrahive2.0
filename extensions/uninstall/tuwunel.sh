#!/usr/bin/env bash
# extensions/uninstall/tuwunel.sh — tuwunel Matrix-Homeserver entfernen
# Hinweis zu HH2-Config-Dateien: ${HH_CONFIG_DIR:-/etc/hydrahive}/matrix/ wird
# NICHT gelöscht — die Dateien enthalten den registration_token und server_name,
# die beim nächsten Install wiederverwendet werden (Idempotenz) und ggf. noch
# im HydraHive-Backend referenziert werden.
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }

TUWUNEL_USER="tuwunel"
TUWUNEL_DIR="/var/lib/tuwunel"
TUWUNEL_CONFIG_DIR="/etc/tuwunel"
TUWUNEL_BIN="/usr/local/bin/tuwunel"

info "Deinstalliere tuwunel..."

# ── Service stoppen und deaktivieren ────────────────────────────────────────
systemctl stop hydrahive-tuwunel 2>/dev/null || true
systemctl disable hydrahive-tuwunel 2>/dev/null || true
rm -f /etc/systemd/system/hydrahive-tuwunel.service
systemctl daemon-reload
success "systemd-Unit hydrahive-tuwunel entfernt"

# ── Binary entfernen ─────────────────────────────────────────────────────────
rm -f "$TUWUNEL_BIN"
success "Binary $TUWUNEL_BIN entfernt"

# ── Config entfernen ─────────────────────────────────────────────────────────
rm -rf "$TUWUNEL_CONFIG_DIR"
success "Config-Verzeichnis $TUWUNEL_CONFIG_DIR entfernt"

# ── Datenbankverzeichnis entfernen ───────────────────────────────────────────
# ACHTUNG: Löscht alle Matrix-Nachrichten und Accounts unwiderruflich.
rm -rf "$TUWUNEL_DIR"
success "Datenverzeichnis $TUWUNEL_DIR entfernt"

# ── System-User entfernen ────────────────────────────────────────────────────
userdel -r "$TUWUNEL_USER" 2>/dev/null || true
success "System-User '$TUWUNEL_USER' entfernt"

# HH2-Config-Dateien (${HH_CONFIG_DIR:-/etc/hydrahive}/matrix/) werden
# NICHT gelöscht — sie werden beim nächsten Install wiederverwendet.
info "Hinweis: ${HH_CONFIG_DIR:-/etc/hydrahive}/matrix/ bleibt erhalten (registration_token + server_name für Re-Install)"

success "tuwunel deinstalliert"
