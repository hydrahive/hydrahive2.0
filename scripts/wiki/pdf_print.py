"""HTML → PDF mit Playwright-Chromium (Seitenzahlen, Lesezeichen, interne Sprünge). WK4.
Aufruf: python3 scripts/wiki/pdf_print.py <eingabe.html> <ausgabe.pdf>"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

FOOTER = ('<div style="font-size:8px;width:100%;text-align:center;color:#888">HydraHive-Handbuch · Seite '
          '<span class="pageNumber"></span> von <span class="totalPages"></span></div>')


async def render(src: Path, out: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(src.resolve().as_uri(), wait_until="networkidle")
        await page.pdf(path=str(out), format="A4", print_background=True, display_header_footer=True,
                       header_template="<span></span>", footer_template=FOOTER, outline=True, tagged=True,
                       margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"})
        await browser.close()


if __name__ == "__main__":
    asyncio.run(render(Path(sys.argv[1]), Path(sys.argv[2])))
