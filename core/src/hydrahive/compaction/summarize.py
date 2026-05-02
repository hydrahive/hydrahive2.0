from __future__ import annotations

import logging

from hydrahive.compaction._chunking import split_at_message_boundaries
from hydrahive.compaction._prompts import MERGE_INSTRUCTIONS as _MERGE_INSTRUCTIONS
from hydrahive.compaction._prompts import SUMMARY_INSTRUCTIONS as _SUMMARY_INSTRUCTIONS
from hydrahive.compaction.tokens import context_window_for, estimate_dense_text, estimate_text

logger = logging.getLogger(__name__)

_USABLE_FRACTION = 0.80


async def summarize(
    *,
    model: str,
    serialized_history: str,
    previous_summary: str | None = None,
    facts: dict | None = None,
    max_tokens: int = 4096,
) -> str:
    """Strukturierte Zusammenfassung. Bei zu großem Input wird verlustfrei
    chunked: History wird in passende Stücke gesplittet, jeder einzeln
    zusammengefasst, dann hierarchisch gemergt (#81 Variante B).
    """
    window = context_window_for(model)
    instructions_tokens = estimate_text(_SUMMARY_INSTRUCTIONS)
    facts_str = _facts_string(facts) if facts else ""
    facts_tokens = estimate_text(facts_str)
    prev_tokens = estimate_text(previous_summary) if previous_summary else 0

    fixed_overhead = instructions_tokens + facts_tokens + prev_tokens + max_tokens + 1000
    usable_for_history = int(window * _USABLE_FRACTION) - fixed_overhead
    if usable_for_history < 10_000:
        usable_for_history = 10_000

    history_tokens = estimate_dense_text(serialized_history)
    if history_tokens <= usable_for_history:
        return await _single_summarize(
            model, _SUMMARY_INSTRUCTIONS, serialized_history,
            previous_summary, facts_str, max_tokens,
        )

    logger.info(
        "Compaction-Chunking: %d Tokens > %d nutzbar — splitte in Chunks",
        history_tokens, usable_for_history,
    )
    chunks = split_at_message_boundaries(serialized_history, usable_for_history)
    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        logger.info("Chunk %d/%d (%d chars) → summarize", i, len(chunks), len(chunk))
        s = await _single_summarize(
            model, _SUMMARY_INSTRUCTIONS, chunk,
            previous_summary if i == 1 else None, facts_str if i == 1 else "",
            max_tokens,
        )
        chunk_summaries.append(s)

    return await _merge_summaries(model, chunk_summaries, max_tokens, usable_for_history)


def _facts_string(facts: dict) -> str:
    parts = ["STRUKTURIERTE FAKTEN (gesicherte Wahrheit, übernimm wörtlich wo passend):"]
    for k, v in facts.items():
        parts.append(f"- {k}: {v}")
    parts.append("")
    return "\n".join(parts)


async def _single_summarize(
    model: str,
    system_prompt: str,
    history_text: str,
    previous_summary: str | None,
    facts_str: str,
    max_tokens: int,
) -> str:
    user_parts: list[str] = []
    if facts_str:
        user_parts.append(facts_str)
    if previous_summary:
        user_parts.append("BISHERIGE ZUSAMMENFASSUNG (aktualisieren statt überschreiben):")
        user_parts.append(previous_summary.strip())
        user_parts.append("")
        user_parts.append("NEUE NACHRICHTEN seit dieser Zusammenfassung:")
    else:
        user_parts.append("KONVERSATION zum Zusammenfassen:")
    user_parts.append(history_text)

    from hydrahive.runner.llm_bridge import call_with_tools
    blocks, _ = await call_with_tools(
        model=model,
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": "\n".join(user_parts)}],
        tools=[],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    out_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "\n".join(p for p in out_parts if p).strip()


async def _merge_summaries(
    model: str, summaries: list[str], max_tokens: int, usable_per_call: int,
) -> str:
    """Hierarchisches Merging: wenn alle Summaries zusammen ins Window passen,
    ein einzelner Merge. Sonst rekursiv in Gruppen mergen."""
    combined = "\n\n---\n\n".join(
        f"## Teil-Zusammenfassung {i+1}/{len(summaries)}\n\n{s}"
        for i, s in enumerate(summaries)
    )
    if estimate_dense_text(combined) <= usable_per_call:
        from hydrahive.runner.llm_bridge import call_with_tools
        blocks, _ = await call_with_tools(
            model=model,
            system_prompt=_MERGE_INSTRUCTIONS,
            messages=[{"role": "user", "content": combined}],
            tools=[],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        out = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return "\n".join(p for p in out if p).strip()

    # Rekursion: Gruppen von je 4 Summaries mergen, dann nochmal
    group_size = 4
    groups = [summaries[i:i + group_size] for i in range(0, len(summaries), group_size)]
    merged_groups: list[str] = []
    for g in groups:
        merged_groups.append(await _merge_summaries(model, g, max_tokens, usable_per_call))
    return await _merge_summaries(model, merged_groups, max_tokens, usable_per_call)


