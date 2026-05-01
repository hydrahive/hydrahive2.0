"""Skills — wiederverwendbare Verhaltensmuster als Markdown mit Frontmatter.

Drei Scopes:
- system  : ausgeliefert mit dem Installer, alle Agents sehen sie
- user    : pro User, alle eigenen Agents sehen sie
- agent   : pro Agent, überschreibt user/system bei Namens-Kollision

Loading-Mechanismen:
- Liste mit Beschreibungen wird vom Runner in den System-Prompt injected
- Tool `load_skill(name)` liefert den Body als Tool-Result
- Tool `list_skills()` listet aktuell verfügbare Skills

Format einer Skill-Datei:

    ---
    name: code-review
    description: Strukturierte Code-Review-Anweisungen
    when_to_use: Wenn der User um Code-Review bittet
    tools_required: [file_read, file_search]
    ---

    Markdown-Body mit Anweisungen…
"""
from hydrahive.skills.loader import (
    delete_skill,
    get_skill,
    list_for_agent,
    save_skill,
)
from hydrahive.skills.models import Skill, SkillScope

__all__ = ["Skill", "SkillScope", "delete_skill", "get_skill", "list_for_agent", "save_skill"]
