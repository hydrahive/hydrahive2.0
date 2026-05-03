#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

if ! brew list nginx &>/dev/null; then
  log "Installiere nginx"
  brew install nginx --quiet
fi

NGINX_CONF_DIR="$(brew --prefix)/etc/nginx/servers"
CERT_DIR="$HH_CONFIG_DIR/tls"
NGINX_CONF="$NGINX_CONF_DIR/hydrahive2.conf"

mkdir -p "$NGINX_CONF_DIR"

# Selbstsigniertes Zertifikat
if [ ! -f "$CERT_DIR/server.crt" ]; then
  log "Erzeuge self-signed TLS-Zertifikat"
  mkdir -p "$CERT_DIR"
  SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -subj "/CN=hydrahive2" \
    -addext "subjectAltName=IP:${SERVER_IP},IP:127.0.0.1,DNS:localhost" \
    2>/dev/null
  chmod 600 "$CERT_DIR/server.key"
fi

log "Schreibe $NGINX_CONF"
cat > "$NGINX_CONF" <<EOF
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     ${CERT_DIR}/server.crt;
    ssl_certificate_key ${CERT_DIR}/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 500m;

    root ${HH_REPO_DIR}/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:${HH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 500m;
    }
}

server {
    listen 80;
    return 301 https://\$host\$request_uri;
}
EOF

# nginx als LaunchDaemon (Port 80/443 braucht root)
NGINX_PLIST="/Library/LaunchDaemons/io.hydrahive.nginx.plist"
NGINX_BIN="$(brew --prefix)/bin/nginx"

sudo tee "$NGINX_PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.nginx</string>
    <key>ProgramArguments</key>
    <array>
        <string>${NGINX_BIN}</string>
        <string>-g</string>
        <string>daemon off;</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/usr/local/var/log/nginx-hydrahive.log</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/var/log/nginx-hydrahive-error.log</string>
</dict>
</plist>
EOF

sudo chmod 644 "$NGINX_PLIST"
sudo launchctl unload "$NGINX_PLIST" 2>/dev/null || true
sudo launchctl load "$NGINX_PLIST"

log "nginx läuft — https://$(ipconfig getifaddr en0 2>/dev/null || echo localhost)"
