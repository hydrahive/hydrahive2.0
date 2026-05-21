#!/usr/bin/env bash
# Legt 3 Starter-Agenten an falls noch keine Agenten vorhanden sind.
# Idempotent: überspringt wenn $HH_DATA_DIR/agents/ bereits Einträge enthält.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

AGENTS_DIR="$HH_DATA_DIR/agents"
mkdir -p "$AGENTS_DIR"

# Bereits Agenten vorhanden? Dann nichts tun.
existing=$(find "$AGENTS_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l)
if [ "$existing" -gt 0 ]; then
  log "Starter-Agenten: bereits $existing Agent(en) vorhanden — überspringe"
  exit 0
fi

log "Lege 3 Starter-Agenten an…"

now=$(python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())")

create_agent() {
  local id="$1"
  local json="$2"
  local dir="$AGENTS_DIR/$id"
  mkdir -p "$dir"
  printf '%s' "$json" > "$dir/config.json"
  chown -R "$HH_USER:$HH_USER" "$dir"
  log "  Agent angelegt: $dir"
}

# --- Coder ---------------------------------------------------------------
CODER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
create_agent "$CODER_ID" '{
  "id": "'"$CODER_ID"'",
  "type": "specialist",
  "name": "Coder",
  "owner": "admin",
  "created_by": "installer",
  "description": "Code-Assistent mit Shell, Datei- und Such-Tools. Für Coding-Tasks, Refactoring und Debugging.",
  "llm_model": "'"${HH_DEFAULT_MODEL:-MiniMax-M2.7}"'",
  "fallback_models": [],
  "tools": ["shell_exec","file_read","file_write","file_patch","file_search","dir_list","read_memory","write_memory","search_memory","todo_write"],
  "mcp_servers": [],
  "temperature": 0.3,
  "max_tokens": 16384,
  "thinking_budget": 0,
  "max_iterations": 60,
  "status": "active",
  "created_at": "'"$now"'",
  "updated_at": "'"$now"'",
  "disabled_skills": [],
  "require_tool_confirm": false,
  "compact_model": "",
  "compact_tool_result_limit": 2000,
  "compact_reserve_tokens": 16384,
  "compact_threshold_pct": 70,
  "tool_result_max_chars": 12000,
  "cache_ttl": "1h",
  "system_prompt": "Du bist ein präziser Code-Assistent.\n\nVor jedem Tool-Call: überlege kurz welche Information du noch brauchst. Plane in Schritten. Nach jedem Tool-Result: evaluiere ob dein Plan noch stimmt.\n\nBei komplexen Tasks: zerlege in Teilschritte, arbeite einen nach dem anderen ab."
}'

# --- Analyst -------------------------------------------------------------
ANALYST_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
create_agent "$ANALYST_ID" '{
  "id": "'"$ANALYST_ID"'",
  "type": "specialist",
  "name": "Analyst",
  "owner": "admin",
  "created_by": "installer",
  "description": "Datamining-Agent für Logs, Sessions und System-Daten. Beantwortet Fragen über Aktivitäten und Muster.",
  "llm_model": "'"${HH_DEFAULT_MODEL:-MiniMax-M2.7}"'",
  "fallback_models": [],
  "tools": ["read_memory","search_memory","write_memory","web_search","fetch_url","file_read","dir_list"],
  "mcp_servers": [],
  "temperature": 0.5,
  "max_tokens": 8192,
  "thinking_budget": 0,
  "max_iterations": 40,
  "status": "active",
  "created_at": "'"$now"'",
  "updated_at": "'"$now"'",
  "disabled_skills": [],
  "require_tool_confirm": false,
  "compact_model": "",
  "compact_tool_result_limit": 2000,
  "compact_reserve_tokens": 16384,
  "compact_threshold_pct": 70,
  "tool_result_max_chars": 12000,
  "cache_ttl": "1h",
  "system_prompt": "Du bist ein Analyse-Agent. Du beantwortest Fragen über Logs, Session-Historien und System-Daten.\n\nSei präzise und strukturiert. Fasse Erkenntnisse in klaren Punkten zusammen."
}'

# --- Allrounder ----------------------------------------------------------
ALLROUNDER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
create_agent "$ALLROUNDER_ID" '{
  "id": "'"$ALLROUNDER_ID"'",
  "type": "specialist",
  "name": "Allrounder",
  "owner": "admin",
  "created_by": "installer",
  "description": "Generalistischer Agent für alle Aufgaben. Web-Suche, Dateien, Shell — kein spezieller Fokus.",
  "llm_model": "'"${HH_DEFAULT_MODEL:-MiniMax-M2.7}"'",
  "fallback_models": [],
  "tools": ["shell_exec","file_read","file_write","file_patch","file_search","dir_list","web_search","http_request","fetch_url","read_memory","write_memory","search_memory","todo_write"],
  "mcp_servers": [],
  "temperature": 0.7,
  "max_tokens": 8192,
  "thinking_budget": 0,
  "max_iterations": 30,
  "status": "active",
  "created_at": "'"$now"'",
  "updated_at": "'"$now"'",
  "disabled_skills": [],
  "require_tool_confirm": false,
  "compact_model": "",
  "compact_tool_result_limit": 2000,
  "compact_reserve_tokens": 16384,
  "compact_threshold_pct": 70,
  "tool_result_max_chars": 12000,
  "cache_ttl": "1h",
  "system_prompt": "Du bist ein vielseitiger Assistent. Du kannst im Web suchen, Dateien lesen und schreiben, Shell-Befehle ausführen und Informationen abrufen.\n\nPasse deinen Stil an die Aufgabe an — bei technischen Fragen präzise, bei kreativen Aufgaben offen."
}'

log "Starter-Agenten angelegt: Coder · Analyst · Allrounder"
