#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere TrinityCore 3.3.5a..."

systemctl stop    trinitycore-335-world trinitycore-335-auth 2>/dev/null || true
systemctl disable trinitycore-335-world trinitycore-335-auth 2>/dev/null || true
rm -f /etc/systemd/system/trinitycore-335-world.service
rm -f /etc/systemd/system/trinitycore-335-auth.service
systemctl daemon-reload

warn "/opt/trinitycore-335 wird entfernt (Source, Build, Server-Binaries)."
warn "Datenbanken (trinity335_auth/characters/world) werden NICHT gelöscht."
warn "Manuell löschen: mysql -e 'DROP DATABASE trinity335_auth; DROP DATABASE trinity335_characters; DROP DATABASE trinity335_world;'"
rm -rf /opt/trinitycore-335

userdel -r trinity335 2>/dev/null || true

rm -f /etc/hydrahive2/extensions/trinitycore-335.credentials.json

if command -v ufw &>/dev/null; then
    ufw delete allow 8085/tcp 2>/dev/null || true
    ufw delete allow 3724/tcp 2>/dev/null || true
fi

success "TrinityCore 3.3.5a deinstalliert (Datenbanken behalten)"
