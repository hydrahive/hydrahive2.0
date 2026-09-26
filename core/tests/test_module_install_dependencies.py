"""Modulabhängigkeiten werden vor dem abhängigen Modul installiert."""
from unittest.mock import patch


def test_install_installs_missing_dependencies(mod_env):
    from hydrahive.modules import installer

    with (
        patch.object(
            installer, "_dependencies",
            side_effect=lambda mid: ("videoeditor",) if mid == "atelier" else (),
        ),
        patch.object(installer, "copy_module_in"),
        patch.object(installer, "_frontend_build"),
        patch.object(installer, "_request_restart"),
        patch.object(installer, "_manifest_has_service", return_value=False),
    ):
        lines = list(installer.install("atelier"))

    assert any("Abhängigkeit videoeditor" in line for line in lines)
    assert any("installiere videoeditor" in line for line in lines)
    assert any("installiere atelier" in line for line in lines)
