#!/bin/bash
# macOS: eigenes, verstecktes System-Konto für HydraHive anlegen (Plan docs/plans/mac-service-user.md).
#
# Warum: Seit macOS 15 sperrt der Datenschutz „Lokales Netzwerk“ alle Nicht-Apple-Programme des am Bildschirm
# angemeldeten Nutzers – auch als LaunchDaemon. Läuft HydraHive als Mac-Besitzer, erreicht es nichts im Heimnetz
# (Portfreigaben, Kopplung, Home Assistant …). Ein System-Konto ohne Anmeldung ist davon nicht betroffen (getestet).
# Wie Linux (Nutzer `hydrahive`) und macOS selbst (`_postgres`, `_www`).
#
# Konto: _hydrahive, UID = GID frei im Bereich 450–499 (Nutzer UND Gruppe frei – auf macOS 27 ist z. B. GID 400
# schon vergeben), Shell /usr/bin/false, kein Passwort, versteckt, eigenes Home (Caches: pip, huggingface, lima).
# Idempotent: gibt es das Konto schon, wird nichts verändert. Ausgabe: Name des Kontos.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

SVC="${HH_SVC_USER:-_hydrahive}"
HOME_DIR="${HH_SVC_HOME:-/usr/local/var/hydrahive2/home}"
FIRST="${HH_SVC_UID_FIRST:-450}"
LAST="${HH_SVC_UID_LAST:-499}"

priv() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

if id "$SVC" >/dev/null 2>&1; then
  log "Dienst-Konto $SVC vorhanden (UID $(id -u "$SVC"))"
else
  used="$( { dscl . -list /Users UniqueID; dscl . -list /Groups PrimaryGroupID; } 2>/dev/null | awk '{print $2}')"
  ID=""
  for ((i = FIRST; i <= LAST; i++)); do
    if ! printf '%s\n' "$used" | grep -qx "$i"; then ID="$i"; break; fi
  done
  if [ -z "$ID" ]; then
    echo "Dienst-Konto: keine freie ID zwischen $FIRST und $LAST" >&2
    exit 1
  fi
  log "Lege Dienst-Konto $SVC an (UID/GID $ID, versteckt, ohne Anmeldung)"
  priv dscl . -create "/Groups/$SVC" PrimaryGroupID "$ID"
  priv dscl . -create "/Groups/$SVC" RealName "HydraHive"
  priv dscl . -create "/Groups/$SVC" Password "*"
  priv dscl . -create "/Users/$SVC" UniqueID "$ID"
  priv dscl . -create "/Users/$SVC" PrimaryGroupID "$ID"
  priv dscl . -create "/Users/$SVC" UserShell /usr/bin/false
  priv dscl . -create "/Users/$SVC" NFSHomeDirectory "$HOME_DIR"
  priv dscl . -create "/Users/$SVC" RealName "HydraHive"
  priv dscl . -create "/Users/$SVC" Password "*"
  priv dscl . -create "/Users/$SVC" IsHidden 1
fi

priv mkdir -p "$HOME_DIR"
priv chown "$SVC:$SVC" "$HOME_DIR"
priv chmod 750 "$HOME_DIR"
echo "$SVC"
