#!/usr/bin/env bash
# Browser-Werkzeug der Agenten (dev-browser) sicherstellen – bei Installation UND Update.
# docs/specs/dev-browser-nachinstallieren.md (Task 3d517e82).
#
# Vorher lag das in modules/87-mcp-servers.sh, das weder install.sh noch update.sh je aufrief:
# neue Installationen hatten kein Browser-Werkzeug, nach dem Server-Umzug fehlte es still.
#
# Wird gesourct; idempotent; Fehler brechen die Installation nicht ab, werden aber gemeldet.
# Erwartet log() vom Aufrufer (Rückfall: echo).

# Feste Version: kein ungeprüfter Sprung auf die 1.0-Vorabversion („next“). Wechsel bewusst hier.
HH_DEV_BROWSER_VERSION="${HH_DEV_BROWSER_VERSION:-0.2.9}"

# Installierte Version aus dem npm-Paket (dev-browser kennt kein --version: „unexpected argument“).
_dev_browser_version() {
  local root
  root="$(npm root -g 2>/dev/null)" || return 0
  sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$root/dev-browser/package.json" 2>/dev/null | head -1
}

ensure_dev_browser() {
  local user="${HH_USER:-hydrahive}" home log_fn=log out
  declare -F log >/dev/null 2>&1 || log_fn=echo
  # Gleicher Ort wie im Werkzeug (tools/web_browser.py): ~/.config/hh-dev-browser-home des Dienst-Nutzers.
  home="${DEV_BROWSER_HOME:-$(eval echo "~$user")/.config/hh-dev-browser-home}"
  local runtime="$home/.dev-browser/node_modules" chromium="$home/.cache/ms-playwright"

  if ! command -v npm >/dev/null 2>&1 && ! command -v dev-browser >/dev/null 2>&1; then
    $log_fn "WARNUNG: npm fehlt – Browser-Werkzeug kann nicht eingerichtet werden"
    return 0
  fi
  mkdir -p "$home"
  chown "$user:$user" "$home" 2>/dev/null || true

  if ! command -v dev-browser >/dev/null 2>&1; then
    $log_fn "Browser-Werkzeug fehlt – installiere dev-browser $HH_DEV_BROWSER_VERSION"
    if ! out=$(npm install -g --no-fund --no-audit "dev-browser@$HH_DEV_BROWSER_VERSION" 2>&1); then
      $log_fn "WARNUNG: dev-browser-Installation fehlgeschlagen – Browser-Werkzeug geht nicht"
      printf '%s\n' "$out" | tail -3 | sed 's/^/    /'
      return 0
    fi
    hash -r
  fi

  if [ -d "$runtime" ] && [ -d "$chromium" ]; then
    $log_fn "Browser-Werkzeug vorhanden (dev-browser $(_dev_browser_version))"
    return 0
  fi

  $log_fn "Browser-Werkzeug: Laufzeit und Chromium nach $home einrichten"
  local tmp_log
  tmp_log="$(mktemp "${TMPDIR:-/tmp}/dev-browser-install.XXXXXX")"
  if sudo -u "$user" env HOME="$home" dev-browser install </dev/null >"$tmp_log" 2>&1 \
     && [ -d "$runtime" ] && [ -d "$chromium" ]; then
    $log_fn "Browser-Werkzeug bereit (dev-browser $(_dev_browser_version))"
  else
    $log_fn "WARNUNG: Browser-Werkzeug nicht vollständig eingerichtet (Laufzeit oder Chromium fehlt)"
    tail -3 "$tmp_log" | sed 's/^/    /'
  fi
  rm -f "$tmp_log"
  return 0
}
