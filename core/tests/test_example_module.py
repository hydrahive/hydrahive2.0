"""Walking-Skeleton-Test: beweist dass das echte example-Modul lädt und migriert."""
from __future__ import annotations


def test_example_module_loads_and_migrates(mod_env):
    import shutil
    from pathlib import Path
    import hydrahive
    repo_root = Path(hydrahive.__file__).resolve().parents[3]
    shutil.copytree(repo_root / "modules" / "example", mod_env / "modules" / "example")
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    from hydrahive.db.connection import db
    load_all()
    assert REGISTRY["example"].loaded is True, REGISTRY["example"].error
    assert REGISTRY["example"].ctx.routers
    with db() as c:
        cols = [r[1] for r in c.execute("PRAGMA table_info(module_example_notes)").fetchall()]
    assert "text" in cols and "id" in cols
