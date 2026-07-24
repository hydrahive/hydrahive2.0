import pytest


@pytest.mark.asyncio
async def test_invalidate_clears_cache(monkeypatch):
    from hydrahive.llm import registry
    from hydrahive.llm.registry import ModelEntry

    async def fake_build():
        return [ModelEntry("a", "p", "a", frozenset({"chat"}))], True

    monkeypatch.setattr(registry, "_build", fake_build)
    registry.invalidate()
    await registry.list_models()
    assert registry.is_known("a") is True
    registry.invalidate()
    assert registry.known_ids() == set()
