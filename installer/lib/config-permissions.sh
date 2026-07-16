#!/usr/bin/env bash
# Self-Heal für schreibbare Runtime-Konfigurationen auf bestehenden Installationen.

repair_llm_config_permissions() {
  local config_dir="${HH_CONFIG_DIR:-/etc/hydrahive2}"
  local service_user="${HH_USER:-hydrahive}"
  local llm_config="$config_dir/llm.json"

  [ -e "$llm_config" ] || return 0

  # Keine Links verfolgen: Update darf nie Besitzer/Rechte eines fremden Ziels ändern.
  if [ -L "$config_dir" ] || [ -L "$llm_config" ] || [ ! -d "$config_dir" ] || [ ! -f "$llm_config" ]; then
    log "WARNUNG: $llm_config ist keine reguläre Config-Datei — Permission-Self-Heal übersprungen"
    return 0
  fi

  log "LLM-Config-Rechte prüfen und reparieren"
  chown -- "$service_user:$service_user" "$config_dir" "$llm_config"
  chmod 750 -- "$config_dir"
  chmod 640 -- "$llm_config"
}
