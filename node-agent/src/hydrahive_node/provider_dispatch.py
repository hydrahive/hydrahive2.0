"""Closed provider dispatch for legacy and Game Studio compute jobs."""

from __future__ import annotations

from hydrahive_node import incus, jobs


class ProviderDispatchError(RuntimeError):
    code = "operation_not_installed"


async def execute(job: jobs.VerifiedOffer) -> dict[str, object]:
    if isinstance(job, jobs.VerifiedGameJob):
        # PR2 establishes the signed protocol and cancellation contract. The
        # real isolated game runtime is installed by PR4; never fall back to a
        # host process or the legacy Incus resource handler.
        raise ProviderDispatchError("game-runtime/v1 is not installed")
    return await incus.execute(job)
