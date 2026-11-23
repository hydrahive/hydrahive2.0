"""Sofortschutz: Projekt-Agenten und Spezialisten laden und installieren nichts.

Vorfall 22.11.2026 (Auftrag b4b1f5ee): Ein Projekt-Agent lud ungefragt PowerShell (538 MB) per curl nach /tmp,
entpackte und startete es. Ziel hydrahive2-modules/ziele/agenten-sofortschutz.md, Regeln 1–4.

Überbrückung bis zum eigenen Linux-Benutzer je Projekt (ziele/agenten-projekt-isolation.md). Wie _shell_guard ist
das eine Wortliste: Wer verschleiert (eval, base64, python -c urllib …), kommt durch. Sie trifft den Normalfall.
Wird von _shell_guard._segment_reason für jedes Befehlsstück aufgerufen (nach Wrappern wie env/timeout).
"""
from __future__ import annotations

import os
import re

_FETCHERS = frozenset({"curl", "wget"})
_ALWAYS_SAVE = frozenset({"aria2c", "axel"})
_INTERPRETERS = frozenset({"sh", "bash", "zsh", "dash", "python", "python3", "perl", "ruby", "node"})
_SYSTEM_PKG = frozenset({"apt", "apt-get", "aptitude", "dpkg", "snap", "flatpak", "brew", "yum", "dnf", "zypper"})
_ALWAYS_GLOBAL = frozenset({"pipx", "gem", "cargo", "go"})          # nur mit „install“
_CURL_SAVE = re.compile(r"^-[A-Za-z]*[oO][A-Za-z]*$")                # -o, -O, -sLO, -fsSLo …
_CURL_SAVE_LONG = frozenset({"--output", "--remote-name", "--remote-name-all", "--output-dir"})
_FOREIGN_DIRS = ("/tmp/", "/var/tmp/", "/dev/shm/", "~/", "$HOME/", "${HOME}/")
_PROC_SUB = re.compile(r"<\(\s*(?:curl|wget)\b")

MSG = ("Herunterladen oder Installieren von Programmen (`{what}`) ist für Projekt-Agenten und Spezialisten "
       "gesperrt (Vorfall 22.11.2026)")


def _base(token: str) -> str:
    return os.path.basename(token.strip("'\""))


def _curl_saves(rest: list[str]) -> bool:
    return any(_CURL_SAVE.match(a) or a.split("=", 1)[0] in _CURL_SAVE_LONG for a in rest)


def _wget_saves(rest: list[str]) -> bool:
    if "--spider" in rest:
        return False
    for i, a in enumerate(rest):
        if a in ("-O", "--output-document") and i + 1 < len(rest):
            return rest[i + 1] != "-"
        if a.startswith("--output-document="):
            return a.split("=", 1)[1] != "-"
        if a.startswith("-") and not a.startswith("--") and "O" in a:
            tail = a[a.index("O") + 1:]
            if tail:                                                  # -qO-  oder  -qOdatei
                return tail != "-"
            return not (i + 1 < len(rest) and rest[i + 1] == "-")     # -qO -  oder  -qO datei
    return True                                                      # wget ohne -O speichert immer


def _pip_install(cmd: str, rest: list[str]) -> bool:
    args = rest[2:] if cmd.startswith("python") and rest[:2] == ["-m", "pip"] else rest
    return bool(args) and args[0] == "install"


def segment_reason(cmd_token: str, rest: list[str]) -> str | None:
    """Sperrgrund für EIN Befehlsstück (Befehl + Argumente, Wrapper schon entfernt) oder None."""
    cmd = _base(cmd_token)
    if cmd in _ALWAYS_SAVE:
        return MSG.format(what=cmd)
    if cmd == "curl" and _curl_saves(rest):
        return MSG.format(what="curl -o")
    if cmd == "wget" and _wget_saves(rest):
        return MSG.format(what="wget")
    if cmd in _SYSTEM_PKG and any(a in ("install", "-i", "--install", "add", "reinstall") for a in rest[:3]):
        return MSG.format(what=f"{cmd} install")
    if cmd in ("pip", "pip3") or (cmd.startswith("python") and rest[:2] == ["-m", "pip"]):
        # Erlaubt nur, wenn das pip/python selbst aus einer venv im Arbeitsordner kommt (.venv/bin/pip …).
        venv = cmd_token.startswith((".venv/", "venv/", "./.venv/", "./venv/")) or "/.venv/bin/" in cmd_token
        if not venv and _pip_install(cmd, rest):
            return MSG.format(what="pip install")
    if cmd in _ALWAYS_GLOBAL and rest[:1] == ["install"]:
        return MSG.format(what=f"{cmd} install")
    if cmd in ("npm", "pnpm") and any(a in ("-g", "--global", "--location=global") for a in rest):
        return MSG.format(what=f"{cmd} -g")
    if cmd == "yarn" and rest[:1] == ["global"]:
        return MSG.format(what="yarn global")
    if cmd_token.startswith(_FOREIGN_DIRS):
        return MSG.format(what=cmd_token)
    if cmd == "chmod" and any(a.startswith(_FOREIGN_DIRS) for a in rest if not a.startswith("-")):
        return MSG.format(what="chmod +x außerhalb des Arbeitsordners")
    return None


def pipeline_reason(commands: list[list[str]]) -> str | None:
    """Ketten wie `curl … | sh` oder `curl … | tee datei`. `commands`: Befehlswörter der Stücke in Reihenfolge
    (Wrapper entfernt). split_top_level trennt ; & | gleich – ein Interpreter NACH einem curl/wget gilt daher
    als verdächtig, auch über `;` hinweg (lieber eine Ablehnung zu viel)."""
    fetched = False
    for ws in commands:
        if not ws:
            continue
        cmd = _base(ws[0])
        if cmd in _FETCHERS:
            fetched = True
            continue
        if fetched and (cmd in _INTERPRETERS or cmd in ("sudo", "tee")):
            if cmd in _INTERPRETERS and len(ws) > 1 and not ws[1].startswith("-"):
                continue                                             # `python3 script.py` liest kein stdin
            return MSG.format(what=f"… | {cmd}")
    return None


def text_reason(text: str) -> str | None:
    """Prozess-Ersetzung `bash <(curl …)` / Umleitung `curl … > datei`. `text` muss quote-maskiert sein
    (_shell_lex.mask_quotes), sonst schlägt `echo 'curl … > x'` falsch an."""
    if _PROC_SUB.search(text):
        return MSG.format(what="<(curl …)")
    for m in re.finditer(r"\b(curl|wget)\b[^|;&\n]*?(?<![0-9&])>>?\s*(?!&)(\S+)", text):
        if m.group(2) not in ("/dev/null", "/dev/stderr", "/dev/stdout"):
            return MSG.format(what=f"{m.group(1)} > Datei")
    return None
