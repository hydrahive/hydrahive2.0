"""Container-Image-Allowlist + incus-Argument-Härtung (Issue #185).

body.image landet als Positional-Arg an einem root-Subprocess (incus launch).
Ohne Validierung kann ein authentifizierter Non-Admin per ':'-haltigem Token
Flags injizieren (--target/--project/--profile). Fix: Allowlist-Regex + '--'.
"""
from __future__ import annotations

import asyncio
import re

import pytest

from hydrahive.containers.models import IMAGE_RE


@pytest.mark.parametrize("img", [
    "ubuntu/22.04", "ubuntu/24.04", "debian/12", "alpine/3.21",
    "archlinux", "centos/9-Stream",
    "images:debian/12", "ubuntu:22.04", "local:my-image",
])
def test_image_re_accepts_valid(img):
    assert re.match(IMAGE_RE, img), f"{img!r} sollte erlaubt sein"


@pytest.mark.parametrize("img", [
    "--target=remote-cluster:ubuntu/22.04",  # Flag-Injection (Kern des Befunds)
    "-foo",
    "--project=other",
    " leadingspace",
    "img with space",
    "img;rm -rf",
    "../../etc/passwd",
    ":noremote",
])
def test_image_re_rejects_malicious(img):
    assert not re.match(IMAGE_RE, img), f"{img!r} sollte abgelehnt werden"


def test_create_container_rejects_malicious_image(client, admin_headers):
    r = client.post("/api/containers", headers=admin_headers, json={
        "name": "validname", "image": "--target=evil:ubuntu",
        "cpu": 1, "ram_mb": 512, "network_mode": "bridged",
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "container_image_invalid"


def test_launch_uses_double_dash_separator(monkeypatch):
    from hydrahive.containers import incus_client as incus

    calls: list[list[str]] = []

    async def fake_run(*args, timeout=None):
        calls.append(list(args))
        return (0, "", "")

    monkeypatch.setattr(incus, "_run", fake_run)
    asyncio.run(incus.launch("myctr", "images:ubuntu", cpu=2, ram_mb=512,
                             network_mode="isolated"))

    launch_call = next(c for c in calls if c and c[0] == "launch")
    assert "--" in launch_call, "'--' Separator fehlt vor den Positional-Args"
    di = launch_call.index("--")
    assert launch_call[di + 1:] == ["images:ubuntu", "myctr"]
    assert "-c" in launch_call[:di], "-c-Optionen müssen VOR dem -- stehen"
