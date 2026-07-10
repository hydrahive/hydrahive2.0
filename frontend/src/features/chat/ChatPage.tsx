import { useRef } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import { ChatPane } from "./ChatPane"

export function ChatPage() {
  const { sid } = useParams<{ sid?: string }>()
  const [searchParams] = useSearchParams()
  const deepLinkSidRef = useRef(sid ?? searchParams.get("session") ?? null)

  return <ChatPane deepLinkSid={deepLinkSidRef.current} />
}
