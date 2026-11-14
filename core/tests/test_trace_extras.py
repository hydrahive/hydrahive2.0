"""Reine Logik: Kurzfassung + GitHub-Link-Erkennung (Spec agent-office.md §2, §8.2)."""
from __future__ import annotations

from hydrahive.api.routes._trace_extras import github_link, result_summary


def test_result_summary_kuerzt_lange_texte():
    assert len(result_summary("A" * 500)) == 200


def test_result_summary_leer_bei_none():
    assert result_summary(None) == ""


def test_result_summary_wandelt_dict_in_text():
    assert result_summary({"a": 1}) != ""


def test_github_link_erkennt_pull_request():
    text = "PR erstellt: https://github.com/hydrahive/hydrahive2.0/pull/42 fertig."
    assert github_link(text) == "https://github.com/hydrahive/hydrahive2.0/pull/42"


def test_github_link_erkennt_issue():
    text = "siehe https://github.com/foo/bar/issues/7"
    assert github_link(text) == "https://github.com/foo/bar/issues/7"


def test_github_link_none_ohne_treffer():
    assert github_link("ganz normaler text") is None
