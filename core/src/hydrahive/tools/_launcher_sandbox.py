"""Agenten-Befehle in einer bubblewrap-Sandbox (Ziel hydrahive2-modules/ziele/agenten-projekt-isolation.md, B2a).

Projekt-Agenten und Spezialisten sehen in der Sandbox:
- ihren Projekt-Workspace beschreibbar (und nur ihn),
- verknüpfte Projekte (``linked_projects``) nur lesend,
- das System (/usr, /bin, /lib*, /etc, /opt …) nur lesend,
- ein leeres, eigenes /tmp und ein eigenes HOME im Workspace (``.home/``),
- nur ihre eigenen Prozesse.

Nicht sichtbar (leere tmpfs darüber): /etc/hydrahive2 (Zugangsdaten, Schlüssel, Mirror), /var/lib/hydrahive2
(Datenbanken, credentials, .ssh, alle anderen Workspaces), /home (Dienst-HOME mit .gitconfig/.ssh), /root, /srv,
/run/user, /proc/*/environ anderer Prozesse (eigener PID-Namespace).

Netz bleibt in dieser Etappe offen (git/gh/npm ci brauchen es); Heimnetz-Sperre ist Etappe B4. Bis dahin gilt dort
weiter die Wortliste aus _shell_guard (ssh/scp/nc …).

Warum bwrap statt eigener Benutzer: bubblewrap + AppArmor-Profil `hydrahive-bwrap-userns` richten Installer
(modules/00-deps.sh) und update.sh auf jeder Installation ein (PDF-Leser nutzt es schon), es braucht kein root und
keinen Benutzer anlegen. „Alles zu, was nicht ausdrücklich eingeblendet ist“ statt „alles offen, was nicht verboten“.

Fehlt bwrap oder schlägt die Sandbox fehl, wird NICHT ungeschützt ausgeführt (fail-closed), sondern eine klare
Meldung zurückgegeben.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from hydrahive.tools._launcher import DevLauncher, LaunchResult

_BWRAP = "/usr/bin/bwrap"
#: Werden leer überdeckt – auch wenn ein Teil davon über einen erlaubten Pfad erreichbar wäre.
_HIDDEN = ("/etc/hydrahive2", "/var/lib/hydrahive2", "/home", "/root", "/srv", "/run/user", "/var/backups",
           "/var/log", "/mnt", "/media")
#: Umgebung in der Sandbox: nur diese Schlüssel aus dem vorbereiteten env (shell._build_env) + feste Werte.
_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "TERM", "TZ", "GH_TOKEN", "GITHUB_TOKEN", "GITEA_TOKEN", "PYTHONPATH",
             "NODE_OPTIONS", "CI")
UNAVAILABLE = ("Sandbox nicht verfügbar (bubblewrap fehlt oder startet nicht). Der Befehl wurde aus Sicherheitsgründen "
               "nicht ausgeführt. Melde das als Blocker; ein Admin prüft das Update von HydraHive.")


def available() -> bool:
    return os.access(_BWRAP, os.X_OK)


def sandbox_args(workspace: Path, cwd: Path, *, read_only: list[Path] | None = None) -> list[str]:
    """bwrap-Argumente (ohne den Befehl). Reine Funktion – testbar ohne bwrap.

    Reihenfolge zählt: erst alles lesend, dann Verstecktes leer überdecken, dann Workspace (rw) und verknüpfte
    Projekte (ro) wieder einblenden – sie liegen unter /var/lib/hydrahive2 und wären sonst mit versteckt."""
    ws = workspace.resolve()
    args = [_BWRAP, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
            "--hostname", "hh-sandbox", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
            "--tmpfs", "/tmp", "--tmpfs", "/var/tmp", "--tmpfs", "/dev/shm"]
    for hidden in _HIDDEN:
        if os.path.isdir(hidden):
            args += ["--tmpfs", hidden]
    for extra in read_only or []:
        p = extra.resolve()
        if p.is_dir() and p != ws:
            args += ["--ro-bind", str(p), str(p)]
    home = ws / ".home"
    args += ["--bind", str(ws), str(ws), "--setenv", "HOME", str(home), "--setenv", "TMPDIR", "/tmp",
             "--chdir", str(cwd.resolve())]
    return args


def sandbox_env(env: dict | None) -> dict:
    """Nur erlaubte Variablen – keine HH_*/Dienst-Umgebung in die Sandbox."""
    src = env if env is not None else dict(os.environ)
    out = {k: v for k, v in src.items() if k in _ENV_KEEP}
    out.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
    out.setdefault("LANG", "C.UTF-8")
    return out


class SandboxLauncher:
    """Wie DevLauncher (Zeitlimit, Prozessgruppe, Hintergrundprozesse), nur in bwrap verpackt."""

    def __init__(self, workspace: Path, read_only: list[Path] | None = None) -> None:
        self.workspace = workspace
        self.read_only = read_only or []
        self._dev = DevLauncher()

    async def run(self, cmd: str, cwd: Path, timeout: int = 60, env: dict | None = None) -> LaunchResult:
        if not available():
            return LaunchResult(exit_code=-1, stdout="", stderr=UNAVAILABLE)
        ws = self.workspace.resolve()
        cwd = cwd.resolve()
        if cwd != ws and ws not in cwd.parents:
            cwd = ws                                                 # nie außerhalb des Workspace starten
        (ws / ".home").mkdir(parents=True, exist_ok=True)
        bash = shutil.which("bash") or "/bin/bash"
        argv = sandbox_args(ws, cwd, read_only=self.read_only) + [bash, "-c", cmd]
        import shlex
        wrapped = " ".join(shlex.quote(a) for a in argv)
        res = await self._dev.run(wrapped, cwd=cwd, timeout=timeout, env=sandbox_env(env))
        if res.exit_code != 0 and res.stderr.startswith("bwrap:"):
            return LaunchResult(exit_code=-1, stdout=res.stdout,
                                stderr=f"{UNAVAILABLE}\n(bwrap meldet: {res.stderr.strip()[:300]})")
        return res
