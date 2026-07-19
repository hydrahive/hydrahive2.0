"""Persistent mTLS WebSocket runtime for read-only node reports."""

from __future__ import annotations

import asyncio
import json
import random
import secrets
import ssl
from datetime import UTC, datetime

import websockets

from hydrahive_node import __version__
from hydrahive_node.capabilities import collect
from hydrahive_node.storage import AgentIdentity, StatePaths, next_sequence

HEARTBEAT_SECONDS = 30.0
MAX_MESSAGE_BYTES = 64 * 1024


def _websocket_url(server_url: str) -> str:
    return server_url.replace("https://", "wss://", 1).rstrip("/") + "/api/compute/agent/connect"


def _ssl_context(paths: StatePaths) -> ssl.SSLContext:
    if paths.server_ca_certificate.is_file():
        context = ssl.create_default_context(cafile=str(paths.server_ca_certificate))
    else:
        context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(str(paths.certificate), str(paths.private_key))
    return context


def _message(
    paths: StatePaths,
    identity: AgentIdentity,
    message_type: str,
    payload: dict[str, object],
) -> tuple[int, str]:
    sequence = next_sequence(paths)
    message = {
        "type": message_type,
        "protocol_version": identity.protocol_version,
        "node_id": identity.node_id,
        "sequence": sequence,
        "nonce": secrets.token_urlsafe(24),
        "sent_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }
    encoded = json.dumps(message, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise RuntimeError("agent message exceeds protocol limit")
    return sequence, encoded


async def _send(websocket, paths: StatePaths, identity: AgentIdentity, message_type: str, payload: dict) -> None:
    sequence, encoded = _message(paths, identity, message_type, payload)
    await websocket.send(encoded)
    raw = await asyncio.wait_for(websocket.recv(), timeout=20.0)
    acknowledgement = json.loads(raw)
    if acknowledgement.get("type") != "ack" or acknowledgement.get("sequence") != sequence:
        raise RuntimeError("invalid acknowledgement from control plane")


async def _run_session(paths: StatePaths, identity: AgentIdentity) -> None:
    async with websockets.connect(
        _websocket_url(identity.server_url),
        ssl=_ssl_context(paths),
        additional_headers={"X-HydraHive-Node-ID": identity.node_id},
        proxy=None,
        compression=None,
        max_size=MAX_MESSAGE_BYTES,
        open_timeout=20.0,
    ) as websocket:
        await _send(websocket, paths, identity, "hello", {"agent_version": __version__})
        capabilities, resources, health_errors = collect()
        await _send(
            websocket,
            paths,
            identity,
            "capabilities",
            {"capabilities": capabilities, "resources": resources},
        )
        while True:
            capabilities, resources, health_errors = collect()
            await _send(
                websocket,
                paths,
                identity,
                "heartbeat",
                {
                    "capabilities": capabilities,
                    "resources": resources,
                    "health_errors": health_errors,
                },
            )
            await asyncio.sleep(HEARTBEAT_SECONDS)


async def run(paths: StatePaths, identity: AgentIdentity) -> None:
    delay = 1.0
    while True:
        try:
            await _run_session(paths, identity)
            delay = 1.0
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(delay + random.uniform(0, min(delay, 5.0)))
            delay = min(delay * 2, 30.0)


def run_forever(paths: StatePaths, identity: AgentIdentity) -> None:
    asyncio.run(run(paths, identity))
