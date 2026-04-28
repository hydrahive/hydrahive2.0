#!/usr/bin/env bash
# Optional: nginx-Reverse-Proxy. Liefert das Frontend aus dist/ + proxied /api → Backend.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if ! command -v nginx >/dev/null 2>&1; then
  log "Installiere nginx"
  apt-get install -y nginx >/dev/null
fi

CONF_FILE=/etc/nginx/sites-available/hydrahive2
log "Schreibe $CONF_FILE"
cat > "$CONF_FILE" <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root $HH_REPO_DIR/frontend/dist;
    index index.html;

    # SPA-Fallback: jeder unbekannte Pfad → index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Backend-API
    location /api/ {
        proxy_pass http://$HH_HOST:$HH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE-Streaming nicht buffern
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }
}
EOF

ln -sf "$CONF_FILE" /etc/nginx/sites-enabled/hydrahive2
rm -f /etc/nginx/sites-enabled/default

log "Teste nginx-Config"
nginx -t

log "Reload nginx"
systemctl reload nginx
