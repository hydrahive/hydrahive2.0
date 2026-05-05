import { Archive, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { ModelPicker } from "./ModelPicker"
import { TokenMeter } from "./TokenMeter"
import { chatApi } from "./api"
import { agentsApi } from "@/features/agents/api"
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
  onSessionChanged: (session: Session) => void
  onAgentChanged?: (agent: AgentBrief) => void
  tokenRefresh: number
}

export function ChatHeader({
  session, agent, orphaned, compacting, compactNote,
  lastTurnTokens, busy, systemPrompt, onCompact, onDelete, onSessionChanged, onAgentChanged, tokenRefresh,
}: Props) {
  const { t, i18n } = useTranslation("chat")

  return (
    <>
      <div className="px-6 py-3 border-b border-white/[6%] flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <h2
            className="text-sm font-medium text-zinc-200 truncate flex items-center gap-2"
            title={systemPrompt ? `${t("session.system_prompt_label")}\n\n${systemPrompt.slice(0, 1500)}${systemPrompt.length > 1500 ? "…" : ""}` : undefined}
          >
            {session.title}
          </h2>
          <p className="text-xs text-zinc-600 mt-0.5 flex items-center gap-2 flex-wrap">
            <span>{t("session.id_short")}: {session.id.slice(0, 8)}…</span>
            {agent && (
              <span className="text-zinc-500 inline-flex items-center gap-1">
                ·{" "}
                <ModelPicker
                  current={agent.llm_model}
                  hint="Modell für diesen Agenten wechseln (gilt für alle Sessions)"
                  onPick={async (m) => {
                    // Agent-Default ändern (greift sofort + im /model-Output) UND
                    // alten Session-Override räumen damit nichts kollidiert.
                    const updatedAgent = await agentsApi.update(agent.id, { llm_model: m })
                    onAgentChanged?.({ ...agent, llm_model: updatedAgent.llm_model })
                    if ((session.metadata as { model_override?: string })?.model_override) {
                      const updated = await chatApi.updateSession(session.id, { model_override: "" })
                      onSessionChanged(updated)
                    }
                  }}
                />
              </span>
            )}
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
          onClick={onCompact}
          disabled={compacting || orphaned}
          title={t("compact.tooltip")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-amber-300 hover:text-amber-200 hover:bg-amber-500/10 border border-amber-500/20 hover:border-amber-500/30 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {compacting ? <Loader2 size={12} className="animate-spin" /> : <Archive size={12} />}
          {t("compact.button")}
        </button>
      </div>

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
