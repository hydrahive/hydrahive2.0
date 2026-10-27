from hydrahive.compaction.tokens import _CHARS_PER_TOKEN_DENSE, estimate_dense_text


def split_at_message_boundaries(text: str, max_tokens_per_chunk: int) -> list[str]:
    """Teilt die serialisierte Historie in Stücke ≤ max_tokens_per_chunk.

    Bevorzugt an Nachrichtengrenzen (Zeilen, die mit `[Rolle]:` beginnen). Ist eine einzelne Nachricht größer als ein
    Stück, wird sie an Zeilen geteilt, eine zu lange Zeile mitten in der Zeile (Task 5406d099: vorher blieb eine
    riesige Nachricht EIN Stück → „prompt is too long“ bei jedem Compact). Es geht nichts verloren:
    "\\n".join(stücke) == text.
    """
    lines = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for line in lines:
        line_tokens = estimate_dense_text(line) + 1
        is_msg_boundary = line.startswith("[") and "]:" in line
        if current and is_msg_boundary and current_tokens + line_tokens > max_tokens_per_chunk:
            chunks.append("\n".join(current))
            current = []
            current_tokens = 0
        current.append(line)
        current_tokens += line_tokens
    if current:
        chunks.append("\n".join(current))
    out: list[str] = []
    for c in chunks:
        out.extend(_hard_split(c, max_tokens_per_chunk) if estimate_dense_text(c) > max_tokens_per_chunk else [c])
    return out


def _hard_split(chunk: str, max_tokens: int) -> list[str]:
    """Zu großes Stück an Zeilen teilen; eine zu lange Zeile in Zeichen-Stücke."""
    max_chars = max(1, int(max_tokens * _CHARS_PER_TOKEN_DENSE))
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for line in chunk.split("\n"):
        if len(line) > max_chars:
            if current:
                pieces.append("\n".join(current))
                current, size = [], 0
            pieces.extend(line[i:i + max_chars] for i in range(0, len(line), max_chars))
            continue
        add = len(line) + (1 if current else 0)
        if current and size + add > max_chars:
            pieces.append("\n".join(current))
            current, size = [], 0
            add = len(line)
        current.append(line)
        size += add
    if current:
        pieces.append("\n".join(current))
    return pieces
