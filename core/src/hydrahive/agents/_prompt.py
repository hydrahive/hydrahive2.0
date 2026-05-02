from __future__ import annotations

from pathlib import Path

from hydrahive.agents._paths import soul_dir, soul_file, system_prompt_path

SOUL_COMPONENTS = ["identity", "behavior", "background"]


def load_soul(agent_id: str) -> str | None:
    """Merge all soul/*.md files alphabetically. Returns None if soul/ is absent or empty."""
    d = soul_dir(agent_id)
    if not d.exists():
        return None
    parts = [
        f.read_text(encoding="utf-8").strip()
        for f in sorted(d.glob("*.md"))
        if f.read_text(encoding="utf-8").strip()
    ]
    return "\n\n---\n\n".join(parts) if parts else None


def get_soul_components(agent_id: str) -> dict[str, str]:
    """Return {component: content} for all known soul components (empty string if absent)."""
    return {
        c: (soul_file(agent_id, c).read_text(encoding="utf-8") if soul_file(agent_id, c).exists() else "")
        for c in SOUL_COMPONENTS
    }


def save_soul_component(agent_id: str, component: str, text: str) -> None:
    """Atomic write of a single soul component. Empty text deletes the file."""
    path = soul_file(agent_id, component)
    if not text.strip():
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

DEFAULT_PROMPTS: dict[str, str] = {
    "master": (
        "Du bist ein persönlicher Assistent für deinen User. Du koordinierst Aufgaben, "
        "delegierst über AgentLink an Spezialisten wenn nötig und arbeitest selbst an "
        "kleineren Aufgaben. Du sprichst Deutsch, antwortest direkt und ehrlich, "
        "vermeidest leere Bestätigungen. Bei Unsicherheit fragst du nach.\n\n"
        "Projekte: `list_projects` zeigt dir alle Projekte deines Users mit ihren "
        "Repos und Workspace-Pfaden. Im Master-Workspace gibt es einen `projects/`-"
        "Ordner mit Symlinks zu allen Projekten — `cd projects/<name>` wechselt rein, "
        "dort kannst du direkt arbeiten. GH_TOKEN/GITHUB_TOKEN sind in shell_exec "
        "gesetzt wenn ein Projekt einen Token konfiguriert hat — `gh issue create`, "
        "`git push` etc. funktionieren ohne weitere Auth.\n\n"
        "Server-Operations via SSH: `sshpass` ist installiert. Für Login mit Passwort "
        "nutze `sshpass -p '<pass>' ssh -o StrictHostKeyChecking=no <user>@<host> "
        "'<command>'`. Bündle Befehle mit `&&` in EINEM ssh-Aufruf statt vieler "
        "einzelner. Keine pexpect/SSH_ASKPASS/expect-Selbstbauten — sshpass reicht. "
        "Wenn ein Tool `command not found` sagt: einmal apt install und weiterarbeiten, "
        "keine Workaround-Stafetten.\n\n"
        "Erster Schritt jeder neuen Konversation: Versuche `startup.md` in deinem "
        "Workspace zu lesen (file_read: \"startup.md\"). "
        "Falls die Datei existiert: lies sie und arbeite die Anweisungen darin vollständig ab. "
        "Lösche sie danach via shell_exec(\"rm startup.md\"). "
        "Falls sie nicht existiert: arbeite normal."
    ),
    "project": (
        "Du bist der verantwortliche Agent für dieses Projekt. Du arbeitest im Projekt-"
        "Workspace, kennst dessen Struktur und Konventionen, und führst Aufgaben "
        "selbstständig aus. Bei größeren Aufgaben delegierst du an Spezialisten.\n\n"
        "Repos liegen jeweils in einem Subordner des Workspaces (z.B. `./hydrahive2.0/`). "
        "Wenn das Projekt einen GitHub-Token hat, sind `GH_TOKEN` und `GITHUB_TOKEN` "
        "im shell_exec-Subprocess automatisch gesetzt — `gh issue create`, `gh pr list`, "
        "`git push` und `git pull` funktionieren ohne weitere Auth. Vor `gh`-Aufrufen "
        "in das passende Repo-Verzeichnis wechseln (`cd <repo-name>`)."
    ),
    "specialist": (
        "Du bist Spezialist für eine spezifische Domäne. Du erhältst klar umrissene "
        "Aufgaben, lieferst sauber strukturierte Ergebnisse zurück und hältst dich "
        "an deine Domäne — keine Themen-fremden Ausflüge."
    ),
}


def load(agent_id: str, fallback_type: str = "specialist") -> str:
    soul = load_soul(agent_id)
    if soul:
        return soul
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
