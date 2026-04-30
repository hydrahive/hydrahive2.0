/**
 * Rechte Sidebar des Butler-Editors — rendert subtype-spezifische Param-Form
 * via Registry-Lookup (siehe properties/registry.tsx).
 */
import { Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { EXTRA_FORMS, FORMS } from "./properties/registry"
import type { BNode } from "./types"

interface PropsPanelProps {
  node: BNode
  agents: { id: string; name: string }[]
  onChange: (params: Record<string, unknown>) => void
  onDelete: () => void
}

export function PropertiesPanel({ node, agents, onChange, onDelete }: PropsPanelProps) {
  const { t } = useTranslation("butler")
  const { subtype, label, params } = node.data
  const Form = FORMS[subtype]
  const Extra = EXTRA_FORMS[subtype]

  return (
    <div className="w-56 shrink-0 border-l border-white/10 bg-[hsl(var(--sidebar-bg,220_15%_8%))] p-4 flex flex-col gap-4 overflow-y-auto">
      <div>
        <p className="text-[0.55rem] font-bold uppercase tracking-widest text-white/30 mb-1">{t("properties")}</p>
        <p className="text-sm font-semibold text-white">{label}</p>
      </div>

      {Form && <Form params={params} onChange={onChange} agents={agents} subtype={subtype} />}
      {Extra && <Extra params={params} onChange={onChange} agents={agents} />}

      <div className="mt-auto pt-3 border-t border-white/10">
        <button type="button" onClick={onDelete}
          className="flex items-center gap-1.5 text-xs text-red-400/60 hover:text-red-400 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {t("removeNode")}
        </button>
      </div>
    </div>
  )
}
