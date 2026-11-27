import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { ToolsTab } from "../_ToolsTab"
import type { McpServerBrief } from "../api"
import type { Agent, ToolMeta } from "../types"
import { areasApi } from "./api"
import { AreasView } from "./AreasView"
import { HelperSwitch } from "./HelperSwitch"
import { PurposeSuggest } from "./PurposeSuggest"
import { toggle } from "./toggle"
import type { AreaCatalog, AreaStatus } from "./types"

interface Props {
  draft: Agent
  tools: ToolMeta[]
  mcpServers: McpServerBrief[]
  onChange: (patch: Partial<Agent>) => void
}

/**
 * Reiter „Was darf der Agent?“ (Spec agent-bereiche.md 2/4.3/4.8): Bereichs-Schalter statt Tool-Listen, dazu Helfer-Bereich,
 * Zweck-Vorschlag und die zugeklappte Expertenansicht (die bisherigen Listen). Geändert wird nur der Entwurf (`draft.tools`);
 * gespeichert wird über den normalen Speichern-Knopf des Editors (Admin). Der Status kommt vom Server für den GESPEICHERTEN
 * Stand, der Entwurf wird darüber gelegt, damit ein Klick sofort sichtbar ist.
 */
export function AreasTab({ draft, tools, mcpServers, onChange }: Props) {
  const { t, i18n } = useTranslation("agents")
  const lang = (i18n.language || "de").split("-")[0]
  const [catalog, setCatalog] = useState<AreaCatalog | null>(null)
  const [status, setStatus] = useState<AreaStatus | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => { areasApi.catalog(lang).then(setCatalog).catch(() => setError(true)) }, [lang])
  useEffect(() => { areasApi.status(draft.id).then(setStatus).catch(() => setError(true)) }, [draft.id])

  const live = useMemo(() => (catalog && status ? overlay(catalog, status, draft.tools) : null), [catalog, status, draft.tools])
  const helper = draft.type === "specialist" || draft.type === "project"
  const byId = new Map(catalog?.areas.map((a) => [a.id, a]) ?? [])
  const apply = (areaId: string, on: boolean) => {
    const area = byId.get(areaId)
    if (area) onChange({ tools: toggle(draft.tools, area.tools, on) })
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-[11px] text-rose-300" role="alert">{t("areas.load_failed")}</p>}
      {catalog && status && live && (
        <>
          {status.editable && <PurposeSuggest agentId={draft.id} catalog={catalog} lang={lang} onApply={(ids) => ids.forEach((id) => apply(id, true))} />}
          <AreasView
            catalog={catalog} status={live} mode={draft.tool_mode ?? "classic"} onMode={(m) => onChange({ tool_mode: m })}
            onToggle={apply} onAdopt={(id) => apply(id, true)}
          />
          {helper && <HelperSwitch agent={draft} catalog={catalog} mayEdit />}
        </>
      )}
      <details className="rounded-md border border-white/[8%] bg-white/[2%]" data-testid="expert-view">
        <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-zinc-300">{t("areas.expert")}</summary>
        <div className="px-3 pb-3 pt-1">
          <p className="mb-3 text-[10px] text-zinc-500">{t("areas.expert_hint")}</p>
          <ToolsTab draft={draft} tools={tools} mcpServers={mcpServers} onChange={onChange} />
        </div>
      </details>
    </div>
  )
}

/** Legt den Entwurf (draft.tools) über den gespeicherten Server-Status: ``on`` = alle Tools des Bereichs im Entwurf. */
function overlay(catalog: AreaCatalog, status: AreaStatus, tools: string[]): AreaStatus {
  const have = new Set(tools)
  return {
    editable: status.editable,
    areas: status.areas.map((s) => {
      const area = catalog.areas.find((a) => a.id === s.id)
      if (!area || area.tools.length === 0) return s
      const mine = area.tools.filter((t) => have.has(t))
      const missing = area.tools.filter((t) => !have.has(t) && !s.via_category.includes(t))
      const keep = s.new.filter((t) => missing.includes(t))
      const state = mine.length > 0 && missing.every((t) => keep.includes(t)) ? "on" : mine.length > 0 || s.via_category.length > 0 ? "partial" : "off"
      return { ...s, state, have: mine, missing, new: state === "on" ? keep : [] }
    }),
  }
}
