import json

from transcript import parse_entries


def _line(**kw):
    return json.dumps(kw)


def test_extracts_user_and_assistant_only():
    lines = [
        _line(type="user", uuid="u1", timestamp="2026-05-29T10:00:00Z",
              message={"role": "user", "content": "hallo"}),
        _line(type="assistant", uuid="a1", timestamp="2026-05-29T10:00:01Z",
              message={"role": "assistant", "content": [{"type": "text", "text": "hi"}]}),
        _line(type="system", uuid="s1", message={"role": "system", "content": "x"}),
        _line(type="file-history-snapshot", uuid="f1"),
        "   ",
        "{not valid json",
    ]
    out = parse_entries(lines)
    assert [e["message_id"] for e in out] == ["u1", "a1"]
    assert out[0] == {"message_id": "u1", "role": "user",
                      "content": "hallo", "created_at": "2026-05-29T10:00:00Z"}
    assert out[1]["content"][0]["text"] == "hi"


def test_skips_entries_without_uuid_or_content():
    lines = [
        _line(type="user", timestamp="t", message={"role": "user", "content": "no uuid"}),
        _line(type="assistant", uuid="a2", message={"role": "assistant"}),  # kein content
    ]
    assert parse_entries(lines) == []
