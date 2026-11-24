# shellcheck shell=bash
# nginx-Block der Testseite eines Projekts (ziele/projekt-testumgebung.md §4, Etappe E1b). Wird von
# installer/modules/60-nginx.sh (Linux) und installer/modules-mac/60-nginx.sh gesourct und an die Config angehängt.
#
# - Eigener Port 8445 (8443 Labor, 8444 Vibe): Der Code der Testseite läuft nie im Ursprung von HydraHive.
# - Nur Heimnetz, Tailscale und der Rechner selbst; sonst deny. Kein Öffnen ins Internet.
# - Jede Anfrage prüft nginx per auth_request gegen /api/project-preview/auth (Cookie hh_project_preview). Das
#   Backend nennt in X-Preview-Port den Port des Projekts aus dem Cookie. Ein gültiges Ergebnis merkt sich nginx 20 s.
# - An die Testseite gehen keine Cookies, von ihr kommt kein Set-Cookie (Cookies trennen nicht nach Port).
# - Merkmal hh_project_preview_auth: update.sh / update-mac.sh schreiben die Config neu, wenn es fehlt.

HH_PREVIEW_PROXY_PORT=8445
HH_PREVIEW_HOME_NETS="127.0.0.1 ::1 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 100.64.0.0/10 fc00::/7 fe80::/10 fd7a:115c:a1e0::/48"

# hh_project_preview_block <zertifikat> <schlüssel> <backend host:port> <cache-ordner>
hh_project_preview_block() {
  local cert="$1" key="$2" backend="$3" cache="$4" allow="" net
  for net in $HH_PREVIEW_HOME_NETS; do
    allow+="    allow $net;"$'\n'
  done
  cat <<EOF

# Testseite eines Projekts (Port $HH_PREVIEW_PROXY_PORT) – Merkmal hh_project_preview_auth.
map \$http_upgrade \$hh_preview_conn {
    default upgrade;
    '' close;
}
proxy_cache_path $cache levels=1 keys_zone=hh_project_preview_auth:1m max_size=5m inactive=10m use_temp_path=off;

server {
    listen $HH_PREVIEW_PROXY_PORT ssl;
    listen [::]:$HH_PREVIEW_PROXY_PORT ssl;
    server_name _;
    server_tokens off;
    ssl_certificate     $cert;
    ssl_certificate_key $key;
    ssl_protocols       TLSv1.2 TLSv1.3;
${allow}    deny all;
    access_log off;
    charset utf-8;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;

    location = /__hh_preview_auth {
        internal;
        proxy_pass http://$backend/api/project-preview/auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Cookie \$http_cookie;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_cache hh_project_preview_auth;
        proxy_cache_key \$cookie_hh_project_preview;
        proxy_cache_valid 200 20s;
    }

    # Ticket einlösen: setzt das Cookie und leitet relativ auf "/" um – der Browser bleibt auf diesem Port.
    location = /__hh_preview_login {
        proxy_pass http://$backend/api/project-preview/login;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$remote_addr;
    }

    location @hh_preview_login {
        default_type text/html;
        return 401 "<!doctype html><meta charset=utf-8><title>Testseite</title><p>Bitte die Testseite über ‚Testseite öffnen‘ im Projekt starten.</p><p>Please open the test page with ‘Open test page’ in the project.</p>";
    }

    location / {
        auth_request /__hh_preview_auth;
        auth_request_set \$hh_preview_port \$upstream_http_x_preview_port;
        error_page 401 = @hh_preview_login;
        proxy_pass http://127.0.0.1:\$hh_preview_port;
        proxy_http_version 1.1;
        proxy_set_header Host \$http_host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$hh_preview_conn;
        proxy_set_header Cookie "";
        proxy_hide_header Set-Cookie;
        proxy_buffering off;
        proxy_read_timeout 1h;
    }
}
EOF
}
