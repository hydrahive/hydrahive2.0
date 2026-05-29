from state import load_state, save_state


def test_load_missing_returns_defaults(tmp_path):
    assert load_state(tmp_path, "cc-1") == {"hh_session_id": None, "synced": 0}


def test_save_then_load_roundtrips(tmp_path):
    save_state(tmp_path, "cc-1", "hh-abc", 7)
    assert load_state(tmp_path, "cc-1") == {"hh_session_id": "hh-abc", "synced": 7}


def test_corrupt_file_returns_defaults(tmp_path):
    (tmp_path / "cc-2.json").write_text("{garbage")
    assert load_state(tmp_path, "cc-2") == {"hh_session_id": None, "synced": 0}
