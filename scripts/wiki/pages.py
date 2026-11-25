"""Seiten des Wikis: Bereich → (Seiten-Name, Titel, Quelle). Ziel hydrahive2-modules/ziele/wiki-automatik.md.

Quelle: ("core", topic)  → Kern-Hilfe   frontend/src/i18n/help/de/<topic>.md
        ("mod", id)      → Modul-Hilfe  hydrahive2-modules/<id>/frontend/help/de/<id>.md
        ("text", name)   → Rahmentext   scripts/wiki/texts/<name>.md
Keine Discord-Quelle. Fehlt eine Datei, fehlt die Seite (Lücke im Protokoll).
"""
from __future__ import annotations

C, M, T = "core", "mod", "text"

SECTIONS: list[tuple[str, list[tuple[str, str, tuple[str, str]]]]] = [
    ("🚀 Einstieg", [
        ("Was-ist-HydraHive", "🐝 Was ist HydraHive?", (T, "Was-ist-HydraHive")),
        ("Erste-Schritte", "🧭 Erste Schritte", (C, "onboarding")),
        ("Buddy", "🤖 Buddy – dein persönlicher Assistent", (C, "buddy")),
        ("Werkstatt-und-Chat", "🛠️ Werkstatt & Chat", (C, "chat")),
        ("Projekte", "📁 Projekte", (C, "projects")),
        ("Dashboard", "📊 Dashboard", (C, "dashboard")),
        ("Hilfe-Assistent", "🆘 Hilfe-Assistent", (C, "helpdesk")),
    ]),
    ("🤖 Agenten & KI", [
        ("Agenten", "🤖 Agenten", (C, "agents")),
        ("LLM-und-Modelle", "🔌 LLM & Modelle", (C, "llm")),
        ("MCP-Server", "🔧 Werkzeuge & MCP-Server", (C, "mcp")),
        ("Skills", "📘 Skills", (C, "skills")),
        ("Gedaechtnis", "🧠 Gedächtnis", (C, "memory")),
        ("Datamining", "⛏️ Datamining", (C, "datamining")),
        ("Zahnfee", "🧚 Zahnfee", (C, "zahnfee")),
        ("Diagramme", "🗺️ Diagramme", (M, "diagramme")),
        ("Hydra-Labor", "🧪 Hydra-Labor", (M, "hydralabor")),
        ("Zerlege-Werkstatt", "🔬 Zerlege-Werkstatt", (M, "zerlegewerkstatt")),
    ]),
    ("🔗 Verbinden & Automatisieren", [
        ("Kommunikation", "📱 Kommunikation", (C, "communication")),
        ("Teamchat", "💬 Teamchat", (C, "teamchat")),
        ("Butler", "🤵 Butler", (C, "butler")),
        ("Credentials", "🔐 Credentials", (C, "credentials")),
        ("Vault", "🔒 Vault", (C, "vault")),
        ("Freigaben-und-Gruppen", "🔑 Freigaben & Gruppen", (C, "access")),
        ("Foederation", "🌐 Föderation", (C, "federation")),
        ("Discord-Serververwaltung", "🛡️ Discord-Serververwaltung", (C, "discord")),
        ("Home-Assistant", "🏠 Home Assistant", (M, "homeassistant")),
        ("Voice", "🎙️ Voice", (M, "voice")),
        ("VoIP", "☎️ VoIP", (M, "telephony")),
        ("Websuche", "🔎 Websuche", (C, "websearch")),
    ]),
    ("🗂️ Organisieren & Alltag", [
        ("Aufgaben", "✅ Aufgaben", (M, "tasks")),
        ("Ideen", "💡 Ideen", (M, "scratchpad")),
        ("Notizbuch", "📓 Notizbuch", (M, "notizbuch")),
        ("Tickets", "🎫 Tickets", (M, "tickets")),
        ("Mailbox", "📬 Mailbox", (M, "mailbox")),
        ("Blueprint", "✏️ Blueprint", (M, "blueprint")),
        ("Haushaltsbuch", "💶 Haushaltsbuch", (M, "haushaltsbuch")),
        ("Cryptoboard", "📈 Cryptoboard", (M, "cryptoboard")),
        ("Meine-Akte", "🩺 Meine Akte", (M, "patientenakte")),
        ("Rechtsberatung", "⚖️ Rechtsberatung", (M, "legal")),
    ]),
    ("🎨 Kreativ & Medien", [
        ("Studio", "🎬 Studio", (M, "studio")),
        ("Atelier", "🎨 Atelier", (M, "atelier")),
        ("Storyteller", "✒️ Storyteller", (M, "storyteller")),
        ("Video-Editor", "✂️ Video-Editor", (M, "videoeditor")),
        ("Tonstudio", "🎚️ Tonstudio", (M, "tonstudio")),
        ("Musik", "🎵 Mediaplayer", (M, "musicplayer")),
        ("Radiostream", "📻 Radiostream", (M, "radiostream")),
        ("Mediacenter", "🎬 Mediacenter", (M, "mediacenter")),
        ("Vitrine", "🖼️ Vitrine", (M, "vitrine")),
        ("Streaming", "⬇️ Streaming-Downloader", (C, "streaming")),
    ]),
    ("🔎 Recherche", [
        ("Deep-Research", "🔭 Deep Research", (M, "deepresearch")),
        ("OpenTor-OSINT", "🧅 OpenTor OSINT", (M, "opentor")),
    ]),
    ("🖥️ Server & Betrieb", [
        ("System", "⚙️ System", (C, "system")),
        ("Admin-Cockpit", "🧭 Admin-Cockpit", (C, "admin")),
        ("Benutzer", "👥 Benutzer", (C, "users")),
        ("Module", "🧩 Module, Plugins & Extensions", (T, "Module")),
        ("Plugins", "🔌 Plugins", (C, "plugins")),
        ("Extensions", "📦 Extensions", (C, "extensions")),
        ("VMs", "🖥️ Virtuelle Maschinen", (C, "vms")),
        ("Container", "📦 Container", (C, "containers")),
        ("Compute-Nodes", "🖧 Compute-Nodes", (C, "nodes")),
        ("Compute-Jobs", "🧮 Compute-Jobs", (C, "jobs")),
        ("Archiv-und-Sicherung", "🗄️ Archiv & Sicherung", (C, "archive")),
        ("Archiver", "💾 Archiver", (M, "archiver")),
        ("Netzwerk", "📡 Netzwerk", (M, "network")),
        ("AI-Sicherheit", "🛡️ AI-Sicherheit", (M, "ai-security")),
        ("Mining", "⛏️ Mining", (M, "mining")),
        ("TV-Werkstatt", "📺 TV-Werkstatt", (M, "tvwerkstatt")),
    ]),
    ("🎮 Freizeit & Eigenständiges", [
        ("Spiele", "🎮 Minigames", (M, "minigames")),
        ("Brettspiele", "♟️ Brettspiele", (M, "boardgames")),
        ("Game-Studio", "🎮 Game Studio", (M, "game-studio")),
        ("Vibe", "✨ Vibe", (M, "vibe")),
        ("HydraVR", "🥽 HydraVR", (M, "vr")),
    ]),
]
