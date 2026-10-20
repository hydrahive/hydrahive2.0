"""macOS hat /bin/bash 3.2 (Befund 20.10.2026 auf dem Test-Mac .186): Mit `set -u` bricht dort jede Verwendung
eines LEEREN Arrays als `"${arr[@]}"` oder `${arr[*]}` mit „unbound variable“ ab (ab Bash 4.4 erlaubt).
Genau so brach update-mac.sh nach dem Merge von #592 in mac-python-heal.sh ab.

Diese Prüfung läuft auf Linux (Bash 5) und erkennt die Muster deshalb im Quelltext.
Sichere Schreibweise: `${arr[@]+"${arr[@]}"}` bzw. `${arr[*]-}`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
MAC_SCRIPTS = sorted([INSTALLER / "update-mac.sh", INSTALLER / "install-mac.sh",
                      *(INSTALLER / "modules-mac").glob("*.sh"),
                      *(INSTALLER / "lib").glob("mac-*.sh")])

# ${x[@]} bzw. ${x[*]} – erlaubt nur in der sicheren Form ${x[@]+"${x[@]}"} oder ${x[*]-}
_ANY = re.compile(r'\$\{(\w+)\[([@*])\]([^}]*)\}')
_SAFE_PLUS = re.compile(r'\$\{(\w+)\[@\]\+"\$\{\1\[@\]\}"\}')

# Arrays, die im Skript fest belegt und nie leer sind (Bash 3.2 bricht nur bei LEEREN ab).
NEVER_EMPTY = {("00-deps.sh", "BREW_PKGS")}


def _unsafe_uses(text: str, script: str = "") -> list[str]:
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        code = "" if line.lstrip().startswith("#") else line.split(" #", 1)[0]
        code = _SAFE_PLUS.sub("", code)                    # sichere +-Form komplett entfernen
        for m in _ANY.finditer(code):
            name, _, rest = m.groups()
            if rest.startswith("-") or (script, name) in NEVER_EMPTY:
                continue
            out.append(f"{n}: {m.group(0)}")
    return out


@pytest.mark.parametrize("script", MAC_SCRIPTS, ids=lambda p: p.name)
def test_no_unsafe_array_expansion_for_bash32(script):
    assert _unsafe_uses(script.read_text(), script.name) == [], f"{script.name}: Bash 3.2 bricht hier mit set -u ab"


def test_detector_finds_the_pattern():
    assert _unsafe_uses('for n in "${broken[@]}"; do') == ["1: ${broken[@]}"]
    assert _unsafe_uses('case " ${broken[*]} " in') == ["1: ${broken[*]}"]
    assert _unsafe_uses('x=( ${a[@]+"${b[@]}"} )') != []                          # + muss auf dasselbe Array zeigen
    assert _unsafe_uses('for n in ${broken[@]+"${broken[@]}"}; do') == []
    assert _unsafe_uses('case " ${broken[*]-} " in') == []
    assert _unsafe_uses('# "${broken[@]}" nur im Kommentar') == []


def test_never_empty_exception_is_real():
    """Die Ausnahme gilt nur, solange das Array im Skript wirklich fest belegt ist."""
    text = (INSTALLER / "modules-mac" / "00-deps.sh").read_text()
    assert re.search(r"^BREW_PKGS=\(\S+", text, re.M), "BREW_PKGS nicht mehr fest belegt – Ausnahme entfernen"


def test_mac_scripts_are_found():
    names = {p.name for p in MAC_SCRIPTS}
    assert {"update-mac.sh", "mac-python-heal.sh", "50-launchd.sh"} <= names
