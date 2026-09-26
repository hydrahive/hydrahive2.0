#!/usr/bin/env bash
# Secrets des HydraHive-Dienstes in eine nur für root lesbare Env-Datei.
#
# Früher standen HH_SECRET_KEY (signiert alle Logins) als Environment= in
# /etc/systemd/system/hydrahive2.service und der Postgres-Mirror-DSN samt
# Passwort in hydrahive2.service.d/pg-mirror.conf, beide 0644: lesbar für jeden
# lokalen Benutzer und über `systemctl show hydrahive2`. systemd liest
# EnvironmentFile= als root, bevor es zum Dienstbenutzer wechselt, deshalb
# darf die Datei root:root 0600 sein.
#
# Quellen bleiben secret_key und pg_mirror.dsn (Backup/Restore, Migration).
# Die Env-Datei wird bei jedem Aufruf vollständig und atomar neu gebaut.

# Wert für systemd EnvironmentFile= in doppelte Anführungszeichen setzen.
# systemd wertet darin nur \ als Escape aus ($ bleibt wörtlich, keine
# Variablen-Ersetzung). Ein '\'' wie in bash versteht systemd NICHT —
# gegen den echten Parser geprüft (systemd-run -p EnvironmentFile=…).
_systemd_env_quote() {
  local v="$1"
  v="${v//\\/\\\\}"
  v="${v//\"/\\\"}"
  printf '"%s"' "$v"
}

write_service_secrets() {
  local config_dir="${HH_CONFIG_DIR:-/etc/hydrahive2}"
  local target="$config_dir/service-secrets.env"
  local key_file="$config_dir/secret_key"
  local dsn_file="$config_dir/pg_mirror.dsn"
  local key dsn tmp

  key="$(tr -d '\r\n' < "$key_file" 2>/dev/null || true)"
  if [ -z "$key" ]; then
    printf 'service-secrets: %s fehlt oder ist leer — nichts geschrieben\n' "$key_file" >&2
    return 1
  fi

  tmp="$(mktemp "$target.XXXXXX")"
  chmod 600 "$tmp"
  {
    printf 'HH_SECRET_KEY=%s\n' "$(_systemd_env_quote "$key")"
    if [ -s "$dsn_file" ]; then
      dsn="$(tr -d '\r\n' < "$dsn_file")"
      printf 'HH_PG_MIRROR_DSN=%s\n' "$(_systemd_env_quote "$dsn")"
    fi
  } > "$tmp"
  if [ "${HH_SERVICE_SECRETS_SKIP_CHOWN:-}" != 1 ]; then
    chown root:root "$tmp"
  fi
  mv -f "$tmp" "$target"
}
