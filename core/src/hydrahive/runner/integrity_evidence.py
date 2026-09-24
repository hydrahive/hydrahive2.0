"""Conservative, prompt-free evidence classification for Integrity observation."""
from __future__ import annotations

import re
from typing import Any

_ARTIFACT_TOOLS = frozenset({"file_write", "file_patch", "write_skill", "delete_skill"})
_UNSAFE_SHELL_FLOW = re.compile(r"\|\||(?<!\|)\|(?!\|)|;|\n|\bset\s+\+e\b", re.I)
_NON_EXECUTING_TEST = re.compile(r"(?:--collect-only|--co\b|--help\b|--version\b)", re.I)
_TEST_COMMAND = re.compile(
    r"(?:^|&&\s*)"
    r"(?:"
    r"(?:[A-Za-z0-9_./-]+/)?pytest\b|"
    r"python(?:3(?:\.\d+)?)?\s+-m\s+pytest\b|"
    r"go\s+test\b|cargo\s+test\b|"
    r"(?:npm|pnpm|yarn)\s+(?:run\s+)?test\b"
    r")",
    re.I,
)
_GIT_COMMIT = re.compile(r"(?:^|&&\s*)git\s+commit\b", re.I)
_GIT_PUSH = re.compile(r"(?:^|&&\s*)git\s+push\b", re.I)
_COMPLETION_PATTERNS = {
    "implemented": re.compile(r"\b(?:implementiert|implemented|eingebaut|built)\b", re.I),
    "tested": re.compile(r"\b(?:getestet|tested|test(?:s)? bestanden|tests? grün)\b", re.I),
    "deployed": re.compile(r"\b(?:deployt|deployed|ausgerollt|live geschaltet)\b", re.I),
    "fixed": re.compile(r"\b(?:behoben|gefixt|fixed|repaired)\b", re.I),
    "finished": re.compile(r"\b(?:fertig|erledigt|done|completed)\b", re.I),
}
_NEGATION_BEFORE_CLAIM = re.compile(
    r"\b(?:nicht|not|never|kein|keine|keinen)(?:\s+\w+){0,2}\s*$", re.I,
)


def completion_claim_kinds(text: str) -> list[str]:
    """Extract positive completion claims while ignoring local negations."""
    found: list[str] = []
    for kind, pattern in _COMPLETION_PATTERNS.items():
        matches = [
            match for match in pattern.finditer(text)
            if not _NEGATION_BEFORE_CLAIM.search(text[max(0, match.start() - 48):match.start()])
        ]
        if matches:
            found.append(kind)
    return found


def evidence_for_tool(
    tool_name: str, arguments: dict[str, Any] | None, *, succeeded: bool,
) -> set[str]:
    """Return strong evidence labels only; never return raw input or output."""
    if not succeeded:
        return set()
    if tool_name in _ARTIFACT_TOOLS:
        return {"artifact_changed"}
    if tool_name != "shell_exec":
        return set()

    command = str((arguments or {}).get("cmd") or "").strip()
    if not command or _UNSAFE_SHELL_FLOW.search(command):
        return set()
    if _TEST_COMMAND.search(command) and not _NON_EXECUTING_TEST.search(command):
        return {"tests_passed"}
    if _GIT_COMMIT.search(command):
        return {"commit_created"}
    if _GIT_PUSH.search(command):
        return {"push_completed"}
    return set()


def missing_evidence_for_claim(kind: str, evidence: set[str]) -> tuple[str, ...] | None:
    """Return missing labels; None means this claim is not mechanically judged."""
    if kind == "implemented":
        if evidence.intersection({"artifact_changed", "commit_created"}):
            return ()
        return ("artifact_changed|commit_created",)
    if kind == "tested":
        return () if "tests_passed" in evidence else ("tests_passed",)
    if kind == "fixed":
        required = ("artifact_changed", "tests_passed")
        return tuple(item for item in required if item not in evidence)
    return None
