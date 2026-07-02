"""Tests für den Theme-Installer + Manifest + Registry.

Themes sind reines Frontend: EIN Kopierziel (themes_frontend_dir/<id>),
kein Service, keine DB. Geschützte Themes (standard/sidebar/aurora) sind
nicht deinstallierbar.
"""
import pytest


@pytest.fixture
def theme_env(tmp_path, monkeypatch):
    """Isolierte Theme-Umgebung — repointet Frontend-Ziel + Hub-Cache in tmp."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    monkeypatch.setattr(settings, "base_dir", tmp_path / "repo", raising=False)
    monkeypatch.setattr(
        settings, "themes_frontend_dir", tmp_path / "repo" / "frontend" / "src" / "themes",
        raising=False,
    )
    monkeypatch.setattr(settings, "theme_hub_cache", tmp_path / "hub", raising=False)
    (tmp_path / "data").mkdir()
    settings.themes_frontend_dir.mkdir(parents=True)
    return tmp_path


# --- Manifest ---------------------------------------------------------------

def test_manifest_load_ok(tmp_path):
    from hydrahive.themes.manifest import ThemeManifest
    p = tmp_path / "theme.json"
    p.write_text(
        '{"id":"aurora","name":"Aurora","version":"1.0.0",'
        '"layout":"sidebar","variables":{"--hh-r":"0.7rem"}}'
    )
    m = ThemeManifest.load(p)
    assert m.id == "aurora" and m.layout == "sidebar"
    assert m.variables == {"--hh-r": "0.7rem"}


def test_manifest_rejects_bad_id(tmp_path):
    from hydrahive.themes.manifest import ThemeManifest, ManifestError
    p = tmp_path / "theme.json"
    p.write_text('{"id":"../evil","name":"X","version":"1.0.0"}')
    with pytest.raises(ManifestError):
        ThemeManifest.load(p)


def test_manifest_missing_field(tmp_path):
    from hydrahive.themes.manifest import ThemeManifest, ManifestError
    p = tmp_path / "theme.json"
    p.write_text('{"id":"x","name":"X"}')  # version fehlt
    with pytest.raises(ManifestError):
        ThemeManifest.load(p)


def test_manifest_variables_must_be_object(tmp_path):
    from hydrahive.themes.manifest import ThemeManifest, ManifestError
    p = tmp_path / "theme.json"
    p.write_text('{"id":"x","name":"X","version":"1.0.0","variables":[]}')
    with pytest.raises(ManifestError):
        ThemeManifest.load(p)


# --- Installer file-ops -----------------------------------------------------

def test_copy_theme_in(theme_env):
    from unittest.mock import patch
    from hydrahive.settings import settings
    from hydrahive.themes.installer import copy_theme_in

    src = settings.theme_hub_cache / "midnight"
    src.mkdir(parents=True)
    (src / "theme.json").write_text('{"id":"midnight","name":"M","version":"1.0.0"}')
    (src / "theme.css").write_text(":root{}")

    with (patch("hydrahive.themes.installer.refresh"),
          patch("hydrahive.themes.installer._cache_path_for", return_value=src)):
        copy_theme_in("midnight")

    dst = settings.themes_frontend_dir / "midnight"
    assert (dst / "theme.json").exists()
    assert (dst / "theme.css").exists()


def test_remove_theme_files(theme_env):
    from hydrahive.settings import settings
    from hydrahive.themes.installer import remove_theme_files

    d = settings.themes_frontend_dir / "midnight"
    d.mkdir(parents=True)
    (d / "theme.json").write_text("{}")

    remove_theme_files("midnight")
    assert not d.exists()


def test_remove_protected_theme_forbidden(theme_env):
    from hydrahive.themes.installer import remove_theme_files, InstallError
    with pytest.raises(InstallError):
        remove_theme_files("aurora")


def test_copy_rejects_traversal_id(theme_env):
    from hydrahive.themes.installer import copy_theme_in, InstallError
    with pytest.raises(InstallError):
        copy_theme_in("../../etc")


def test_remove_rejects_traversal_id(theme_env):
    from hydrahive.themes.installer import remove_theme_files, InstallError
    with pytest.raises(InstallError):
        remove_theme_files("../../etc")


# --- Registry ---------------------------------------------------------------

def test_list_installed_scans_dir(theme_env):
    from hydrahive.settings import settings
    from hydrahive.themes import registry

    d = settings.themes_frontend_dir / "midnight"
    d.mkdir(parents=True)
    (d / "theme.json").write_text('{"id":"midnight","name":"Midnight","version":"1.2.0"}')

    got = registry.list_installed()
    ids = {t["id"]: t for t in got}
    assert "midnight" in ids
    assert ids["midnight"]["version"] == "1.2.0"
    assert ids["midnight"]["protected"] is False


def test_list_installed_marks_protected(theme_env):
    from hydrahive.settings import settings
    from hydrahive.themes import registry

    d = settings.themes_frontend_dir / "aurora"
    d.mkdir(parents=True)
    (d / "theme.json").write_text('{"id":"aurora","name":"Aurora","version":"1.0.0"}')

    got = {t["id"]: t for t in registry.list_installed()}
    assert got["aurora"]["protected"] is True
