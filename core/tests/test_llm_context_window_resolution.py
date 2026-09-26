"""Kontextfenster-Auflösung — Regression gegen still zu kleine Fenster.

Hintergrund: Beim Umschalten auf neue Claude-Modelle bekamen Chats ein
32k-Fenster statt 1M. Ursache war eine Kette aus drei Lücken:

1. Anthropic liefert das Fenster als `max_input_tokens` — der Katalog las
   nur `context_length`/`context_window` und verwarf den Wert.
2. Die API liefert datierte Snapshots (`claude-opus-5-20260115`), die
   METADATA-Tabelle kennt nur den Alias (`claude-opus-5`). Lookup schlug fehl.
3. Die Heuristik kannte die 5er-Generation nicht → 32k-Default.

Jede Lücke allein hätte gereicht. Diese Tests decken alle drei ab.
"""
from hydrahive.compaction.tokens import context_window_for
from hydrahive.llm._catalog_data import METADATA, STATIC_MODELS
from hydrahive.llm.catalog import _parse_models_response

_DEFAULT_FALLBACK = 32_000


def test_anthropic_api_max_input_tokens_is_used() -> None:
    """Die Models-API ist SSOT — ihr Wert muss im Katalog ankommen.

    Kritischster Fall: ein Modell, das in KEINER unserer Tabellen steht,
    muss trotzdem sein korrektes Fenster bekommen. Genau das macht den
    Unterschied zwischen "muss gepflegt werden" und "funktioniert von selbst".
    """
    response = {"data": [
        {"id": "claude-opus-5-5-20260301", "type": "model",
         "max_input_tokens": 1_000_000, "max_tokens": 128_000},
        {"id": "claude-voellig-neu-20270101", "type": "model",
         "max_input_tokens": 5_000_000, "max_tokens": 200_000},
    ]}

    parsed = {m["id"]: m["context_window"] for m in _parse_models_response("anthropic", response)}

    assert parsed["claude-opus-5-5-20260301"] == 1_000_000
    assert parsed["claude-voellig-neu-20270101"] == 5_000_000


def test_explicit_context_length_wins_over_max_input_tokens() -> None:
    """Provider, die beides liefern, dürfen nicht überschrieben werden."""
    response = {"data": [
        {"id": "some-model", "context_length": 128_000, "max_input_tokens": 999},
    ]}

    parsed = _parse_models_response("openrouter", response)

    assert parsed[0]["context_window"] == 128_000


def test_dated_snapshots_resolve_to_alias_metadata() -> None:
    """`claude-opus-5-20260115` muss wie `claude-opus-5` behandelt werden.

    Das war der eigentliche Bug: die API liefert IMMER datierte Snapshots.
    """
    assert context_window_for("claude-opus-5-20260115") == 1_000_000
    assert context_window_for("claude-sonnet-5-20260115") == 1_000_000
    assert context_window_for("claude-fable-5-20260201") == 1_000_000
    assert context_window_for("claude-haiku-4-5-20251001") == 200_000


def test_dated_snapshot_resolution_survives_provider_prefix() -> None:
    """Prefix UND Datums-Suffix gleichzeitig — beides muss abfallen."""
    assert context_window_for("anthropic/claude-opus-5-20260115") == 1_000_000


def test_claude_5_generation_has_heuristic_fallback() -> None:
    """Zweites Netz: unbekannte 5er-Variante ohne METADATA-Eintrag.

    Greift wenn weder API-Refresh gelaufen ist noch die Tabelle gepflegt —
    darf dann nicht auf 32k fallen.
    """
    assert context_window_for("claude-opus-5-9-experimental") == 1_000_000
    assert context_window_for("claude-sonnet-5-2-preview") == 1_000_000


def test_haiku_45_keeps_200k_not_inflated_to_1m() -> None:
    """Gegenprobe: Haiku 4.5 hat laut Anthropic 200k, nicht 1M.

    Ein zu GROSSES Fenster ist genauso schädlich — die Compaction greift
    dann zu spät und das Modell wirft einen 400er.
    """
    assert context_window_for("claude-haiku-4-5") == 200_000
    assert context_window_for("claude-haiku-4-5-20251001") == 200_000


def test_live_registry_window_beats_stale_metadata(monkeypatch) -> None:
    """Der Live-Wert der Provider-API muss die statische Tabelle überstimmen.

    Real aufgetreten nach dem 32k-Fix: Anthropic hatte das Fenster von
    Sonnet 4.5 nachträglich auf 1M erweitert, die API meldete das auch —
    aber die hartkodierte METADATA stand noch auf 200.000 und gewann.

    Dieselbe Fehlerklasse wie der ursprüngliche Bug: eine gepflegte
    Konstante überstimmt die Wahrheit vom Anbieter. Anbieter erweitern
    Fenster bestehender Modelle, unsere Tabelle veraltet dabei zwangsläufig.
    """
    from hydrahive.llm import registry

    monkeypatch.setattr(
        registry, "cached_context_window",
        lambda model_id: 1_000_000 if model_id == "claude-sonnet-4-5" else None,
    )

    # METADATA sagt 200_000 — der Live-Wert muss gewinnen.
    assert METADATA["claude-sonnet-4-5"]["context_window"] == 200_000
    assert context_window_for("claude-sonnet-4-5") == 1_000_000


def test_metadata_still_used_when_registry_is_cold(monkeypatch) -> None:
    """Ohne Katalog-Refresh bleibt METADATA die Quelle — kein 32k-Rückfall."""
    from hydrahive.llm import registry

    monkeypatch.setattr(registry, "cached_context_window", lambda model_id: None)

    assert context_window_for("claude-sonnet-4-5") == 200_000
    assert context_window_for("claude-opus-5-20260115") == 1_000_000


def test_every_static_model_resolves_to_real_window() -> None:
    """Strukturtest — verhindert, dass sich der Bug wiederholt.

    Jedes Modell aus STATIC_MODELS muss ein echtes Fenster liefern, nicht
    den 32k-Default. Wer künftig ein Modell hinzufügt und die Metadaten
    vergisst, bricht hier — statt still mit einem winzigen Kontext zu laufen.
    """
    unresolved = []
    for provider, models in STATIC_MODELS.items():
        for model in models:
            if provider == "ollama":
                continue  # Ollama holt das Fenster live per /api/show
            if context_window_for(model) == _DEFAULT_FALLBACK:
                unresolved.append(f"{provider}:{model}")

    assert not unresolved, (
        "Modelle ohne aufgelöstes Kontextfenster (fallen auf 32k zurück): "
        f"{unresolved}. METADATA in _catalog_data.py ergänzen."
    )


def test_static_anthropic_models_have_metadata_entries() -> None:
    """Jedes angebotene Anthropic-Modell braucht einen Tabelleneintrag.

    Fängt den Fall ab, dass STATIC_MODELS erweitert wird ohne METADATA —
    dann würde nur noch die Heuristik greifen, die bei einer neuen
    Namensfamilie zwangsläufig danebenliegt.
    """
    missing = [m for m in STATIC_MODELS["anthropic"] if m not in METADATA]

    assert not missing, f"STATIC_MODELS ohne METADATA-Eintrag: {missing}"
