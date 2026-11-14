"""checkpoint_finding/split_checkpoint_findings mit generalisiertem reason-Feld
(Spec delegation-reliability.md 3.2: Shutdown-Checkpoint neben max_iterations)."""
from __future__ import annotations

from hydrahive.agentlink.checkpoints import checkpoint_finding, split_checkpoint_findings


def test_default_reason_bleibt_max_iterations():
    cp = checkpoint_finding(resume_token="tok_abcdefgh12", session_id="s1", remaining_work="rest")
    _visible, payload = split_checkpoint_findings([cp])
    assert payload["reason"] == "max_iterations"


def test_shutdown_reason_wird_transportiert_und_erkannt():
    cp = checkpoint_finding(resume_token="tok_abcdefgh12", session_id="s1",
                            remaining_work="rest", reason="shutdown")
    assert '"reason":"shutdown"' in cp or '"reason": "shutdown"' in cp
    _visible, payload = split_checkpoint_findings([cp])
    assert payload is not None
    assert payload["reason"] == "shutdown"
    assert payload["resume_token"] == "tok_abcdefgh12"


def test_unbekannter_reason_wird_trotzdem_akzeptiert_wenn_gueltig():
    """split_checkpoint_findings validiert Format, nicht eine feste Werteliste —
    neue Gründe müssen ohne Code-Änderung an dieser Stelle funktionieren."""
    cp = checkpoint_finding(resume_token="tok_abcdefgh12", session_id="s1",
                            remaining_work="rest", reason="irgendwas_neues")
    _visible, payload = split_checkpoint_findings([cp])
    assert payload["reason"] == "irgendwas_neues"
