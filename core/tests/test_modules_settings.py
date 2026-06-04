"""Tests für Module-System-Settings-Pfade (Task 1: modules_dir + Hub)."""


def test_modules_dir_under_data_dir(monkeypatch, tmp_path):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    monkeypatch.delattr(settings, "modules_dir", raising=False)  # ggf. gecachten cached_property-Wert entfernen
    assert settings.modules_dir == tmp_path / "modules"


def test_module_hub_git_url_is_set():
    from hydrahive.settings import settings
    assert isinstance(settings.module_hub_git_url, str) and settings.module_hub_git_url
