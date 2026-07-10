"""Tests für hydrahive.modules.loader (load_all)."""
from __future__ import annotations


def test_load_all_loads_module_and_migrations(mod_env, make_module):
    from hydrahive.db.connection import db
    make_module(mod_env / "modules", "alpha")   # == settings.modules_dir
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


def test_load_all_isolates_broken_module(mod_env, make_module):
    make_module(mod_env / "modules", "good")
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


def test_load_all_idempotent_rerun(mod_env, make_module):
    from hydrahive.db.connection import db
    make_module(mod_env / "modules", "beta")
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all(); load_all()
    assert "beta" in REGISTRY and REGISTRY["beta"].loaded is True
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_schema_version WHERE module_id='beta'").fetchone()[0] == 1


def test_ensure_required_bundled_modules_installs_missing_task(mod_env, make_module):
    from hydrahive.modules.loader import ensure_required_bundled_modules

    make_module(mod_env / "repo" / "modules", "tasks")
    ensure_required_bundled_modules()

    assert (mod_env / "modules" / "tasks" / "manifest.json").is_file()
    assert (mod_env / "modules" / "tasks" / "backend" / "__init__.py").is_file()


def test_ensure_required_bundled_modules_repairs_broken_task_dir(mod_env, make_module):
    from hydrahive.modules.loader import ensure_required_bundled_modules

    make_module(mod_env / "repo" / "modules", "tasks")
    broken = mod_env / "modules" / "tasks"
    broken.mkdir(parents=True)
    (broken / "stale.txt").write_text("broken")

    ensure_required_bundled_modules()

    assert not (broken / "stale.txt").exists()
    assert (broken / "manifest.json").is_file()


def test_ensure_required_bundled_modules_does_not_overwrite_installed_task(mod_env, make_module):
    from hydrahive.modules.loader import ensure_required_bundled_modules

    make_module(mod_env / "repo" / "modules", "tasks")
    installed = make_module(mod_env / "modules", "tasks")
    marker = installed / "custom.txt"
    marker.write_text("keep")

    ensure_required_bundled_modules()

    assert marker.read_text() == "keep"
