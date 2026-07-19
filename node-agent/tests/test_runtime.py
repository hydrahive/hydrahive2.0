from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from hydrahive_node import capabilities, runtime
from hydrahive_node.storage import AgentIdentity, StatePaths


def _identity() -> AgentIdentity:
    return AgentIdentity(
        server_url="https://hydrahive.test",
        node_id="node-1",
        certificate_fingerprint="ab" * 32,
        certificate_expires_at="2030-01-01T00:00:00Z",
    )


def test_protocol_messages_have_persistent_sequence_and_fresh_nonce(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)

    first_sequence, first_raw = runtime._message(paths, _identity(), "hello", {"agent_version": "0.1.0"})
    second_sequence, second_raw = runtime._message(paths, _identity(), "heartbeat", {"resources": {}})
    first = json.loads(first_raw)
    second = json.loads(second_raw)

    assert (first_sequence, second_sequence) == (1, 2)
    assert first["node_id"] == "node-1"
    assert first["nonce"] != second["nonce"]
    assert os.stat(paths.protocol_state).st_mode & 0o777 == 0o600


def test_protocol_sequence_is_process_safe(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")
    paths.directory.mkdir(mode=0o700)
    with ThreadPoolExecutor(max_workers=8) as executor:
        sequences = list(executor.map(lambda _: runtime._message(paths, _identity(), "heartbeat", {})[0], range(20)))

    assert sorted(sequences) == list(range(1, 21))


def test_capability_collection_is_bounded_and_typed() -> None:
    reported, resources, errors = capabilities.collect()

    assert isinstance(reported["hostname"], str)
    assert len(reported["hostname"]) <= 255
    assert isinstance(reported["instance_types"], list)
    assert isinstance(resources["cpu_cores"], int)
    assert isinstance(resources["memory_total_bytes"], int)
    assert all(isinstance(error, str) for error in errors)
