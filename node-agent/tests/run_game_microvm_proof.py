"""Explicit real-run entry point for Game Studio PR-0 evidence generation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE_AGENT_ROOT = HERE.parent
sys.path.insert(0, str(NODE_AGENT_ROOT))

from game_microvm_contract import ProofConfig  # noqa: E402
from game_microvm_harness import run_proof  # noqa: E402
from game_microvm_runtime import ProofExecutionError, run_incus  # noqa: E402
FIXTURE = HERE / "fixtures" / "game_runtime_godot"


def main() -> int:
    output_raw = os.environ.get("HH_GAME_PROOF_OUTPUT", "")
    output = Path(output_raw)
    if not output_raw or not output.is_absolute():
        raise SystemExit("HH_GAME_PROOF_OUTPUT must be an absolute path")
    config = ProofConfig.from_env(os.environ)
    result = run_proof(config, FIXTURE, output)
    if result.get("proof_mode") != "real-incus-kvm" or result.get("cleanup_confirmed") is not True:
        raise RuntimeError("real proof did not confirm execution and cleanup")
    if os.environ.get("HH_GAME_PROOF_DELETE_IMAGE") != "1":
        raise SystemExit("HH_GAME_PROOF_DELETE_IMAGE=1 is required for final evidence")
    deleted = run_incus("image", "delete", config.image, timeout=120.0)
    if deleted.returncode != 0:
        raise ProofExecutionError("proof_image_cleanup_failed")
    remaining = run_incus("image", "list", config.image, "--format=json", timeout=30.0)
    if remaining.returncode != 0 or json.loads(remaining.stdout):
        raise ProofExecutionError("proof_image_cleanup_unconfirmed")
    result["image_cleanup_confirmed"] = True
    target = output / "game-studio-pr0-result.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
