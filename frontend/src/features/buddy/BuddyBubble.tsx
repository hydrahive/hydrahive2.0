import { CompactionBlock } from "@/features/chat/CompactionBlock"
import type { ContentBlock, Message } from "@/features/chat/types"
import { BuddyUserBubble } from "./_BuddyUserBubble"
import { BuddyAssistantBubble } from "./_BuddyAssistantBubble"

interface Props {
  message: Message
  onResend?: (messageId: string, newText: string) => void
  onRetry?: (assistantMessageId: string) => void
  busy?: boolean
}

export function BuddyBubble({ message, onResend, onRetry, busy }: Props) {
  if (message.role === "compaction") return <CompactionBlock message={message} />
  const blocks = normalize(message.content)
  if (message.role === "user") {
    return <BuddyUserBubble message={message} blocks={blocks} onResend={onResend} busy={busy} />
  }
  return <BuddyAssistantBubble message={message} blocks={blocks} onRetry={onRetry} busy={busy} />
}

function normalize(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === "string") return [{ type: "text", text: content }]
  return content
}
