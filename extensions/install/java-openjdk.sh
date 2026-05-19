#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

JDK_PKG="openjdk-21-jdk"

# Schon installiert?
if command -v java &>/dev/null; then
    INSTALLED="$(java -version 2>&1 | head -1 || echo "")"
    success "Java bereits installiert: ${INSTALLED}"
    exit 0
fi

info "Installiere ${JDK_PKG} und Maven..."
apt-get update -qq
apt-get install -y "${JDK_PKG}" maven

# JAVA_HOME für Agents setzen (in /etc/environment falls nicht vorhanden)
JAVA_HOME_PATH="$(update-java-alternatives -l 2>/dev/null | awk '{print $3}' | head -1 || echo "")"
if [ -n "${JAVA_HOME_PATH}" ]; then
    if ! grep -q "^JAVA_HOME=" /etc/environment 2>/dev/null; then
        echo "JAVA_HOME=${JAVA_HOME_PATH}" >> /etc/environment
    fi
    info "JAVA_HOME=${JAVA_HOME_PATH}"
fi

success "Java installiert: $(java -version 2>&1 | head -1)"
success "Maven installiert: $(mvn --version 2>/dev/null | head -1)"
