"""compaction.redact muss die zentrale SECRET_PATTERNS-SSOT nutzen — sonst
Drift (zwei Listen), exakt die Ursache des OpenRouter-Leaks."""
from __future__ import annotations

from hydrahive.compaction.redact import redact


def test_redact_nutzt_zentrale_patterns_nvapi():
    """nvapi- fehlte in der alten compaction-Liste, ist in der zentralen SSOT."""
    key = "nvapi-" + "A" * 40
    assert key not in redact(f"NVIDIA_NIM_API_KEY={key}")


def test_redact_weiterhin_github_token():
    tok = "ghp_" + "A" * 36
    assert tok not in redact(f"GH_TOKEN={tok}")


def test_redact_nicht_string_unveraendert():
    assert redact(None) is None


def test_redact_normaler_text_bleibt():
    text = "git commit -m 'fix handler'"
    assert redact(text) == text
