import { CompactionBlock } from "./CompactionBlock"
import { UserBubble } from "./_UserBubble"
import { AssistantBubble } from "./_AssistantBubble"
import type { ContentBlock, Message } from "./types"

interface Props {
  message: Message
  onResend?: (messageId: string, newText: string) => void
  onRetry?: (assistantMessageId: string) => void
  busy?: boolean
}

function normalizeContent(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === "string") return [{ type: "text", text: content }]
  return content
}

export function MessageBubble({ message, onResend, onRetry, busy }: Props) {
  if (message.role === "compaction") return <CompactionBlock message={message} />

  const blocks = normalizeContent(message.content)
  const isLive = message.id.startsWith("live-")
  const isPersisted = !message.id.startsWith("local-") && !isLive

  if (message.role === "user") {
    return <UserBubble message={message} blocks={blocks} isPersisted={isPersisted} busy={busy} onResend={onResend} />
  }

  return <AssistantBubble message={message} blocks={blocks} isLive={isLive} isPersisted={isPersisted} busy={busy} onRetry={onRetry} />
}
