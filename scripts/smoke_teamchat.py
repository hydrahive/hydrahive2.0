#!/usr/bin/env python3
"""Manueller Smoke-Test der Team-Chat-Kette gegen einen LAUFENDEN tuwunel.

Beweist end-to-end (echter Homeserver, KEINE Mocks): Account-Provisioning (UIAA-
Register), Idempotenz, Raum-Erstellung, Senden, History, Mitglieder und den
Membership-Security-Gate.

Eigenständig: setzt eine isolierte Wegwerf-Umgebung (tmp-DB, Wegwerf-secret_key),
liest server_name + registration_token aus der vom tuwunel-Installer geschriebenen
Datei. Legt Test-Accounts (smoke_*) + einen Raum auf dem echten Homeserver an
(harmlose Testdaten auf dem lokalen Homeserver).

Lauf auf dem tuwunel-Host, im HH2-venv:
    <hh2-venv>/bin/python scripts/smoke_teamchat.py
"""
import asyncio
import os
import tempfile

# --- isolierte Smoke-Umgebung (unabhängig vom Backend-Service) ---------------
os.environ["HH_DATA_DIR"] = tempfile.mkdtemp(prefix="teamchat-smoke-")
os.environ["HH_TEAMCHAT_ENABLED"] = "1"
os.environ.setdefault("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
# Wegwerf-Secret: nur für DIESEN Lauf konsistent (leitet das deterministische
# Matrix-Passwort ab). Nicht der echte Backend-HH_SECRET_KEY — egal für den Test.
os.environ.setdefault("HH_SECRET_KEY", "smoke-test-secret-konsistent")

# server_name + registration_token aus der Installer-Datei (Pfad robust suchen)
_matrix_dir = None
for _d in ("/etc/hydrahive2/matrix", "/etc/hydrahive/matrix"):
    if os.path.exists(os.path.join(_d, "server_name")):
        _matrix_dir = _d
        break
if not _matrix_dir:
    raise SystemExit(
        "FEHLER: keine matrix/server_name-Datei gefunden — ist die tuwunel-Extension installiert?"
    )
os.environ["HH_MATRIX_SERVER_NAME"] = open(f"{_matrix_dir}/server_name").read().strip()
os.environ["HH_MATRIX_REGISTRATION_TOKEN"] = open(f"{_matrix_dir}/registration_token").read().strip()
print(
    f"[smoke] homeserver={os.environ['HH_MATRIX_HOMESERVER_URL']} "
    f"server_name={os.environ['HH_MATRIX_SERVER_NAME']} (config-dir: {_matrix_dir})"
)

from hydrahive.db.connection import init_db          # noqa: E402
from hydrahive.db import teamchat as db_teamchat      # noqa: E402
from hydrahive.teamchat.identity import ensure_identity, ensure_bot_identity  # noqa: E402
from hydrahive.teamchat import rooms, messages, agent_membership  # noqa: E402


async def main() -> None:
    init_db()

    print("\n[1] Provisioning (echte Matrix-Accounts via UIAA-Register)...")
    alice = await ensure_identity("smoke_alice")
    bob = await ensure_identity("smoke_bob")
    print(f"    alice -> {alice.user_id}")
    print(f"    bob   -> {bob.user_id}")

    print("\n[2] Idempotenz (zweiter ensure_identity darf NICHT neu registrieren)...")
    alice2 = await ensure_identity("smoke_alice")
    assert alice2.user_id == alice.user_id, "Idempotenz verletzt!"
    print(f"    ok, gleiche MXID: {alice2.user_id}")

    print("\n[3] Raum anlegen (alice lädt bob ein)...")
    room_id = await rooms.create_room("smoke_alice", "Smoke Test Room", ["smoke_bob"])
    print(f"    room_id = {room_id}")

    print("\n[4] Nachricht senden (alice)...")
    sent = await messages.send_message(room_id, "smoke_alice", "Hallo aus dem Smoke-Test!")
    print(f"    event_id = {sent['event_id']}")

    print("\n[5] History lesen (bob)...")
    hist = await messages.history(room_id, "smoke_bob", limit=10)
    for m in hist:
        print(f"    {m['sender']}: {m['text']}")

    print("\n[6] Mitglieder...")
    members = await rooms.list_members(room_id, "smoke_alice")
    print(f"    {members}")

    print("\n[7] Membership-Gate (Security-Fix)...")
    bob_in = await rooms.is_member(room_id, "smoke_bob")
    await ensure_identity("smoke_stranger")
    stranger_in = await rooms.is_member(room_id, "smoke_stranger")
    print(f"    bob ist Mitglied:      {bob_in}   (erwartet True)")
    print(f"    stranger ist Mitglied: {stranger_in}   (erwartet False)")
    assert bob_in is True and stranger_in is False, "Membership-Gate falsch!"

    print("\n[8] Bot-Identität (eigener Namensraum, agent-Präfix)...")
    bot = await ensure_bot_identity("smoke_agent_buddy")
    print(f"    bot -> {bot.user_id}   (erwartet @agent-smoke_agent_buddy:...)")
    assert bot.user_id.startswith("@agent-smoke_agent_buddy:"), "Bot-localpart falsch!"

    print("\n[9] Agent zuschalten (Bot tritt dem Raum bei)...")
    await agent_membership.attach_agent(room_id, "smoke_alice", "smoke_agent_buddy")
    members_with_bot = await rooms.list_members(room_id, "smoke_alice")
    print(f"    Mitglieder: {members_with_bot}")
    assert bot.user_id in members_with_bot, "Bot ist dem Raum nicht beigetreten!"
    assert db_teamchat.list_room_agents(room_id), "Agent-Zuordnung nicht in DB!"

    print("\n[10] Agent wegschalten (Bot verlässt den Raum)...")
    await agent_membership.detach_agent(room_id, "smoke_agent_buddy")
    members_after = await rooms.list_members(room_id, "smoke_alice")
    print(f"    Mitglieder: {members_after}")
    assert bot.user_id not in members_after, "Bot hat den Raum nicht verlassen!"
    assert not db_teamchat.list_room_agents(room_id), "Agent-Zuordnung nicht entfernt!"

    print(
        "\n✅ SMOKE-TEST OK — Mensch- UND Agent-Bot-Kette laufen gegen den echten tuwunel."
        "\n   (Die LLM-gestützte Agent-Antwort selbst testet Till im Browser, Etappe 4b.)"
    )


if __name__ == "__main__":
    asyncio.run(main())
