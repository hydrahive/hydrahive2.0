import { Settings, SquarePen } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { HydraMascot } from "@/shared/HydraMascot"
import { ModelPicker } from "@/features/chat/ModelPicker"
import { ProjectPicker } from "@/features/chat/ProjectPicker"
import { ReasoningEffortPill, type EffortLevel } from "@/features/chat/ReasoningEffortPill"
import type { ProjectBrief } from "@/features/chat/api"
import { BuddyUsageChip } from "./_BuddyUsageChip"
import type { BuddyState } from "./api"

type LastTurnTokens = {
  input: number
  output: number
  cache_creation: number
  cache_read: number
} | null

export function BuddyCockpitHeader({
  state,
  mascotState,
  mascotAnimate,
  projects,
  projectBusy,
  reasoningEffort,
  effortEnabled,
  extendedEffort,
  busy,
  lastTurnTokens,
  onProjectPick,
  onModelPick,
  onEffortSelect,
  onSettings,
  onNewChat,
}: {
  state: BuddyState
  mascotState: "idle" | "working" | "speaking" | "error" | "sleeping"
  mascotAnimate: boolean
  projects: ProjectBrief[]
  projectBusy: boolean
  reasoningEffort: EffortLevel | null
  effortEnabled: boolean
  extendedEffort: boolean
  busy: boolean
  lastTurnTokens: LastTurnTokens
  onProjectPick: (pid: string | null) => void | Promise<void>
  onModelPick: (model: string) => void | Promise<void>
  onEffortSelect: (effort: EffortLevel | null) => Promise<void>
  onSettings: () => void
  onNewChat: () => void | Promise<void>
}) {
  const { t } = useTranslation("buddy")
  return (
    <header className="border-b border-white/[6%] bg-black/35 px-3 py-2.5 sm:px-5">
      {state.created && (
        <div className="pb-2 text-center text-[11px] text-[var(--hh-accent-text)]">{t("just_woken_up")}</div>
      )}
      <div className="flex min-w-0 flex-wrap items-center gap-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <HydraMascot state={mascotState} size={34} animate={mascotAnimate} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-zinc-100">{state.agent_name}</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-600">{t("cockpit.title")}</p>
          </div>
        </div>
        <ProjectPicker current={state.project_id} projects={projects} onPick={onProjectPick} busy={projectBusy} />
        {state.model && (
          <div className="min-w-[9rem] max-w-[12rem] shrink">
            <ModelPicker current={state.model} hint={t("cockpit.model_hint")} fullWidth onPick={onModelPick} />
          </div>
        )}
        {effortEnabled && (
          <ReasoningEffortPill current={reasoningEffort} extended={extendedEffort} onSelect={onEffortSelect} />
        )}
        <div className="min-w-0 flex-1" />
        <BuddyUsageChip
          model={state.model}
          provider={state.provider}
          lastTurnTokens={lastTurnTokens}
          busy={busy}
          sessionId={state.session_id}
        />
        <HelpButton topic="buddy" />
        <button
          onClick={onSettings}
          title={t("boxes.buddy_settings")}
          className="border border-white/[8%] p-1.5 text-zinc-500 transition-all hover:bg-white/[6%] hover:text-zinc-300"
        >
          <Settings size={13} />
        </button>
        <button
          onClick={onNewChat}
          disabled={busy}
          title={t("new_chat")}
          className="flex items-center gap-1.5 border border-white/[8%] px-2.5 py-1 text-xs text-zinc-400 transition-all hover:bg-white/[6%] hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <SquarePen size={11} />
          {t("new_chat")}
        </button>
      </div>
    </header>
  )
}
