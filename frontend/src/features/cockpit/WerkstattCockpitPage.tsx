import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { ChatPage } from "@/features/chat/ChatPage"

/** Cockpit wrapper for the general Werkstatt/chat workspace. */
export function WerkstattCockpitPage() {
  return (
    <CockpitShell
      title="Werkstatt"
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/werkstatt" context="Chat und Sessions" />
      <main className="min-h-0 flex-1 overflow-hidden p-[10px]">
        <ChatPage embedded />
      </main>
    </CockpitShell>
  )
}
