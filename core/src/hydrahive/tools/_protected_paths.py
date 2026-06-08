"""Erkennt Schreib-Absicht von Shell-Befehlen auf geschützte System-Pfade.

Schicht A des Harakiri-Schutzes: ein deterministischer Speed-Bump. Wenn ein
shell_exec-Befehl plausibel in einen System-Pfad (/opt, /etc, ...) schreibt,
hängt der Runner ihn an das bestehende Bestätigungs-Popup. Lesen wird bewusst
NICHT geflaggt.

Bewusst kein Shell-Parser: das ist ein Stolperdraht gegen Unfälle
(`rm -rf /opt`), kein bypass-fester Wall. Die echte Mauer ist Schicht B
(OS-Ebene, read-only Mount im Launcher). Wer schreiben *will*, kommt per
`eval`/base64/Variablen daran vorbei — das ist hier akzeptiert und dokumentiert.
"""
from __future__ import annotations

import os
import re
from collections.abc import Sequence

# System-Wurzeln, die praktisch nie der Arbeitsbereich eines Agenten sind.
# /tmp, /home, /var, der Workspace und Projekt-Repos sind bewusst NICHT dabei —
# dort schreiben Agenten legitim, ein Popup würde nur nerven.
_SYSTEM_PREFIXES = (
    "/opt", "/etc", "/usr", "/bin", "/sbin",
    "/boot", "/lib", "/lib64", "/root", "/sys", "/proc", "/dev",
)

# Befehle, deren WIRKUNG der Zielpfad ist (alle Pfad-Argumente sind Schreibziele).
_DESTRUCTIVE = {
    "rm", "rmdir", "shred", "unlink", "truncate", "chmod", "chown",
    "chgrp", "mkdir", "touch", "mount", "mkfs",
}
# Befehle, bei denen das LETZTE Pfad-Argument das Ziel ist (Quelle wird nur gelesen).
_DEST_LAST = {"cp", "mv", "install", "rsync", "ln"}
# Wrapper, die wir überspringen, um an den echten Befehl zu kommen.
_WRAPPERS = {"sudo", "env", "nice", "nohup", "time", "doas"}

_REDIRECT = re.compile(r">>?\s*([^\s;|&>]+)")

# Pseudo-Geräte unter /dev sind normale Redirect-Ziele (2>/dev/null ist DAS
# häufigste Shell-Idiom) — kein Harakiri. Echte Block-Devices (/dev/sda) bleiben
# geschützt. Ohne diese Ausnahme würde der Schutz bei fast jedem Befehl nerven.
_SAFE_DEV = frozenset({
    "/dev/null", "/dev/zero", "/dev/full", "/dev/random", "/dev/urandom",
    "/dev/stdin", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/ptmx",
})


def _is_safe_dev(path: str) -> bool:
    return path in _SAFE_DEV or path.startswith("/dev/fd/")

# --- Geheimnisse (Vertraulichkeit, schmal) ---
# Hier ist JEDER Zugriff selten und relevant — read wie write → Popup.
_SECRET_FILES = ("/etc/shadow", "/etc/gshadow", "/etc/sudoers")
_SECRET_DIRS = ("/etc/ssl/private", "/etc/sudoers.d")
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".jks")
_SECRET_BASENAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".netrc", ".pgpass", ".htpasswd"}
_CRED_SUFFIX = ".credentials.json"
_SSH_MARKER = "/.ssh/"


def default_protected() -> tuple[str, ...]:
    """System-Prefixe + HH-Install-Dir (ENV direkt gelesen, kein cached settings)."""
    base = os.environ.get("HH_BASE_DIR", "/opt/hydrahive2").rstrip("/")
    if base and not any(base == p or base.startswith(p + "/") for p in _SYSTEM_PREFIXES):
        return (*_SYSTEM_PREFIXES, base)
    return _SYSTEM_PREFIXES


def _hit(token: str, protected: Sequence[str]) -> str | None:
    path = token.strip("'\"")
    for pre in protected:
        if path == pre or path.startswith(pre + "/"):
            if pre == "/dev" and _is_safe_dev(path):
                return None
            return pre
    return None


def _is_root_target(token: str) -> bool:
    return token.strip("'\"") in ("/", "/*")


def _segment_target(seg: str, protected: Sequence[str]) -> str | None:
    # Redirections (`> /opt/x`, `2>>/etc/y`) — unabhängig vom Befehl.
    for m in _REDIRECT.finditer(seg):
        if (h := _hit(m.group(1), protected)):
            return h

    tokens = seg.split()
    while tokens and tokens[0] in _WRAPPERS:
        tokens = tokens[1:]
    if not tokens:
        return None

    cmd = os.path.basename(tokens[0])
    args = tokens[1:]
    path_args = [a for a in args if a.startswith("/") or a.strip("'\"").startswith("/")]

    if cmd in _DESTRUCTIVE or cmd == "tee":
        for a in args:
            if _is_root_target(a) and cmd in _DESTRUCTIVE:
                return "/"
            if (h := _hit(a, protected)):
                return h

    if cmd == "dd":
        for a in args:
            if a.startswith("of=") and (h := _hit(a[3:], protected)):
                return h

    if cmd == "sed" and any(a.startswith("-i") for a in args):
        for a in path_args:
            if (h := _hit(a, protected)):
                return h

    if cmd in _DEST_LAST and path_args:
        if (h := _hit(path_args[-1], protected)):
            return h

    return None


def wants_protected_write(cmd: str, protected: Sequence[str] | None = None) -> str | None:
    """Gibt den getroffenen Prefix zurück wenn `cmd` in einen geschützten Pfad
    schreibt, sonst None. `protected` default = default_protected()."""
    if not cmd or not cmd.strip():
        return None
    prefixes = protected if protected is not None else default_protected()
    for seg in re.split(r"[;&|\n]+", cmd):
        if (h := _segment_target(seg, prefixes)):
            return h
    return None


def _sensitive_token(tok: str) -> str | None:
    tok = tok.strip("'\"")
    if not tok or tok.startswith("-"):
        return None
    if any(tok == f or tok.startswith(f) for f in _SECRET_FILES):
        return tok
    if any(tok.startswith(d + "/") or tok == d for d in _SECRET_DIRS):
        return tok
    if _SSH_MARKER in tok or tok.endswith("/.ssh"):
        # Nur Home-Verzeichnisse sind sensitiv (/home/…/.ssh, /root/.ssh).
        # Workspace-SSH-Configs ($WORKSPACE/.ssh/config, /var/lib/…/.ssh/) sind
        # normale Agenten-Operation — kein Popup.
        if any(p in tok for p in ("/home/", "/root/")):
            return tok
    bn = os.path.basename(tok)
    low = bn.lower()
    if bn in _SECRET_BASENAMES:
        # Service-Account-Keys (absolute Pfade außerhalb /home/ und /root/) und
        # Shell-Variablen-Referenzen ($KEYDIR/id_ed25519) sind legitime
        # Agenten-Operationen — kein Popup. User-Home-Pfade und relative Namen bleiben geblockt.
        is_service_path = (
            tok.startswith("/") and not any(p in tok for p in ("/home/", "/root/"))
        ) or tok.startswith("$")
        if not is_service_path:
            return tok
    if low.endswith(_CRED_SUFFIX):
        return tok
    if any(low.endswith(s) for s in _SECRET_SUFFIXES):
        return tok
    # Absolutes .env (/opt/app/.env) ist sensibel; relatives Workspace-.env nicht.
    if tok.startswith("/") and (bn == ".env" or bn.startswith(".env.")):
        return tok
    return None


def wants_sensitive_read(cmd: str) -> str | None:
    """Gibt den getroffenen Pfad zurück wenn `cmd` ein Geheimnis (Key, Shadow,
    Credentials, .ssh, ...) berührt — read wie write. Sonst None."""
    if not cmd or not cmd.strip():
        return None
    for tok in cmd.replace("|", " ").replace(";", " ").replace("&", " ").split():
        if (h := _sensitive_token(tok)):
            return h
    return None


def shell_confirm_reason(cmd: str) -> str | None:
    """Kombiniert beide Gates → fertige Popup-Begründung oder None.

    Schreib-Gate (Integrität) hat Vorrang, dann Geheimnis-Gate (Vertraulichkeit).
    """
    if (w := wants_protected_write(cmd)):
        return f"Schreibzugriff auf geschützten Pfad: {w}"
    if (s := wants_sensitive_read(cmd)):
        return f"Zugriff auf Geheimnis: {s}"
    return None
