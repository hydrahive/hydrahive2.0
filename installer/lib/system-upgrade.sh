#!/usr/bin/env bash
# Das ganze System mit aktualisieren – nicht nur HydraHive (docs/specs/system-updates.md, Task f24c39bf).
#
# Befund 26.10.2026 (PHP2Shell, CVE-2026-109618/-109619): update.sh hob nie Systempakete an. hydratest hatte
# 225 offene Pakete und keine automatischen Sicherheitsupdates; auf .2 standen 25 Pakete und ein
# Rechner-Neustart offen, ohne dass es jemand sah.
#
#   hh_ensure_auto_updates  nachts Sicherheitsupdates (unattended-upgrades) + Dienste automatisch neu starten
#                           (needrestart) – eigene Dateien, Ubuntu-Dateien bleiben unangetastet.
#   hh_system_upgrade       bei jedem HydraHive-Update ALLE Pakete anheben (entfernt nie etwas).
#
# Wird gesourct; idempotent. Fehler sind nie fatal – das HydraHive-Update läuft weiter.

HH_AUTO_UPGRADES_CONF="${HH_AUTO_UPGRADES_CONF:-/etc/apt/apt.conf.d/21hydrahive-auto-upgrades}"
HH_NEEDRESTART_CONF="${HH_NEEDRESTART_CONF:-/etc/needrestart/conf.d/50-hydrahive.conf}"
HH_REBOOT_REQUIRED_FILE="${HH_REBOOT_REQUIRED_FILE:-/run/reboot-required}"

_su_log() {
  if declare -F log >/dev/null 2>&1; then log "$*"; else printf '  · %s\n' "$*"; fi
}

# Datei nur schreiben, wenn der Inhalt abweicht (idempotent, kein Log-Rauschen).
_su_write() {
  local path="$1" want="$2" what="$3"
  [ "$(cat "$path" 2>/dev/null)" = "$want" ] && return 0
  _su_log "$what schreiben ($path)"
  mkdir -p "$(dirname "$path")"
  printf '%s\n' "$want" > "$path"
  chmod 644 "$path"
}

hh_ensure_auto_updates() {
  command -v apt-get >/dev/null 2>&1 || return 0
  local missing=() p
  for p in unattended-upgrades needrestart; do
    dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    _su_log "Automatische Updates einrichten: ${missing[*]} installieren"
    DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install -y -qq \
      -o DPkg::Lock::Timeout=600 "${missing[@]}" >/dev/null 2>&1 \
      || _su_log "WARNUNG: ${missing[*]} nicht installiert – automatische Updates fehlen vorerst"
  fi

  # Nach 20auto-upgrades gelesen → gewinnt, auch wenn Ubuntus Datei fehlt oder abgeschaltet ist.
  _su_write "$HH_AUTO_UPGRADES_CONF" '// HydraHive: Sicherheitsupdates täglich automatisch einspielen.
// Verwaltet von installer/lib/system-upgrade.sh — nicht von Hand ändern.
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";' "Automatische Sicherheitsupdates"

  # Dienste mit alten Bibliotheken im Speicher automatisch neu starten. Ausgenommen: HydraHive selbst
  # (das Update startet es am Ende neu; ein Neustart von hydrahive2-update bräche das laufende Update ab,
  # nachts unterbräche er Chats) sowie incus/containerd (laufende Container/VMs). Docker, lxc und libvirt
  # schließt needrestart schon selbst aus.
  _su_write "$HH_NEEDRESTART_CONF" '# HydraHive: nach Updates betroffene Dienste automatisch neu starten, nie nachfragen.
# Verwaltet von installer/lib/system-upgrade.sh — nicht von Hand ändern.
$nrconf{restart} = '"'a'"';
$nrconf{kernelhints} = 0;
$nrconf{ucodehints} = 0;
$nrconf{override_rc} = {
    %{$nrconf{override_rc}},
    qr(^hydrahive2) => 0,
    qr(^hydra-voice-bridge) => 0,
    qr(^incus) => 0,
    qr(^containerd) => 0,
};' "Automatische Dienst-Neustarts"
  return 0
}

hh_system_upgrade() {
  if [ "${HH_SYSTEM_UPGRADE:-yes}" = "no" ]; then
    _su_log "Systemupdate abgeschaltet (HH_SYSTEM_UPGRADE=no)"
    return 0
  fi
  command -v apt-get >/dev/null 2>&1 || return 0
  _su_log "System aktualisieren (alle Pakete)"

  # Ein abgebrochener früherer Lauf blockiert sonst jedes apt.
  dpkg --configure -a >/dev/null 2>&1 \
    || _su_log "WARNUNG: dpkg --configure -a fehlgeschlagen – versuche trotzdem weiter"

  local apt_opts=(-o DPkg::Lock::Timeout=600)
  # Eine kaputte Fremdquelle darf die übrigen Updates nicht verhindern.
  ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get "${apt_opts[@]}" -qq update >/dev/null 2>&1 \
    || _su_log "WARNUNG: Paketlisten nicht vollständig abrufbar – aktualisiere mit dem, was da ist"

  local out rc=0
  # upgrade --with-new-pkgs: neue Abhängigkeiten (z. B. neue Kernel) kommen mit, entfernt wird nie etwas.
  # confdef/confold: von Hand geänderte Konfigurationen bleiben.
  # LC_ALL=C: feste englische Ausgabe, damit das Zählen nicht von der Systemsprache abhängt.
  # ACCEPT_EULA=Y: Microsoft-Pakete (msodbcsql18, mssql-tools18) fragen bei JEDER neuen Version erneut nach der
  # Lizenz und brechen sonst ab (Befund hydratest 26.10.). Angehoben wird nur, was schon installiert ist –
  # die Lizenz wurde dabei bereits angenommen.
  out="$(LC_ALL=C ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get "${apt_opts[@]}" -y \
    --with-new-pkgs -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold upgrade 2>&1)" || rc=$?
  if [ "$rc" -ne 0 ]; then
    _su_log "WARNUNG: Systemupdate fehlgeschlagen – HydraHive-Update läuft weiter"
    printf '%s\n' "$out" | grep -E '^(E:|ERROR|dpkg: error|Errors were)' | head -6 | sed 's/^/    /'
    # Pakete, die nach dem Abbruch nur entpackt sind, fertig einrichten (sonst blockieren sie das nächste apt).
    dpkg --configure -a >/dev/null 2>&1 || true
    return 0
  fi

  local n
  n="$(printf '%s\n' "$out" | grep -c '^Setting up ' || true)"
  _su_log "Systempakete aktualisiert: ${n:-0}"

  # Grafiktreiber (nvidia-driver-580, libnvidia-gl-595, nvidia-kernel-common-580 …): Kernel-Modul und neue
  # Bibliothek passen erst nach einem Neustart zusammen.
  if printf '%s\n' "$out" | grep -qE '^Setting up (lib)?nvidia-[a-z0-9-]*[0-9]{3}'; then
    mkdir -p "$(dirname "$HH_REBOOT_REQUIRED_FILE")"
    touch "$HH_REBOOT_REQUIRED_FILE"
  fi
  if [ -e "$HH_REBOOT_REQUIRED_FILE" ]; then
    _su_log "HINWEIS: Neustart des Rechners nötig, damit alle Updates wirken (HydraHive startet ihn nie selbst)"
  fi
  return 0
}
