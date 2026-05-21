#!/usr/bin/env bash
# Installiert Standard-MCP-Server via npm und legt Default-Konfiguration an.
# Idempotent: überspringt bereits installierte Pakete, überschreibt keine vorhandene Config.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

MCP_CONFIG="$HH_CONFIG_DIR/mcp_servers.json"

# Node.js muss da sein (kommt von 00-deps.sh oder nodejs-Extension)
if ! command -v npm >/dev/null 2>&1; then
  log "MCP-Server: npm nicht gefunden — überspringe"
  exit 0
fi

# MCP-Pakete installieren (npm -g ist idempotent bei bereits installierten Versionen)
MCP_PACKAGES=(
  "@modelcontextprotocol/server-filesystem"
  "@modelcontextprotocol/server-git"
  "@modelcontextprotocol/server-sqlite"
  "@modelcontextprotocol/server-fetch"
  "@modelcontextprotocol/server-sequential-thinking"
  "@modelcontextprotocol/server-time"
)

log "MCP-Server: installiere ${#MCP_PACKAGES[@]} npm-Pakete…"
npm install -g --silent "${MCP_PACKAGES[@]}" 2>&1 | grep -v "^npm warn" || true
log "MCP-Server: Pakete installiert"

# Default-Config nur anlegen wenn noch nicht vorhanden
if [ -f "$MCP_CONFIG" ]; then
  log "MCP-Config bereits vorhanden: $MCP_CONFIG — überspringe"
  exit 0
fi

DATA_HOME="${HH_DATA_DIR:-/var/lib/hydrahive2}"

log "MCP-Config anlegen: $MCP_CONFIG"
cat > "$MCP_CONFIG" <<MCPJSON
[
  {
    "id": "filesystem",
    "name": "Filesystem",
    "description": "Lese- und Schreibzugriff auf Verzeichnisse",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "$DATA_HOME"],
    "enabled": true
  },
  {
    "id": "git",
    "name": "Git",
    "description": "Git-Repository-Operationen",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-git"],
    "enabled": true
  },
  {
    "id": "sqlite",
    "name": "SQLite",
    "description": "SQLite-Datenbank-Abfragen",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-sqlite", "$DATA_HOME/sessions.db"],
    "enabled": false
  },
  {
    "id": "fetch",
    "name": "Fetch",
    "description": "HTTP-Requests und Web-Inhalte abrufen",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-fetch"],
    "enabled": true
  },
  {
    "id": "sequential-thinking",
    "name": "Sequential Thinking",
    "description": "Strukturiertes mehrstufiges Denken",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-sequential-thinking"],
    "enabled": true
  },
  {
    "id": "time",
    "name": "Time",
    "description": "Aktuelles Datum/Uhrzeit und Zeitzonenkonvertierung",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-time"],
    "enabled": true
  }
]
MCPJSON

chown "$HH_USER:$HH_USER" "$MCP_CONFIG"
log "MCP-Server eingerichtet: $(jq 'length' "$MCP_CONFIG") Server konfiguriert"
