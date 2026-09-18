import { useParams, useSearchParams } from "react-router-dom"
import { ChatPane } from "./ChatPane"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"

export function ChatPage(props?: { embedded?: boolean }) {
  const embedded = props?.embedded ?? false
  const { sid } = useParams<{ sid?: string }>()
  const [searchParams] = useSearchParams()
  const deepLinkSid = sid ?? searchParams.get("session") ?? null

  if (embedded) return <ChatPane deepLinkSid={deepLinkSid} />

  return (
    <CockpitShell title="Werkstatt" className="cockpit-route flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="werkstatt" context="Chat-Arbeitsfläche" />
      <main className="min-h-0 flex-1 overflow-hidden p-[10px]">
        <div className="h-full min-h-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b]">
          <ChatPane deepLinkSid={deepLinkSid} />
        </div>
      </main>
    </CockpitShell>
  )
}
