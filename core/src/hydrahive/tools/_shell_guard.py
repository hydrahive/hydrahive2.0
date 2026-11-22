"""Harte Sperre für shell_exec von Projekt-Agenten und Spezialisten.

Vorfall 20.11.2026 (Auftrag 5257951b): Ein Spezialist sollte „Live-Daten lesen“,
nahm die global hinterlegten SSH-Zugänge, ging per `ssh` auf Tills Workstation,
nutzte dort passwortloses `sudo` und las HH_SECRET_KEY, HH_COMPUTE_PROXY_SECRET
und das Mirror-Passwort. Till: „der Zugriff auf externe Rechner muss weg für
Projekt und Spezialisten“. docs/specs/agent-guardrails.md

Anders als der Harakiri-Schutz (_protected_paths: Bestätigungs-Popup) ist das
eine ABLEHNUNG ohne Rückfrage: ein Spezialist hat keinen Menschen vor sich, der
ein Popup beantworten könnte.

Gesperrt für Agent-Typ `project` und `specialist` (Master/Buddy bleibt frei):
1. Fremde Rechner: ssh, scp, sftp, sshpass, autossh, slogin, mosh, telnet, rsh;
   nc/ncat/socat mit Ziel; rsync/rclone mit `host:`-Ziel. Git über SSH-URL bleibt
   erlaubt (Transport, kein Shell-Zugang).
2. Rechte-Ausweitung: sudo, doas, su, pkexec, runuser, nsenter, chroot, setpriv;
   docker/podman/incus/lxc exec|run|shell|attach|console.
3. Geheimnisse: /etc/hydrahive2, .ssh, /var/lib/hydrahive2/{.ssh*,credentials},
   /proc/*/environ, /etc/shadow|sudoers, pg_mirror.dsn, users.json, .netrc/.pgpass,
   *.pem/*.key.

Kein vollständiger Shell-Parser: wer per eval/base64 verschleiert, kommt durch.
Die Sperre trifft den Normalfall (genau den vom 20.11.); die Werkzeugbeschreibung
bewirbt SSH nicht mehr. Die echte Mauer wäre ein eigener Unix-User ohne sudo.
"""
from __future__ import annotations

import os
import re

from hydrahive.tools._shell_heredoc import strip_heredocs
from hydrahive.tools._shell_lex import split_top_level, words

GUARDED_TYPES = frozenset({"project", "specialist"})

_REMOTE = frozenset({"ssh", "scp", "sftp", "sshpass", "autossh", "slogin", "mosh", "telnet", "rlogin", "rsh"})
_NET_TOOLS = frozenset({"nc", "ncat", "netcat", "socat"})
_COPY_REMOTE = frozenset({"rsync", "rclone"})
_ESCALATE = frozenset({"sudo", "doas", "su", "pkexec", "runuser", "nsenter", "chroot", "setpriv"})
_CONTAINER = frozenset({"docker", "podman", "incus", "lxc", "nerdctl"})
_CONTAINER_SUBCMDS = frozenset({"exec", "run", "shell", "attach", "console"})
_WRAPPERS = frozenset({"env", "nice", "nohup", "time", "timeout", "command", "exec", "xargs", "stdbuf", "ionice"})
_SHELLS = frozenset({"bash", "sh", "zsh", "dash"})

_REMOTE_SPEC = re.compile(r"^(?:[\w.\-]+@)?[\w.\-]+:(?!//)")
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

_SECRET_PATTERNS = tuple(re.compile(p) for p in (
    r"/etc/hydrahive2(?:/|\b)",
    r"(?:^|[\s/~'\"=])\.ssh(?:/|\b)",
    r"/var/lib/hydrahive2/\.ssh",
    r"/var/lib/hydrahive2/credentials",
    r"/proc/(?:\d+|self|\$\S*?)/environ",
    r"/etc/(?:shadow|gshadow|sudoers)",
    r"\bpg_mirror\.dsn\b",
    r"(?:^|[\s/'\"])users\.json\b",
    r"(?:^|[\s/'\"])\.(?:netrc|pgpass)\b",
    r"\S\.(?:pem|key|p12|pfx)\b",
))

BLOCK_MARKER = "Abgelehnt ohne Ausführung (Sicherheitsregel"   # agent_tree erkennt Sperren daran
_MSG_TAIL = (". Abgelehnt ohne Ausführung (Sicherheitsregel nach Vorfall 20.11.2026). Brauchst du Daten von "
             "einem anderen Rechner, Rechte oder ein Geheimnis: stoppe und melde das als Blocker an deinen "
             "Auftraggeber, statt einen anderen Weg zu suchen.")


def _base(token: str) -> str:
    return os.path.basename(token.strip("'\""))


def _command_words(seg: str) -> list[str]:
    """Wörter ab dem eigentlichen Befehl (VAR=wert und Wrapper wie env/timeout übersprungen)."""
    ws = words(seg)
    i = 0
    while i < len(ws):
        if _ASSIGN.match(ws[i]):
            i += 1
            continue
        if _base(ws[i]) in _WRAPPERS:
            i += 1
            while i < len(ws) and (ws[i].startswith("-") or ws[i][:1].isdigit() or _ASSIGN.match(ws[i])):
                i += 1
            continue
        break
    return ws[i:]


def _segment_reason(seg: str) -> str | None:
    ws = _command_words(seg)
    if not ws:
        return None
    cmd, rest = _base(ws[0]), ws[1:]
    if cmd in _REMOTE:
        return f"Zugriff auf fremde Rechner (`{cmd}`) ist für Projekt-Agenten und Spezialisten gesperrt"
    if cmd in _NET_TOOLS and any(not a.startswith("-") for a in rest):
        return f"Netzwerk-Verbindung mit `{cmd}` ist für Projekt-Agenten und Spezialisten gesperrt"
    if cmd in _COPY_REMOTE and any(_REMOTE_SPEC.match(a.strip("'\"")) for a in rest if not a.startswith("-")):
        return f"Kopieren von/zu fremden Rechnern (`{cmd} host:…`) ist für Projekt-Agenten und Spezialisten gesperrt"
    if cmd in _ESCALATE:
        return f"Rechte-Ausweitung (`{cmd}`) ist für Projekt-Agenten und Spezialisten gesperrt"
    if cmd in _CONTAINER:
        sub = next((a for a in rest[:3] if a in _CONTAINER_SUBCMDS), None)
        if sub:
            return f"Befehle in Containern (`{cmd} {sub}`) sind für Projekt-Agenten und Spezialisten gesperrt"
    if cmd in _SHELLS:
        for i, a in enumerate(rest):
            if a == "-c" and i + 1 < len(rest):
                return check_text(rest[i + 1].strip("'\""))
    return None


def check_text(cmd: str) -> str | None:
    """Sperrgrund (ohne Agenten-Prüfung) oder None."""
    raw = cmd or ""
    text = strip_heredocs(raw)
    # split_top_level trennt schon an ; & | und Zeilenumbruch, aber nur AUSSERHALB von Anführungszeichen.
    # Bis 22.11.2026 wurde jedes Stück zusätzlich stumpf an "|" geteilt: Ein Suchmuster wie
    # grep -E 'x|ssh' wurde dadurch zum Befehl „ssh'“ (Fehlalarm beim Notizbuch-Auftrag).
    for seg in split_top_level(text):
        reason = _segment_reason(seg)
        if reason:
            return reason
    for a, b in re.findall(r"\$\(([^()]*)\)|`([^`]*)`", text):
        reason = check_text(a or b)
        if reason:
            return reason
    for pat in _SECRET_PATTERNS:
        m = pat.search(raw)
        if m:
            return f"Zugriff auf Geheimnis-Dateien (`{m.group(0).strip()}`) ist für Projekt-Agenten und Spezialisten gesperrt"
    return None


def agent_type(agent_id: str) -> str | None:
    try:
        from hydrahive.agents import config as agent_config
        return (agent_config.get(agent_id) or {}).get("type")
    except Exception:
        return None


def blocked_reason(cmd: str, agent_id: str) -> str | None:
    """Sperrgrund für diesen Agenten, sonst None. Unbekannter Agent-Typ → gesperrt behandeln (fail-closed)."""
    kind = agent_type(agent_id)
    if kind is not None and kind not in GUARDED_TYPES:
        return None
    reason = check_text(cmd)
    return f"{reason}{_MSG_TAIL}" if reason else None
