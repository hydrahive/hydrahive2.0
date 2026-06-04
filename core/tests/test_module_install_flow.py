"""Tests für Modul-Orchestrierung: install / uninstall Generators (Task 11)."""
from unittest.mock import patch


def test_install_flow_calls_steps(mod_env):
    with (patch("hydrahive.modules.installer.copy_module_in") as cp,
          patch("hydrahive.modules.installer._run_service_script") as svc,
          patch("hydrahive.modules.installer._frontend_build") as build,
          patch("hydrahive.modules.installer._request_restart") as restart,
          patch("hydrahive.modules.installer._manifest_has_service", return_value=False)):
        from hydrahive.modules.installer import install
        list(install("example"))   # Generator (Log-Zeilen)
    cp.assert_called_once_with("example")
    build.assert_called_once()
    restart.assert_called_once()
    svc.assert_not_called()


def test_uninstall_keeps_data(mod_env):
    with (patch("hydrahive.modules.installer.remove_module_files") as rm,
          patch("hydrahive.modules.installer._run_service_script") as svc,
          patch("hydrahive.modules.installer._frontend_build"),
          patch("hydrahive.modules.installer._request_restart"),
          patch("hydrahive.modules.installer._manifest_has_service", return_value=False)):
        from hydrahive.modules.installer import uninstall
        list(uninstall("example"))
    rm.assert_called_once_with("example")
    # KEIN drop-table-Aufruf existiert — Daten bleiben per Design.
