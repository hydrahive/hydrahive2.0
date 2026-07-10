import { useState } from "react"
import { Archive, ChevronDown, Loader2, SquarePen } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { NewChatHint } from "./NewChatHint"
import { TokenMeter } from "./TokenMeter"
import type { ChatState } from "./useChat"
import type { AgentBrief, Session } from "./types"

interface Props {
  session: Session
  agent: AgentBrief | null
  orphaned: boolean
  compacting: boolean
  compactNote: string | null
  lastTurnTokens: ChatState["lastTurnTokens"]
  busy: boolean
  systemPrompt: string
  onCompact: () => void
  onDelete: () => void
  onNewSession: () => void
  tokenRefresh: number
  cockpitMode?: boolean
  sessions?: Session[]
  activeSessionId?: string | null
  onSelectSession?: (sessionId: string) => void
}

export function ChatHeader({
  session, agent, orphaned, compacting, compactNote,
  lastTurnTokens, busy, systemPrompt, onCompact, onDelete, onNewSession, tokenRefresh,
  cockpitMode = false, sessions = [], activeSessionId = null, onSelectSession,
}: Props) {
  const { t, i18n } = useTranslation("chat")
  const [sessionMenuOpen, setSessionMenuOpen] = useState(false)

  if (cockpitMode) {
    return (
      <>
        <div className="flex min-h-[52px] items-center justify-between gap-3 border-b border-[#2a364b] bg-[#121a29] px-[14px]">
          <div className="min-w-0 flex-1">
            <h2
              className="truncate text-sm font-bold text-[#e8eef8]"
              title={systemPrompt ? `${t("session.system_prompt_label")}\n\n${systemPrompt.slice(0, 1500)}${systemPrompt.length > 1500 ? "…" : ""}` : undefined}
            >
              {session.title || t("session.untitled", { defaultValue: "Neue Session" })}
            </h2>
            <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-[#8d9ab0]">
              <span>Session: {session.id.slice(0, 8)}…</span>
              {agent && <span>· {agent.llm_model}</span>}
              {lastTurnTokens && !busy && (
                <span title={t("tokens.tooltip")}>
                  · letzter Turn: <span className="tabular-nums">
                    <span className="text-[#4ade80]">↑{lastTurnTokens.input.toLocaleString(i18n.language)}</span>
                    {" "}<span className="text-[#4ade80]">↓{lastTurnTokens.output.toLocaleString(i18n.language)}</span>
                    {lastTurnTokens.cache_read > 0 && <> <span className="text-[#69d7ff]">⚡{lastTurnTokens.cache_read.toLocaleString(i18n.language)}</span></>}
                    {lastTurnTokens.cache_creation > 0 && <> <span className="text-[#fbbf24]">💾{lastTurnTokens.cache_creation.toLocaleString(i18n.language)}</span></>}
                  </span>
                </span>
              )}
              {compactNote && <span className="text-[#fbbf24]">· {compactNote}</span>}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {sessions.length > 0 && onSelectSession && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setSessionMenuOpen((open) => !open)}
                  className="flex max-w-[240px] items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2.5 py-1.5 text-xs font-semibold text-[#e8eef8] outline-none hover:border-[#46617f]"
                  title="Projekt-Session wählen"
                >
                  <span className="truncate">{session.title || "Neue Session"}</span>
                  <ChevronDown size={12} className="shrink-0 text-[#8d9ab0]" />
                </button>
                {sessionMenuOpen && (
                  <div className="absolute right-0 z-30 mt-1 max-h-[320px] w-[280px] overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-1 shadow-2xl shadow-black/50">
                    {sessions.map((item) => {
                      const active = item.id === (activeSessionId ?? session.id)
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => {
                            onSelectSession(item.id)
                            setSessionMenuOpen(false)
                          }}
                          className={[
                            "block w-full truncate rounded-[4px] px-2.5 py-2 text-left text-xs font-semibold transition-colors",
                            active ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#cdd7e6] hover:bg-[#172133] hover:text-[#e8eef8]",
                          ].join(" ")}
                        >
                          {item.title || "Neue Session"}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
            <TokenMeter sessionId={session.id} refresh={tokenRefresh} />
            <button
              onClick={onCompact}
              disabled={compacting || orphaned}
              title={t("compact.tooltip")}
              className="rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-1.5 text-xs font-bold text-[#e8eef8] transition-colors hover:border-[#46617f] hover:bg-[#1b2536] disabled:cursor-not-allowed disabled:opacity-30"
            >
              {compacting ? <Loader2 size={12} className="mr-1 inline animate-spin" /> : <Archive size={12} className="mr-1 inline" />}
              Komprimieren
            </button>
            <button
              onClick={onNewSession}
              disabled={busy}
              title={t("session.new_chat")}
              className="rounded-[4px] border border-transparent bg-gradient-to-br from-[#1fb6ff] to-[#8b5cf6] px-3 py-1.5 text-xs font-bold text-white transition-colors hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-30"
            >
              <SquarePen size={12} className="mr-1 inline" /> Neuer Chat
            </button>
          </div>
        </div>
        <NewChatHint inputTokens={lastTurnTokens?.input ?? null} onNewChat={onNewSession} />
        {orphaned && (
          <div className="mx-3 mt-3 flex items-center justify-between gap-4 rounded-[4px] border border-amber-500/30 bg-amber-500/[6%] px-4 py-3 text-sm text-amber-200">
            <span>{t("session.orphaned_banner")}</span>
            <button onClick={onDelete} className="rounded-[4px] bg-amber-500/20 px-3 py-1 text-xs text-amber-100 hover:bg-amber-500/30">
              {t("session.delete_session")}
            </button>
          </div>
        )}
      </>
    )
  }

  return (
    <>
      <div className="flex h-[52px] items-center gap-3 border-b border-[#2a364b] bg-[#121a29] px-[14px]">
        <div className="flex-1 min-w-0">
          <h2
            className="text-sm font-bold text-[#e8eef8] truncate flex items-center gap-2"
            title={systemPrompt ? `${t("session.system_prompt_label")}\n\n${systemPrompt.slice(0, 1500)}${systemPrompt.length > 1500 ? "…" : ""}` : undefined}
          >
            {session.title}
          </h2>
          <p className="text-xs text-[#8d9ab0] mt-0.5 flex items-center gap-2 flex-wrap">
            <span>{t("session.id_short")}: {session.id.slice(0, 8)}…</span>
            {agent && <span className="text-zinc-500">· {agent.llm_model.replace(/^anthropic\//, "")}</span>}
            {lastTurnTokens && !busy && (
              <span className="text-zinc-500" title={t("tokens.tooltip")}>
                · {t("tokens.last_turn")}: <span className="tabular-nums">
                  <span className="text-emerald-400/80">↑{lastTurnTokens.input.toLocaleString(i18n.language)}</span>
                  {" "}<span className="text-emerald-400/80">↓{lastTurnTokens.output.toLocaleString(i18n.language)}</span>
                  {lastTurnTokens.cache_read > 0 && (
                    <> {" "}<span className="text-cyan-400/80">⚡{lastTurnTokens.cache_read.toLocaleString(i18n.language)}</span></>
                  )}
                  {lastTurnTokens.cache_creation > 0 && (
                    <> {" "}<span className="text-amber-400/80">💾{lastTurnTokens.cache_creation.toLocaleString(i18n.language)}</span></>
                  )}
                </span>
              </span>
            )}
            {compactNote && <span className="text-amber-400">· {compactNote}</span>}
          </p>
        </div>
        <TokenMeter sessionId={session.id} refresh={tokenRefresh} />
        <HelpButton topic="chat" />
        <button
          onClick={onNewSession}
          disabled={busy}
          title={t("session.new_chat")}
          className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-1.5 text-xs text-[#e8eef8] transition-colors hover:border-[#46617f] hover:bg-[#1b2536] disabled:cursor-not-allowed disabled:opacity-30"
        >
          <SquarePen size={12} />
          {t("session.new_chat")}
        </button>
        <button
          onClick={onCompact}
          disabled={compacting || orphaned}
          title={t("compact.tooltip")}
          className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-1.5 text-xs text-[#e8eef8] transition-colors hover:border-[#46617f] hover:bg-[#1b2536] disabled:cursor-not-allowed disabled:opacity-30"
        >
          {compacting ? <Loader2 size={12} className="animate-spin" /> : <Archive size={12} />}
          {t("compact.button")}
        </button>
      </div>

      <NewChatHint inputTokens={lastTurnTokens?.input ?? null} onNewChat={onNewSession} />

      {orphaned && (
        <div className="mx-6 mt-4 px-4 py-3 rounded-lg border border-amber-500/30 bg-amber-500/[6%] text-sm text-amber-200 flex items-center justify-between gap-4">
          <span>{t("session.orphaned_banner")}</span>
          <button
            onClick={onDelete}
            className="px-3 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 text-xs whitespace-nowrap"
          >
            {t("session.delete_session")}
          </button>
        </div>
      )}
    </>
  )
}
