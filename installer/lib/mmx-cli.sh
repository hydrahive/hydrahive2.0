#!/usr/bin/env bash
# mmx-cli (MiniMax: TTS, Bild/Video/Musik) auf der festen Soll-Version halten (docs/specs/system-updates.md).
#
# Befund 26.10.2026: installiert wurde nur, wenn mmx fehlte, ohne Version – .2 hatte 1.0.28, hydratest 1.0.12.
# Neu installiert wird mmx weiter von 00-deps.sh / 55-voice.sh (mit dieser Soll-Version); das Update hebt an.
#
# Wird gesourct; idempotent; Fehler sind nie fatal.

# Wechsel bewusst hier (geprüft, dann anheben).
HH_MMX_VERSION="${HH_MMX_VERSION:-1.0.28}"

_mmx_version() {
  local root
  root="$(npm root -g 2>/dev/null)" || return 0
  sed -n 's/.*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$root/mmx-cli/package.json" 2>/dev/null | head -1
}

ensure_mmx_cli() {
  local log_fn=log have out
  declare -F log >/dev/null 2>&1 || log_fn=echo
  command -v mmx >/dev/null 2>&1 || return 0
  command -v npm >/dev/null 2>&1 || return 0
  have="$(_mmx_version)" || have=""
  [ -n "$have" ] || return 0
  if [ "$have" = "$HH_MMX_VERSION" ]; then
    $log_fn "mmx-cli aktuell ($have)"
    return 0
  fi
  $log_fn "mmx-cli $have → $HH_MMX_VERSION anheben"
  if ! out=$(npm install -g --no-fund --no-audit "mmx-cli@$HH_MMX_VERSION" 2>&1); then
    $log_fn "WARNUNG: mmx-cli-Anhebung fehlgeschlagen – $have bleibt"
    printf '%s\n' "$out" | tail -3 | sed 's/^/    /'
    return 0
  fi
  hash -r
  $log_fn "mmx-cli $(_mmx_version) bereit"
  return 0
}
