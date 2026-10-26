#!/bin/bash
# macOS: Zusatz-Modul „Dateifreigabe“ (docs/plans/mac-file-sharing.md §2.1) – Gegenstück zu modules/47-samba.sh.
#
# Nutzt die macOS-eigene Dateifreigabe (SMB) statt Samba:
#   - Freigabe-Konto hhshare: versteckt, ohne Login-Shell (/usr/bin/false), nicht in staff – nur für SMB
#   - zufälliges Passwort in $HH_CONFIG_DIR/samba.password (0600, Dienst-Konto; das Cockpit zeigt es an)
#   - Durchgehen bis workspaces/projects per ACL (search) – KEIN chown -R / chmod -R (Lehre Umzug .2 → .226)
#   - SMB-Dienst an, LaunchDaemon io.hydrahive.shares (root) setzt Projekt-Freigaben um (lib/mac-shares-ctl.sh)
# Idempotent: zweiter Lauf legt nichts neu an und ändert das Passwort nicht. Läuft als root (mac-addon-ctl.sh).
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_USER="${HH_USER:?HH_USER fehlt}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
PLIST="${HH_SHARES_PLIST:-/Library/LaunchDaemons/io.hydrahive.shares.plist}"
SHARE_USER="hhshare"
PWFILE="$HH_CONFIG_DIR/samba.password"
SHARES="$HH_CONFIG_DIR/mac-shares.d"

priv() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

# Mac-Besitzer (der Mensch am Mac): Der Finder verbindet sich nicht per SMB mit dem eigenen Mac (live 26.10., NetFS 65
# bei jeder eigenen Adresse). Er bekommt freigegebene Projekte deshalb direkt in ~/HydraHive (mac-shares-ctl.sh).
# Wie im ganzen Mac-Installer: der Besitzer von Homebrew (lib/mac-roles.sh). Gleich dem Dienst-Konto → kein Extra.
if [ -z "${HH_MAC_OWNER+x}" ]; then
  HH_MAC_OWNER="$(source "$(dirname "$0")/../lib/mac-roles.sh" >/dev/null 2>&1 && echo "$HH_BREW_USER" || true)"
fi
case "$HH_MAC_OWNER" in root|"$HH_USER") HH_MAC_OWNER="" ;; esac
[[ "$HH_MAC_OWNER" =~ ^[A-Za-z_][A-Za-z0-9_.-]{0,31}$ ]] || HH_MAC_OWNER=""

# --- Passwort (bleibt bei weiteren Läufen gleich) ---
if [ ! -s "$PWFILE" ]; then
  log "Erzeuge Passwort für die Dateifreigabe"
  ( umask 077; /usr/bin/python3 -c 'import secrets; print(secrets.token_urlsafe(18))' > "$PWFILE" )
fi
priv chown "$HH_USER" "$PWFILE"
chmod 600 "$PWFILE"

# --- Freigabe-Konto ---
if ! dscl . -read "/Users/$SHARE_USER" UniqueID >/dev/null 2>&1; then
  uid=400
  while dscl . -list /Users UniqueID | awk '{print $2}' | grep -qx "$uid"; do uid=$((uid + 1)); done
  log "Lege Freigabe-Konto $SHARE_USER an (UID $uid, ohne Anmeldung)"
  priv dscl . -create "/Users/$SHARE_USER"
  priv dscl . -create "/Users/$SHARE_USER" UniqueID "$uid"
  priv dscl . -create "/Users/$SHARE_USER" PrimaryGroupID 20
  priv dscl . -create "/Users/$SHARE_USER" RealName "HydraHive Dateifreigabe"
  priv dscl . -create "/Users/$SHARE_USER" NFSHomeDirectory /var/empty
fi
priv dscl . -create "/Users/$SHARE_USER" UserShell /usr/bin/false
priv dscl . -create "/Users/$SHARE_USER" IsHidden 1
# Passwort setzen ohne es als Argument zu übergeben (nicht in der Prozessliste): dscl liest im interaktiven Modus
# Befehle von der Standardeingabe.
set_pw() { printf 'passwd /Users/%s %s\n' "$SHARE_USER" "$(cat "$PWFILE")" | priv dscl . >/dev/null 2>&1; }
# macOS legt den Passwort-Hash für SMB nur an, wenn er fürs Konto eingeschaltet ist – und erst beim Passwort-Setzen.
# Ohne ihn: NT_STATUS_LOGON_FAILURE. pwpolicy stürzt aber ab, solange das Konto kein Passwort hat (beides live am Mac
# mit macOS 27 gesehen). Deshalb: Passwort, SMB-Hash an, Passwort noch einmal.
set_pw
priv pwpolicy -u "$SHARE_USER" sethashtypes SMB-NT on >/dev/null 2>&1 || log "Achtung: SMB-Passwort-Hash nicht eingeschaltet"
set_pw

# --- Rechte: nur durchgehen bis zu den Projekten (nicht auflisten – andere Projekte bleiben unsichtbar) ---
for who in "$SHARE_USER" ${HH_MAC_OWNER:+"$HH_MAC_OWNER"}; do
  SEARCH="user:$who allow search"
  for d in "$HH_DATA_DIR" "$HH_DATA_DIR/workspaces" "$HH_DATA_DIR/workspaces/projects"; do
    [ -d "$d" ] || continue
    priv chmod -a "$SEARCH" "$d" 2>/dev/null || true
    priv chmod +a "$SEARCH" "$d"
  done
done

# --- Auftrags-Ordner (Backend schreibt, root liest) ---
mkdir -p "$SHARES"
priv chown "$HH_USER" "$SHARES"
chmod 750 "$SHARES"

# --- SMB-Dienst an ---
log "Schalte die macOS-Dateifreigabe (SMB) ein"
# smbd ist ab Werk nicht geladen (Disabled=true in der System-plist) – kickstart allein findet ihn dann nicht.
priv launchctl enable system/com.apple.smbd
priv launchctl load -w /System/Library/LaunchDaemons/com.apple.smbd.plist >/dev/null 2>&1 || true

# --- LaunchDaemon für die Projekt-Freigaben ---
log "Schreibe $PLIST"
priv tee "$PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.shares</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${HH_REPO_DIR}/installer/lib/mac-shares-ctl.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HH_DATA_DIR</key>
        <string>${HH_DATA_DIR}</string>
        <key>HH_CONFIG_DIR</key>
        <string>${HH_CONFIG_DIR}</string>
        <key>HH_USER</key>
        <string>${HH_USER}</string>
        <key>HH_MAC_OWNER</key>
        <string>${HH_MAC_OWNER}</string>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>WatchPaths</key>
    <array>
        <string>${SHARES}</string>
    </array>
    <key>StandardOutPath</key>
    <string>${HH_LOG_DIR}/hydrahive2-shares.log</string>
    <key>StandardErrorPath</key>
    <string>${HH_LOG_DIR}/hydrahive2-shares.log</string>
</dict>
</plist>
EOF
priv chmod 644 "$PLIST"
priv launchctl bootout system "$PLIST" >/dev/null 2>&1 || true
priv launchctl bootstrap system "$PLIST" >/dev/null 2>&1 || true

# --- Eingeschaltete Projekte neu beauftragen (nach Update: Besitzer-Zugang, Rechte, aufgeräumte Datensätze) ---
for st in "$SHARES"/*.state; do
  [ -f "$st" ] || continue
  id="$(basename "$st" .state)"
  [[ "$id" =~ ^[A-Za-z0-9_-]{1,64}$ ]] && [ "$(cat "$st")" = "on" ] && [ -s "$SHARES/$id.name" ] || continue
  printf 'on\n%s\n%s\n' "$(head -1 "$SHARES/$id.name")" "$HH_DATA_DIR/workspaces/projects/$id" > "$SHARES/.$id.want.tmp"
  mv "$SHARES/.$id.want.tmp" "$SHARES/$id.want"
done

log "Dateifreigabe bereit. Konto: $SHARE_USER, Passwort im Cockpit (Projekt → Einstellungen → Im Netz freigeben)"
