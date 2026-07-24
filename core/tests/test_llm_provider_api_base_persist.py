"""Sichert die Frontend→Backend-Kette für den Ollama-Provider ab.

Das Frontend schickt beim Anlegen eines Ollama-Providers ein `api_base`-Feld.
Das Pydantic-Modell `LlmProvider` listet api_base nicht explizit — es wird über
`model_config = ConfigDict(extra="allow")` durchgereicht. Dieser Test stellt
sicher, dass model_dump() das Feld NICHT droppt (sonst käme es nie in die
llm.json und der ganze Provider wäre unbrauchbar).

Import von `hydrahive.api.routes.llm` bewusst LAZY (in der Funktion), damit das
settings-Singleton nicht zur Collection-Zeit auf das echte /var/lib/hydrahive2
festgenagelt wird (bricht sonst die tmp-Isolation anderer Tests). Gleiches
Muster wie test_llm_media_models_config.py.
"""
from __future__ import annotations


def test_api_base_survives_model_dump():
    from hydrahive.api.routes.llm import LlmProvider
    p = LlmProvider(
        id="ollama", name="Ollama (lokal)", api_key="", models=[],
        api_base="http://localhost:11434",
    )
    dumped = p.model_dump()
    assert dumped["api_base"] == "http://localhost:11434"


def test_api_base_survives_full_config_dump():
    from hydrahive.api.routes.llm import LlmConfig, LlmProvider
    cfg = LlmConfig(providers=[
        LlmProvider(id="ollama", name="Ollama", api_key="", models=[],
                    api_base="http://localhost:11434"),
        LlmProvider(id="openai", name="OpenAI", api_key="sk-x", models=[]),
    ])
    dumped = cfg.model_dump()
    ollama = next(p for p in dumped["providers"] if p["id"] == "ollama")
    openai = next(p for p in dumped["providers"] if p["id"] == "openai")
    assert ollama["api_base"] == "http://localhost:11434"
    # Nicht-Ollama-Provider haben kein api_base (kein leeres Feld untergejubelt).
    assert "api_base" not in openai
