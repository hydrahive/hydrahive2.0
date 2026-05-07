#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Installiere Ollama..."

if command -v ollama &>/dev/null; then
    info "Ollama bereits installiert — prüfe Service..."
else
    curl -fsSL -o /tmp/ollama-install.sh https://ollama.ai/install.sh
    bash /tmp/ollama-install.sh
    rm -f /tmp/ollama-install.sh
    success "Ollama installiert"
fi

# Service sicherstellen
if ! systemctl list-unit-files ollama.service &>/dev/null | grep -q ollama; then
    useradd -r -s /bin/false -m -d /usr/share/ollama ollama 2>/dev/null || true
    mkdir -p /usr/share/ollama/.ollama
    chown -R ollama:ollama /usr/share/ollama
    cat > /etc/systemd/system/ollama.service << 'UNIT'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
UNIT
    systemctl daemon-reload
fi

systemctl enable ollama &>/dev/null
if ! systemctl is-active --quiet ollama; then
    systemctl start ollama
    sleep 5
fi
success "Ollama-Service aktiv"

# Default-Modelle
for model in "llama3.2:3b"; do
    if ollama list 2>/dev/null | grep -qF "${model%%:*}"; then
        info "Modell $model bereits vorhanden"
    else
        info "Lade $model (kann einige Minuten dauern)..."
        ollama pull "$model" && success "Modell $model geladen" || warn "Modell $model konnte nicht geladen werden"
    fi
done

success "Ollama bereit — http://127.0.0.1:11434"
