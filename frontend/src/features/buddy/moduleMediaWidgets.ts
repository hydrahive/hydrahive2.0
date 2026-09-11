import type { BuddyMediaWidget } from "@/modules/types"

function isBuddyMediaWidget(value: unknown): value is BuddyMediaWidget {
  if (!value || typeof value !== "object") return false
  const widget = value as Partial<BuddyMediaWidget>
  return typeof widget.id === "string"
    && /^[a-z0-9][a-z0-9-]{0,63}$/.test(widget.id)
    && typeof widget.order === "number"
    && Number.isFinite(widget.order)
    && typeof widget.component === "function"
}

/** Validiert optionale Modulexporte und entfernt doppelte stabile IDs. */
export function normalizeBuddyMediaWidgets(values: unknown[]): BuddyMediaWidget[] {
  const seen = new Set<string>()
  return values
    .filter(isBuddyMediaWidget)
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id))
    .filter((widget) => {
      if (seen.has(widget.id)) return false
      seen.add(widget.id)
      return true
    })
}
