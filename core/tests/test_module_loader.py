"""Tests für hydrahive.modules.loader (load_all).

_make_module ist eine wiederverwendbare Hilfsfunktion — sie wird auch von
Task 6 (Install/Uninstall) importiert.
"""
from __future__ import annotations
from pathlib import Path


def _make_module(modules_dir: Path, mid: str) -> Path:
    """Legt ein minimales, valides Modul-Verzeichnis an."""
    md = modules_dir / mid
    (md / "backend").mkdir(parents=True)
    (md / "migrations").mkdir()
    (md / "manifest.json").write_text('{"id":"%s","name":"X","version":"1.0.0"}' % mid)
    (md / "migrations" / "001_t.sql").write_text(
        f"CREATE TABLE module_{mid}_t (id INTEGER);"
    )
    (md / "backend" / "__init__.py").write_text(
        "from fastapi import APIRouter\n"
        "def register(ctx):\n"
        "    r=APIRouter()\n"
        "    @r.get('/ping')\n"
        "    def ping(): return {'ok': True}\n"
        "    ctx.register_router(r)\n"
        "    ctx.register_migrations('migrations')\n"
    )
    return md


def test_load_all_loads_module_and_migrations(mod_env):
    from hydrahive.db.connection import db
    _make_module(mod_env / "modules", "alpha")   # == settings.modules_dir
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all()
    assert REGISTRY["alpha"].loaded is True
    assert REGISTRY["alpha"].ctx.routers
    with db() as c:
        count = c.execute(
            "SELECT COUNT(*) FROM module_schema_version WHERE module_id='alpha'"
        ).fetchone()[0]
    assert count == 1


def test_load_all_isolates_broken_module(mod_env):
    _make_module(mod_env / "modules", "good")
    bad = mod_env / "modules" / "bad"
    (bad / "backend").mkdir(parents=True)
    (bad / "manifest.json").write_text('{"id":"bad","name":"B","version":"1"}')
    (bad / "backend" / "__init__.py").write_text("raise RuntimeError('boom')\n")
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all()
    assert REGISTRY["good"].loaded is True
    assert REGISTRY["bad"].loaded is False and REGISTRY["bad"].error


def test_load_all_module_without_register(mod_env):
    md = mod_env / "modules" / "noreg"; (md / "backend").mkdir(parents=True)
    (md / "manifest.json").write_text('{"id":"noreg","name":"N","version":"1.0.0"}')
    (md / "backend" / "__init__.py").write_text("x = 1\n")  # kein register
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all()
    assert REGISTRY["noreg"].loaded is False
    assert "register" in (REGISTRY["noreg"].error or "")


def test_load_all_idempotent_rerun(mod_env):
    from hydrahive.db.connection import db
    _make_module(mod_env / "modules", "beta")
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all(); load_all()
    assert "beta" in REGISTRY and REGISTRY["beta"].loaded is True
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_schema_version WHERE module_id='beta'").fetchone()[0] == 1
