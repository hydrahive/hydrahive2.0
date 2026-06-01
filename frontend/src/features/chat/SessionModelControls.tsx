import { useTranslation } from "react-i18next"
import { ModelPicker } from "./ModelPicker"
import { ReasoningEffortPill } from "./ReasoningEffortPill"
import { chatApi } from "./api"
import { agentsApi } from "@/features/agents/api"
import type { AgentBrief, Session } from "./types"

interface Props {
  session: Session
  agent: AgentBrief
  onSessionChanged: (session: Session) => void
  onAgentChanged?: (agent: AgentBrief) => void
}

/** Modell-Picker + Reasoning-Effort für die aktive Session/Agent.
 *  Kapselt die Override-Logik (Agent-Default vs. Session-Override) und die
 *  modellabhängige Effort-Unterstützung an einer Stelle. */
export function SessionModelControls({ session, agent, onSessionChanged, onAgentChanged }: Props) {
  const { t } = useTranslation("chat")

  const activeModel = (session.metadata as { model_override?: string })?.model_override || agent.llm_model || ""
  const strippedModel = activeModel.replace(/^anthropic\//, "")
  const isClaudeModel = strippedModel.startsWith("claude-")
  const supportsReasoningEffort = isClaudeModel || /^MiniMax-M2/.test(strippedModel)
  const supportsExtendedEffort = /^claude-(opus-4-6|opus-4-7|opus-4-8|sonnet-4-6)/.test(strippedModel)

  return (
    <div className="border-t border-white/[8%] bg-black/20">
      <div className="px-2.5 py-2 border-b border-white/[5%] flex items-center gap-2">
        <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-9 shrink-0">{t("model")}</span>
        <div className="flex-1 min-w-0">
          <ModelPicker
            current={agent.llm_model}
            hint={t("model_hint")}
            fullWidth
            onPick={async (m) => {
              const updatedAgent = await agentsApi.update(agent.id, { llm_model: m })
              onAgentChanged?.({ ...agent, llm_model: updatedAgent.llm_model })
              if ((session.metadata as { model_override?: string })?.model_override) {
                const updated = await chatApi.updateSession(session.id, { model_override: "" })
                onSessionChanged(updated)
              }
            }}
          />
        </div>
      </div>
      {supportsReasoningEffort && (
        <div className="px-2.5 py-2 flex items-center gap-2">
          <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-9 shrink-0">{t("effort_label")}</span>
          <ReasoningEffortPill
            current={(session.metadata as { reasoning_effort?: string })?.reasoning_effort}
            extended={supportsExtendedEffort}
            onSelect={async (effort) => {
              const updated = await chatApi.updateSession(session.id, { reasoning_effort: effort })
              onSessionChanged(updated)
            }}
          />
        </div>
      )}
    </div>
  )
}
