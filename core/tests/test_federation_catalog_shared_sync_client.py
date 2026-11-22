"""V1 — catalog_sync meldet die eigenen Schalter shared/remote_edits in jedem
Push (docs/specs/federation-shared-tasks.md §Schalter). Gegen den gefälschten
Hub aus _catalog_sync_env (echte Hub-Annahme aus S1 dahinter).
"""
from __future__ import annotations

from hydrahive.federation import catalog_sync
from tests._catalog_fakes import hub_rows
from tests._catalog_sync_env import T0

pytest_plugins = ["tests._catalog_sync_env"]


def _put_settings(client, admin_headers, **over):
    from tests.test_federation_catalog_e1 import _settings_body

    return client.put(
        "/api/federation/catalog/settings", headers=admin_headers,
        json=_settings_body(excluded_projects=["proj-geheim"], **over),
    )


async def test_sync_meldet_shared_und_remote_edits_aus_den_einstellungen(env, client, admin_headers):
    r = _put_settings(client, admin_headers, shared=True, remote_edits=True)
    assert r.status_code == 200, r.text

    env["tasks"].put("t-1", T0)
    assert await catalog_sync.sync() == "ok"

    assert env["hub"].sent
    assert env["hub"].sent[-1]["shared"] is True
    assert env["hub"].sent[-1]["remote_edits"] is True

    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute(
            "SELECT shared, remote_edits FROM federation_catalog_sources WHERE peer_id = ?",
            (env["peer"]["id"],),
        ).fetchone()
    assert dict(row) == {"shared": 1, "remote_edits": 1}


async def test_sync_meldet_defaults_ohne_einstellung(env):
    env["tasks"].put("t-2", T0)
    assert await catalog_sync.sync() == "ok"
    assert env["hub"].sent[-1]["shared"] is False
    assert env["hub"].sent[-1]["remote_edits"] is False
