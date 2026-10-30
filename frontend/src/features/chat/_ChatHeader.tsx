import { Archive, Loader2, SquarePen } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { NewChatHint } from "./NewChatHint"
import { SessionMenu } from "./_SessionMenu"
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
  newSessionBusy?: boolean
  tokenRefresh: number
  cockpitMode?: boolean
  sessions?: Session[]
  activeSessionId?: string | null
  onSelectSession?: (sessionId: string) => void
}

export function ChatHeader({
  session, agent, orphaned, compacting, compactNote,
  lastTurnTokens, busy, systemPrompt, onCompact, onDelete, onNewSession, newSessionBusy = false, tokenRefresh,
  cockpitMode = false, sessions = [], activeSessionId = null, onSelectSession,
}: Props) {
  const { t, i18n } = useTranslation("chat")

  if (cockpitMode) {
    return (
      <>
        <div className="flex min-h-[52px] items-center justify-between gap-2 border-b border-s-rand bg-s-kopf px-[14px]">
          <div className="min-w-0 flex-1">
            <h2
              className="truncate text-sm font-bold text-[#e8eef8]"
              title={systemPrompt ? `${t("session.system_prompt_label")}\n\n${systemPrompt.slice(0, 1500)}${systemPrompt.length > 1500 ? "…" : ""}` : undefined}
            >
              {session.title || t("session.untitled", { defaultValue: "Neue Session" })}
            </h2>
            <p className="mt-0.5 flex min-w-0 flex-nowrap items-center gap-2 text-xs text-[#9aa7bc] sm:flex-wrap">
              <span className="hidden sm:inline">Session: {session.id.slice(0, 8)}…</span>
              {agent && <span className="min-w-0 truncate" title={agent.llm_model}>· {agent.llm_model}</span>}
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
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            {sessions.length > 0 && onSelectSession && (
              <SessionMenu session={session} sessions={sessions} activeSessionId={activeSessionId} onSelectSession={onSelectSession} />
            )}
            <div className="hidden sm:flex" data-token-meter="1"><TokenMeter sessionId={session.id} refresh={tokenRefresh} /></div>
            <button
              onClick={onCompact}
              disabled={compacting || orphaned}
              title={t("compact.tooltip")}
              aria-label="Komprimieren"
              className="shrink-0 rounded-[4px] border border-s-rand bg-s-innen px-2 py-1.5 sm:px-3 text-xs font-bold text-[#e8eef8] transition-colors hover:border-s-rand-hover hover:bg-s-hebung disabled:cursor-not-allowed disabled:opacity-30"
            >
              {compacting ? <Loader2 size={12} className="inline animate-spin sm:mr-1" /> : <Archive size={12} className="inline sm:mr-1" />}
              <span className="hidden sm:inline">Komprimieren</span>
            </button>
            <button
              onClick={onNewSession}
              disabled={busy || newSessionBusy}
              title={t("session.new_chat")}
              aria-label={newSessionBusy ? "Übergabe wird erstellt …" : "Neuer Chat"}
              className="shrink-0 rounded-[4px] border border-transparent bg-gradient-to-br from-[#1fb6ff] to-[#8b5cf6] px-2 py-1.5 sm:px-3 text-xs font-bold text-white transition-colors hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-30"
            >
              {newSessionBusy ? <Loader2 size={12} className="inline animate-spin sm:mr-1" /> : <SquarePen size={12} className="inline sm:mr-1" />}
              <span className="hidden sm:inline">{newSessionBusy ? "Übergabe wird erstellt …" : "Neuer Chat"}</span>
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
      <div className="flex h-[52px] items-center gap-2 border-b sm:gap-3 border-s-rand bg-s-kopf px-[14px]">
        <div className="flex-1 min-w-0">
          <h2
            className="text-sm font-bold text-[#e8eef8] truncate flex items-center gap-2"
            title={systemPrompt ? `${t("session.system_prompt_label")}\n\n${systemPrompt.slice(0, 1500)}${systemPrompt.length > 1500 ? "…" : ""}` : undefined}
          >
            {session.title}
          </h2>
          <p className="text-xs text-[#9aa7bc] mt-0.5 flex items-center gap-2 flex-wrap">
            <span className="hidden sm:inline">{t("session.id_short")}: {session.id.slice(0, 8)}…</span>
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
        <div className="hidden sm:flex" data-token-meter="1"><TokenMeter sessionId={session.id} refresh={tokenRefresh} /></div>
        <HelpButton topic="chat" />
        <button
          onClick={onNewSession}
          disabled={busy || newSessionBusy}
          title={t("session.new_chat")}
          aria-label={t("session.new_chat")}
          className="flex shrink-0 items-center gap-1.5 rounded-[4px] border border-s-rand bg-s-innen px-2 py-1.5 sm:px-3 text-xs text-[#e8eef8] transition-colors hover:border-s-rand-hover hover:bg-s-hebung disabled:cursor-not-allowed disabled:opacity-30"
        >
          {newSessionBusy ? <Loader2 size={12} className="animate-spin" /> : <SquarePen size={12} />}
          <span className="hidden sm:inline">{newSessionBusy ? "Übergabe wird erstellt …" : t("session.new_chat")}</span>
        </button>
        <button
          onClick={onCompact}
          disabled={compacting || orphaned}
          title={t("compact.tooltip")}
          aria-label={t("compact.button")}
          className="flex shrink-0 items-center gap-1.5 rounded-[4px] border border-s-rand bg-s-innen px-2 py-1.5 sm:px-3 text-xs text-[#e8eef8] transition-colors hover:border-s-rand-hover hover:bg-s-hebung disabled:cursor-not-allowed disabled:opacity-30"
        >
          {compacting ? <Loader2 size={12} className="animate-spin" /> : <Archive size={12} />}
          <span className="hidden sm:inline">{t("compact.button")}</span>
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
