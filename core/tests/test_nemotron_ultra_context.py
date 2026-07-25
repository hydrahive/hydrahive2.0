"""Regression: Nemotron 3 Ultra 550B braucht ein korrektes Kontextfenster.

Bug (Kunde): Der NVIDIA-NIM-Endpoint /v1/models meldet für dieses Modell KEIN
context_length (kommt als None rein). Ohne METADATA-Fallback fiel die Compaction
auf den 32k-Default (im UI als kleiner Wert sichtbar) statt auf das echte
Fenster. NIM-Default = 262144 (256K, offizielle NVIDIA-Doku).
"""
from __future__ import annotations


def test_nemotron_ultra_550b_has_metadata_context():
    from hydrahive.llm._catalog_data import METADATA
    mid = "nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b"
    assert mid in METADATA, "Nemotron Ultra 550B fehlt in METADATA"
    assert METADATA[mid]["context_window"] == 262_144


def test_context_window_for_ultra_uses_metadata():
    from hydrahive.compaction.tokens import context_window_for
    # Kein 32k-Default mehr — echtes Fenster aus METADATA.
    assert context_window_for("nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b") == 262_144
