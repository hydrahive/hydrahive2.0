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


# --- SSH / Remote-Transport ---------------------------------------------------
# Das Gate schützt das LOKALE System. Ein `ssh host '<script>'` führt <script>
# auf einer Gegenstelle aus — dortige System-Pfade gehen den Lokal-Schutz nichts
# an. Deshalb: (a) gequotete Strings sind beim Top-Level-Splitten opak (der
# Remote-Body wird nicht an seinen `&&`/`;` zersägt), (b) Redirections in Quotes
# zählen nicht, (c) das `ssh -i <key>` ist Transport-Auth, kein Geheimnis-Lesen.
# Befehle, bei denen `-i <pfad>` das Identity-File ist (Transport-Auth).
# Bewusst OHNE rsync: dort ist `-i` = --itemize-changes, kein Key-Argument.
_SSH_FAMILY = frozenset({"ssh", "scp", "sftp", "slogin", "sshpass", "autossh"})


def _split_top_level(cmd: str) -> list[str]:
    """Splittet an `;`, `&`, `|`, Newline — aber nur AUSSERHALB von Quotes.

    Ersetzt das quote-blinde `re.split`: `ssh host 'a && b'` bleibt ein Segment,
    statt in lokal aussehende `a`/`b` zu zerfallen.
    """
    segs: list[str] = []
    buf: list[str] = []
    q: str | None = None
    i, n = 0, len(cmd)
    while i < n:
        c = cmd[i]
        if q is not None:
            buf.append(c)
            if c == "\\" and q == '"' and i + 1 < n:
                buf.append(cmd[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in ("'", '"'):
            q = c
            buf.append(c)
        elif c == "\\" and i + 1 < n:
            buf.append(c)
            buf.append(cmd[i + 1])
            i += 2
            continue
        elif c in ";&|\n":
            segs.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        segs.append("".join(buf))
    return segs


def _mask_quotes(s: str) -> str:
    """Ersetzt gequotete Inhalte durch Leerzeichen (Quote-Zeichen bleiben).

    So matcht der Redirect-Scan nur Redirections ausserhalb von Quotes —
    `echo x > /etc/y` innerhalb von `ssh host '...'` ist ein Remote-Redirect.
    """
    out: list[str] = []
    q: str | None = None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if q is not None:
            if c == "\\" and q == '"' and i + 1 < n:
                out.append("  ")
                i += 2
                continue
            if c == q:
                q = None
                out.append(c)
            else:
                out.append(" ")
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(c)
            out.append(s[i + 1])
            i += 2
            continue
        if c in ("'", '"'):
            q = c
        out.append(c)
        i += 1
    return "".join(out)


def _has_ssh_token(tokens: Sequence[str]) -> bool:
    return any(os.path.basename(t.strip("'\"")) in _SSH_FAMILY for t in tokens)

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
    # Redirections (`> /opt/x`, `2>>/etc/y`) — unabhängig vom Befehl. Es zählt
    # nur ein Redirect-OPERATOR ausserhalb von Quotes (sonst ist es ein Remote-
    # Redirect, `ssh h 'echo>/etc/y'`). Das ZIEL darf gequotet sein (`> '/etc/x'`)
    # — deshalb am Original matchen und nur die Operator-Position gegen die
    # Maske prüfen (gleiche Länge, also positionsgleich).
    masked = _mask_quotes(seg)
    for m in _REDIRECT.finditer(seg):
        if masked[m.start()] != seg[m.start()]:
            continue
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
    for seg in _split_top_level(cmd):
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
    if bn in _SECRET_BASENAMES or low.endswith(_CRED_SUFFIX):
        return tok
    if any(low.endswith(s) for s in _SECRET_SUFFIXES):
        return tok
    # Absolutes .env (/opt/app/.env) ist sensibel; relatives Workspace-.env nicht.
    if tok.startswith("/") and (bn == ".env" or bn.startswith(".env.")):
        return tok
    return None


def wants_sensitive_read(cmd: str) -> str | None:
    """Gibt den getroffenen Pfad zurück wenn `cmd` ein Geheimnis (Key, Shadow,
    Credentials, .ssh, ...) berührt — read wie write. Sonst None.

    Pro Segment ausgewertet: in einem ssh-Segment ist der Wert nach `-i`/`-o`
    ein Identity-File / eine ssh-Option (Transport-Auth) und kein Geheimnis-Lesen.
    Ohne ssh im Segment (z.B. `cp -i key /tmp`) bleibt der Treffer bestehen.
    """
    if not cmd or not cmd.strip():
        return None
    for seg in _split_top_level(cmd):
        tokens = seg.split()
        ssh_ctx = _has_ssh_token(tokens)
        prev = ""
        for tok in tokens:
            # ssh `-i <key>` = Identity-File; `-o Key=Value` (z.B. IdentityFile=)
            # = ssh-Option. Beides ist Transport-Auth, kein Geheimnis-Lesen. Ein
            # nackter Pfad nach `-o` (kein `=`) ist KEINE ssh-Option → nicht exempt.
            exempt = ssh_ctx and (prev == "-i" or (prev == "-o" and "=" in tok))
            prev = tok
            if exempt:
                continue
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
