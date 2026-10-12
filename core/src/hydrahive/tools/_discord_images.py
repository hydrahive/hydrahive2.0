"""Bilder für discord_post / discord_reply prüfen und laden (docs/specs/discord-attachments.md).

Ein Anhang verlässt das System, deshalb strenger als Lesen:
- nur der eigene Arbeitsordner (``safe_path``, Symlinks aufgelöst), keine verknüpften Projekte,
- nur Bilder, erkannt an Endung UND Inhalt (Magic Bytes),
- Schutzliste für Schlüssel-/Konfig-Orte, auch wenn die Datei als Bild getarnt ist,
- feste Grenzen; alles wird geprüft, bevor irgendetwas gesendet wird.
Fehlermeldungen nennen den Pfad so, wie der Agent ihn angegeben hat, nie den aufgelösten.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hydrahive.tools._path import PathOutsideWorkspace, safe_path

MAX_IMAGES = 4
MAX_BYTES = 8 * 1024 * 1024        # Discord ohne Boost: 8 MB je Datei
MAX_TOTAL = 24 * 1024 * 1024

_MAGIC: dict[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
}
_ALLOWED = (*_MAGIC, "webp")
_PROTECTED_PARTS = {".ssh", ".git", ".gnupg", ".aws", ".hydrahive", ".config"}
_PROTECTED_MARKERS = (".key", ".pem", ".p12", ".pfx", ".env", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
                      ".credentials", ".netrc", ".pgpass", ".htpasswd")
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


class ImageError(ValueError):
    """Bild abgelehnt. Text ist für den Agenten/Menschen gedacht."""


@dataclass(frozen=True)
class ImageFile:
    filename: str
    data: bytes


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _is_image(ext: str, head: bytes) -> bool:
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return any(head.startswith(m) for m in _MAGIC.get(ext, ()))


def _protected(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    if any(p in _PROTECTED_PARTS for p in parts[:-1]):
        return True
    name = parts[-1] if parts else ""
    return any(m in name for m in _PROTECTED_MARKERS)


def _clean_name(name: str) -> str:
    stem, dot, ext = name.rpartition(".")
    cleaned = _UNSAFE.sub("_", stem if dot else name)[:80] or "bild"
    return f"{cleaned}.{ext.lower()}" if dot else cleaned


def load_images(workspace: Path, paths: list[str]) -> list[ImageFile]:
    """Alle Pfade prüfen und laden. Wirft ``ImageError`` beim ersten Problem (dann wird nichts gesendet)."""
    if len(paths) > MAX_IMAGES:
        raise ImageError(f"Zu viele Bilder ({len(paths)}) – höchstens {MAX_IMAGES} je Nachricht.")
    root = workspace.resolve()
    out: list[ImageFile] = []
    total = 0
    for raw in paths:
        shown = str(raw)
        try:
            p = safe_path(workspace, shown)
        except PathOutsideWorkspace:
            raise ImageError(f"Bild '{shown}' liegt außerhalb des Arbeitsordners.") from None
        if _protected(p.relative_to(root)):
            raise ImageError(f"Bild '{shown}' liegt an einem geschützten Ort und wird nicht hochgeladen.")
        if not p.is_file():
            raise ImageError(f"Bild '{shown}' nicht gefunden.")
        ext = _ext(p.name)
        if ext not in _ALLOWED:
            raise ImageError(f"'{shown}': kein erlaubtes Bildformat (erlaubt: png, jpg, gif, webp).")
        size = p.stat().st_size
        if size == 0:
            raise ImageError(f"Bild '{shown}' ist leer.")
        if size > MAX_BYTES:
            raise ImageError(f"Bild '{shown}' ist zu groß ({size // 1024} KB, höchstens {MAX_BYTES // 1024} KB).")
        total += size
        if total > MAX_TOTAL:
            raise ImageError(f"Die Bilder sind zusammen zu groß (höchstens {MAX_TOTAL // (1024 * 1024)} MB).")
        data = p.read_bytes()
        if not _is_image(ext, data[:16]):
            raise ImageError(f"'{shown}' ist kein gültiges {ext.upper()}-Bild (Inhalt passt nicht zur Endung).")
        out.append(ImageFile(_clean_name(p.name), data))
    return out
