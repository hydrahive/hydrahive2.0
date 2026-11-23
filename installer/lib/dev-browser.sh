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

# Nächstliegende Plattform, die Playwright für Linux kennt: ubuntu24.04 mit passender Architektur.
# Nur für Ubuntu-Abkömmlinge neuer als 24.04 (sonst leer → kein Rückfall).
_dev_browser_fallback_platform() {
  local id="" ver="" arch osr="${HH_OS_RELEASE:-/etc/os-release}"
  [ -r "$osr" ] || return 0
  id="$(. "$osr" && echo "${ID:-}")"
  ver="$(. "$osr" && echo "${VERSION_ID:-}")"
  case "$id" in ubuntu|pop|neon|tuxedo) ;; *) return 0 ;; esac
  [ "${ver%%.*}" -ge 26 ] 2>/dev/null || return 0
  case "${HH_UNAME_M:-$(uname -m)}" in x86_64|amd64) arch=x64 ;; aarch64|arm64) arch=arm64 ;; *) return 0 ;; esac
  echo "ubuntu24.04-$arch"
}

_dev_browser_install() {  # user home platform log
  if [ -n "$3" ]; then
    sudo -u "$1" env HOME="$2" PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="$3" dev-browser install </dev/null >"$4" 2>&1
  else
    sudo -u "$1" env HOME="$2" dev-browser install </dev/null >"$4" 2>&1
  fi
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
  else
    # Vorhanden, aber andere Version (Befund .4: 0.2.7 statt 0.2.9; Task f24c39bf): auf die Soll-Version.
    # Unbekannte Version (package.json nicht lesbar) → nichts erzwingen.
    local have
    have="$(_dev_browser_version)" || have=""
    if [ -n "$have" ] && [ "$have" != "$HH_DEV_BROWSER_VERSION" ]; then
      $log_fn "Browser-Werkzeug: dev-browser $have → $HH_DEV_BROWSER_VERSION anheben"
      if ! out=$(npm install -g --no-fund --no-audit "dev-browser@$HH_DEV_BROWSER_VERSION" 2>&1); then
        $log_fn "WARNUNG: dev-browser-Anhebung fehlgeschlagen – $have bleibt"
        printf '%s\n' "$out" | tail -3 | sed 's/^/    /'
        return 0
      fi
      hash -r
      # Neue Version → Laufzeit und Chromium passend neu einrichten (unten).
      runtime="$runtime.neu-einrichten"
    fi
  fi

  if [ -d "$runtime" ] && [ -d "$chromium" ]; then
    $log_fn "Browser-Werkzeug vorhanden (dev-browser $(_dev_browser_version))"
    return 0
  fi

  $log_fn "Browser-Werkzeug: Laufzeit und Chromium nach $home einrichten"
  local tmp_log platform
  tmp_log="$(mktemp "${TMPDIR:-/tmp}/dev-browser-install.XXXXXX")"
  runtime="$home/.dev-browser/node_modules"
  platform=""
  if _dev_browser_install "$user" "$home" "" "$tmp_log" && [ -d "$runtime" ] && [ -d "$chromium" ]; then
    $log_fn "Browser-Werkzeug bereit (dev-browser $(_dev_browser_version))"
  elif grep -q "does not support chromium on ubuntu" "$tmp_log" \
       && platform="$(_dev_browser_fallback_platform)" && [ -n "$platform" ]; then
    # Neueres Ubuntu, als das in dev-browser gebündelte Playwright kennt (Befund 23.11.2026: Playwright 1.58
    # kennt höchstens ubuntu24.04, Ubuntu 26.04 bricht ab). Chromium für Linux ist für alle Ubuntu-Versionen
    # dasselbe Paket (Chrome for Testing linux64). Nur der Download braucht die bekannte Kennung; beim Start
    # findet dev-browser Chromium im selben Ordner wieder (geprüft auf 26.04: Start ohne Kennung lädt Seiten).
    $log_fn "Browser-Werkzeug: Ubuntu-Version dem gebündelten Playwright unbekannt – nehme Chromium für $platform"
    if _dev_browser_install "$user" "$home" "$platform" "$tmp_log" && [ -d "$runtime" ] && [ -d "$chromium" ]; then
      $log_fn "Browser-Werkzeug bereit (dev-browser $(_dev_browser_version), Chromium für $platform)"
    else
      $log_fn "WARNUNG: Browser-Werkzeug nicht vollständig eingerichtet (Laufzeit oder Chromium fehlt)"
      tail -3 "$tmp_log" | sed 's/^/    /'
    fi
  else
    $log_fn "WARNUNG: Browser-Werkzeug nicht vollständig eingerichtet (Laufzeit oder Chromium fehlt)"
    tail -3 "$tmp_log" | sed 's/^/    /'
  fi
  rm -f "$tmp_log"
  return 0
}
