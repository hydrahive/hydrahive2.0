#!/usr/bin/env bash
# SearXNG — privater Meta-Suchmaschinen-Service für HydraHive-Agents.
#
# Idempotent: prüft jeden Schritt einzeln.
# Läuft als systemd-Service auf Port 8888 (konfigurierbar via HH_SEARXNG_PORT).
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if [ "${HH_INSTALL_SEARXNG:-yes}" = "no" ]; then
  log "SearXNG übersprungen (HH_INSTALL_SEARXNG=no)"
  exit 0
fi

SEARXNG_PORT="${HH_SEARXNG_PORT:-8888}"
SEARXNG_DIR="/opt/searxng"
SEARXNG_USER="searxng"
SEARXNG_VENV="$SEARXNG_DIR/venv"

log "Abhängigkeiten installieren"
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-dev python3-pip git libssl-dev libffi-dev

# Interpreter: hh_pick_python (System-Python >= 3.12, aufgelöst auf die
# versionierte Datei). NICHT `python3 -m venv`: dann folgt bin/python dem
# System-Link, und nach einem Python-Wechsel findet SearXNG seine Pakete nicht
# mehr (Ausfall 29.08.–26.09.2026). Spec docs/specs/python-314-umstieg.md.
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"
# shellcheck source=installer/lib/python-venv.sh
source "$LIB_DIR/python-venv.sh"
# shellcheck source=installer/lib/searxng-venv.sh
source "$LIB_DIR/searxng-venv.sh"

# System-User anlegen (falls nicht vorhanden)
if ! id "$SEARXNG_USER" &>/dev/null; then
  log "System-User '$SEARXNG_USER' anlegen"
  useradd -r -s /bin/false -d "$SEARXNG_DIR" "$SEARXNG_USER"
fi

# SearXNG clonen / updaten
if [ ! -d "$SEARXNG_DIR/.git" ]; then
  log "SearXNG clonen"
  git clone https://github.com/searxng/searxng "$SEARXNG_DIR" --depth=1 2>&1 | tail -3
else
  log "SearXNG bereits vorhanden — überspringe Clone"
fi

# Virtualenv anlegen bzw. bei abweichender Python-Version neu bauen.
hh_searxng_sync_venv "$SEARXNG_DIR" "$SEARXNG_USER" "searxng.service"

log "Python-Abhängigkeiten installieren"
"$SEARXNG_VENV/bin/pip" install -q --upgrade pip setuptools wheel
# requirements.txt zuerst — enthält msgspec und andere Build-Deps
if [ -f "$SEARXNG_DIR/requirements.txt" ]; then
  "$SEARXNG_VENV/bin/pip" install -q -r "$SEARXNG_DIR/requirements.txt"
fi
"$SEARXNG_VENV/bin/pip" install -q --no-build-isolation "$SEARXNG_DIR"

# Eigene Einstellungsdatei. NICHT searx/settings.yml — das ist SearXNGs
# mitgelieferte Standarddatei (2.766 Zeilen), auf der use_default_settings
# aufbaut. Frühere Versionen dieses Moduls haben sie überschrieben; dann
# fehlten alle Standardwerte (Spec docs/specs/websearch-blocked-engines.md §2).
SEARXNG_SETTINGS="$SEARXNG_DIR/searxng/settings.yml"
OLD_SETTINGS="$SEARXNG_DIR/searx/settings.yml"
install -d -m 0755 "$(dirname "$SEARXNG_SETTINGS")"

SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
# Bestehenden Secret-Key beibehalten: eigene Datei, sonst (einmalig) die alte Stelle.
for f in "$SEARXNG_SETTINGS" "$OLD_SETTINGS"; do
  if [ -f "$f" ] && grep -q "^# HydraHive SearXNG — automatisch generiert" "$f" 2>/dev/null; then
    EXISTING_SECRET=$(grep "secret_key:" "$f" | head -1 | awk '{print $2}' | tr -d '"')
    if [ -n "$EXISTING_SECRET" ]; then SECRET="$EXISTING_SECRET"; break; fi
  fi
done

# Von einer alten Version überschriebene Standarddatei wiederherstellen.
if [ -d "$SEARXNG_DIR/.git" ] && grep -q "^# HydraHive SearXNG — automatisch generiert" "$OLD_SETTINGS" 2>/dev/null; then
  log "SearXNG-Standarddatei wiederherstellen (war von altem Installer überschrieben)"
  mkdir -p /var/backups
  cp -a "$OLD_SETTINGS" "/var/backups/searxng-default-settings-$(date +%Y%m%d-%H%M%S).yml"
  git -c safe.directory="$SEARXNG_DIR" -C "$SEARXNG_DIR" checkout -- searx/settings.yml
fi

# Nur eigene (generierte) oder fehlende Datei schreiben. Von Hand angepasste
# Dateien bleiben stehen; die Suchanbieter ergänzt dann migrations/searxng-engines.sh.
if [ -f "$SEARXNG_SETTINGS" ] && ! grep -q "^# HydraHive SearXNG — automatisch generiert" "$SEARXNG_SETTINGS"; then
  log "Eigene SearXNG-Einstellungen gefunden — nicht überschrieben"
else
log "SearXNG konfigurieren"
cat > "$SEARXNG_SETTINGS" <<EOFSETTINGS
# HydraHive SearXNG — automatisch generiert von 76-searxng.sh
use_default_settings: true

server:
  secret_key: "$SECRET"
  bind_address: "0.0.0.0"
  port: $SEARXNG_PORT
  # Kein Rate-Limiting — nur internes HydraHive-Netz
  limiter: false
  public_instance: false
  image_proxy: false

search:
  safe_search: 0
  autocomplete: ""
  formats:
    - html
    - json

# Bing und Yandex einschalten (Standard: aus). Am 02.10.2026 lieferten
# DuckDuckGo/Startpage (CAPTCHA), Brave (zu viele Anfragen) und Google (leer)
# keine Treffer mehr. Nur name + disabled — sonst gehen SearXNGs
# Standardfelder (shortcut, categories …) verloren.
engines:
  - name: bing
    disabled: false
  - name: yandex
    disabled: false

ui:
  default_theme: simple
  default_locale: de
EOFSETTINGS
fi

# Berechtigungen setzen
chown -R "$SEARXNG_USER:$SEARXNG_USER" "$SEARXNG_DIR"

# systemd-Service
cat > /etc/systemd/system/searxng.service <<EOF
[Unit]
Description=SearXNG Metasearch Engine
After=network.target

[Service]
Type=simple
User=$SEARXNG_USER
WorkingDirectory=$SEARXNG_DIR
ExecStart=$SEARXNG_VENV/bin/python -m searx.webapp
Environment=SEARXNG_SETTINGS_PATH=$SEARXNG_SETTINGS
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable searxng
systemctl restart searxng

log "SearXNG gestartet auf http://localhost:$SEARXNG_PORT"
log "Für ProjektX: PROJEKTX_SEARXNG_URL=http://localhost:$SEARXNG_PORT"
log "Für HydraHive-Agents: WEB_SEARCH_URL=http://localhost:$SEARXNG_PORT"
