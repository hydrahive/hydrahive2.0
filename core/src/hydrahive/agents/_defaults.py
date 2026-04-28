from __future__ import annotations

DEFAULT_TOOLS: dict[str, list[str]] = {
    "master": [
        "shell_exec", "file_read", "file_write", "file_patch", "file_search",
        "dir_list", "web_search", "http_request", "read_memory", "write_memory",
        "todo_write", "ask_agent", "send_mail",
    ],
    "project": [
        "shell_exec", "file_read", "file_write", "file_patch", "file_search",
        "dir_list", "read_memory", "write_memory", "todo_write", "ask_agent",
    ],
    "specialist": [],
}

DEFAULT_TEMPERATURE = 0.7
# Höher als üblich, damit Code-Generation (Tetris, längere Files) durchläuft.
# Ein Tool-Use mit 5000-Zeichen-content braucht ~1500-2000 Tokens nur fürs Input-JSON.
DEFAULT_MAX_TOKENS = 8192
DEFAULT_THINKING_BUDGET = 0
