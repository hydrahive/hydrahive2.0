"""Tests für Secret-Redaction im Tool-Output.

Wert-basiert: bekannte Secret-Werte werden aus Strings/Dicts/Listen
geschwärzt — egal WIE ein Agent sie in den Output bekommt (env-Dump,
`echo $KEY`, `cat /etc/hydrahive2/llm.json`). Greift an der Engstelle
ToolResult, bevor der Output in DB/Transcript/Stream/Datamining landet.
"""
from __future__ import annotations

from hydrahive.credentials import redaction
from hydrahive.tools.base import ToolResult

# Gleiche Länge/Form wie der real geleakte OpenRouter-Key (widerrufen).
LONG_KEY = "sk-or-v1-" + "a" * 64


def test_scrubt_bekannten_secret_wert_aus_string():
    out = redaction.scrub(f"key={LONG_KEY} ende", secrets={LONG_KEY})
    assert LONG_KEY not in out
    assert out == f"key={redaction.PLACEHOLDER} ende"


def test_kurze_werte_werden_nicht_geschwaerzt():
    """Schutz vor katastrophalen False-Positives: ein zu kurzer 'Secret'-Wert
    darf nicht überall im Output matchen und ihn zerstören."""
    out = redaction.scrub("abc def abc", secrets={"abc"})
    assert out == "abc def abc"


def test_rekursiert_in_dict_output():
    output = {"stdout": f"OPENROUTER_API_KEY={LONG_KEY}", "exit_code": 0}
    out = redaction.scrub(output, secrets={LONG_KEY})
    assert LONG_KEY not in out["stdout"]
    assert out["exit_code"] == 0  # Nicht-Strings bleiben unangetastet


def test_rekursiert_in_liste():
    out = redaction.scrub(["safe", f"x{LONG_KEY}y"], secrets={LONG_KEY})
    assert out[0] == "safe"
    assert LONG_KEY not in out[1]


def test_scrub_result_schwaerzt_output_und_laesst_success():
    result = ToolResult.ok({"stdout": f"k={LONG_KEY}", "exit_code": 0})
    scrubbed = redaction.scrub_result(result, secrets={LONG_KEY})
    assert scrubbed.success is True
    assert LONG_KEY not in scrubbed.output["stdout"]


def test_scrub_result_mutiert_das_original_nicht():
    """Immutability: scrub_result gibt ein neues ToolResult zurück, das
    Original bleibt unverändert."""
    result = ToolResult.ok({"stdout": f"k={LONG_KEY}"})
    redaction.scrub_result(result, secrets={LONG_KEY})
    assert LONG_KEY in result.output["stdout"]


def test_scrub_result_schwaerzt_auch_error_feld():
    result = ToolResult.fail(f"crash mit token {LONG_KEY}")
    scrubbed = redaction.scrub_result(result, secrets={LONG_KEY})
    assert LONG_KEY not in scrubbed.error
    assert scrubbed.success is False


def test_secret_values_enthaelt_openrouter_env_key(monkeypatch):
    """Engstelle zur SSOT: was in der shell-Denylist steht, wird aus dem
    Output geschwärzt — ohne dritte hartcodierte Liste."""
    monkeypatch.setenv("OPENROUTER_API_KEY", LONG_KEY)
    assert LONG_KEY in redaction.secret_values()


def test_secret_values_ignoriert_kurze_env_werte(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert "x" not in redaction.secret_values()


# --- Pattern-Detektion (historische Audit) -----------------------------------
# Wert-Abgleich findet rotierte Alt-Keys nicht mehr. Die Audit sucht nach
# Key-FORMEN, um bereits geleakte Secrets in der History aufzuspüren.

def test_detect_findet_openrouter_key():
    text = f"OPENROUTER_API_KEY={LONG_KEY}\nPATH=/usr/bin"
    assert LONG_KEY in redaction.detect_secrets(text)


def test_detect_findet_anthropic_key():
    key = "sk-ant-api03-" + "A" * 40
    assert key in redaction.detect_secrets(f"export KEY={key}")


def test_detect_ignoriert_normalen_text():
    assert redaction.detect_secrets("git commit -m 'fix bug in handler'") == []


def test_detect_leerer_string():
    assert redaction.detect_secrets("") == []


def test_mask_zeigt_nicht_den_ganzen_wert():
    masked = redaction.mask(LONG_KEY)
    assert LONG_KEY not in masked
    assert masked.startswith("sk-or-v1-")  # Prefix als Hinweis erlaubt


def test_redact_detected_ersetzt_gefundene_keys():
    text = f"key={LONG_KEY} ende"
    out = redaction.redact_detected(text)
    assert LONG_KEY not in out
    assert redaction.PLACEHOLDER in out


def test_detect_findet_openrouter_key_mit_buchstaben():
    """Echte OpenRouter-Keys sind nicht hex-only — base62 muss matchen."""
    key = "sk-or-v1-" + "Ab9Zx" * 8
    assert key in redaction.detect_secrets(f"KEY={key}")


def test_detect_findet_github_token():
    """HH injiziert GH_TOKEN selbst (shell.py) — GitHub-Leak ist real."""
    tok = "ghp_" + "A" * 36
    assert tok in redaction.detect_secrets(f"GH_TOKEN={tok}")


def test_detect_findet_github_fine_grained_pat():
    tok = "github_pat_" + "B" * 40
    assert tok in redaction.detect_secrets(f"export X={tok}")


def test_detect_findet_huggingface_token():
    tok = "hf_" + "C" * 34
    assert tok in redaction.detect_secrets(f"HF_TOKEN={tok}")


def test_detect_dedupt_mehrfache_vorkommen():
    """Derselbe Key zweimal im Text → genau ein Eintrag (Dedup)."""
    found = redaction.detect_secrets(f"{LONG_KEY} und nochmal {LONG_KEY}")
    assert found.count(LONG_KEY) == 1
