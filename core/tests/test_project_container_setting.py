"""docs/specs/projekt-container-ausfuehrung.md (K1a): Projekt-Einstellung execution – setzen, prüfen, fail-closed."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

# --- Projekt-Einstellung -----------------------------------------------------------------------------------------

def _project(client, admin_headers) -> str:
    r = client.post("/api/projects", headers=admin_headers, json={"name": "Labor-Probe", "llm_model": "test/model"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture
def known_container(monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: name == "hh-labor-probe")


def test_ohne_einstellung_ist_es_der_server(client, admin_headers):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    assert execution.of(project_config.get(pid)) == {"mode": "host"}
    assert execution.of(None) == {"mode": "host"}


def test_container_setzen_ueber_kern_funktion(client, admin_headers, known_container):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    execution.set_container(pid, "hh-labor-probe", actor="admin")
    assert execution.of(project_config.get(pid)) == {"mode": "container", "container": "hh-labor-probe",
                                                     "workdir": "/work", "user": 1000}


@pytest.mark.parametrize("name", ["", "Grossbuchstabe", "1start", "a", "x;rm -rf /", "a b", "../x", "a" * 64,
                                  "-flag", "--project=evil"])
def test_ungueltiger_containername(client, admin_headers, name, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda n: True)
    pid = _project(client, admin_headers)
    with pytest.raises(execution.ExecutionError) as e:
        execution.set_container(pid, name, actor="admin")
    assert e.value.code == "project_container_invalid"


def test_unbekannter_container(client, admin_headers, known_container):
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    with pytest.raises(execution.ExecutionError) as e:
        execution.set_container(pid, "hh-gibt-es-nicht", actor="admin")
    assert e.value.code == "project_container_missing"


@pytest.mark.parametrize(("workdir", "user"), [("relativ", 1000), ("/", 1000), ("/work/../etc", 1000),
                                               ("/work", 0), ("/work", -1), ("/work", "1000"), ("/work", True),
                                               ("/work", 65536)])
def test_ungueltiges_arbeitsverzeichnis_oder_nutzer(client, admin_headers, known_container, workdir, user):
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    with pytest.raises(execution.ExecutionError) as e:
        execution.set_container(pid, "hh-labor-probe", actor="admin", workdir=workdir, user=user)
    assert e.value.code == "project_container_invalid"


def test_patch_route_kann_execution_nicht_setzen(client, admin_headers):
    """Nur über die Kern-Funktion bzw. die eigene Admin-Route – nicht nebenbei über das normale PATCH."""
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    client.patch(f"/api/projects/{pid}", headers=admin_headers,
                 json={"execution": {"mode": "container", "container": "hh-labor-probe"}})
    assert execution.of(project_config.get(pid)) == {"mode": "host"}


def test_config_update_kann_execution_nicht_setzen(client, admin_headers):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    project_config.update(pid, execution={"mode": "container", "container": "hh-labor-probe"})
    assert execution.of(project_config.get(pid)) == {"mode": "host"}


def test_zurueck_auf_server_nur_ausdruecklich(client, admin_headers, known_container):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    pid = _project(client, admin_headers)
    execution.set_container(pid, "hh-labor-probe", actor="admin")
    with pytest.raises(execution.ExecutionError):
        execution.set_host(pid, actor="admin", confirm="")
    assert execution.of(project_config.get(pid))["mode"] == "container"
    with pytest.raises(execution.ExecutionError):
        execution.set_host(pid, actor="admin", confirm="Labor-Prob")
    with pytest.raises(execution.ExecutionError):
        execution.set_host(pid, actor="admin", confirm="ja")
    assert execution.of(project_config.get(pid))["mode"] == "container"
    execution.set_host(pid, actor="admin", confirm="Labor-Probe")
    assert execution.of(project_config.get(pid)) == {"mode": "host"}


def test_kaputter_eintrag_gilt_nicht_als_server(client, admin_headers):
    """Ein beschädigtes execution-Feld darf NIE still auf den Server zurückfallen."""
    from hydrahive.projects import execution
    for broken in ({"mode": "container"}, {"mode": "weird"}, {"mode": "container", "container": "X;y"}, "container",
                   {"mode": "container", "container": "hh-ok", "workdir": "/"}):
        with pytest.raises(execution.ExecutionError):
            execution.of({"id": "p", "execution": broken})


