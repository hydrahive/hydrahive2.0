#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Rust..."

rm -rf /usr/local/rustup /usr/local/cargo
rm -f /usr/local/bin/cargo /usr/local/bin/rustc /usr/local/bin/rustup
rm -f /etc/profile.d/rust.sh

warn "Projektspezifische Cargo-Caches in Home-Verzeichnissen wurden nicht gelöscht."
success "Rust deinstalliert"
