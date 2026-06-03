import { useEffect, useRef, useState, type KeyboardEvent } from "react"
import { useTranslation } from "react-i18next"
import { AtSign, Hash, Send } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { EmoteText } from "@/features/chat/EmoteText"
import { Markdown } from "@/features/chat/Markdown"
import { mxidToName } from "./_format"
import type { RoomAgent, TeamMessage } from "./types"

const CARD_BG =
  "linear-gradient(158deg, rgba(255,255,255,.06), rgba(255,255,255,.015)), " +
  "linear-gradient(160deg, rgba(16,78,139,.38), rgba(16,78,139,.13) 65%), #1c2334"

interface ChatViewProps {
  roomName: string
  messages: TeamMessage[]
  agents: RoomAgent[]
  onSend: (text: string) => void | Promise<void>
}

export function ChatView({ roomName, messages, agents, onSend }: ChatViewProps) {
  const { t } = useTranslation("teamchat")
  const me = useAuthStore((s) => s.username)
  const [draft, setDraft] = useState("")
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  // Bot-MXID (@agent-<id>) → Agent-Anzeigename. Der localpart nach "agent-" ist
  // die agent_id; in roomAgents nachschlagen, sonst Rohwert.
  function displayName(sender: string): { label: string; isBot: boolean } {
    const { name, isBot } = mxidToName(sender)
    if (!isBot) return { label: name, isBot }
    const agent = agents.find((a) => a.agent_id === name)
    return { label: agent?.name ?? name, isBot }
  }

  function insertMention(name: string) {
    setDraft((d) => `@${name} ` + d)
    inputRef.current?.focus()
  }

  function submit() {
    const text = draft.trim()
    if (!text) return
    setDraft("")
    Promise.resolve(onSend(text)).catch(() => setDraft(text))
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div
      className="relative flex flex-col flex-1 min-h-0 rounded-[28px] border border-[#104E8B]/70 shadow-2xl shadow-[0_0_50px_-12px_rgba(16,78,139,0.6)] overflow-hidden backdrop-blur"
      style={{ background: CARD_BG }}
    >
      <div className="absolute inset-0 pointer-events-none rounded-[28px] ring-1 ring-inset ring-[#104E8B]/30" />

      <div className="px-5 py-2.5 border-b border-white/[6%] flex items-center gap-2 bg-black/30">
        <Hash size={15} className="text-[var(--hh-accent-text)]" />
        <p className="text-sm font-medium text-zinc-100 truncate">{roomName}</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-xs text-zinc-500 italic text-center pt-8">{t("no_messages")}</p>
        )}
        {messages.map((m) => {
          const { label, isBot } = displayName(m.sender)
          const mine = label === me
          return (
            <div key={m.event_id} className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
              <div className="flex items-center gap-1.5 mb-0.5 px-1">
                {isBot && <span className="text-[10px]">🐙</span>}
                <span className={`text-[11px] font-medium ${isBot ? "text-[var(--hh-accent-text)]" : "text-zinc-400"}`}>
                  {label}
                </span>
              </div>
              <div
                className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm break-words ${
                  isBot ? "" : "whitespace-pre-wrap"
                } ${
                  mine
                    ? "bg-[#104E8B]/50 text-zinc-100 rounded-tr-sm"
                    : "bg-white/[6%] text-zinc-200 rounded-tl-sm"
                }`}
              >
                {/* Mensch: Plain-Text + Inline-Emotes. Bot: Markdown (+ Emotes) —
                    identisch zum regulären Chat (EmoteText/Markdown). */}
                {isBot ? <Markdown text={m.text} /> : <EmoteText text={m.text} />}
              </div>
            </div>
          )
        })}
        <div ref={endRef} />
      </div>

      <div className="border-t border-white/[6%] bg-black/30 px-3 pt-2 pb-3">
        {agents.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap mb-2">
            <span className="text-[10px] text-zinc-500 inline-flex items-center gap-1">
              <AtSign size={11} /> {t("address")}:
            </span>
            {agents.map((a) => (
              <button
                key={a.agent_id}
                onClick={() => insertMention(a.name ?? a.agent_id)}
                className="text-[11px] px-2 py-0.5 rounded-full bg-[#104E8B]/30 text-[var(--hh-accent-text)] hover:bg-[#104E8B]/50 border border-white/[8%] transition-all"
              >
                @{a.name ?? a.agent_id}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder={t("input_placeholder")}
            className="flex-1 resize-none bg-white/[4%] border border-white/[8%] rounded-xl px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#104E8B]/70 max-h-32"
          />
          <button
            onClick={submit}
            disabled={!draft.trim()}
            title={t("send")}
            className="shrink-0 p-2.5 rounded-xl bg-[#104E8B]/60 text-zinc-100 hover:bg-[#104E8B]/80 border border-white/[8%] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
