"""One-Shot-Migration: Agents mit `compact_threshold_pct == 100` auf 75 setzen.

Hintergrund (Issue #126): Default wurde 100 → 75 geändert um Token-Verbrauch
zu reduzieren. Bestehende Agent-Configs mit explizit gesetztem 100 bleiben
unverändert (setdefault greift nicht). Dieses Script erkennt sie und bietet
ein Update an — mit Dry-Run als Default.

Aufruf:
    python -m hydrahive.scripts.migrate_compact_threshold              # dry-run
    python -m hydrahive.scripts.migrate_compact_threshold --apply       # tatsächlich schreiben
    python -m hydrahive.scripts.migrate_compact_threshold --apply --to 80
"""
from __future__ import annotations

import argparse
import json
import sys

from hydrahive.agents._defaults import DEFAULT_COMPACT_THRESHOLD_PCT
from hydrahive.agents._paths import config_path
from hydrahive.agents._config_utils import save_atomic
from hydrahive.settings import settings

OLD_VALUE = 100


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Tatsächlich schreiben (sonst nur Dry-Run)")
    parser.add_argument("--to", type=int, default=DEFAULT_COMPACT_THRESHOLD_PCT,
                        help=f"Neuer Wert (Default: {DEFAULT_COMPACT_THRESHOLD_PCT})")
    args = parser.parse_args()

    if not settings.agents_dir.exists():
        print(f"Kein agents-Verzeichnis unter {settings.agents_dir} — nichts zu tun.")
        return 0

    candidates: list[tuple[str, dict]] = []
    for agent_dir in sorted(settings.agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        cfg_path = agent_dir / "config.json"
        if not cfg_path.exists():
            continue
        try:
            cfg = json.loads(cfg_path.read_text())
        except json.JSONDecodeError:
            print(f"  ⚠  defekt: {cfg_path}", file=sys.stderr)
            continue
        if cfg.get("compact_threshold_pct") == OLD_VALUE:
            candidates.append((agent_dir.name, cfg))

    if not candidates:
        print(f"Keine Agents mit compact_threshold_pct={OLD_VALUE} gefunden.")
        return 0

    action = "WERDE ÄNDERN" if args.apply else "WÜRDE ÄNDERN (Dry-Run, nutze --apply)"
    print(f"{action}: {len(candidates)} Agent(s) von {OLD_VALUE} → {args.to}")
    for agent_id, cfg in candidates:
        name = cfg.get("name", "<ohne Namen>")
        print(f"  - {agent_id}  ({name})")
        if args.apply:
            cfg["compact_threshold_pct"] = args.to
            save_atomic(config_path(agent_id), cfg)
    if args.apply:
        print(f"\nFertig. {len(candidates)} Config(s) aktualisiert.")
    else:
        print(f"\nKein Schreibzugriff. --apply um tatsächlich zu schreiben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
