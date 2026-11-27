"""Agenten-Bereiche (docs/specs/agent-bereiche.md 3.1/3.2): 26 Schalter in 9 Gruppen statt Tool-Listen.

Ein Bereich ist nur eine SICHT auf ``agent.tools`` (E1): Er ordnet Tool-Namen einem Schalter in Alltagssprache zu. Gespeichert
wird nie ``bereich:x``, Rechteprüfungen ändern sich nicht. Schnittregeln: ein Bereich ist eine Sache aus dem Alltag; Lesen und
Verändern nur getrennt, wenn das Verändern ⚠️ ist; 🔒 private Daten, 💶 jede Nutzung kostet Geld; höchstens 4 Schalter je Gruppe.

Marken: ``risky`` = ⚠️ schwer rückgängig oder wirkt außerhalb von HydraHive, ``private`` = 🔒, ``costly`` = 💶.
Tool-Muster: exakte Namen oder ein Präfix mit ``*`` am Ende (``graph_*``); ein Stern woanders ist verboten.
Module melden eigene Bereiche und Zuordnungen im Manifest (``agent_areas``, siehe ``_area_registry``).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

GROUPS: tuple[str, ...] = ("files_code", "internet", "organize", "creative", "team", "post", "home", "private", "server")
GROUP_NAMES: dict[str, dict[str, str]] = {
    "files_code": {"de": "Dateien & Code", "en": "Files & code"},
    "internet": {"de": "Internet", "en": "Internet"},
    "organize": {"de": "Organisieren", "en": "Organize"},
    "creative": {"de": "Kreativ", "en": "Creative"},
    "team": {"de": "Team", "en": "Team"},
    "post": {"de": "Post", "en": "Mail"},
    "home": {"de": "Zuhause", "en": "Home"},
    "private": {"de": "Privates", "en": "Private"},
    "server": {"de": "Server", "en": "Server"},
}
MARKS = ("risky", "private", "costly")
_ID = re.compile(r"^[a-z][a-z_]{1,39}$")
_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+\*?$")


def check_pattern(pattern: str) -> str:
    """Name oder Präfix-Muster (``*`` nur ganz am Ende, höchstens einmal); sonst ValueError."""
    if not isinstance(pattern, str) or not _PATTERN.fullmatch(pattern) or pattern == "*":
        raise ValueError(f"Ungültiges Tool-Muster {pattern!r}: nur Name oder Präfix mit * am Ende")
    return pattern


@dataclass(frozen=True)
class Area:
    id: str
    group: str
    name: dict[str, str]
    sentence: dict[str, str]
    marks: tuple[str, ...]
    tools: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.id):
            raise ValueError(f"Ungültige Bereichs-ID {self.id!r} (nur a-z und _)")
        if self.group not in GROUPS:
            raise ValueError(f"Bereich {self.id}: unbekannte Gruppe {self.group!r}")
        if not set(self.marks) <= set(MARKS):
            raise ValueError(f"Bereich {self.id}: unbekannte Markierung in {self.marks!r}")
        for text in (self.name, self.sentence):
            if set(text) != {"de", "en"} or not all(str(v).strip() for v in text.values()):
                raise ValueError(f"Bereich {self.id}: Name und Satz brauchen de und en")
        for pattern in self.tools:
            check_pattern(pattern)


def _a(id_: str, group: str, de: str, en: str, sde: str, sen: str, marks: tuple[str, ...], *tools: str) -> Area:
    return Area(id_, group, {"de": de, "en": en}, {"de": sde, "en": sen}, marks, tools)


R, P, C = "risky", "private", "costly"
CORE_AREAS: tuple[Area, ...] = (
    _a("files_read", "files_code", "Dateien lesen", "Read files", "Dateien und PDFs im Projekt lesen",
       "Read files and PDFs in the project", (), "file_read", "read_document"),
    _a("files_write", "files_code", "Dateien ändern", "Change files",
       "Dateien im Projekt anlegen, ändern und überschreiben", "Create, change and overwrite files in the project",
       (R,), "file_write", "file_patch"),
    _a("code", "files_code", "Code verstehen", "Understand code",
       "Zusammenhänge im Code, Statistiken und die Git-Historie ansehen",
       "Look at how code fits together, statistics and the Git history", (),
       "graph_*", "plugin__code-metrics__*", "plugin__git-stats__*", "plugin__file-search__*"),
    _a("web_search", "internet", "Im Internet suchen", "Search the internet",
       "Suchmaschine befragen und Recherche-Berichte mit Quellen erstellen",
       "Query a search engine and write research reports with sources", (C,), "web_search", "research_report"),
    _a("web_open", "internet", "Webseiten öffnen", "Open web pages",
       "Seiten abrufen, im Browser bedienen und Webdienste ansprechen",
       "Fetch pages, use the browser and talk to web services", (R,),
       "fetch_url", "web_browser", "plugin__http-tester__*"),
    _a("memory", "organize", "Gedächtnis", "Memory", "Sich Dinge merken und frühere Gespräche durchsuchen",
       "Remember things and search earlier conversations", (P,),
       "read_memory", "write_memory", "search_memory", "datamining_*"),
    _a("tasks", "organize", "Aufgaben & Ideen", "Tasks & ideas", "Tasks, Ideen und den Notizzettel lesen und pflegen",
       "Read and maintain tasks, ideas and the scratchpad", (), "task_*", "idea_*", "read_scratchpad"),
    _a("tickets", "organize", "Tickets & GitHub", "Tickets & GitHub",
       "Tickets anlegen und bearbeiten, GitHub-Projekte ansehen und verknüpfen",
       "Create and edit tickets, view and link GitHub projects", (), "ticket_*", "github_project_*"),
    _a("diagrams", "organize", "Diagramme & Skizzen", "Diagrams & sketches",
       "Diagramme und Blueprint-Entwürfe erstellen", "Create diagrams and blueprint drafts", (),
       "diagramm_*", "blueprint_*"),
    _a("media", "creative", "Bilder, Musik, Video", "Images, music, video",
       "Medien erzeugen, Bilder beschreiben, Audio abtippen", "Generate media, describe images, transcribe audio", (C,),
       "generate_*", "analyze_image", "transcribe_audio", "plugin__minimax-creator__*"),
    _a("atelier", "creative", "Atelier", "Atelier", "Figuren, Stil und Drehbuch im Atelier vorbereiten",
       "Prepare characters, style and screenplay in the atelier", (), "atelier_*"),
    _a("books", "creative", "Bücher schreiben", "Write books", "Im Storyteller lesen und Vorschläge ablegen",
       "Read in the storyteller and leave suggestions", (), "storyteller_*"),
    _a("delegate", "team", "Andere Agenten beauftragen", "Hand work to other agents",
       "Aufgaben an Helfer-Agenten abgeben", "Pass tasks on to helper agents", (C,), "ask_agent"),
    _a("helpers", "team", "Helfer anlegen", "Create helpers",
       "Neue Spezialisten und Skills im Projekt anlegen und einstellen",
       "Create and configure new specialists and skills in the project", (R,),
       "create_specialist", "configure_specialist", "list_specialists", "write_skill", "delete_skill", "list_projects"),
    _a("mail_read", "post", "E-Mails lesen", "Read emails", "Postfächer durchsuchen und Mails mit Anhängen lesen",
       "Search mailboxes and read mails with attachments", (P,),
       "read_mail", "mailbox_accounts", "mailbox_search", "mailbox_read", "mailbox_attachment"),
    _a("mail_write", "post", "E-Mails schreiben", "Write emails",
       "Entwürfe anlegen, Mails markieren, verschieben und senden", "Create drafts, flag, move and send mails", (R, P),
       "send_mail", "mailbox_draft", "mailbox_flag", "mailbox_move"),
    _a("home_view", "home", "Haus ansehen", "View the house",
       "Zustand von Lampen, Sensoren und Geräten lesen", "Read the state of lamps, sensors and devices", (),
       "ha_list_entities", "ha_get_state", "ha_render_template"),
    _a("home_control", "home", "Haus steuern", "Control the house", "Geräte im Haus schalten",
       "Switch devices in the house", (R,), "ha_call_service"),
    _a("downloads", "home", "Filme & Musik laden", "Download films & music", "Medien suchen und herunterladen",
       "Search for and download media", (R,), "mediacenter_*"),
    _a("health", "private", "Gesundheit", "Health", "Patientenakte und Gesundheitsdaten lesen",
       "Read the patient record and health data", (P,), "query_fhir_data", "query_health_data"),
    _a("finance", "private", "Finanzen & Krypto", "Finance & crypto", "Kurse, Analysen und das eigene Portfolio ansehen",
       "View prices, analyses and your own portfolio", (P,), "query_crypto_*", "query_portfolio"),
    _a("legal", "private", "Recht", "Legal", "Rechtsfälle, Normen, Fristen und Briefentwürfe",
       "Legal cases, statutes, deadlines and letter drafts", (P,), "legal_*"),
    _a("shell", "server", "Befehle ausführen", "Run commands", "Programme und Befehle direkt auf dem Server starten",
       "Start programs and commands directly on the server", (R,), "shell_exec"),
    _a("server_admin", "server", "Server verwalten", "Manage the server", "Webmin: Systemstatus und Einstellungen",
       "Webmin: system status and settings", (R,), "webmin_status", "webmin_call"),
    _a("game_server", "server", "Spiele-Server", "Game server", "RoM-Server: Zonen und Accounts verwalten",
       "RoM server: manage zones and accounts", (R,), "rom_*"),
    _a("security_research", "server", "Sicherheitsforschung", "Security research",
       "Tor-Quellen prüfen und Reverse-Engineering-Fälle", "Check Tor sources and reverse-engineering cases", (R,),
       "opentor_*", "reverse_*"),
)

#: Grundausstattung: harmlos und für jeden Agenten nötig – kein Schalter (Regel 5).
BASE_TOOLS: frozenset[str] = frozenset({
    "list_skills", "load_skill", "help_search", "help_read", "error_report_prepare", "list_prompts", "get_prompt",
    "save_prompt", "todo_write", "find_tools", "find_skills", "run_tool",
})


def matches(pattern: str, name: str) -> bool:
    return name.startswith(pattern[:-1]) if pattern.endswith("*") else name == pattern


def tools_of(area: Area, registered: Iterable[str]) -> list[str]:
    """Die registrierten Tool-Namen dieses Bereichs (Muster aufgelöst), sortiert und ohne Doppelte."""
    names = list(registered)
    return sorted({n for n in names if any(matches(p, n) for p in area.tools)})
