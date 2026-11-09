"""CLI: python -m hydrahive.harness_bench run|compare …

Beispiel:
  python -m hydrahive.harness_bench run --owner till --model openai-codex/gpt-5.6-sol --attempts 3 --out baseline.json
  python -m hydrahive.harness_bench compare baseline.json nachher.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path


def _bootstrap() -> None:
    """Nur was der Runner braucht: DB, Plugins, Module und deren Werkzeuge. Keine API, keine Jobs."""
    import dataclasses

    from hydrahive import modules as module_system
    from hydrahive.db import init_db
    from hydrahive.modules.registry import REGISTRY
    from hydrahive.plugins import loader as plugin_loader
    from hydrahive.tools import register_module_tools

    init_db()
    plugin_loader.load_all()
    module_system.load_all()
    register_module_tools([
        dataclasses.replace(t, module_id=m.manifest.id)
        for m in REGISTRY.values() if m.loaded and m.ctx and m.manifest for t in m.ctx.tools
    ])


def main() -> None:
    parser = argparse.ArgumentParser(prog="harness_bench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--owner", required=True)
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--attempts", type=int, default=3)
    run_p.add_argument("--only", nargs="*")
    run_p.add_argument("--out", type=Path, required=True)
    cmp_p = sub.add_parser("compare")
    cmp_p.add_argument("before", type=Path)
    cmp_p.add_argument("after", type=Path)
    args = parser.parse_args()

    from hydrahive.harness_bench.report import compare, markdown, summarize

    if args.cmd == "run":
        _bootstrap()
        from hydrahive.harness_bench.runner import run_bench
        results = asyncio.run(run_bench(owner=args.owner, model=args.model, attempts=args.attempts, only=args.only))
        args.out.write_text(json.dumps({"model": args.model, "results": results}, indent=2, ensure_ascii=False))
        print(markdown(summarize(results), title=f"Benchmark {args.model}"))
    else:
        before = summarize(json.loads(args.before.read_text())["results"])
        after = summarize(json.loads(args.after.read_text())["results"])
        print(compare(before, after))


if __name__ == "__main__":
    main()
