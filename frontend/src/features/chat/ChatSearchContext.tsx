import { createContext, useCallback, useContext, useMemo, useState } from "react"
import type { Message } from "./types"

interface SearchState {
  query: string
  activeIdx: number
  matchCount: number
  activeMessageId: string | null
  setQuery: (q: string) => void
  next: () => void
  prev: () => void
}

const Ctx = createContext<SearchState | null>(null)

export function useChatSearch(): SearchState {
  return useContext(Ctx) ?? {
    query: "", activeIdx: 0, matchCount: 0, activeMessageId: null,
    setQuery: () => {}, next: () => {}, prev: () => {},
  }
}

function msgText(msg: Message): string {
  if (typeof msg.content === "string") return msg.content
  if (!Array.isArray(msg.content)) return ""
  return msg.content
    .map((b) => {
      if (b.type === "text") return (b as { type: "text"; text: string }).text ?? ""
      if (b.type === "tool_result") return (b as { type: "tool_result"; content: string }).content ?? ""
      return ""
    })
    .join(" ")
}

export function ChatSearchProvider({ messages, children }: { messages: Message[]; children: React.ReactNode }) {
  const [query, setQueryRaw] = useState("")
  const [activeIdx, setActiveIdx] = useState(0)

  const matches = useMemo(() => {
    if (!query.trim()) return []
    const q = query.toLowerCase()
    return messages.filter((m) => msgText(m).toLowerCase().includes(q))
  }, [messages, query])

  const matchCount = matches.length
  const activeMessageId = matches[activeIdx]?.id ?? null

  const setQuery = useCallback((q: string) => { setQueryRaw(q); setActiveIdx(0) }, [])
  const next = useCallback(() => setActiveIdx((i) => matchCount ? (i + 1) % matchCount : 0), [matchCount])
  const prev = useCallback(() => setActiveIdx((i) => matchCount ? (i - 1 + matchCount) % matchCount : 0), [matchCount])

  return (
    <Ctx.Provider value={{ query, activeIdx, matchCount, activeMessageId, setQuery, next, prev }}>
      {children}
    </Ctx.Provider>
  )
}
