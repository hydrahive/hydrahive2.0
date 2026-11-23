"""Baut das GitHub-Wiki aus den Repos (Ziel hydrahive2-modules/ziele/wiki-automatik.md, WK1–WK3).

Aufruf: python3 scripts/wiki/build.py <kern-checkout> <modul-checkout> <wiki-ordner>
Schreibt <Seite>.md, Home.md, _Sidebar.md, _Footer.md. Fehlende Artikel → Seite fehlt, Lücke im Protokoll.
Datenschutz-Treffer → Abbruch (Exit 1), dann wird nichts veröffentlicht.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pages import SECTIONS  # noqa: E402

FORBIDDEN = [
    (r"\b192\.168\.\d+\.\d+\b", "private IP"), (r"\b10\.\d+\.\d+\.\d+\b", "private IP"),
    (r"\b172\.(1[6-9]|2\d|3[01])\.\d+\.\d+\b", "private IP"),
    (r"hydrahive-master|hydratest\b", "Rechnername"), (r"/srv/|/home/\w", "interner Pfad"),
    (r"\bTill(s)?\b", "Personenname"), (r"\bbibi\b|\bmaske\b", "Benutzername"),
    (r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9-]{20,}", "Token"),
]
#: Projektgeschichte: der Gründer darf auf dieser Seite namentlich genannt werden.
ALLOW_NAME_IN = {"Was-ist-HydraHive"}


def check_public(slug: str, text: str) -> list[str]:
    hits = []
    for pat, label in FORBIDDEN:
        if label == "Personenname" and slug in ALLOW_NAME_IN:
            continue
        for m in re.finditer(pat, text):
            line = text[: m.start()].count("\n") + 1
            hits.append(f"{slug}:{line}: {label}: …{text[max(0, m.start() - 30): m.end() + 30]!r}…")
    return hits


def source_path(core: Path, mods: Path, src: tuple[str, str]) -> Path:
    kind, name = src
    if kind == "core":
        return core / "frontend" / "src" / "i18n" / "help" / "de" / f"{name}.md"
    if kind == "mod":
        return mods / name / "frontend" / "help" / "de" / f"{name}.md"
    return HERE / "texts" / f"{name}.md"


def footer_note(src: tuple[str, str]) -> str:
    kind, name = src
    if kind == "core":
        where = f"Kern-Repo `frontend/src/i18n/help/de/{name}.md`"
    elif kind == "mod":
        where = f"Modul-Repo `{name}/frontend/help/de/{name}.md`"
    else:
        return ""
    return f"\n---\n*Quelle: In-App-Hilfe von HydraHive ({where}). Korrekturen bitte dort.*\n"


def page_md(title: str, raw: str, src: tuple[str, str]) -> str:
    body = re.sub(r"\A# [^\n]*\n+", "", raw).strip()            # H1 kommt aus dem Wiki-Titel
    return f"# {title}\n\n{body}\n{footer_note(src)}"


def build(core: Path, mods: Path, wiki: Path) -> tuple[list[str], list[str], list[str]]:
    """→ (geschriebene Seiten, Lücken, Datenschutz-Treffer)."""
    written, gaps, problems = [], [], []
    for _, pages in SECTIONS:
        for slug, title, src in pages:
            path = source_path(core, mods, src)
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                gaps.append(f"{slug}: kein Artikel ({src[0]}:{src[1]})")
                continue
            md = page_md(title, path.read_text(encoding="utf-8"), src)
            problems += check_public(slug, md)
            (wiki / f"{slug}.md").write_text(md, encoding="utf-8")
            written.append(slug)
    present = set(written)
    (wiki / "_Sidebar.md").write_text(sidebar(present), encoding="utf-8")
    home = home_md(present)
    (wiki / "Home.md").write_text(home, encoding="utf-8")
    footer = (HERE / "texts" / "_Footer.md").read_text(encoding="utf-8")
    (wiki / "_Footer.md").write_text(footer, encoding="utf-8")
    problems += check_public("Home", home) + check_public("_Footer", footer)
    return written, gaps, problems


def _short(title: str) -> str:
    return title.split(" ", 1)[1] if " " in title else title


def sidebar(present: set[str]) -> str:
    lines = ["**[[🏠 Start|Home]]**", ""]
    for name, pages in SECTIONS:
        items = [f"- [[{_short(t)}|{s}]]" for s, t, _ in pages if s in present]
        if items:
            lines += [f"**{name}**", *items, ""]
    return "\n".join(lines)


def home_md(present: set[str]) -> str:
    parts = [(HERE / "texts" / "Home.md").read_text(encoding="utf-8").rstrip(), ""]
    for name, pages in SECTIONS:
        items = [f"- [[{t}|{s}]]" for s, t, _ in pages if s in present]
        if items:
            parts += [f"## {name}", *items, ""]
    return "\n".join(parts)


def remove_stale(wiki: Path, written: list[str]) -> list[str]:
    """Seiten, die es nicht mehr gibt (z. B. früher aus Discord), aus dem Wiki entfernen."""
    keep = set(written) | {"Home", "_Sidebar", "_Footer"}
    gone = []
    for p in wiki.glob("*.md"):
        if p.stem not in keep:
            p.unlink()
            gone.append(p.stem)
    return sorted(gone)


def main(argv: list[str]) -> int:
    core, mods, wiki = (Path(a) for a in argv[1:4])
    wiki.mkdir(parents=True, exist_ok=True)
    written, gaps, problems = build(core, mods, wiki)
    gone = remove_stale(wiki, written)
    print(f"{len(written)} Seiten geschrieben")
    for g in gaps:
        print(f"LÜCKE: {g}")
    for g in gone:
        print(f"ENTFERNT: {g}")
    if problems:
        print("DATENSCHUTZ – Bau abgebrochen:\n" + "\n".join(problems))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
