"""Agenten-Befehle in einer bubblewrap-Sandbox.

Ziel hydrahive2-modules/ziele/agenten-projekt-isolation.md (B2a) und Nachtrag …-B3.md (B3a: Allowlist).

**Allowlist, nicht Sperrliste.** Die Sandbox startet mit einer leeren Wurzel und blendet nur ein:
- System lesend: ``/usr`` (und die Verweise ``/bin``, ``/lib`` … wie auf dem Rechner), ``/etc``, ``/sys``,
  den Programmordner von HydraHive (``settings.base_dir``, dort liegt die Python-Umgebung) und den Ordner, auf den
  ``/etc/resolv.conf`` zeigt (Namensauflösung);
- den eigenen Workspace beschreibbar, verknüpfte Projekte (``linked_projects``) lesend;
- eigenes ``/dev``, ``/proc`` (eigener PID-Namespace), ``/tmp``, ``/run``; ``HOME`` im Workspace (``.home/``).

Alles andere fehlt – ``/home``, ``/root``, ``/srv``, ``/mnt``, ``/media``, ``/var``, weitere Platten, andere
Programme unter ``/opt`` –, ohne dass ein Pfad dieses Rechners hier steht (Till 23.11.: „ALLES muss auch für andere
passen“). Die eigenen Daten-, Konfig-, Log- und Archiv-Ordner kommen aus den Einstellungen (``HH_DATA_DIR``,
``HH_CONFIG_DIR``, ``HH_LOG_DIR``, Archiv-Ort) und werden zusätzlich leer überdeckt, falls sie unter einem
eingeblendeten Ordner liegen (z. B. Konfig unter ``/etc``). Liegt ein einzublendender System-Ordner selbst in so
einem Ordner, wird er nicht eingeblendet.

Netz bleibt in dieser Etappe offen (git/gh/npm ci); Heimnetz-Sperre ist Etappe B4, bis dahin gilt die Wortliste
aus _shell_guard (ssh/scp/nc …).

bubblewrap + AppArmor-Profil ``hydrahive-bwrap-userns`` richten Installer (modules/00-deps.sh) und update.sh auf
jeder Linux-Installation ein. Fehlt bwrap (z. B. macOS) oder scheitert die Sandbox, wird NICHT ungeschützt
ausgeführt (fail-closed), sondern eine klare Meldung zurückgegeben.
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
from pathlib import Path

from hydrahive.tools._launcher import DevLauncher, LaunchResult

logger = logging.getLogger(__name__)

_BWRAP = "/usr/bin/bwrap"
#: System-Ordner, die lesend eingeblendet werden (wenn vorhanden). Verweise (usrmerge: /bin → usr/bin) werden als
#: Verweis nachgebaut, nicht verfolgt.
_SYSTEM_RO = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32", "/etc", "/sys", "/snap")
#: Umgebung in der Sandbox: nur diese Schlüssel aus dem vorbereiteten env (shell._build_env) + feste Werte.
_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "TERM", "TZ", "GH_TOKEN", "GITHUB_TOKEN", "GITEA_TOKEN", "PYTHONPATH",
             "NODE_OPTIONS", "CI", "HH_PREVIEW_PORT")
UNAVAILABLE = ("Sandbox nicht verfügbar (bubblewrap fehlt oder startet nicht). Der Befehl wurde aus Sicherheitsgründen "
               "nicht ausgeführt. Melde das als Blocker; ein Admin prüft das Update von HydraHive.")


def available() -> bool:
    return os.access(_BWRAP, os.X_OK)


def _real(p: Path | str) -> Path:
    return Path(os.path.realpath(p))


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def private_dirs() -> list[Path]:
    """Ordner des Dienstes, die nie in der Sandbox auftauchen dürfen – aus den Einstellungen, nicht fest."""
    from hydrahive.settings import settings
    out = [settings.data_dir, settings.config_dir]
    log_dir = _real(settings.log_dir)
    if log_dir != Path("/"):
        out.append(log_dir)
    try:
        from hydrahive.archive.location import archive_root
        out.append(archive_root())
    except Exception:  # noqa: BLE001 – Archiv nicht lesbar: dann eben nur die übrigen
        logger.warning("Sandbox: Archiv-Ort nicht lesbar", exc_info=True)
    seen: list[Path] = []
    for p in out:
        r = _real(p)
        if r != Path("/") and r not in seen:
            seen.append(r)
    return seen


def system_ro() -> list[Path]:
    """Lesend eingeblendete Ordner: System + Programmordner + Ziel von /etc/resolv.conf."""
    from hydrahive.settings import settings
    dirs = [Path(d) for d in _SYSTEM_RO]
    dirs.append(Path(settings.base_dir))
    resolv = _real("/etc/resolv.conf")
    if resolv.exists() and not any(_inside(resolv, _real(d)) for d in ("/etc", "/usr")):
        dirs.append(resolv.parent)
    return dirs


def sandbox_args(workspace: Path, cwd: Path, *, read_only: list[Path] | None = None,
                 private: list[Path] | None = None, system: list[Path] | None = None) -> list[str]:
    """bwrap-Argumente (ohne den Befehl). Reine Funktion – ``private``/``system`` für Tests einsetzbar.

    Reihenfolge zählt: System lesend → private Ordner darin leer überdecken → verknüpfte Projekte lesend →
    Workspace beschreibbar (zuletzt, damit er auch dann sichtbar ist, wenn er unter einem privaten Ordner liegt –
    das ist der Normalfall: Workspaces liegen im Datenordner)."""
    ws = _real(workspace)
    private = [_real(p) for p in (private if private is not None else private_dirs())]
    system = system if system is not None else system_ro()
    args = [_BWRAP, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
            "--hostname", "hh-sandbox", "--dev", "/dev", "--proc", "/proc",
            "--tmpfs", "/tmp", "--tmpfs", "/var/tmp", "--tmpfs", "/run", "--tmpfs", "/dev/shm"]
    mounted: list[Path] = []
    for d in system:
        d = Path(d)
        if d.is_symlink():
            args += ["--symlink", os.readlink(d), str(d)]
            continue
        r = _real(d)
        if not r.is_dir() or r == Path("/"):
            continue
        if any(_inside(r, p) for p in private):
            logger.warning("Sandbox: %s liegt in einem privaten Ordner – nicht eingeblendet", r)
            continue
        args += ["--ro-bind", str(r), str(r)]
        mounted.append(r)
    for p in private:                                          # z. B. Konfig unter /etc → leer überdecken
        if any(_inside(p, m) for m in mounted) and p.is_dir():
            args += ["--tmpfs", str(p)]
    for extra in read_only or []:
        p = _real(extra)
        if p.is_dir() and p != ws:
            args += ["--ro-bind", str(p), str(p)]
    home = ws / ".home"
    args += ["--bind", str(ws), str(ws)]
    shown = [ws] + [_real(x) for x in read_only or []]
    for p in private:                                          # privater Ordner IM Workspace → wieder leer
        if p != ws and any(_inside(p, s) for s in shown) and p.is_dir():
            args += ["--tmpfs", str(p)]
    args += ["--setenv", "HOME", str(home), "--setenv", "TMPDIR", "/tmp", "--chdir", str(_real(cwd))]
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
        wrapped = " ".join(shlex.quote(a) for a in argv)
        res = await self._dev.run(wrapped, cwd=cwd, timeout=timeout, env=sandbox_env(env))
        if res.exit_code != 0 and res.stderr.startswith("bwrap:"):
            return LaunchResult(exit_code=-1, stdout=res.stdout,
                                stderr=f"{UNAVAILABLE}\n(bwrap meldet: {res.stderr.strip()[:300]})")
        return res
