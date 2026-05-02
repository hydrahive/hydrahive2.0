from hydrahive.compaction.tokens import estimate_dense_text


def split_at_message_boundaries(text: str, max_tokens_per_chunk: int) -> list[str]:
    """Splits serialized history at message boundaries (lines starting with `[Role]:`)."""
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
    return chunks
