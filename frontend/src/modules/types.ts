import type { ComponentType } from "react"

export interface BuddyMediaWidgetProps {
  onPrompt: (text: string) => void
  projectId?: string | null
}

/** Optionaler, stabil identifizierter Modulbeitrag für den Buddy-Media-Slot. */
export interface BuddyMediaWidget {
  id: string
  order: number
  component: ComponentType<BuddyMediaWidgetProps>
}
