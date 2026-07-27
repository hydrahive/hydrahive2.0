"""Wacht darüber, dass Tests gegen das REPO laufen — nie gegen /opt.

Hintergrund: Auf dem Server liegt ein editable-Install, dessen .pth-Datei
`/opt/hydrahive2/core/src` fest in sys.path einträgt. Ohne `pythonpath = ["src"]`
in der pytest-Config gewinnt dieser Produktionsstand: man testet dann unbemerkt
den ALTEN Code, und neue Module aus dem Arbeitsverzeichnis werfen
ModuleNotFoundError — obwohl die Datei direkt daneben liegt.

Dieser Test schlägt fehl, sobald jemand die pythonpath-Option entfernt oder die
Test-Umgebung so verbiegt, dass wieder eine Fremdinstallation importiert wird.
"""
from __future__ import annotations

from pathlib import Path


def test_hydrahive_wird_aus_diesem_repo_importiert():
    import hydrahive

    imported = Path(hydrahive.__file__).resolve()
    expected_src = (Path(__file__).resolve().parents[1] / "src").resolve()

    assert imported.is_relative_to(expected_src), (
        f"Tests laufen gegen eine FREMDE hydrahive-Installation:\n"
        f"  importiert: {imported}\n"
        f"  erwartet unter: {expected_src}\n"
        f"Ursache ist meist eine fehlende `pythonpath = [\"src\"]`-Option in "
        f"core/pyproject.toml ([tool.pytest.ini_options])."
    )
