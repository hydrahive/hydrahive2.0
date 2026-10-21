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

HL_BACKEND_PORT="${HL_BACKEND_PORT:-9000}"
HL_FRONTEND_PORT="${HL_FRONTEND_PORT:-9001}"

# Gleiche Regeln wie der Linux-nginx (installer/modules/60-nginx.sh), soweit sie auf dem Mac gelten.
# Merkmale hh_*: update-mac.sh schreibt die Konfiguration neu, wenn eines fehlt.
# Wichtig: add_header in einer location schaltet die Vererbung der Server-Kopfzeilen ab. Darum setzt nur
# die Modul-Sandbox (eigene, vollständige Kopfzeilen) ein add_header auf location-Ebene.
# Neue Konfiguration erst prüfen (nginx -t), dann übernehmen. Sonst legt ein Fehler beim Update den
# Webserver lahm – HydraHive wäre bis zum nächsten Eingriff von Hand nicht erreichbar.
NGINX_NEW="$NGINX_CONF.new"
log "Schreibe $NGINX_CONF"
cat > "$NGINX_NEW" <<EOF
# Cache-Control je Pfad: gehashte Assets hart cachen, index.html nie (sonst weißer Bildschirm nach Updates).
map \$uri \$hh_cache_control {
    default    "no-cache";
    ~^/assets/ "public, max-age=31536000, immutable";
}

map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     ${CERT_DIR}/server.crt;
    ssl_certificate_key ${CERT_DIR}/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 500m;

    root ${HH_REPO_DIR}/frontend/dist;
    index index.html;

    # Sicherheits-Kopfzeilen wie Linux (hh_security_headers)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header Permissions-Policy "geolocation=(), microphone=(self), camera=(), payment=()" always;
    add_header Cache-Control \$hh_cache_control always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob: https://assets.coingecko.com https://coin-images.coingecko.com https://images.cryptocompare.com https://resources.cryptocompare.com https://www.cryptocompare.com; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval'; connect-src 'self' wss:; font-src 'self' data:; media-src 'self' blob:; object-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # chat-upload-limit: 200 MiB Nutzdaten + Multipart-Overhead vor FastAPI begrenzen.
    location ~ ^/api/sessions/[^/]+/messages(?:/[^/]+/resend)?/?$ {
        proxy_pass http://127.0.0.1:${HH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        client_max_body_size 205M;
        error_page 413 = @chat_upload_limit_error;
    }

    location @chat_upload_limit_error {
        default_type application/json;
        return 413 '{"detail":{"code":"upload_request_too_large","params":{"max_mib":205}}}';
    }

    # Server-Kopplung (docs/specs/server-peering.md): nur aus dem Tailnet (hh_peering_tailnet).
    location /api/peering/ {
        allow 100.64.0.0/10;
        allow fd7a:115c:a1e0::/48;
        deny all;
        proxy_pass http://127.0.0.1:${HH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 1m;  # hh_peering_tailnet
    }

    location ~ ^/api/module-device/[a-z0-9-]+/sandbox/ {
        add_header Content-Security-Policy "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header Cache-Control "no-store" always;
        proxy_pass http://127.0.0.1:${HH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 64k;  # hh_module_sandbox
    }

    location /api/ {
        proxy_pass http://127.0.0.1:${HH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        client_max_body_size 500m;
    }

    # AgentLink hat keine eigene Anmeldung: nginx prüft jeden /agentlink/-Weg gegen HydraHive
    # (Cookie hh_agentlink, nur Admins, gesetzt über „Dashboard öffnen“). Merkmal hh_agentlink_auth.
    location = /_hh_agentlink_auth {
        internal;
        proxy_pass http://127.0.0.1:${HH_PORT}/api/agentlink/dashboard-auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Cookie \$http_cookie;
        proxy_set_header X-Original-URI \$request_uri;
    }

    location @hh_agentlink_login {
        return 302 /;
    }

    location /agentlink/ {
        auth_request /_hh_agentlink_auth;
        error_page 401 = @hh_agentlink_login;
        proxy_pass http://127.0.0.1:${HL_FRONTEND_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /agentlink/api/ {
        auth_request /_hh_agentlink_auth;
        proxy_pass http://127.0.0.1:${HL_BACKEND_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
    }

    location /agentlink/ws {
        auth_request /_hh_agentlink_auth;
        proxy_pass http://127.0.0.1:${HL_BACKEND_PORT}/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}

server {
    listen 80;
    return 301 https://\$host\$request_uri;
}
EOF

NGINX_BIN="$(brew --prefix)/bin/nginx"
if [ -x "$NGINX_BIN" ] && [ -f "$NGINX_CONF" ]; then
  mv -f "$NGINX_CONF" "$NGINX_CONF.bak"
  mv -f "$NGINX_NEW" "$NGINX_CONF"
  if ! sudo "$NGINX_BIN" -t >/dev/null 2>&1; then
    log "nginx -t meldet Fehler – alte Konfiguration bleibt:"
    sudo "$NGINX_BIN" -t 2>&1 | sed 's/^/      /' || true
    mv -f "$NGINX_CONF" "$NGINX_CONF.rejected"
    mv -f "$NGINX_CONF.bak" "$NGINX_CONF"
    exit 1
  fi
  rm -f "$NGINX_CONF.bak"
else
  mv -f "$NGINX_NEW" "$NGINX_CONF"
fi

# nginx als LaunchDaemon (Port 80/443 braucht root)
NGINX_PLIST="${HH_NGINX_PLIST:-/Library/LaunchDaemons/io.hydrahive.nginx.plist}"

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
