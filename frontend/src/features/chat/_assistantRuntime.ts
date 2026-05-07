import { useExternalStoreRuntime } from "@assistant-ui/react"
import type { AppendMessage, ThreadMessageLike } from "@assistant-ui/react"
import type { Message, ContentBlock, ImageSource } from "./types"

function imgUrl(src: ImageSource): string {
  return src.type === "url" ? src.url : `data:${src.media_type};base64,${src.data}`
}

export function convertMessage(msg: Message, _idx: number): ThreadMessageLike {
  const role =
    msg.role === "compaction" || msg.role === "system" ? "system"
    : msg.role === "tool" ? "assistant"
    : (msg.role as "user" | "assistant")

  let content: ThreadMessageLike["content"]
  if (typeof msg.content === "string") {
    content = msg.content || " "
  } else if (!Array.isArray(msg.content)) {
    content = " "
  } else {
    const toolResults = new Map<string, ContentBlock & { type: "tool_result" }>()
    for (const b of msg.content) {
      if (b.type === "tool_result") toolResults.set(b.tool_use_id, b)
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const parts: any[] = []
    for (const b of msg.content) {
      if (b.type === "text" && b.text) {
        parts.push({ type: "text", text: b.text })
      } else if (b.type === "image") {
        parts.push({ type: "image", image: imgUrl(b.source) })
      } else if (b.type === "tool_use") {
        const res = toolResults.get(b.id)
        parts.push({
          type: "tool-call",
          toolCallId: b.id,
          toolName: b.name,
          args: b.input,
          result: res?.content,
          isError: res?.is_error ?? false,
        })
      }
    }
    content = (parts.length > 0 ? parts : " ") as ThreadMessageLike["content"]
  }

  return {
    id: msg.id,
    role,
    content,
    createdAt: new Date(msg.created_at),
    metadata: {
      custom: {
        _originalRole: msg.role,
        _tokenCount: msg.token_count,
        ...msg.metadata,
      },
    },
  }
}

export function useHydraRuntime(
  messages: Message[],
  busy: boolean,
  send: (text: string, files: File[], resendId?: string) => Promise<void>,
  cancel: () => void,
) {
  return useExternalStoreRuntime<Message>({
    messages,
    isRunning: busy,
    convertMessage,
    onNew: async (msg: AppendMessage) => {
      const text = msg.content
        .filter((p) => p.type === "text")
        .map((p) => (p as { type: "text"; text: string }).text)
        .join("")
      await send(text, [])
    },
    onEdit: async (msg: AppendMessage) => {
      const text = msg.content
        .filter((p) => p.type === "text")
        .map((p) => (p as { type: "text"; text: string }).text)
        .join("")
      await send(text, [], msg.parentId ?? undefined)
    },
    onReload: async (parentId: string | null) => {
      const idx = parentId ? messages.findIndex((m) => m.id === parentId) : -1
      const parent = idx >= 0 ? messages[idx] : [...messages].reverse().find((m) => m.role === "user")
      if (!parent) return
      const text =
        typeof parent.content === "string"
          ? parent.content
          : Array.isArray(parent.content)
          ? parent.content
              .filter((b) => b.type === "text")
              .map((b) => (b as { type: "text"; text: string }).text)
              .join("")
          : ""
      await send(text, [], parent.id)
    },
    onCancel: async () => cancel(),
  })
}
