from pathlib import Path

from hydrahive.skills.models import parse


SKILL = Path(__file__).resolve().parent.parent / "src/hydrahive/skills/system_defaults/document-reading.md"


def test_document_reading_skill_is_parseable_and_requires_document_tool():
    skill = parse(SKILL.read_text(encoding="utf-8"), scope="system", owner="system")

    assert skill.name == "document-reading"
    assert skill.tools_required == ["read_document"]
    assert "nicht `file_read`" in skill.body
    assert "nicht an einen Cloud-Dienst" in skill.body
