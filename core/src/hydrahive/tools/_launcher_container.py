"""Befehle eines Container-Projekts in dessen incus-Container ausführen
(docs/specs/projekt-container-ausfuehrung.md).

- `incus exec <ct> … -- bash -lc <befehl>` als Argumentliste: Der Server startet keine eigene Shell, der Befehl ist
  genau ein Argument.
- Keine Umgebung des Servers (Tokens, HH_*, PATH), nur eine feste kleine Liste.
- Zeitlimit/Abbruch: Host-Prozess beenden UND im Container alles mit derselben HH_EXEC_ID.
- Container aus → Fehler, er wird nicht von selbst gestartet. Projekt nicht lesbar → Fehler, kein Rückfall auf den
  Server (fail-closed).
"""
from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

from hydrahive.tools._launcher import Launcher, LaunchResult, get_launcher

_INCUS = shutil.which("incus") or "incus"
_KILL_TIMEOUT = 10
# Eigene Sitzung/Gruppe (setsid), PGID für den Abbruch merken, dann den Befehl des Agenten als Login-Shell. Der Befehl
# kommt als $1 – er wird nie in diesen Text eingesetzt.
_WRAPPER = ('echo "$(ps -o pgid= $$ | tr -d " ")" > "/tmp/hh-exec-$HH_EXEC_ID.pgid"; '
            'trap \'rm -f "/tmp/hh-exec-$HH_EXEC_ID.pgid"\' EXIT; bash -lc "$1"')


class ExecutionUnavailable(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ContainerDown(ExecutionUnavailable):
    def __init__(self) -> None:
        super().__init__("project_container_down")


def launcher_for(ctx) -> Launcher:
    """Launcher für diesen Lauf. Ohne Projekt oder bei Host-Projekt: der Standard (wie bisher)."""
    if not ctx.project_id:
        return get_launcher()
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    try:
        project = project_config.get(ctx.project_id)
        if project is None:
            raise ExecutionUnavailable("project_execution_unavailable")
        ex = execution.of(project)
    except ExecutionUnavailable:
        raise
    except Exception:  # noqa: BLE001 – jede Störung heißt: nicht ausführen, nie auf dem Server
        raise ExecutionUnavailable("project_execution_unavailable") from None
    if ex["mode"] == "host":
        return get_launcher()
    return ContainerLauncher(ex["container"], ex["workdir"], ex["user"])


class ContainerLauncher:
    def __init__(self, container: str, workdir: str, user: int) -> None:
        self.container, self.workdir, self.user = container, workdir, user

    async def _running(self) -> bool:
        p = await asyncio.create_subprocess_exec(
            _INCUS, "list", "--format", "csv", "-c", "s", "--", f"^{self.container}$",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env={"PATH": "/usr/bin:/bin"})
        out, _ = await p.communicate()
        return out.decode(errors="replace").strip().upper() == "RUNNING"

    async def _kill_inside(self, exec_id: str) -> None:
        """Die ganze Prozessgruppe des Befehls im Container beenden. Der Wrapper hat seine PGID beim Start in
        /tmp/hh-exec-<id>.pgid geschrieben (exec_id ist ein uuid-hex, also ohne Sonderzeichen)."""
        p = await asyncio.create_subprocess_exec(
            _INCUS, "exec", self.container, "--user", str(self.user), "--group", str(self.user), "--",
            "sh", "-c", f'g=$(cat /tmp/hh-exec-{exec_id}.pgid 2>/dev/null) && [ -n "$g" ] && pkill -KILL -g "$g"; '
                        f'rm -f /tmp/hh-exec-{exec_id}.pgid',
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, env={"PATH": "/usr/bin:/bin"})
        try:
            await asyncio.wait_for(p.communicate(), timeout=_KILL_TIMEOUT)
        except (asyncio.TimeoutError, ProcessLookupError):
            pass

    async def run(self, cmd: str, cwd: Path, timeout: int = 60, env: dict | None = None) -> LaunchResult:
        del cwd, env                       # bewusst ignoriert: Arbeitsort und Umgebung kommen aus dem Projekt
        if not await self._running():
            raise ContainerDown()
        exec_id = uuid.uuid4().hex
        args = [_INCUS, "exec", self.container, "--cwd", self.workdir,
                "--user", str(self.user), "--group", str(self.user),
                "--env", "HOME=/home/labor", "--env", "LANG=C.UTF-8", "--env", f"HH_EXEC_ID={exec_id}",
                "--", "setsid", "bash", "-c", _WRAPPER, "hh-exec", cmd]
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin"})
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.CancelledError:
            proc.kill()
            await self._kill_inside(exec_id)
            raise
        except asyncio.TimeoutError:
            proc.kill()
            await self._kill_inside(exec_id)
            return LaunchResult(exit_code=-1, stdout="", stderr=f"Timeout nach {timeout}s", timed_out=True)
        return LaunchResult(exit_code=proc.returncode or 0, stdout=out.decode(errors="replace"),
                            stderr=err.decode(errors="replace"))
