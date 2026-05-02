import { Plus, Save, ToggleLeft, ToggleRight, Trash2, Workflow } from "lucide-react"
import { cn } from "@/shared/cn"
import { useTranslation } from "react-i18next"
import type { ButlerFlow } from "./types"

interface Props {
  flows: ButlerFlow[]
  activeFlowId: string | null
  projectId: string | null
  flowName: string
  flowEnabled: boolean
  saving: boolean
  onSelectFlow: (flow: ButlerFlow | null) => void
  onNameChange: (name: string) => void
  onToggle: () => void
  onNew: () => void
  onSave: () => void
  onDelete: () => void
}

export function ButlerTopBar({
  flows, activeFlowId, projectId, flowName, flowEnabled, saving,
  onSelectFlow, onNameChange, onToggle, onNew, onSave, onDelete,
}: Props) {
  const { t } = useTranslation("butler")

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-4 py-2.5 shrink-0">
      <Workflow className="h-5 w-5 text-indigo-400 shrink-0" />
      <h1 className="text-base font-semibold text-white mr-1">Butler</h1>
      {projectId && (
        <span className="rounded-full bg-indigo-500/20 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300">
          {projectId}
        </span>
      )}

      <select
        value={activeFlowId || ""}
        onChange={e => {
          const flow = flows.find(f => f.id === e.target.value)
          onSelectFlow(flow ?? null)
        }}
        className="rounded-lg bg-zinc-900 border border-white/15 px-2.5 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500/50"
      >
        <option value="">{t("newFlowOption")}</option>
        {flows
          .filter(f => !projectId || f.scope_id === projectId || !f.scope_id)
          .map(f => (
            <option key={f.id} value={f.id}>{f.name}{f.enabled ? "" : ` ${t("inactive")}`}</option>
          ))}
      </select>

      <input
        type="text"
        value={flowName}
        onChange={e => onNameChange(e.target.value)}
        placeholder={t("flowNamePlaceholder")}
        className="rounded-lg bg-zinc-900 border border-white/15 px-2.5 py-1.5 text-sm text-white placeholder-white/25 focus:outline-none focus:border-indigo-500/50 w-40"
      />

      <button type="button" onClick={onToggle}
        className={cn(
          "flex items-center gap-1.5 text-sm px-2.5 py-1.5 rounded-lg border transition-colors",
          flowEnabled
            ? "border-green-500/40 bg-green-950/30 text-green-400 hover:bg-green-950/50"
            : "border-white/15 bg-zinc-900 text-white/35 hover:bg-white/10"
        )}
      >
        {flowEnabled ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
        {flowEnabled ? t("active") : t("inactiveLabel")}
      </button>

      <div className="flex-1" />

      <button type="button" onClick={onNew}
        className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-zinc-900 px-2.5 py-1.5 text-sm text-white hover:bg-white/10 transition-colors"
      >
        <Plus className="h-3.5 w-3.5" />
        {"Neu"}
      </button>

      <button type="button" onClick={onSave} disabled={saving}
        className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-3 py-1.5 text-sm text-white transition-colors"
      >
        <Save className="h-3.5 w-3.5" />
        {saving ? "Speichert…" : "Speichern"}
      </button>

      {activeFlowId && (
        <button type="button" onClick={onDelete}
          className="flex items-center gap-1.5 rounded-lg border border-red-500/40 bg-red-950/20 px-2.5 py-1.5 text-sm text-red-400 hover:bg-red-950/40 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
