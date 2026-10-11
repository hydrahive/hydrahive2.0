#!/usr/bin/env bash
# Vorab-Prüfungen für install.sh (docs/specs/installer-core-first.md §1). Wird gesourct.
#
# Anlass: Unter WSL brach apt mitten im Herunterladen mit „Temporary failure resolving 'archive.ubuntu.com'“ ab.
# - hh_apt_retries: apt wiederholt fehlgeschlagene Downloads (kurze DNS-/Netz-Aussetzer). Kein Eingriff ins Netz.
# - hh_preflight_dns: prüft vor Phase 1 die Namensauflösung und bricht sonst mit klarer Meldung ab. Repariert nichts.

HH_APT_CONF_DIR="${HH_APT_CONF_DIR:-/etc/apt/apt.conf.d}"
HH_PROC_VERSION="${HH_PROC_VERSION:-/proc/version}"
# Hosts, von denen der Kern-Installer lädt (00-deps.sh: Ubuntu-Archiv, NodeSource, GitHub).
HH_PREFLIGHT_HOSTS="${HH_PREFLIGHT_HOSTS:-archive.ubuntu.com deb.nodesource.com github.com}"

hh_apt_retries() {
  local f="$HH_APT_CONF_DIR/80hydrahive-retries"
  [ -f "$f" ] && return 0                       # schon da (oder vom Admin angepasst) → nicht anfassen
  mkdir -p "$HH_APT_CONF_DIR"
  {
    echo "// Von HydraHive gesetzt (installer/lib/preflight.sh): fehlgeschlagene Downloads wiederholen."
    echo 'Acquire::Retries "5";'
  } > "$f"
  chmod 644 "$f"
}

hh_is_wsl() {
  grep -qi microsoft "$HH_PROC_VERSION" 2>/dev/null
}

hh_preflight_dns() {
  local host failed=""
  [ "${HH_SKIP_PREFLIGHT:-no}" = "yes" ] && return 0
  for host in $HH_PREFLIGHT_HOSTS; do
    getent hosts "$host" >/dev/null 2>&1 || { failed="$host"; break; }
  done
  [ -z "$failed" ] && return 0
  {
    printf '\nKeine Namensauflösung: %s lässt sich nicht auflösen.\n' "$failed"
    printf 'Ohne Namensauflösung kann der Installer keine Pakete laden. Es wurde noch nichts installiert.\n\n'
    printf 'Prüfen:  getent hosts archive.ubuntu.com   und   cat /etc/resolv.conf\n'
    if hh_is_wsl; then
      printf '\nUnter WSL hilft meist:\n'
      printf '  1. In PowerShell: wsl --shutdown   – dann Ubuntu neu öffnen und den Installer erneut starten.\n'
      printf '  2. Reicht das nicht: in %%UserProfile%%\\.wslconfig unter [wsl2] die Zeile dnsTunneling=false\n'
      printf '     eintragen, wsl --shutdown, neu starten.\n'
      printf '  Mehr: README, Abschnitt „Windows über WSL2“.\n'
    fi
    printf '\nOhne Prüfung starten (z. B. eigener Paket-Spiegel): HH_SKIP_PREFLIGHT=yes\n'
  } >&2
  return 1
}
