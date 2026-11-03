"""macOS nutzt standardmäßig ein case-insensitives Dateisystem.

TypeScript löst `./Name` zuerst als Name.ts und danach als Name.tsx auf. Zwei
Dateien mit gleichem Stamm, aber anderer Schreibung/TS-Endung können deshalb auf
Linux funktionieren und auf macOS als TS1149/TS1261 abbrechen.
"""
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src"
TS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}


def test_frontend_has_no_case_insensitive_module_stem_collisions() -> None:
    by_stem: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in TS_EXTENSIONS:
            relative = path.relative_to(ROOT)
            key = (relative.parent.as_posix().casefold(), path.stem.casefold())
            by_stem[key].append(relative.as_posix())

    collisions = [sorted(paths) for paths in by_stem.values() if len(paths) > 1]
    assert not collisions, "Auf case-insensitivem macOS mehrdeutig: " + repr(collisions)
