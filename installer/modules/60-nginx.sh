#!/usr/bin/env bash
# nginx-Reverse-Proxy mit HTTPS (Self-Signed-Cert).
# getUserMedia (Mikrofon) erfordert einen Secure Context (HTTPS oder localhost).
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if [ "${HH_INSTALL_NGINX:-yes}" = "no" ]; then
  log "nginx übersprungen (HH_INSTALL_NGINX=no)"
  exit 0
fi

if ! command -v nginx >/dev/null 2>&1; then
  log "Installiere nginx"
  apt-get install -y nginx
fi

if ! command -v openssl >/dev/null 2>&1; then
  apt-get install -y openssl
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

COMPUTE_PKI_DIR="$HH_CONFIG_DIR/compute-pki"
log "Initialisiere Compute-CA für mTLS"
env HH_CONFIG_DIR="$HH_CONFIG_DIR" HH_DATA_DIR="$HH_DATA_DIR" \
  "$HH_REPO_DIR/.venv/bin/python" -c "from hydrahive.compute.identity import ensure_compute_ca; ensure_compute_ca()"
chown -R "$HH_USER:$HH_USER" "$COMPUTE_PKI_DIR"
chmod 700 "$COMPUTE_PKI_DIR"
chmod 600 "$COMPUTE_PKI_DIR/ca-key.pem"
chmod 644 "$COMPUTE_PKI_DIR/ca-cert.pem"
COMPUTE_PROXY_SECRET="$(cat "$HH_CONFIG_DIR/compute_proxy_secret")"
COMPUTE_PROXY_SNIPPET=/etc/nginx/snippets/hydrahive-compute-secret.conf
install -d -m 0755 /etc/nginx/snippets
printf 'proxy_set_header X-HydraHive-Proxy-Secret "%s";\n' "$COMPUTE_PROXY_SECRET" > "$COMPUTE_PROXY_SNIPPET"
chmod 600 "$COMPUTE_PROXY_SNIPPET"

CONF_FILE=/etc/nginx/sites-available/hydrahive2
log "Schreibe $CONF_FILE (HTTPS)"
cat > "$CONF_FILE" <<EOF
# WebSocket-Upgrade-Helper: connection_upgrade ist 'upgrade' wenn Upgrade-Header
# gesetzt, sonst 'close' — sonst zerstört der proxy_set_header normale Requests.
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

# Cache-Control je Pfad: content-gehashte Assets (/assets/) sind immutable und
# dürfen hart gecacht werden; index.html/HTML NIE hart cachen — sonst hält der
# Browser nach einem Deploy die alte index.html mit toten Asset-Hashes → 404 →
# weißer Screen. 'no-cache' = speichern erlaubt, aber immer per ETag revalidieren.
map \$uri \$hh_cache_control {
    default    "no-cache";
    ~^/assets/ "public, max-age=31536000, immutable";
}

# HTTP: nur Health-Ingest durchlassen, alles andere → HTTPS
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location /api/health-data/ {
        proxy_pass http://$HH_HOST:$HH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_buffering off;
        proxy_cache off;
        client_max_body_size 64M;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_certificate     $TLS_DIR/hydrahive.crt;
    ssl_certificate_key $TLS_DIR/hydrahive.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_client_certificate $COMPUTE_PKI_DIR/ca-cert.pem;
    ssl_verify_client optional;
    ssl_verify_depth 1;

    root $HH_REPO_DIR/frontend/dist;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    # microphone=(self) erlaubt Mikrofon-Zugriff vom gleichen Origin
    add_header Permissions-Policy "geolocation=(), microphone=(self), camera=(), payment=()" always;
    # Anti-Stale-Cache (siehe map \$hh_cache_control oben). Ein einzelner add_header
    # auf Server-Ebene — bewusst KEIN add_header in location-Bloecken, sonst faellt
    # die Vererbung der Security-Header (CSP etc.) weg.
    add_header Cache-Control \$hh_cache_control always;
    # script-src braucht 'unsafe-eval' wegen three.js Shader-Compile + d3 Path-Builder
    # (beide verwenden new Function()). 'wasm-unsafe-eval' für künftiges WASM
    # (xterm/novnc bauen mit WebAssembly).
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob: https://assets.coingecko.com https://coin-images.coingecko.com https://images.cryptocompare.com https://resources.cryptocompare.com https://www.cryptocompare.com; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval'; connect-src 'self' wss:; font-src 'self' data:; media-src 'self' blob:; object-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location = /api/compute/agent/connect {
        if (\$ssl_client_verify != SUCCESS) { return 403; }
        proxy_pass http://$HH_HOST:$HH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-HydraHive-Node-ID \$http_x_hydrahive_node_id;
        proxy_set_header X-HydraHive-Client-Cert \$ssl_client_escaped_cert;
        include $COMPUTE_PROXY_SNIPPET;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        client_max_body_size 64k;
    }

    # chat-upload-limit: 200 MiB Nutzdaten + Multipart-Overhead vor FastAPI begrenzen.
    location ~ ^/api/sessions/[^/]+/messages(?:/[^/]+/resend)?/?$ {
        proxy_pass http://$HH_HOST:$HH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
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

    # AgentLink-Frontend — SPA über denselben HTTPS-Origin, kein Mixed-Content.
    location /agentlink/ {
        proxy_pass http://127.0.0.1:${HL_FRONTEND_PORT:-9001}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # AgentLink-Backend-API — REST-Calls des Dashboards über denselben Origin.
    location /agentlink/api/ {
        proxy_pass http://127.0.0.1:${HL_BACKEND_PORT:-9000}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
    }

    # AgentLink-WebSocket — Dashboard live-updates.
    location /agentlink/ws {
        proxy_pass http://127.0.0.1:${HL_BACKEND_PORT:-9000}/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
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
