#!/usr/bin/env bash
# Bindet die von HydraHive verwaltete SSH-Config in die SSH-Config des
# Service-Users ein.
#
# Hintergrund: ssh_key-Credentials landen in $HH_DATA_DIR/.ssh/config
# (credentials/ssh.py). ssh liest aber nur $HOME/.ssh/config — und $HOME
# (/home/hydrahive) ist im Service per ProtectHome=read-only gesperrt, das
# Backend kann dort also nichts eintragen. Deshalb setzt der Installer/Updater
# (als root) einmalig eine Include-Zeile. Danach greift `ssh <host>` ohne -F.
#
# Wird gesourct; idempotent.

ensure_ssh_credentials_include() {
  local service_user="${HH_USER:-hydrahive}"
  local data_dir="${HH_DATA_DIR:-/var/lib/hydrahive2}"
  local home_dir="${HH_SSH_HOME:-/home/$service_user}"
  local ssh_dir="$home_dir/.ssh"
  local user_config="$ssh_dir/config"
  local include_line="Include $data_dir/.ssh/config"

  # Keine Links verfolgen: nie fremde Ziele anfassen.
  if [ -L "$ssh_dir" ] || [ -L "$user_config" ]; then
    log "WARNUNG: $ssh_dir oder $user_config ist ein Symlink — SSH-Include übersprungen"
    return 0
  fi

  mkdir -p -- "$ssh_dir"
  chmod 700 -- "$ssh_dir"

  if [ -f "$user_config" ] && grep -qxF -- "$include_line" "$user_config"; then
    return 0
  fi

  log "SSH-Credentials-Config in $user_config einbinden"
  # Include muss VOR jedem Host-Block stehen, sonst gilt es nur innerhalb des
  # letzten Host-Matches — darum vorne einfügen.
  local tmp
  tmp="$(mktemp "$ssh_dir/.config.XXXXXX")"
  {
    printf '# HydraHive: ssh_key-Credentials (verwaltet über die Web-UI)\n'
    printf '%s\n' "$include_line"
    if [ -f "$user_config" ]; then
      printf '\n'
      cat -- "$user_config"
    fi
  } > "$tmp"
  mv -f -- "$tmp" "$user_config"
  chmod 600 -- "$user_config"
  chown -- "$service_user:$service_user" "$ssh_dir" "$user_config" 2>/dev/null || true
}
