# shellcheck shell=bash
# Ordner für die Projekt-Freigaben (Samba) anlegen – für den Dienst-User erreichbar, egal welche umask beim
# Installieren galt.
#
# Befund 23.11.2026 (Windows/WSL): /etc/samba war drwx------ root:root, hh-projects.d darunter drwxrwsr-x.
# Der Dienst-User kam nicht durch /etc/samba, sah hh-projects.d also nicht, und die Freigabe meldete
# „samba_not_installed“, obwohl Samba installiert war. mkdir -p / install -d legen fehlende Elternordner mit der
# aktuellen umask an (bei 077 → 700). Darum den Elternordner hier ausdrücklich durchgängig machen.
#
# hh_samba_includes_dir <ordner> <dienst-user>
hh_samba_includes_dir() {
  local dir="$1" user="$2" parent
  parent="$(dirname "$dir")"
  mkdir -p "$parent"
  # Nur Rechte ergänzen, nichts wegnehmen (Ubuntu liefert /etc/samba als 755).
  chmod a+rx "$parent"
  mkdir -p "$dir"
  chgrp "$user" "$dir" 2>/dev/null || true
  chmod 2775 "$dir"
}
