/** Modellwechsel einer Antwort (Spec agent-templates.md Kap. 8) aus den Nachrichten-Metadaten lesen. */
export interface ModelSwitchInfo {
  from_model: string
  to_model: string
  reason: string
}

const REASONS = new Set(["auth", "quota", "rate_limit", "overload", "timeout", "stream_abort", "empty", "cooldown"])

export function readModelSwitches(metadata?: Record<string, unknown>): ModelSwitchInfo[] {
  const raw = metadata?.model_switches
  if (!Array.isArray(raw)) return []
  return raw.flatMap((s) => {
    if (!s || typeof s !== "object") return []
    const { from_model, to_model, reason } = s as Record<string, unknown>
    if (typeof from_model !== "string" || typeof to_model !== "string" || typeof reason !== "string") return []
    return [{ from_model, to_model, reason: REASONS.has(reason) ? reason : "other" }]
  })
}
