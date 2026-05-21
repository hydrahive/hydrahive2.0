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

    try:
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
            return ToolResult.fail(f"Timeout nach {timeout}s")
    except FileNotFoundError:
        return ToolResult.fail("dev-browser Binary nicht gefunden (PATH-Problem?)")
    except OSError as e:
        return ToolResult.fail(f"Prozess-Start fehlgeschlagen: {e}")

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")

    if len(stdout) > _MAX_OUTPUT:
        stdout = stdout[:_MAX_OUTPUT] + f"\n… (gekürzt, {len(stdout_b)} Bytes gesamt)"

    exit_code = proc.returncode or 0
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
