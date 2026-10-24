"""docs/specs/modul-update-alle.md: „Alle updaten“ – alle Module ersetzen, EINMAL bauen, EINMAL neu starten.
Anlass (Task b74c972d): Die alte Schleife im Browser baute und startete je Modul neu; der Neustart riss das nächste
Update ab (502), nur ein Teil kam an."""
from __future__ import annotations

import json
import subprocess
from contextlib import contextmanager
from unittest.mock import patch

import pytest

INSTALLED = {"alpha": "1.0.0", "beta": "2.0.0", "gamma": "0.1.0", "delta": "3.0.0"}
HUB = {"alpha": "1.0.1", "beta": "2.0.0", "gamma": "0.2.0", "delta": "3.1.0", "neu": "1.0.0"}


def _write_installed(mod_env, versions=INSTALLED, service=()):
    for mid, ver in versions.items():
        d = mod_env / "modules" / mid
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.json").write_text(json.dumps({"id": mid, "name": mid, "version": ver, "has_service": mid in service}))


@contextmanager
def _env(mod_env, *, fail=None, service=(), build_error=None, hub=HUB):
    """Installer-Bausteine durch Attrappen ersetzen; `calls` hält die Reihenfolge fest."""
    _write_installed(mod_env, service=service)
    calls: list[str] = []

    def replace(mid):
        calls.append(f"replace:{mid}")
        if fail and mid in fail:
            raise fail[mid]
        (mod_env / "modules" / mid / "manifest.json").write_text(json.dumps({"id": mid, "name": mid, "version": hub[mid]}))

    def build():
        calls.append("build")
        if build_error:
            raise build_error

    with (patch("hydrahive.modules.installer.refresh", side_effect=lambda: calls.append("refresh")),
          patch("hydrahive.modules.installer.available_version", side_effect=lambda mid: hub.get(mid)),
          patch("hydrahive.modules.installer._ensure_dependencies", side_effect=lambda mid, seen: iter(())),
          patch("hydrahive.modules.installer.replace_module_in", side_effect=replace),
          patch("hydrahive.modules.installer._manifest_has_service", side_effect=lambda mid: mid in service),
          patch("hydrahive.modules.installer._run_service_script", side_effect=lambda mid, s: calls.append(f"{s}:{mid}")),
          patch("hydrahive.modules.installer._frontend_build", side_effect=build),
          patch("hydrahive.modules.installer._request_restart", side_effect=lambda: calls.append("restart"))):
        yield calls


def _run():
    from hydrahive.modules.installer import update_all
    return list(update_all())


def test_alle_mit_update_einmal_bauen_einmal_neustart(mod_env):
    with _env(mod_env) as calls:
        lines = _run()
    assert calls == ["refresh", "replace:alpha", "replace:delta", "replace:gamma", "build", "restart"]
    assert any("alpha: fertig (1.0.0 → 1.0.1)" in l for l in lines)
    assert any("delta: fertig (3.0.0 → 3.1.0)" in l for l in lines)
    assert lines[-1] == "[modules] Fertig: 3 aktualisiert, 0 fehlgeschlagen"


def test_nur_module_mit_update_nicht_installierte_bleiben_unberuehrt(mod_env):
    with _env(mod_env) as calls:
        _run()
    assert "replace:beta" not in calls
    assert "replace:neu" not in calls


def test_ein_fehler_stoppt_die_anderen_nicht(mod_env):
    err = PermissionError(13, "Permission denied", "/var/lib/hydrahive2/modules/delta")
    with _env(mod_env, fail={"delta": err}) as calls:
        lines = _run()
    assert calls == ["refresh", "replace:alpha", "replace:delta", "replace:gamma", "build", "restart"]
    assert any(l.startswith("[modules] delta: FEHLER") and "Permission denied" in l for l in lines)
    assert lines[-2] == "[modules] Fertig: 2 aktualisiert, 1 fehlgeschlagen"
    assert lines[-1].startswith("[modules] Fehlgeschlagen: delta (") and "Permission denied" in lines[-1]


@pytest.mark.parametrize("exc", [
    PermissionError(13, "Permission denied"),
    OSError(28, "No space left on device"),
    subprocess.CalledProcessError(1, ["bash", "install.sh"]),
])
def test_fehlerarten_werden_aufgefangen(mod_env, exc):
    with _env(mod_env, fail={"alpha": exc}) as calls:
        lines = _run()
    assert "replace:gamma" in calls and calls[-2:] == ["build", "restart"]
    assert any(l.startswith("[modules] alpha: FEHLER") for l in lines)


def test_install_error_wird_aufgefangen(mod_env):
    from hydrahive.modules.installer import InstallError
    with _env(mod_env, fail={"gamma": InstallError("module_not_in_hub:gamma")}) as calls:
        lines = _run()
    assert calls[-2:] == ["build", "restart"]
    assert any("gamma: FEHLER" in l and "module_not_in_hub" in l for l in lines)


def test_nichts_zu_tun_kein_build_kein_neustart(mod_env):
    with _env(mod_env, hub=dict(INSTALLED)) as calls:
        lines = _run()
    assert calls == ["refresh"]
    assert lines == ["[modules] Alle Module sind aktuell"]


def test_alle_scheitern_kein_build_kein_neustart_und_fehler(mod_env):
    from hydrahive.modules.installer import InstallError
    fail = {m: PermissionError(13, "Permission denied") for m in ("alpha", "delta", "gamma")}
    with _env(mod_env, fail=fail) as calls:
        with pytest.raises(InstallError) as info:
            _run()
    assert "build" not in calls and "restart" not in calls
    assert str(info.value).startswith("module_update_all_failed")
    assert all(m in str(info.value) for m in ("alpha", "delta", "gamma"))


def test_build_fehler_kein_neustart(mod_env):
    with _env(mod_env, build_error=subprocess.CalledProcessError(1, ["npm", "run", "build"])) as calls:
        with pytest.raises(subprocess.CalledProcessError):
            _run()
    assert calls[-1] == "build"
    assert "restart" not in calls


def test_dienst_module_werden_gestoppt_und_gestartet(mod_env):
    with _env(mod_env, service=("gamma",)) as calls:
        _run()
    i = calls.index("replace:gamma")
    assert calls[i - 1] == "uninstall.sh:gamma"
    assert calls[i + 1] == "install.sh:gamma"
    assert "uninstall.sh:alpha" not in calls


def test_abhaengigkeiten_je_modul_sichergestellt(mod_env):
    seen: list[str] = []
    with _env(mod_env):
        with patch("hydrahive.modules.installer._ensure_dependencies", side_effect=lambda mid, s: (seen.append(mid), iter(()))[1]):
            _run()
    assert seen == ["alpha", "delta", "gamma"]


def test_ungueltige_modulordner_werden_ignoriert(mod_env):
    (mod_env / "modules" / ".alpha-update-xyz").mkdir()
    (mod_env / "modules" / "kaputt").mkdir()
    (mod_env / "modules" / "kaputt" / "manifest.json").write_text("{nicht json")
    with _env(mod_env) as calls:
        _run()
    assert [c for c in calls if c.startswith("replace:")] == ["replace:alpha", "replace:delta", "replace:gamma"]
