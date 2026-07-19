from __future__ import annotations

import io

from hydrahive_node import cli
from hydrahive_node.storage import AgentIdentity


def test_enroll_cli_prints_identity_but_not_token(tmp_path, monkeypatch, capsys) -> None:
    token = "secret-enrollment-token"
    identity = AgentIdentity(
        server_url="https://hydrahive.test",
        node_id="node-1",
        certificate_fingerprint="ab" * 32,
        certificate_expires_at="2030-01-01T00:00:00Z",
    )
    monkeypatch.setattr(cli, "enroll", lambda **kwargs: identity)
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(token + "\n"))

    result = cli.main(
        [
            "--state-dir",
            str(tmp_path),
            "enroll",
            "--server",
            identity.server_url,
            "--token-stdin",
            "--name",
            "Node One",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert identity.node_id in output
    assert identity.certificate_fingerprint in output
    assert token not in output
