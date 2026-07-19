"""Command-line entry point for the HydraHive node agent."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from hydrahive_node.enrollment import AgentEnrollmentError, enroll
from hydrahive_node.storage import StatePaths, load_identity

DEFAULT_STATE_DIR = Path(os.environ.get("HYDRAHIVE_NODE_STATE_DIR", "/var/lib/hydrahive-node"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hydrahive-node")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    enroll_command = commands.add_parser("enroll", help="enroll this host with a HydraHive control plane")
    enroll_command.add_argument("--server", required=True)
    token_source = enroll_command.add_mutually_exclusive_group()
    token_source.add_argument("--token-file", type=Path)
    token_source.add_argument("--token-stdin", action="store_true")
    enroll_command.add_argument("--name", required=True)
    enroll_command.add_argument("--ca-file", type=Path)
    commands.add_parser("run", help="run the persistent node-agent channel")
    return parser


def _read_token(args: argparse.Namespace) -> str:
    if args.token_file:
        if args.token_file.stat().st_mode & 0o077:
            raise AgentEnrollmentError("token file permissions must be 0600")
        return args.token_file.read_text(encoding="utf-8").strip()
    if args.token_stdin:
        return sys.stdin.readline().strip()
    return getpass.getpass("Enrollment token: ").strip()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = StatePaths(args.state_dir)
    if args.command == "enroll":
        try:
            identity = enroll(
                server_url=args.server,
                token=_read_token(args),
                node_name=args.name,
                paths=paths,
                ca_file=args.ca_file,
            )
        except AgentEnrollmentError as exc:
            print(f"Enrollment failed: {exc}")
            return 1
        print(f"Node ID: {identity.node_id}")
        print(f"Certificate fingerprint: {identity.certificate_fingerprint}")
        return 0
    identity = load_identity(paths)
    from hydrahive_node.runtime import run_forever

    run_forever(paths, identity)
    return 0
