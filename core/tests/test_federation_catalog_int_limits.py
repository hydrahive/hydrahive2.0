"""Security-Review #742: Ganzzahlen über dem SQLite-Bereich (2**63) sind ungültige
Felder (400 bzw. 404), kein Absturz mit 500. Gilt für Push, Pull und Anstupsen."""
from __future__ import annotations

from tests.test_federation_catalog_push_hub import _code, _push, _send, hub  # noqa: F401 - hub ist Fixture


def test_riesige_seq_und_intervall_beim_push(client, hub):  # noqa: F811
    fp, _peer = hub
    r = _send(client, fp, _push(2**63))
    assert r.status_code == 400 and _code(r) == "peer_payload_invalid"
    r = _send(client, fp, _push(1, interval_seconds=2**70))
    assert r.status_code == 200                                       # Intervall wird verworfen
