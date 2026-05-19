#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere OpenJDK 21 und Maven..."

apt-get remove -y --purge openjdk-21-jdk openjdk-21-jre-headless maven 2>/dev/null || true
apt-get autoremove -y 2>/dev/null || true

# JAVA_HOME aus /etc/environment entfernen
sed -i '/^JAVA_HOME=/d' /etc/environment 2>/dev/null || true

warn "Projektspezifische Maven-Caches (~/.m2) wurden nicht gelöscht."
success "Java/Maven deinstalliert"
