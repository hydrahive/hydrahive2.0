from redact import redact_entries, redact_text


def test_redacts_api_key_and_bearer():
    assert "hhk_" not in redact_text("key=hhk_abcd1234efgh5678")
    assert redact_text("Authorization: Bearer abc.def.ghi").endswith("[redacted]")


def test_redacts_password_assignment_keeps_label():
    out = redact_text("HH_PASS=supersecret")
    assert "supersecret" not in out
    assert out.startswith("HH_PASS=")


def test_passes_through_innocent_text():
    assert redact_text("ganz normaler text ohne secrets") == "ganz normaler text ohne secrets"


def test_redact_entries_walks_blocks_and_keeps_metadata():
    entries = [{"message_id": "a", "role": "assistant", "created_at": "t",
                "content": [{"type": "text", "text": "token=hhk_zzzz11112222aaaa"}]}]
    out = redact_entries(entries)
    assert "hhk_zzzz" not in out[0]["content"][0]["text"]
    assert out[0]["message_id"] == "a"
    assert out[0]["created_at"] == "t"
