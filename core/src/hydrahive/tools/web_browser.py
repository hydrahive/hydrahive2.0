"""Browser-Automation via dev-browser (QuickJS WASM Sandbox).

Erfordert: npm install -g dev-browser && dev-browser install

Das Script läuft in einer QuickJS-Sandbox — kein Zugriff auf Host-Filesystem
oder Netzwerk außer über den Browser. Volle Playwright-API verfügbar.

Beispiel-Script:
    const page = await browser.getPage("main");
    await page.goto("https://example.com", {waitUntil: "domcontentloaded"});
    console.log(await page.title());
    console.log(await page.textContent("h1"));
"""
from __future__ import annotations

import asyncio
import logging
import shutil

from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_MAX_OUTPUT = 80_000

_DESCRIPTION = """\
Steuert einen echten Browser (Playwright/Chromium, headless). Führt ein \
JavaScript-Script in einer sandboxed QuickJS-Umgebung aus. Besser als \
fetch_url für JS-gerenderte Seiten, SPAs, Login-Flows, Forms und Screenshots.

Script-API (QuickJS, NICHT Node.js):
  const page = await browser.getPage("main");   // persistente benannte Seite
  await page.goto(url, {waitUntil: "domcontentloaded"});
  const text = await page.textContent("selector");
  const html = await page.content();            // komplettes DOM
  await page.fill("input[name=q]", "Suche");
  await page.click("button[type=submit]");
  const buf = await page.screenshot({type:"jpeg",quality:50});
  await saveScreenshot(buf, "shot.jpg");         // ~/.dev-browser/tmp/shot.jpg
  console.log("output");                         // erscheint im Ergebnis

Seiten bleiben zwischen Aufrufen erhalten wenn derselbe Name genutzt wird.\
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "script": {
            "type": "string",
            "description": "JavaScript-Code der im Browser ausgeführt wird.",
        },
        "url": {
            "type": "string",
            "description": (
                "Convenience: Navigation am Anfang. Wenn angegeben wird "
                "page.goto(URL) automatisch vorangestellt."
            ),
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in Sekunden (default 60).",
            "default": 60,
        },
    },
    "required": ["script"],
}


# Fehler-Signaturen, die auf einen veralteten Daemon hindeuten (z.B. nach
# Sandbox-Remount: der Daemon hängt in einem alten Mount-Namespace und sein
# /tmp ist nicht mehr beschreibbar → Playwright scheitert an mkdtemp).
# In diesem Fall: Daemon killen, Socket/PID räumen, einmal retryen.
_STALE_DAEMON_SIGS = (
    "mkdtemp",
    "ENOENT",
    "no such file or directory",
    "ECONNREFUSED",
    "socket",
    "daemon",
)


def _kill_stale_daemon(dev_home: str) -> bool:
    """Killt einen hängenden dev-browser-Daemon und räumt Socket/PID auf.

    Gibt True zurück, wenn etwas aufgeräumt wurde (also ein Retry sinnvoll ist).
    """
    import os
    import signal

    state_dir = os.path.join(dev_home, ".dev-browser")
    pid_file = os.path.join(state_dir, "daemon.pid")
    sock_file = os.path.join(state_dir, "daemon.sock")
    cleaned = False

    try:
        with open(pid_file, encoding="utf-8") as fh:
            pid = int(fh.read().strip())
    except (OSError, ValueError):
        pid = 0

    if pid > 1:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(pid, sig)
                cleaned = True
            except ProcessLookupError:
                break
            except OSError:
                break
            import time
            time.sleep(0.5)
            try:
                os.kill(pid, 0)  # noch da?
            except ProcessLookupError:
                break

    for path in (sock_file, pid_file):
        try:
            os.unlink(path)
            cleaned = True
        except OSError:
            pass

    logger.info("dev-browser: stale daemon aufgeräumt (cleaned=%s)", cleaned)
    return cleaned


async def _run_dev_browser(
    script: str, env: dict, timeout: int
) -> tuple[int, str, str]:
    """Startet dev-browser einmal und liefert (exit_code, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "dev-browser", "--headless",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(input=script.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    return (proc.returncode or 0), stdout, stderr


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    if not shutil.which("dev-browser"):
        return ToolResult.fail(
            "dev-browser nicht installiert. "
            "Ausführen: npm install -g dev-browser && dev-browser install"
        )

    script: str = args.get("script") or ""
    url: str = (args.get("url") or "").strip()
    timeout = max(10, min(120, int(args.get("timeout") or 60)))

    if url:
        preamble = (
            f"const page = await browser.getPage(\"main\");\n"
            f"await page.goto({url!r}, {{waitUntil: \"domcontentloaded\"}});\n"
        )
        script = preamble + script

    if not script.strip():
        return ToolResult.fail("Kein Script angegeben")

    # dev-browser braucht ein beschreibbares HOME für ~/.dev-browser/ und
    # ~/.cache/ms-playwright/. /home/hydrahive ist read-only gemountet,
    # aber .config/ ist beschreibbar.
    import os
    dev_home = os.path.expanduser("~/.config/hh-dev-browser-home")
    os.makedirs(dev_home, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = dev_home

    # Eigenes, garantiert beschreibbares TMPDIR mitgeben, damit Playwright
    # nicht vom geerbten /tmp abhängt (das nach einem Remount im Daemon-
    # Namespace tot sein kann).
    tmp_dir = os.path.join(dev_home, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    env["TMPDIR"] = tmp_dir

    # Beim allerersten Aufruf nach Daemon-Tod fährt der Daemon erst hoch —
    # das kann ein paar Spawn-Races (ProcessLookupError/OSError) auslösen,
    # bis der Socket bereit ist. Daher mit Backoff mehrfach versuchen.
    exit_code = stdout = stderr = None
    last_spawn_err: Exception | None = None
    for attempt in range(4):
        try:
            exit_code, stdout, stderr = await _run_dev_browser(script, env, timeout)
            break
        except asyncio.TimeoutError:
            return ToolResult.fail(f"Timeout nach {timeout}s")
        except FileNotFoundError:
            return ToolResult.fail(
                "dev-browser Binary nicht gefunden (PATH-Problem?)"
            )
        except OSError as e:
            # ProcessLookupError ist OSError-Subklasse — Spawn-Race, Daemon
            # fährt noch hoch. Kurz warten und neu versuchen.
            last_spawn_err = e
            if attempt < 3:
                logger.info(
                    "dev-browser: Spawn-Race (Versuch %d) — retry", attempt + 1
                )
                await asyncio.sleep(1.0 + attempt)
                continue
            return ToolResult.fail(
                f"Prozess-Start fehlgeschlagen nach {attempt + 1} Versuchen: "
                f"{last_spawn_err or e}"
            )

    # Selbstheilung: Sieht der Fehler nach einem veralteten Daemon aus
    # (Sandbox-Remount → totes /tmp im alten Namespace), Daemon killen und
    # genau einmal frisch retryen.
    if exit_code != 0 and any(
        sig.lower() in (stderr or "").lower() for sig in _STALE_DAEMON_SIGS
    ):
        logger.warning(
            "dev-browser exit %s mit stale-daemon-Signatur — retry nach cleanup",
            exit_code,
        )
        if _kill_stale_daemon(dev_home):
            try:
                exit_code, stdout, stderr = await _run_dev_browser(
                    script, env, timeout
                )
            except asyncio.TimeoutError:
                return ToolResult.fail(f"Timeout nach {timeout}s (nach Daemon-Restart)")
            except OSError as e:
                return ToolResult.fail(f"Prozess-Start fehlgeschlagen (Retry): {e}")

    if len(stdout) > _MAX_OUTPUT:
        stdout = stdout[:_MAX_OUTPUT] + f"\n… (gekürzt, {len(stdout)} Bytes gesamt)"

    if exit_code != 0:
        return ToolResult.fail(
            f"dev-browser exit {exit_code}",
            stdout=stdout,
            stderr=stderr[:2000],
        )

    return ToolResult.ok(stdout or "(kein Output)", stderr=stderr[:500] if stderr else None)


TOOL = Tool(
    name="web_browser",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="web",
)
