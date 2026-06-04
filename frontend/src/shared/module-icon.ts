import * as Icons from "lucide-react"
import type { LucideIcon } from "lucide-react"

/**
 * Resolve a lucide icon name (string) to a LucideIcon component.
 * Falls back to Icons.Boxes if the name is not found.
 */
export function moduleIcon(name: string): LucideIcon {
  const icon = (Icons as unknown as Record<string, LucideIcon>)[name]
  return icon ?? Icons.Boxes
}
