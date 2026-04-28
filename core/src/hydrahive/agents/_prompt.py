from __future__ import annotations

from hydrahive.agents._paths import system_prompt_path

DEFAULT_PROMPTS: dict[str, str] = {
    "master": (
        "Du bist ein persönlicher Assistent für deinen User. Du koordinierst Aufgaben, "
        "delegierst über AgentLink an Spezialisten wenn nötig und arbeitest selbst an "
        "kleineren Aufgaben. Du sprichst Deutsch, antwortest direkt und ehrlich, "
        "vermeidest leere Bestätigungen. Bei Unsicherheit fragst du nach."
    ),
    "project": (
        "Du bist der verantwortliche Agent für dieses Projekt. Du arbeitest im Projekt-"
        "Workspace, kennst dessen Struktur und Konventionen, und führst Aufgaben "
        "selbstständig aus. Bei größeren Aufgaben delegierst du an Spezialisten."
    ),
    "specialist": (
        "Du bist Spezialist für eine spezifische Domäne. Du erhältst klar umrissene "
        "Aufgaben, lieferst sauber strukturierte Ergebnisse zurück und hältst dich "
        "an deine Domäne — keine Themen-fremden Ausflüge."
    ),
}


def load(agent_id: str, fallback_type: str = "specialist") -> str:
    path = system_prompt_path(agent_id)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return DEFAULT_PROMPTS.get(fallback_type, DEFAULT_PROMPTS["specialist"])


def save(agent_id: str, prompt: str) -> None:
    """Atomic write via temp + rename, so concurrent reads never see half-written file."""
    path = system_prompt_path(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(prompt, encoding="utf-8")
    tmp.replace(path)


def init_default(agent_id: str, agent_type: str) -> None:
    """Write the type-default prompt only if no prompt file exists yet."""
    path = system_prompt_path(agent_id)
    if path.exists():
        return
    save(agent_id, DEFAULT_PROMPTS.get(agent_type, DEFAULT_PROMPTS["specialist"]))
