#!/usr/bin/env bash
# NAT-Netz für Container auf Servern ohne br0, z. B. VPS
# (docs/specs/container-nat-ports.md). Wird gesourct, idempotent.
#
# - incus-Netz hhnat0 (10.10.0.1/24, NAT, ohne IPv6)
# - ufw: Container dürfen DHCP/DNS am Host nutzen und nach außen routen.
#   Ohne diese Regeln verwirft ufw (DEFAULT_FORWARD_POLICY=DROP) jeden
#   weitergeleiteten Verkehr, Container kämen nicht ins Internet.

HH_NAT_NET="${HH_NAT_NET:-hhnat0}"
HH_NAT_CIDR="${HH_NAT_CIDR:-10.10.0.1/24}"

hh_nat_log() {
  if declare -F log >/dev/null 2>&1; then log "$*"; else printf '  · %s\n' "$*"; fi
}

# Ja, wenn kein br0 da ist oder HH_CONTAINER_NAT=yes erzwingt.
hh_nat_wanted() {
  [ "${HH_CONTAINER_NAT:-}" = "yes" ] && return 0
  [ "${HH_CONTAINER_NAT:-}" = "no" ] && return 1
  ! ip link show br0 >/dev/null 2>&1
}

ensure_container_nat() {
  hh_nat_wanted || return 0
  command -v incus >/dev/null 2>&1 || return 0

  if incus network show "$HH_NAT_NET" >/dev/null 2>&1; then
    hh_nat_log "NAT-Netz $HH_NAT_NET vorhanden"
  else
    hh_nat_log "NAT-Netz $HH_NAT_NET anlegen ($HH_NAT_CIDR)"
    incus network create "$HH_NAT_NET" \
      ipv4.address="$HH_NAT_CIDR" ipv4.nat=true \
      ipv6.address=none \
      ipv4.dhcp.ranges=10.10.0.200-10.10.0.250
  fi

  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "^Status: active"; then
    if ! ufw status 2>/dev/null | grep -q "hh-nat-in"; then
      hh_nat_log "ufw: DHCP/DNS aus $HH_NAT_NET zum Host erlauben"
      ufw allow in on "$HH_NAT_NET" comment hh-nat-in >/dev/null
    fi
    if ! ufw status 2>/dev/null | grep -q "hh-nat-out"; then
      hh_nat_log "ufw: Container aus $HH_NAT_NET nach außen routen"
      ufw route allow in on "$HH_NAT_NET" comment hh-nat-out >/dev/null
    fi
  fi
}

# Root-Helfer für Portfreigaben (docs/specs/container-nat-ports.md). Eigene
# sudoers-Datei nur für diesen einen Befehl, damit die Funktion nicht an der
# breiten Extensions-Regel hängt.
install_portforward_helper() {
  local repo="${HH_REPO_DIR:-/opt/hydrahive2}"
  local user="${HH_USER:-hydrahive}"
  local target=/usr/local/sbin/hh-portforward
  local sudoers=/etc/sudoers.d/hydrahive2-portforward
  install -o root -g root -m 0755 "$repo/installer/lib/hh-portforward" "$target"
  local tmp
  tmp="$(mktemp)"
  printf '%s ALL=(root) NOPASSWD: %s\n' "$user" "$target" > "$tmp"
  if visudo -c -f "$tmp" >/dev/null 2>&1; then
    install -o root -g root -m 0440 "$tmp" "$sudoers"
  else
    hh_nat_log "WARNUNG: sudoers für hh-portforward ungültig — nicht installiert"
  fi
  rm -f "$tmp"
}

