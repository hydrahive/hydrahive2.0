#!/usr/bin/env bash
# nginx-Reverse-Proxy mit HTTPS (Self-Signed-Cert).
# getUserMedia (Mikrofon) erfordert einen Secure Context (HTTPS oder localhost).
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if ! command -v nginx >/dev/null 2>&1; then
  log "Installiere nginx"
  apt-get install -y nginx >/dev/null
fi

if ! command -v openssl >/dev/null 2>&1; then
  apt-get install -y openssl >/dev/null
fi

# Self-Signed-Cert anlegen falls noch nicht vorhanden
TLS_DIR=/etc/hydrahive2/tls
if [ ! -f "$TLS_DIR/hydrahive.crt" ]; then
  log "Erzeuge Self-Signed-TLS-Zertifikat"
  mkdir -p "$TLS_DIR"
  # Server-IP für SAN ermitteln — sonst schlägt Zertifikatsprüfung beim LAN-Zugriff fehl
  SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '/src/{print $7; exit}' || hostname -I 2>/dev/null | awk '{print $1}')
  SAN="IP:127.0.0.1"
  [ -n "$SERVER_IP" ] && [ "$SERVER_IP" != "127.0.0.1" ] && SAN="IP:127.0.0.1,IP:$SERVER_IP"
  log "TLS SAN: $SAN"
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "$TLS_DIR/hydrahive.key" \
    -out    "$TLS_DIR/hydrahive.crt" \
    -subj   "/CN=hydrahive2/O=HydraHive/C=DE" \
    -addext "subjectAltName=$SAN" \
    2>/dev/null
  chmod 600 "$TLS_DIR/hydrahive.key"
  chmod 644 "$TLS_DIR/hydrahive.crt"
fi

CONF_FILE=/etc/nginx/sites-available/hydrahive2
log "Schreibe $CONF_FILE (HTTPS)"
cat > "$CONF_FILE" <<EOF
# WebSocket-Upgrade-Helper: connection_upgrade ist 'upgrade' wenn Upgrade-Header
# gesetzt, sonst 'close' — sonst zerstört der proxy_set_header normale Requests.
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

# HTTP → HTTPS redirect
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_certificate     $TLS_DIR/hydrahive.crt;
    ssl_certificate_key $TLS_DIR/hydrahive.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    root $HH_REPO_DIR/frontend/dist;
    index index.html;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    # microphone=(self) erlaubt Mikrofon-Zugriff vom gleichen Origin
    add_header Permissions-Policy "geolocation=(), microphone=(self), camera=(), payment=()" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' wss:; font-src 'self' data:; media-src 'self' blob:; object-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://$HH_HOST:$HH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        # WebSocket-Upgrade (Container-Console)
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        client_max_body_size 8G;  # ISO-Uploads können groß sein
    }

    # VNC WebSocket-Proxy (websockify auf 127.0.0.1:6080)
    location /vnc-ws/ {
        proxy_pass http://127.0.0.1:6080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # AgentLink-Frontend-Proxy — verhindert Mixed-Content wenn HydraHive auf HTTPS läuft.
    # Statt http://127.0.0.1:9001 direkt im Browser öffnen, läuft der Traffic über
    # denselben HTTPS-Origin → kein Mixed-Content-Block.
    location /agentlink/ {
        proxy_pass http://127.0.0.1:${HL_FRONTEND_PORT:-9001}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "$CONF_FILE" /etc/nginx/sites-enabled/hydrahive2
rm -f /etc/nginx/sites-enabled/default

log "Teste nginx-Config"
nginx -t

log "nginx aktivieren und starten"
systemctl enable nginx >/dev/null 2>&1
if systemctl is-active --quiet nginx; then
  systemctl reload nginx
else
  systemctl start nginx
fi
