"""CI-Prüfung gegen feste Modellnamen in Modulen (Plan E5)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_fixed_models.py"
_spec = importlib.util.spec_from_file_location("check_fixed_models", _SCRIPT)
cfm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfm)


def test_findet_festes_modell(tmp_path):
    (tmp_path / "a.py").write_text('x = create(llm_model="claude-haiku-4-5")\n')
    assert len(cfm.scan([tmp_path])) == 1


def test_begruendung_und_tests_ausgenommen(tmp_path):
    (tmp_path / "a.py").write_text('m = complete(model="claude-x")  # feste-modell-id: nur Demo\n')
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text('model="claude-x"\n')
    assert cfm.scan([tmp_path]) == []


def test_kern_module_sauber():
    assert cfm.scan([_SCRIPT.parents[1] / "modules"]) == []
