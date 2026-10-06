#!/usr/bin/env bash
# Tailscale automatisch aktuell halten (Sicherheitsupdates).
#
# Befund 06.10.2026: Auf .2 und VPS lief Tailscale 1.102.4, obwohl 1.102.5 im
# Repo lag. unattended-upgrades war aktiv, erlaubte aber nur Ubuntu-Quellen
# (50unattended-upgrades: Allowed-Origins distro/-security). Die Paketquelle
# pkgs.tailscale.com (Origin "Tailscale") wurde nie berücksichtigt. Der
# eingebaute Tailscale-Autoupdater meldete nur "starting/stopping update checks".
#
# Drei Ebenen, jede für sich ausreichend:
#   1. unattended-upgrades: eigene Datei erlaubt Origin=Tailscale (täglich)
#   2. bei jedem HydraHive-Update sofort auf die neueste Version
#   3. Tailscale-eigener Autoupdater bleibt an
#
# Wird gesourct; idempotent. Fehler sind nie fatal.

HH_TS_APT_CONF="${HH_TS_APT_CONF:-/etc/apt/apt.conf.d/52hydrahive-tailscale}"

_ts_log() {
  if declare -F log >/dev/null 2>&1; then log "$*"; else printf '  · %s\n' "$*"; fi
}

ensure_tailscale_autoupdate() {
  command -v tailscale >/dev/null 2>&1 || return 0

  # 1. unattended-upgrades: Tailscale-Quelle zulassen. Eigene Datei, damit die
  #    Ubuntu-Datei 50unattended-upgrades unverändert bleibt (Paket-Updates).
  #    apt hängt Listen aus mehreren Dateien aneinander.
  local want
  want='// HydraHive: Tailscale-Sicherheitsupdates automatisch einspielen.
// Verwaltet von installer/lib/tailscale-autoupdate.sh — nicht von Hand ändern.
Unattended-Upgrade::Origins-Pattern {
        "origin=Tailscale,label=Tailscale";
};'
  if [ "$(cat "$HH_TS_APT_CONF" 2>/dev/null)" != "$want" ]; then
    _ts_log "Tailscale für automatische Updates freigeben ($HH_TS_APT_CONF)"
    printf '%s\n' "$want" > "$HH_TS_APT_CONF"
    chmod 644 "$HH_TS_APT_CONF"
  fi
  if ! dpkg -s unattended-upgrades >/dev/null 2>&1; then
    _ts_log "HINWEIS: unattended-upgrades nicht installiert — Tailscale wird nur bei HydraHive-Updates aktualisiert"
  fi

  # 2. Sofort aktualisieren, wenn eine neuere Version bereitliegt.
  #    Vorher NUR die Tailscale-Paketliste neu laden (schnell, fasst andere
  #    Quellen nicht an). Kopie in ein Temp-Verzeichnis, weil die Quelle als
  #    tailscale.list ODER tailscale.sources (deb822) vorliegen kann.
  local before after src tmp
  src="$(ls /etc/apt/sources.list.d/tailscale.list /etc/apt/sources.list.d/tailscale.sources 2>/dev/null | head -1)"
  if [ -n "$src" ]; then
    tmp="$(mktemp -d)"
    cp "$src" "$tmp/"
    apt-get update -qq -o Dir::Etc::sourcelist=/dev/null \
      -o Dir::Etc::sourceparts="$tmp" -o APT::Get::List-Cleanup=0 >/dev/null 2>&1 \
      || _ts_log "WARNUNG: Tailscale-Paketliste nicht abrufbar"
    rm -rf "$tmp"
  fi
  before="$(tailscale version 2>/dev/null | head -1)"
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --only-upgrade tailscale >/dev/null 2>&1; then
    after="$(tailscale version 2>/dev/null | head -1)"
    if [ "$before" != "$after" ]; then
      _ts_log "Tailscale aktualisiert: $before → $after"
    else
      _ts_log "Tailscale aktuell ($after)"
    fi
  else
    _ts_log "WARNUNG: Tailscale-Update fehlgeschlagen — unattended-upgrades versucht es erneut"
  fi

  # 3. Eingebauter Autoupdater (zusätzlich).
  tailscale set --auto-update >/dev/null 2>&1 || true
}
