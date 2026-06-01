from __future__ import annotations
from pathlib import Path

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB (Lesen + Schreiben)
MAX_ENTRIES = 2000  # Verzeichnis-Listing-Cap gegen Memory-Spikes (z.B. node_modules)


def list_dir(abs_path: Path) -> list[dict]:
    """Eine Ebene listen. Ordner zuerst, dann Dateien, alphabetisch.
    `.git`-Einträge werden ausgeblendet. Hart auf MAX_ENTRIES gekappt."""
    if not abs_path.is_dir():
        raise NotADirectoryError(str(abs_path))
    entries = []
    for child in sorted(abs_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name.startswith(".git"):
            continue
        entries.append({
            "name": child.name,
            "is_dir": child.is_dir(),
            "size": child.stat().st_size if child.is_file() else None,
        })
        if len(entries) >= MAX_ENTRIES:
            break
    return entries


def read_file(abs_path: Path) -> str:
    """Datei als Text lesen. Wirft bei zu groß oder fehlend."""
    if not abs_path.is_file():
        raise FileNotFoundError(str(abs_path))
    if abs_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file_too_large")
    return abs_path.read_text(encoding="utf-8")


def write_file(abs_path: Path, content: str) -> None:
    """Datei schreiben, Eltern-Verzeichnisse anlegen falls nötig.
    Größen-Limit spiegelt das Lese-Limit (Schutz gegen Disk-Fill)."""
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("file_too_large")
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
