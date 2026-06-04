"""Tests für Module-Installer-Dateioperationen (Task 8).

Nur file-ops: copy_module_in / remove_module_files.
Orchestrierung (build, restart, service) ist Task 11 — nicht hier.
"""
from unittest.mock import patch


def test_install_copies_backend_and_frontend(mod_env):
    from hydrahive.settings import settings

    src = settings.module_hub_cache / "example"     # Hub-Cache-Quelle
    (src / "backend").mkdir(parents=True)
    (src / "frontend").mkdir(parents=True)
    (src / "manifest.json").write_text('{"id":"example","name":"X","version":"1.0.0"}')
    (src / "backend" / "__init__.py").write_text("def register(ctx): pass\n")
    (src / "frontend" / "index.tsx").write_text("export const routes=[]\n")
    (settings.base_dir / "frontend" / "src" / "modules").mkdir(parents=True)

    with (patch("hydrahive.modules.installer.refresh"),
          patch("hydrahive.modules.installer._cache_path_for", return_value=src)):
        from hydrahive.modules.installer import copy_module_in
        copy_module_in("example")

    assert (settings.modules_dir / "example" / "backend" / "__init__.py").exists()
    assert (settings.base_dir / "frontend" / "src" / "modules" / "example" / "index.tsx").exists()


def test_remove_module_keeps_no_data_touch(mod_env):
    from hydrahive.settings import settings

    md = settings.modules_dir / "example"
    md.mkdir(parents=True)
    (md / "x").write_text("y")

    fe = settings.base_dir / "frontend" / "src" / "modules" / "example"
    fe.mkdir(parents=True)
    (fe / "i").write_text("z")

    from hydrahive.modules.installer import remove_module_files
    remove_module_files("example")

    assert not md.exists() and not fe.exists()
