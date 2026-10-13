#!/usr/bin/env bash
# Gemeinsame, idempotente Python-venv-Reparatur für Installer und Update.
# Wird gesourct; setzt HH_VENV_REBUILT auf 0 oder 1.

hh_venv_log() {
  if declare -F log >/dev/null 2>&1; then
    log "$*"
  else
    printf '  · %s\n' "$*"
  fi
}

hh_pick_python() {
  local candidate resolved

  if [ -n "${HH_PYTHON:-}" ]; then
    case "$HH_PYTHON" in
      /*) ;;
      *) printf 'HH_PYTHON muss ein absoluter Pfad sein: %s\n' "$HH_PYTHON" >&2; return 1 ;;
    esac
    resolved="$(readlink -f -- "$HH_PYTHON" 2>/dev/null || true)"
    if [ -z "$resolved" ] || [ ! -x "$resolved" ]; then
      printf 'HH_PYTHON ist nicht ausführbar: %s\n' "$HH_PYTHON" >&2
      return 1
    fi
    printf '%s\n' "$resolved"
    return 0
  fi

  # Absolute Systempfade verhindern, dass ein manipuliertes PATH bei einem als
  # root laufenden Update einen fremden Interpreter einschleust.
  # HH_PYTHON_BIN_DIR (Standard /usr/bin) nur für Tests und Sonderinstallationen.
  local bin_dir="${HH_PYTHON_BIN_DIR:-/usr/bin}"
  case "$bin_dir" in
    /*) ;;
    *) printf 'HH_PYTHON_BIN_DIR muss ein absoluter Pfad sein: %s\n' "$bin_dir" >&2; return 1 ;;
  esac

  # Zuerst das System-Python der Distribution (Ubuntu 26.04: 3.14, 24.04: 3.12).
  # Aufgelöst auf die versionierte Datei: ein venv aus /usr/bin/python3 liefe nach
  # einem Distributionswechsel still mit dem neuen Interpreter und fände seine
  # Pakete nicht mehr (SearXNG-Ausfall 29.08.–26.09.2026). Ein venv aus
  # /usr/bin/python3.14 zeigt dann ins Leere, und hh_venv_needs_rebuild baut neu.
  # Nur wenn das System-Python zu alt ist: nachinstalliertes 3.13/3.12 (deadsnakes).
  for candidate in "$bin_dir/python3" "$bin_dir/python3.13" "$bin_dir/python3.12"; do
    resolved="$(readlink -f -- "$candidate" 2>/dev/null || true)"
    [ -n "$resolved" ] && [ -x "$resolved" ] || continue
    if hh_python_at_least_312 "$resolved"; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done

  printf 'Kein Python ab 3.12 unter %s gefunden (hydrahive-core verlangt >= 3.12).\n' "$bin_dir" >&2
  return 1
}

hh_python_at_least_312() {
  local minor
  minor="$(hh_python_minor "$1" 2>/dev/null || true)"
  [[ "$minor" =~ ^3\.([0-9]+)$ ]] && [ "${BASH_REMATCH[1]}" -ge 12 ]
}

hh_python_minor() {
  "$1" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
}

hh_ensure_venv_module() {
  local python_bin="$1" minor package
  "$python_bin" -m ensurepip --version >/dev/null 2>&1 && return 0

  [ "$(id -u)" -eq 0 ] || {
    printf 'Python-venv-Unterstützung fehlt für %s; Installation benötigt root.\n' "$python_bin" >&2
    return 1
  }
  minor="$(hh_python_minor "$python_bin")"
  [[ "$minor" =~ ^3\.[0-9]+$ ]] || {
    printf 'Ungültige Python-Version: %s\n' "$minor" >&2
    return 1
  }
  if [ "$python_bin" = "/usr/bin/python3" ]; then
    package="python3-venv"
  else
    package="python${minor}-venv"
  fi
  hh_venv_log "Venv-Modul fehlt — installiere $package"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y -- "$package"
  "$python_bin" -m ensurepip --version >/dev/null 2>&1 || {
    printf 'Venv-Unterstützung fehlt trotz Installation von %s.\n' "$package" >&2
    return 1
  }
}

# Erfolg (0) bedeutet: Rebuild ist nötig. Das erlaubt idiomatische Nutzung in
# einem if-Block trotz des semantischen Namens.
hh_venv_needs_rebuild() {
  local venv="$1" python_bin="$2" want have
  local venv_python="$venv/bin/python"

  [ -x "$venv_python" ] || return 0

  want="$(hh_python_minor "$python_bin" 2>/dev/null || true)"
  have="$(hh_python_minor "$venv_python" 2>/dev/null || true)"
  [ -n "$want" ] && [ "$want" = "$have" ] || return 0

  # Ein existierender Interpreter genügt nicht: nach partiellen Upgrades kann
  # pip fehlen oder seine Installation unbrauchbar sein.
  "$venv_python" -m pip --version >/dev/null 2>&1 || return 0
  return 1
}

hh_run_as_owner_home() {
  local owner="$1" owner_home="$2"
  shift 2
  if [ "$(id -u)" -eq 0 ] && [ "$owner" != "root" ]; then
    /usr/bin/sudo -u "$owner" -- /usr/bin/env HOME="$owner_home" "$@"
  else
    /usr/bin/env HOME="$owner_home" "$@"
  fi
}

hh_run_as_owner() {
  local owner="$1" owner_home
  shift
  owner_home="$(getent passwd "$owner" | cut -d: -f6)"
  hh_run_as_owner_home "$owner" "$owner_home" "$@"
}

hh_ensure_python_venv() {
  local venv="$1" owner="$2" service="${3:-}" trusted_parent="${4:-}"
  local python_bin resolved_venv resolved_parent owner_group
  HH_VENV_REBUILT=0

  id "$owner" >/dev/null 2>&1 || {
    printf 'Venv-Owner existiert nicht: %s\n' "$owner" >&2
    return 1
  }
  [ ! -L "$venv" ] || {
    printf 'Venv-Pfad darf kein Symlink sein: %s\n' "$venv" >&2
    return 1
  }

  if [ -n "$trusted_parent" ]; then
    resolved_venv="$(realpath -m -- "$venv")"
    resolved_parent="$(realpath -m -- "$trusted_parent")"
    case "$resolved_venv/" in
      "$resolved_parent"/*) ;;
      *) printf 'Venv liegt außerhalb des erlaubten Pfads: %s\n' "$venv" >&2; return 1 ;;
    esac
  fi

  python_bin="$(hh_pick_python)"
  hh_venv_log "Python-venv: Zielinterpreter $python_bin ($("$python_bin" --version 2>&1))"

  if ! hh_venv_needs_rebuild "$venv" "$python_bin"; then
    hh_venv_log "Python-venv ist gesund — kein Rebuild"
    return 0
  fi

  hh_ensure_venv_module "$python_bin"
  HH_VENV_REBUILT=1
  if [ -n "$service" ] && command -v systemctl >/dev/null 2>&1 \
      && systemctl cat "$service" >/dev/null 2>&1; then
    hh_venv_log "Stoppe $service vor dem Venv-Rebuild"
    systemctl stop "$service" || true
  fi

  hh_venv_log "Python-venv fehlt oder ist inkompatibel — baue mit --clear neu"
  mkdir -p -- "$(dirname -- "$venv")"
  if [ "$(id -u)" -eq 0 ]; then
    owner_group="$(id -gn "$owner")"
    chown "$owner:$owner_group" "$(dirname -- "$venv")"
  fi
  hh_run_as_owner "$owner" "$python_bin" -m venv --clear "$venv"

  "$venv/bin/python" -m pip --version >/dev/null 2>&1 || {
    printf 'Neu aufgebautes Venv enthält kein funktionsfähiges pip: %s\n' "$venv" >&2
    return 1
  }
  hh_venv_log "Python-venv neu aufgebaut: $($venv/bin/python --version 2>&1)"
}
