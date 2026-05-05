#!/usr/bin/env bash
# LLM-Provider-Wizard — fragt Provider-Keys ab und schreibt llm.json.
# Source-bar von install.sh und onboard.sh. Benötigt:
#   - HH_CONFIG_DIR (Pfad zur Config)
#   - HH_USER (Service-User)
#   - is_tty(), log() Funktionen vom Aufrufer
#   - NO_PROMPT (0/1)

# Provider-Tabelle: id|Display-Name|Default-Modelle (kommasep)|Key-URL
# Die Modell-Listen sind als sinnvolle Defaults gemeint — der User kann
# sie später unter https://server/llm anpassen.
provider_info() {
  # Modell-IDs mit LiteLLM-Provider-Prefix wo nötig (außer Anthropic + MiniMax,
  # die laufen direkt über das anthropic-SDK und brauchen den Prefix nicht).
  case "$1" in
    anthropic)  echo "Anthropic|claude-sonnet-4-6,claude-opus-4-7,claude-haiku-4-5|https://console.anthropic.com/" ;;
    openai)     echo "OpenAI|openai/gpt-5,openai/gpt-5-mini,openai/gpt-4o|https://platform.openai.com/api-keys" ;;
    minimax)    echo "MiniMax|MiniMax-Text-01,MiniMax-M1|https://intl.minimaxi.com/" ;;
    openrouter) echo "OpenRouter|openrouter/auto,openrouter/anthropic/claude-sonnet-4-6,openrouter/openai/gpt-5|https://openrouter.ai/keys" ;;
    groq)       echo "Groq|groq/llama-3.3-70b-versatile,groq/llama-3.1-8b-instant|https://console.groq.com/keys" ;;
    mistral)    echo "Mistral|mistral/mistral-large-latest,mistral/mistral-medium|https://console.mistral.ai/api-keys/" ;;
    gemini)     echo "Google Gemini|gemini/gemini-2.0-flash,gemini/gemini-2.0-pro|https://aistudio.google.com/apikey" ;;
    nvidia)     echo "NVIDIA NIM|nvidia_nim/meta/llama-3.3-70b-instruct,nvidia_nim/meta/llama-3.1-405b-instruct|https://build.nvidia.com/" ;;
  esac
}

PROVIDER_IDS=(anthropic openai minimax openrouter groq mistral gemini nvidia)

llm_wizard() {
  local llm_json="${HH_CONFIG_DIR}/llm.json"

  # Kein TTY oder no-prompt: skippen
  if ! is_tty || [ "${NO_PROMPT:-0}" = "1" ]; then
    log "LLM-Wizard übersprungen (kein TTY) — später unter https://<server>/llm"
    return 0
  fi

  # Wenn schon befüllt: überspringen außer --reconfigure
  if [ -f "$llm_json" ] && [ "${RECONFIGURE:-0}" != "1" ]; then
    if python3 -c "
import json,sys
try: d=json.load(open('$llm_json'))
except Exception: sys.exit(1)
sys.exit(0 if d.get('providers') else 1)
" 2>/dev/null; then
      log "llm.json hat schon Provider — überspringe Wizard."
      log "Erneut abfragen: sudo bash install.sh --reconfigure"
      return 0
    fi
  fi

  printf "\n\033[1;36m── LLM-Provider-Setup ──\033[0m\n" >/dev/tty
  printf "  Welche Provider hast du? Du kannst mehrere wählen.\n" >/dev/tty
  printf "  (Enter = überspringen, alles später unter https://<server>/llm)\n\n" >/dev/tty

  local i=0
  for pid in "${PROVIDER_IDS[@]}"; do
    i=$((i+1))
    local info name
    info=$(provider_info "$pid")
    name="${info%%|*}"
    printf "  %d) %s\n" "$i" "$name" >/dev/tty
  done
  printf "\n  Welche aktivieren? (z.B. \"1,3\" oder Enter = skip): " >/dev/tty
  local choices
  read -r choices </dev/tty || choices=""

  if [ -z "$choices" ]; then
    log "LLM-Wizard übersprungen — später unter https://<server>/llm"
    return 0
  fi

  # Auswahl parsen → IDs sammeln
  local sel_ids=()
  IFS=',' read -ra IDX_ARR <<< "$choices"
  for idx in "${IDX_ARR[@]}"; do
    idx=$(echo "$idx" | tr -d ' ')
    [[ "$idx" =~ ^[0-9]+$ ]] || continue
    [ "$idx" -lt 1 ] && continue
    [ "$idx" -gt "${#PROVIDER_IDS[@]}" ] && continue
    sel_ids+=("${PROVIDER_IDS[$((idx-1))]}")
  done

  if [ ${#sel_ids[@]} -eq 0 ]; then
    log "Keine gültige Auswahl — Wizard übersprungen"
    return 0
  fi

  # Pro ausgewählten Provider Key abfragen
  local sel_entries=()  # je Eintrag: pid|name|key|models
  local oauth_done=()   # provider-IDs für die OAuth schon llm.json geschrieben hat
  printf "\n" >/dev/tty
  for pid in "${sel_ids[@]}"; do
    local info name rest models url
    info=$(provider_info "$pid")
    name="${info%%|*}"
    rest="${info#*|}"
    models="${rest%|*}"
    url="${rest##*|}"
    printf "  \033[1;37m%s\033[0m\n" "$name" >/dev/tty

    # OAuth-Pfad — aktuell nur Anthropic
    if [ "$pid" = "anthropic" ]; then
      if ask_yn "  OAuth-Login (Pro/Max-Account, kein API-Key nötig)?" "y"; then
        if python3 "$INSTALLER_DIR/lib/oauth_anthropic_cli.py" "$llm_json"; then
          oauth_done+=("anthropic")
          # Modelle für Default-Auswahl trotzdem registrieren — kein Key nötig
          sel_entries+=("$pid|$name|<oauth>|$models")
          continue
        else
          log "  OAuth fehlgeschlagen — fallback auf API-Key"
        fi
      fi
    fi

    # API-Key-Pfad
    printf "  Key holen: %s\n" "$url" >/dev/tty
    printf "  API-Key (Eingabe versteckt, Enter = skip): " >/dev/tty
    local key
    read -rs key </dev/tty || key=""
    printf "\n" >/dev/tty
    if [ -n "$key" ]; then
      sel_entries+=("$pid|$name|$key|$models")
    fi
  done

  if [ ${#sel_entries[@]} -eq 0 ]; then
    log "Keine Keys eingegeben — Wizard übersprungen"
    return 0
  fi

  # Default-Modell-Auswahl: alle Modelle der gewählten Provider auflisten
  local all_models=() j=0
  printf "\n  \033[1;37mDefault-Modell:\033[0m\n" >/dev/tty
  for entry in "${sel_entries[@]}"; do
    local emodels
    emodels="${entry##*|}"
    IFS=',' read -ra MARR <<< "$emodels"
    for m in "${MARR[@]}"; do
      j=$((j+1))
      all_models+=("$m")
      printf "  %d) %s\n" "$j" "$m" >/dev/tty
    done
  done
  printf "\n  Default-Modell wählen [1]: " >/dev/tty
  local def_idx default_model
  read -r def_idx </dev/tty || def_idx=""
  [ -z "$def_idx" ] && def_idx=1
  [[ "$def_idx" =~ ^[0-9]+$ ]] || def_idx=1
  [ "$def_idx" -lt 1 ] && def_idx=1
  [ "$def_idx" -gt "${#all_models[@]}" ] && def_idx=1
  default_model="${all_models[$((def_idx-1))]}"

  # llm.json schreiben — Daten via stdin an Python (Keys nicht in ps sichtbar).
  # `python3 -c '...'` statt heredoc, weil Heredoc-Stdin sonst die Pipe-Stdin
  # überschreibt → Python würde leere Daten lesen.
  mkdir -p "$HH_CONFIG_DIR"
  if ! {
    printf "%s\n" "$default_model"
    for entry in "${sel_entries[@]}"; do
      printf "%s\n" "$entry"
    done
  } | python3 -c '
import json, sys
# Existing llm.json laden — OAuth-Block + embed_model + nicht angefasste Provider erhalten
try:
    existing = json.load(open(sys.argv[1]))
except Exception:
    existing = {}
existing_providers = existing.get("providers", [])
old_by_id = {p.get("id"): p for p in existing_providers}

lines = sys.stdin.read().splitlines()
if not lines:
    sys.exit("no input")
default_model = lines[0]
new_providers = []
new_pids = set()
for line in lines[1:]:
    if not line:
        continue
    pid, name, key, models = line.split("|", 3)
    p = {
        "id": pid,
        "name": name,
        "api_key": "" if key == "<oauth>" else key,
        "models": [m for m in models.split(",") if m],
    }
    # OAuth-Block aus vorigem Schreibvorgang (oauth_anthropic_cli.py) übernehmen
    old = old_by_id.get(pid) or {}
    if old.get("oauth"):
        p["oauth"] = old["oauth"]
    new_providers.append(p)
    new_pids.add(pid)
# Provider die im aktuellen Wizard NICHT ausgewählt wurden bleiben unverändert.
for p in existing_providers:
    if p.get("id") not in new_pids:
        new_providers.append(p)
out = {
    "providers": new_providers,
    "default_model": default_model or existing.get("default_model", ""),
    "embed_model": existing.get("embed_model", ""),
}
with open(sys.argv[1], "w") as f:
    json.dump(out, f, indent=2)
' "$llm_json" 2>&1; then
    log "FEHLER: llm.json schreiben fehlgeschlagen — Provider später unter https://<server>/llm eintragen"
    return 0
  fi

  # Datei muss vom Backend (HH_USER) überschrieben werden können — sonst
  # ignoriert die Web-UI Speicherungen still.
  chown "${HH_USER:-hydrahive}:${HH_USER:-hydrahive}" "$llm_json" 2>/dev/null || true
  chmod 640 "$llm_json" 2>/dev/null || true
  log "LLM-Config geschrieben: $llm_json (Default: $default_model)"
}
