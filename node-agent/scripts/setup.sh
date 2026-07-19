#!/bin/sh
# HydraHive Compute-Node — geführte Einrichtung.
#
# Dieses Skript führt dich Schritt für Schritt durch die komplette Einrichtung
# eines neuen Compute-Nodes. Du musst nur ein paar Fragen beantworten und am Ende
# im HydraHive-Cockpit auf "Freigeben" klicken.
#
# Aufruf (als root):   sudo sh scripts/setup.sh
set -eu

# --- kleine Helfer für lesbare Ausgabe --------------------------------------
if [ -t 1 ]; then
    B="$(printf '\033[1m')"; G="$(printf '\033[32m')"; Y="$(printf '\033[33m')"
    R="$(printf '\033[31m')"; C="$(printf '\033[36m')"; N="$(printf '\033[0m')"
else
    B=""; G=""; Y=""; R=""; C=""; N=""
fi
say()  { printf '%s\n' "$*"; }
step() { printf '\n%s==> %s%s\n' "$B" "$*" "$N"; }
ok()   { printf '%s  ✓ %s%s\n' "$G" "$*" "$N"; }
warn() { printf '%s  ! %s%s\n' "$Y" "$*" "$N"; }
die()  { printf '%s  ✗ %s%s\n' "$R" "$*" "$N" >&2; exit 1; }
ask()  { # ask "Frage" VARNAME
    printf '%s%s%s ' "$C" "$1" "$N"
    IFS= read -r _ans || die "Abbruch."
    eval "$2=\$_ans"
}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

say ""
say "${B}HydraHive Compute-Node — Einrichtung${N}"
say "Dauer: ca. 5 Minuten. Du brauchst: die Adresse deines HydraHive-Servers und"
say "einen Kopplungs-Code (Token) aus dem Cockpit. Beides holst du im nächsten Schritt."
say ""

# --- 0. als root? -----------------------------------------------------------
[ "$(id -u)" -eq 0 ] || die "Bitte mit sudo starten:  sudo sh scripts/setup.sh"

confirm() { # confirm "Frage" -> 0 wenn ja
    printf '%s%s [J/n]%s ' "$C" "$1" "$N"
    IFS= read -r _yn || return 1
    case "${_yn:-j}" in j*|J*|y*|Y*|"") return 0 ;; *) return 1 ;; esac
}

# --- 1. Voraussetzungen prüfen und ggf. einrichten -------------------------
step "Schritt 1/5: Voraussetzungen prüfen"

command -v python3 >/dev/null 2>&1 || die "Python 3 fehlt. Installiere es mit:  apt install python3 python3-pip"
ok "Python 3 vorhanden"

# Incus installieren, falls es fehlt
if command -v incus >/dev/null 2>&1; then
    ok "Incus ist installiert"
else
    warn "Incus ist nicht installiert."
    if command -v apt-get >/dev/null 2>&1; then
        if confirm "Soll ich Incus jetzt automatisch installieren?"; then
            say "  Installiere Incus (das kann ein bis zwei Minuten dauern)…"
            apt-get update -qq || die "apt-get update fehlgeschlagen. Internetverbindung prüfen."
            DEBIAN_FRONTEND=noninteractive apt-get install -y -qq incus \
                || die "Incus-Installation fehlgeschlagen. Prüfe: apt-get install incus"
            command -v incus >/dev/null 2>&1 || die "Incus ist nach der Installation nicht auffindbar."
            ok "Incus installiert"
        else
            die "Ohne Incus geht es nicht. Installiere es mit:  apt install incus"
        fi
    else
        die "Kein apt-get gefunden. Bitte Incus manuell installieren, dann erneut starten."
    fi
fi

# Incus initialisieren, falls noch nie geschehen (Gruppe incus-admin fehlt sonst)
if ! getent group incus-admin >/dev/null 2>&1; then
    warn "Incus wurde noch nie initialisiert."
    if confirm "Soll ich Incus jetzt mit Standardeinstellungen initialisieren?"; then
        say "  Initialisiere Incus (Standard-Storage, keine LAN-Änderung)…"
        incus admin init --auto \
            || die "incus admin init fehlgeschlagen. Manuell versuchen:  incus admin init"
        getent group incus-admin >/dev/null 2>&1 \
            || die "Gruppe incus-admin fehlt weiterhin. Bitte 'incus admin init' manuell ausführen."
        ok "Incus initialisiert"
    else
        die "Incus muss initialisiert werden. Führe aus:  incus admin init"
    fi
else
    ok "Incus ist einsatzbereit"
fi

# Bridge br0 sicherstellen (der Agent hängt Container/VMs an 'br0')
if incus network show br0 >/dev/null 2>&1; then
    ok "Netzwerk-Bridge 'br0' vorhanden"
else
    warn "Die vom Agent benötigte Bridge 'br0' fehlt."
    say "  Ich lege eine von Incus verwaltete Bridge 'br0' mit eigenem Subnetz an."
    say "  ${Y}Das verändert deine SSH-Verbindung NICHT${N} — die Bridge nutzt NAT."
    say "  (Für echtes LAN-Bridging, damit Container IPs aus deinem Heimnetz bekommen,"
    say "   siehe README — das ist ein bewusster manueller Schritt.)"
    if confirm "Soll ich die Bridge 'br0' (NAT) jetzt anlegen?"; then
        incus network create br0 \
            || die "Konnte Bridge 'br0' nicht anlegen. Prüfe:  incus network create br0"
        ok "Bridge 'br0' angelegt (NAT-Modus)"
    else
        die "Ohne Bridge 'br0' können keine Workloads starten. Lege sie an mit:  incus network create br0"
    fi
fi

# KVM (optional, nur für VMs)
if [ -e /dev/kvm ]; then
    ok "KVM vorhanden — dieser Node kann auch virtuelle Maschinen betreiben"
else
    warn "Kein /dev/kvm — dieser Node kann nur Container betreiben, keine VMs. (Das ist ok.)"
fi

# --- 2. Agent installieren --------------------------------------------------
step "Schritt 2/5: Node-Agent installieren"
sh "$SCRIPT_DIR/scripts/install.sh" >/dev/null 2>&1 || sh "$SCRIPT_DIR/scripts/install.sh"
command -v hydrahive-node >/dev/null 2>&1 || die "Installation fehlgeschlagen — 'hydrahive-node' nicht gefunden."
ok "Agent installiert"

# --- 3. Angaben abfragen ----------------------------------------------------
step "Schritt 3/5: Deine Angaben"
say "Öffne jetzt im Browser dein HydraHive-Cockpit und gehe zu:"
say "   ${B}Admin  →  Compute-Nodes  →  \"Node koppeln\"${N}"
say "Vergib dort einen Namen, klicke auf Token erzeugen und kopiere den Code."
say ""

DEFAULT_NAME="$(hostname 2>/dev/null || echo compute-01)"
ask "Adresse deines HydraHive-Servers (z.B. https://hydrahive.example.com):" SERVER
[ -n "${SERVER:-}" ] || die "Keine Server-Adresse eingegeben."
case "$SERVER" in
    https://*) : ;;
    http://*)  die "Bitte eine https://-Adresse verwenden (verschlüsselt), nicht http://." ;;
    *)         SERVER="https://$SERVER"; warn "https:// ergänzt → $SERVER" ;;
esac

ask "Name für diesen Node [${DEFAULT_NAME}] (muss exakt dem Namen im Cockpit entsprechen):" NODE_NAME
[ -n "${NODE_NAME:-}" ] || NODE_NAME="$DEFAULT_NAME"

say ""
say "Füge jetzt den ${B}Kopplungs-Code (Token)${N} aus dem Cockpit ein."
ask "Token:" TOKEN
[ -n "${TOKEN:-}" ] || die "Kein Token eingegeben."

# --- 4. Kopplung durchführen ------------------------------------------------
step "Schritt 4/5: Node koppeln"
TOKEN_FILE="$(mktemp)"
chmod 600 "$TOKEN_FILE"
printf '%s' "$TOKEN" > "$TOKEN_FILE"
chown hydrahive-node "$TOKEN_FILE" 2>/dev/null || true

set +e
OUT="$(sudo -u hydrahive-node hydrahive-node enroll \
        --server "$SERVER" --name "$NODE_NAME" --token-file "$TOKEN_FILE" 2>&1)"
RC=$?
set -e
rm -f "$TOKEN_FILE"

if [ "$RC" -ne 0 ]; then
    say "$OUT"
    die "Kopplung fehlgeschlagen. Häufige Ursachen:
       • Server-Adresse falsch oder nicht erreichbar
       • Token abgelaufen oder schon benutzt → im Cockpit einen neuen erzeugen
       • Name stimmt nicht mit dem Cockpit überein"
fi

FINGERPRINT="$(printf '%s\n' "$OUT" | sed -n 's/^Certificate fingerprint: //p')"
ok "Node erfolgreich angemeldet"

# --- 5. Freigabe + Start ----------------------------------------------------
step "Schritt 5/5: Im Cockpit freigeben und starten"
say ""
say "${B}Wichtig — jetzt im Cockpit bestätigen:${N}"
say "Der Node steht dort auf ${Y}\"Wartet\"${N}. Klicke auf ${B}\"Freigeben\"${N} und"
say "vergleiche diesen Sicherheits-Code Zeichen für Zeichen:"
say ""
say "   ${G}${B}${FINGERPRINT:-<siehe Ausgabe oben>}${N}"
say ""
ask "Hast du im Cockpit freigegeben? Dann Enter drücken zum Starten…" _

systemctl enable --now hydrahive-node.service
sleep 2
if systemctl is-active --quiet hydrahive-node.service; then
    ok "Node-Agent läuft"
else
    warn "Agent läuft noch nicht sauber. Log ansehen mit:  journalctl -u hydrahive-node -e"
fi

say ""
say "${G}${B}Fertig!${N} Dein Node erscheint im Cockpit gleich als ${G}\"Online\"${N}."
say "Ab jetzt kannst du beim Anlegen von Containern und VMs diesen Node auswählen."
say ""
say "Status jederzeit prüfen:  ${C}systemctl status hydrahive-node${N}"
say "Live-Log ansehen:         ${C}journalctl -u hydrahive-node -f${N}"
say ""
