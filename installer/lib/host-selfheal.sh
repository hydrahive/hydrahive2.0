#!/usr/bin/env bash
# Host-Reparaturen nach einem Distro-Upgrade (v.a. Ubuntu 24.04 -> 26.04).
# Wird gesourct; alle Funktionen sind idempotent und greifen nur ein, wenn der
# Fehlerzustand nachweislich vorliegt. Siehe docs/specs/host-selfheal-ubuntu-2604.md.

# Pfade als Variablen, damit Tests gegen ein tmp-Verzeichnis laufen können.
HH_RESOLVED_CONF_DIR="${HH_RESOLVED_CONF_DIR:-/etc/systemd/resolved.conf.d}"
HH_RESOLV_CONF="${HH_RESOLV_CONF:-/etc/resolv.conf}"
HH_SYSTEMD_SYSTEM_DIR="${HH_SYSTEMD_SYSTEM_DIR:-/etc/systemd/system}"

# DNS-Server, die den Wildcard-Bind 0.0.0.0:53 beanspruchen und deshalb mit dem
# resolved-Stub bzw. dem dnsmasq einer Incus-Bridge kollidieren.
HH_HOST_DNS_UNITS="${HH_HOST_DNS_UNITS:-pihole-FTL dnsmasq named bind9 unbound}"

hh_host_log() {
  if declare -F log >/dev/null 2>&1; then
    log "$*"
  else
    printf '  · %s\n' "$*"
  fi
}

# Gibt den Namen des aktiven Host-DNS-Servers aus (leer, wenn keiner läuft).
hh_host_dns_unit() {
  local unit
  command -v systemctl >/dev/null 2>&1 || return 0
  for unit in $HH_HOST_DNS_UNITS; do
    if systemctl is-active "$unit" >/dev/null 2>&1; then
      printf '%s\n' "$unit"
      return 0
    fi
  done
}

# ── /tmp darf keine RAM-Disk sein ────────────────────────────────────────────
# Ubuntu 26.04 aktiviert die Vendor-Unit tmp.mount. /tmp landet dadurch im RAM.
# Läuft es voll (grosse Mediendateien), geraten RAM und Swap unter Druck,
# SQLite-Commits blockieren und Downloads brechen mit "database is locked" ab.
hh_fix_tmp_on_tmpfs() {
  local fstype

  command -v systemctl >/dev/null 2>&1 || return 0
  command -v findmnt >/dev/null 2>&1 || return 0

  fstype="$(findmnt -no FSTYPE /tmp 2>/dev/null || true)"
  [ "$fstype" = "tmpfs" ] || return 0

  if [ "$(systemctl is-enabled tmp.mount 2>/dev/null || true)" = "masked" ]; then
    return 0
  fi

  hh_host_log "/tmp liegt im RAM (tmpfs) — maskiere tmp.mount"
  systemctl mask tmp.mount >/dev/null 2>&1 || {
    hh_host_log "WARNUNG: tmp.mount konnte nicht maskiert werden"
    return 0
  }
  # Bewusst kein umount: bei laufendem Betrieb sind Dateien offen. Ein
  # erzwungenes Aushängen würde Prozesse beschädigen.
  hh_host_log "/tmp liegt nach dem nächsten Reboot wieder auf der Platte"
}

# ── systemd-resolved-Stub vs. Host-DNS-Server ────────────────────────────────
# Distro-Upgrades setzen /etc/systemd/resolved.conf auf den Werkszustand zurück.
# Der Stub-Listener belegt dann wieder 127.0.0.53:53 und verdrängt Pi-hole & Co.
# Das Drop-in überlebt kommende Upgrades, anders als die Hauptdatei.
hh_fix_resolved_stub() {
  local dns_unit dropin changed=0

  command -v systemctl >/dev/null 2>&1 || return 0
  dns_unit="$(hh_host_dns_unit)"
  [ -n "$dns_unit" ] || return 0

  dropin="$HH_RESOLVED_CONF_DIR/10-hydrahive-no-stub.conf"
  if [ ! -f "$dropin" ]; then
    hh_host_log "DNS-Server '$dns_unit' aktiv — resolved-Stub-Listener abschalten"
    mkdir -p "$HH_RESOLVED_CONF_DIR"
    cat > "$dropin" <<'EOF'
# Von HydraHive gesetzt: ein lokaler DNS-Server (z.B. Pi-hole) belegt Port 53
# auf allen Interfaces. Der Stub-Listener von systemd-resolved würde damit
# kollidieren ("failed to create listening socket for port 53: Address in use").
# Distro-Upgrades setzen /etc/systemd/resolved.conf zurück — dieses Drop-in
# bleibt davon unberührt.
[Resolve]
DNSStubListener=no
EOF
    changed=1
  fi

  # Der Stub antwortet nicht mehr — resolv.conf darf nicht auf ihn zeigen.
  if [ -L "$HH_RESOLV_CONF" ]; then
    case "$(readlink "$HH_RESOLV_CONF")" in
      *stub-resolv.conf)
        hh_host_log "resolv.conf zeigt auf den Stub — auf echten Resolver umhängen"
        ln -sf /run/systemd/resolve/resolv.conf "$HH_RESOLV_CONF"
        changed=1
        ;;
    esac
  fi

  [ "$changed" -eq 1 ] || return 0
  systemctl restart systemd-resolved >/dev/null 2>&1 || true
  systemctl restart "$dns_unit" >/dev/null 2>&1 || true
}

# ── Incus-Bridge belegt Port 53 ──────────────────────────────────────────────
# Incus startet je verwalteter Bridge einen dnsmasq, der TCP auf <bridge-ip>:53
# hält. Das verhindert den Wildcard-Bind eines Host-DNS-Servers. "port=0"
# schaltet nur den DNS-Teil ab — DHCP für die Container bleibt aktiv.
hh_fix_incus_bridge_dns() {
  local dns_unit bridge raw

  command -v incus >/dev/null 2>&1 || return 0
  dns_unit="$(hh_host_dns_unit)"
  [ -n "$dns_unit" ] || return 0

  while IFS=',' read -r bridge type managed _rest; do
    [ -n "$bridge" ] || continue
    [ "$type" = "bridge" ] || continue
    [ "$managed" = "YES" ] || continue

    raw="$(incus network get "$bridge" raw.dnsmasq 2>/dev/null || true)"
    case "$raw" in *port=0*) continue ;; esac

    hh_host_log "Incus-Bridge '$bridge' blockiert Port 53 — DNS abschalten (DHCP bleibt)"
    incus network set "$bridge" raw.dnsmasq port=0 >/dev/null 2>&1 \
      || hh_host_log "WARNUNG: raw.dnsmasq für '$bridge' nicht setzbar"
  done < <(incus network list --format=csv -c ntm 2>/dev/null || true)
}

# ── Boot-Reihenfolge absichern ───────────────────────────────────────────────
# Zusätzlicher Schutz: startet Incus vor Pi-hole, war die Bridge zuerst da.
hh_fix_pihole_ordering() {
  local dropin_dir

  command -v systemctl >/dev/null 2>&1 || return 0
  command -v incus >/dev/null 2>&1 || return 0
  systemctl is-active pihole-FTL >/dev/null 2>&1 || return 0

  dropin_dir="$HH_SYSTEMD_SYSTEM_DIR/pihole-FTL.service.d"
  [ -f "$dropin_dir/10-after-incus.conf" ] && return 0

  hh_host_log "Startreihenfolge sichern: pihole-FTL nach incus"
  mkdir -p "$dropin_dir"
  cat > "$dropin_dir/10-after-incus.conf" <<'EOF'
# Von HydraHive gesetzt: Incus legt beim Start verwaltete Bridges mit eigenem
# dnsmasq an. Startete dieser vor Pi-hole, belegte er Port 53 und Pi-hole kam
# nicht hoch — der Host hatte dann keine Namensauflösung mehr.
[Unit]
After=incus.service
EOF
  systemctl daemon-reload >/dev/null 2>&1 || true
}

# ── Wirkprüfung ──────────────────────────────────────────────────────────────
# Wichtig: "systemctl is-active pihole-FTL" meldet auch dann "active", wenn das
# interne dnsmasq den Port nicht binden konnte. Nur eine echte Abfrage zeigt,
# ob DNS wirklich funktioniert.
hh_verify_dns() {
  local dns_unit

  dns_unit="$(hh_host_dns_unit)"
  [ -n "$dns_unit" ] || return 0
  command -v dig >/dev/null 2>&1 || return 0

  hh_dns_answers() {
    dig +short +timeout=3 +tries=1 github.com @127.0.0.1 >/dev/null 2>&1
  }

  hh_dns_answers && return 0

  hh_host_log "DNS-Server '$dns_unit' antwortet nicht — Neustart"
  systemctl restart "$dns_unit" >/dev/null 2>&1 || true
  sleep 3

  if hh_dns_answers; then
    hh_host_log "DNS wieder funktionsfähig"
    return 0
  fi
  hh_host_log "WARNUNG: DNS antwortet weiterhin nicht — Port 53 manuell prüfen (ss -lunp 'sport = :53')"
}
