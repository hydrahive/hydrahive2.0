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


def test_copy_module_in_rejects_traversal_id(mod_env):
    import pytest
    from hydrahive.modules.installer import copy_module_in, InstallError
    with pytest.raises(InstallError):
        copy_module_in("../../etc")


def test_remove_module_files_rejects_traversal_id(mod_env):
    import pytest
    from hydrahive.modules.installer import remove_module_files, InstallError
    with pytest.raises(InstallError):
        remove_module_files("../../etc")


# --- Update-Erkennung (Option A: Versionsvergleich) ------------------------

def test_is_update_available_semver():
    from hydrahive.modules.installer import is_update_available
    assert is_update_available("1.0.0", "1.1.0") is True
    assert is_update_available("1.0.0", "2.0.0") is True
    assert is_update_available("1.2.0", "1.10.0") is True   # echtes Semver, nicht String
    assert is_update_available("1.1.0", "1.1.0") is False
    assert is_update_available("2.0.0", "1.0.0") is False   # installiert neuer


def test_is_update_available_missing_versions():
    from hydrahive.modules.installer import is_update_available
    assert is_update_available(None, "1.0.0") is False
    assert is_update_available("1.0.0", None) is False
    assert is_update_available(None, None) is False


def test_is_update_available_non_semver_fallback():
    from hydrahive.modules.installer import is_update_available
    # Nicht-parsebare Versionen → String-Ungleichheit (konservativ Update anbieten)
    assert is_update_available("2024-01", "2024-02") is True
    assert is_update_available("foo", "foo") is False


def test_available_version_reads_hub_cache_manifest(mod_env):
    from unittest.mock import patch
    src = mod_env / "hub" / "example"
    src.mkdir(parents=True)
    (src / "manifest.json").write_text('{"id":"example","name":"X","version":"1.3.0"}')
    with patch("hydrahive.modules.installer._cache_path_for", return_value=src):
        from hydrahive.modules.installer import available_version
        assert available_version("example") == "1.3.0"


def test_available_version_missing_manifest_returns_none(mod_env):
    from unittest.mock import patch
    src = mod_env / "hub" / "gone"
    src.mkdir(parents=True)  # kein manifest.json
    with patch("hydrahive.modules.installer._cache_path_for", return_value=src):
        from hydrahive.modules.installer import available_version
        assert available_version("gone") is None


def test_available_version_not_in_hub_returns_none(mod_env):
    # _cache_path_for wirft InstallError, wenn das Modul nicht im Hub steht
    from hydrahive.modules.installer import available_version
    from unittest.mock import patch
    with patch("hydrahive.modules.installer.hub_client.read_hub_index",
               return_value={"modules": []}):
        assert available_version("unknown") is None


def test_available_description_reads_hub_cache_manifest(mod_env):
    from unittest.mock import patch
    src = mod_env / "hub" / "demo"
    src.mkdir(parents=True)
    (src / "manifest.json").write_text(
        '{"id":"demo","name":"Demo","version":"1.0.0","description":"Zwei Sätze. Test."}'
    )
    with patch("hydrahive.modules.installer._cache_path_for", return_value=src):
        from hydrahive.modules.installer import available_description
        assert available_description("demo") == "Zwei Sätze. Test."


def test_available_description_missing_returns_empty(mod_env):
    from unittest.mock import patch
    src = mod_env / "hub" / "nodesc"
    src.mkdir(parents=True)
    (src / "manifest.json").write_text('{"id":"nodesc","name":"X","version":"1.0.0"}')
    with patch("hydrahive.modules.installer._cache_path_for", return_value=src):
        from hydrahive.modules.installer import available_description
        assert available_description("nodesc") == ""
