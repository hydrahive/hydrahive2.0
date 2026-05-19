#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

# System-weite Installation nach /usr/local/{rustup,cargo}
export RUSTUP_HOME="/usr/local/rustup"
export CARGO_HOME="/usr/local/cargo"

# Schon installiert?
if [ -x /usr/local/bin/cargo ]; then
    INSTALLED="$(/usr/local/bin/cargo --version 2>/dev/null || echo "")"
    success "Rust bereits installiert: ${INSTALLED}"
    info "Führe rustup update aus..."
    RUSTUP_HOME="${RUSTUP_HOME}" CARGO_HOME="${CARGO_HOME}" \
        /usr/local/bin/rustup update stable 2>/dev/null || true
    exit 0
fi

info "Installiere Rust via rustup (system-weit)..."
apt-get install -y curl build-essential 2>/dev/null || true

curl -fsSL https://sh.rustup.rs | \
    env RUSTUP_HOME="${RUSTUP_HOME}" CARGO_HOME="${CARGO_HOME}" \
    sh -s -- -y --no-modify-path --default-toolchain stable

# Symlinks damit cargo/rustc/rustup im PATH der Agents liegen
for BIN in cargo rustc rustup; do
    ln -sf "${CARGO_HOME}/bin/${BIN}" "/usr/local/bin/${BIN}"
done

# Profile für Login-Shells
cat > /etc/profile.d/rust.sh <<PROFILE
export RUSTUP_HOME="${RUSTUP_HOME}"
export CARGO_HOME="${CARGO_HOME}"
export PATH="\$PATH:${CARGO_HOME}/bin"
PROFILE
chmod 644 /etc/profile.d/rust.sh

success "Rust installiert: $(/usr/local/bin/cargo --version)"
