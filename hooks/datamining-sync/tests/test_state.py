from state import load_state, save_state


def test_load_missing_returns_defaults(tmp_path):
    assert load_state(tmp_path, "cc-1") == {"hh_session_id": None, "synced_ids": []}


def test_save_then_load_roundtrips(tmp_path):
    save_state(tmp_path, "cc-1", "hh-abc", ["u0", "u1"])
    assert load_state(tmp_path, "cc-1") == {"hh_session_id": "hh-abc", "synced_ids": ["u0", "u1"]}


def test_corrupt_file_returns_defaults(tmp_path):
    (tmp_path / "cc-2.json").write_text("{garbage")
    assert load_state(tmp_path, "cc-2") == {"hh_session_id": None, "synced_ids": []}
