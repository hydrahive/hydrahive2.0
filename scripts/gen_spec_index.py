"""Erzeugt docs/specs/README.md aus Dateinamen + Git-Historie + H1-Titel.
Rein mechanisch — liest keine Spec-Inhalte ausser der ersten Ueberschrift."""
import re
import subprocess
from pathlib import Path

SPECS = Path("docs/specs")

def h1(p: Path) -> str:
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[:10]:
        if line.startswith("# "):
            return line[2:].strip()
    return p.stem

def status(p: Path) -> str:
    """Nur wenn die Spec ihn selbst nennt — nichts erfinden."""
    head = "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    m = re.search(r"\*\*Status:\*\*\s*([^\n—-]+)", head)
    return m.group(1).strip() if m else ""

def last_change(p: Path) -> str:
    r = subprocess.run(["git", "log", "-1", "--format=%ad", "--date=short", "--", str(p)],
                       capture_output=True, text=True)
    return r.stdout.strip() or "?"

files = sorted(SPECS.glob("*.md"))
files = [f for f in files if f.name != "README.md"]

# Serien erkennen: gemeinsamer Praefix vor -vN / -N
series: dict[str, list[Path]] = {}
single: list[Path] = []
for f in files:
    m = re.match(r"^(.+?)-v?\d+[a-z]?$", f.stem)
    (series.setdefault(m.group(1), []).append(f) if m else single.append(f))
for k in [k for k, v in series.items() if len(v) < 2]:
    single.extend(series.pop(k))

lines = [
    "# Spec-Index",
    "",
    "> Automatisch erzeugt aus Dateinamen, Git-Historie und Überschriften.",
    "> Neu erzeugen: `python3 scripts/gen_spec_index.py`",
    "",
    f"{len(files)} Spezifikationen. Die Spalte **Status** zeigt nur, was die Spec",
    "selbst im Kopf angibt — leer heißt: nicht angegeben, nicht automatisch geraten.",
    "",
]

if series:
    lines += ["## Mehrteilige Reihen", "",
              "Bei Reihen ist in der Regel der **letzte Teil** der aktuelle Stand;",
              "frühere Teile beschreiben bereits umgesetzte Etappen.", ""]
    for name in sorted(series):
        parts = sorted(series[name], key=lambda p: p.stem)
        lines += [f"### {name}", "", "| Spec | Titel | Status | Zuletzt geändert |",
                  "|---|---|---|---|"]
        for p in parts:
            lines.append(f"| [`{p.name}`]({p.name}) | {h1(p)} | {status(p)} | {last_change(p)} |")
        lines.append("")

lines += ["## Einzelne Spezifikationen", "",
          "| Spec | Titel | Status | Zuletzt geändert |", "|---|---|---|---|"]
for p in sorted(single, key=lambda x: x.stem):
    lines.append(f"| [`{p.name}`]({p.name}) | {h1(p)} | {status(p)} | {last_change(p)} |")
lines.append("")

(SPECS / "README.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Index geschrieben: {len(files)} Specs, {len(series)} Reihen, {len(single)} einzeln")
