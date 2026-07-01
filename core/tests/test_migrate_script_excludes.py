"""Statische Prüfung der Exclude-Liste in installer/migrate.sh.

Verhindert Regression: die rsync-Excludes dürfen NUR regenerierbaren Ballast
ausschließen — niemals Nutzdaten (Git-Repos, workspaces, modules, vms,
Plattenarchive). Till: "wenn z.B. das Plattenarchiv weg ist, habe ich ein
ernsthaftes Problem."
"""
from __future__ import annotations

from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / "installer" / "migrate.sh"
)


@pytest.fixture(scope="module")
def script_text() -> str:
    if not SCRIPT.exists():
        pytest.skip(f"migrate.sh nicht gefunden: {SCRIPT}")
    return SCRIPT.read_text()


# Ballast, der ausgeschlossen sein MUSS (regenerierbar).
BALLAST = [
    "node_modules/",
    ".venv/",
    "__pycache__/",
    ".plugin-cache/",
    ".module-cache/",
    "gocache/",
    "gomods/",
    "memory_index.db",
]

# Nutzdaten-Verzeichnisse, die NIEMALS als exclude-Pattern auftauchen dürfen.
# Exakter Vergleich gegen den Pattern-Wert (nicht Substring) — sonst kollidiert
# z.B. das legitime 'node_modules/' mit 'modules/'.
FORBIDDEN_PATTERNS = {
    ".git",
    ".git/",
    "workspaces",
    "workspaces/",
    "modules",
    "modules/",
    "vms",
    "vms/",
    "projects",
    "projects/",
    "agents",
    "agents/",
}


def _exclude_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if "--exclude" in ln]


def _exclude_patterns(text: str) -> list[str]:
    """Extrahiert den Pattern-Wert aus jeder --exclude 'wert'-Zeile."""
    import re
    out = []
    for ln in _exclude_lines(text):
        m = re.search(r"--exclude\s+'([^']*)'", ln)
        if m:
            out.append(m.group(1))
    return out


def test_ballast_is_excluded(script_text):
    excludes = "\n".join(_exclude_lines(script_text))
    for item in BALLAST:
        assert item in excludes, f"Ballast '{item}' fehlt in den rsync-Excludes"


def test_userdata_never_excluded(script_text):
    patterns = set(_exclude_patterns(script_text))
    clash = patterns & FORBIDDEN_PATTERNS
    assert not clash, f"Nutzdaten dürfen NICHT excludet werden: {clash}"


def test_uses_archive_flags(script_text):
    # -aAX erhält Permissions, ACLs, xattrs → echter Klon.
    assert "-aAX" in script_text
    # numeric-ids: UID/GID werden 1:1 übertragen (Ownership-Erhalt).
    assert "--numeric-ids" in script_text
    # resumierbar bei Abbruch.
    assert "--partial" in script_text


def test_password_never_in_process_args(script_text):
    # sshpass MUSS -f (Datei) nutzen, nie -p (Passwort als Argument → ps-sichtbar).
    assert "sshpass -f" in script_text
    assert "sshpass -p" not in script_text


def test_secret_is_cleaned_up(script_text):
    # Die Secret-Datei muss am Ende gelöscht werden (finish/trap).
    assert 'rm -f "$SECRET"' in script_text
