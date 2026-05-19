#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Go..."

rm -rf /usr/local/go
rm -f /usr/local/bin/go /usr/local/bin/gofmt
rm -f /etc/profile.d/golang.sh

warn "GOPATH (~/go) wurde nicht gelöscht — manuell entfernen falls gewünscht."
success "Go deinstalliert"
