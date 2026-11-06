"""Die Sicherheitsregel von HydraHive erlaubt iframes nur für die Vibe-Vorschau (Port 8444) – und sonst nichts.

Ohne `frame-src` fällt der Browser auf `default-src 'self'` zurück und blockiert das Vorschau-Fenster des Moduls Vibe
(auf hydratest gemessen 6.11.2026). Das Modul selbst darf den Kern nicht ändern, darum steht die Freigabe hier.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FILES = ("installer/modules/60-nginx.sh", "installer/modules-mac/60-nginx.sh")
_CSP = re.compile(r'add_header Content-Security-Policy "(default-src \'self\';[^"]*)"')


def _main_csp(rel: str) -> str:
    found = _CSP.findall((ROOT / rel).read_text(encoding="utf-8"))
    assert len(found) == 1, f"{rel}: genau eine Haupt-CSP erwartet, gefunden {len(found)}"
    return found[0]


@pytest.mark.parametrize("rel", FILES)
def test_frame_src_erlaubt_nur_eigenen_ursprung_und_port_8444(rel):
    csp = _main_csp(rel)
    m = re.search(r"frame-src ([^;]+);", csp)
    assert m, f"{rel}: frame-src fehlt – Vibe-Vorschau würde blockiert"
    assert m.group(1).split() == ["'self'", "https://*:8444"]


@pytest.mark.parametrize("rel", FILES)
def test_einbetten_von_aussen_bleibt_gesperrt(rel):
    csp = _main_csp(rel)
    assert "frame-ancestors 'self';" in csp and "object-src 'none';" in csp
    assert "default-src 'self';" in csp and "frame-src *" not in csp and "frame-src https:" not in csp
