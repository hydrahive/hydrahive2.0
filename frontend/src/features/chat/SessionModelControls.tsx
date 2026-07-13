import { useTranslation } from "react-i18next"
import { ModelPicker } from "./ModelPicker"
import { ReasoningEffortPill } from "./ReasoningEffortPill"
import { chatApi } from "./api"
import { useEffortLevels } from "@/features/llm/effort"
import type { AgentBrief, Session } from "./types"

interface Props {
  session: Session
  agent: AgentBrief
  onSessionChanged: (session: Session) => void
}

/** Modell-Picker + Reasoning-Effort für die aktive Session/Agent.
 *  Das Modell wird als SESSION-Override (session.metadata.model_override)
 *  gesetzt — session-lokal, ohne Admin-Rechte, und der Runner liest es pro
 *  Iteration frisch (greift also ab dem nächsten Turn/Schritt). Der Agent-
 *  Default bleibt unangetastet; „Reset" nimmt den Override wieder zurück. */
export function SessionModelControls({ session, agent, onSessionChanged }: Props) {
  const { t } = useTranslation("chat")
  const override = (session.metadata as { model_override?: string })?.model_override
  const activeModel = override || agent.llm_model || ""
  const effortLevels = useEffortLevels(activeModel)
  const supportsReasoningEffort = effortLevels.length > 0

  return (
    <div className="border-t border-white/[8%] bg-black/20">
      <div className="px-2.5 py-2 border-b border-white/[5%] flex items-center gap-2">
        <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-9 shrink-0">{t("model")}</span>
        <div className="flex-1 min-w-0">
          <ModelPicker
            current={activeModel}
            hint={override ? t("model_hint") : `${t("model_hint")} · ${agent.llm_model}`}
            fullWidth
            showReset={!!override}
            onReset={async () => {
              const updated = await chatApi.updateSession(session.id, { model_override: "" })
              onSessionChanged(updated)
            }}
            onPick={async (m) => {
              const updated = await chatApi.updateSession(session.id, { model_override: m })
              onSessionChanged(updated)
            }}
          />
        </div>
      </div>
      {supportsReasoningEffort && (
        <div className="px-2.5 py-2 flex items-center gap-2">
          <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-9 shrink-0">{t("effort_label")}</span>
          <ReasoningEffortPill
            current={(session.metadata as { reasoning_effort?: string })?.reasoning_effort}
            levels={effortLevels}
            dropUp
            onSelect={async (effort) => {
              const updated = await chatApi.updateSession(session.id, { reasoning_effort: effort ?? "" })
              onSessionChanged(updated)
            }}
          />
        </div>
      )}
    </div>
  )
}
