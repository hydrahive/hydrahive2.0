import { useState } from "react"
import { AlertTriangle, Search, Server } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { McpServerBrief } from "@/features/agents/api"
import type { BuddyConfig, BuddyConfigPatch, BuddyToolMeta } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
  mcpServers: McpServerBrief[]
}

export function BuddySettingsTools({ config, draft, onChange, mcpServers }: Props) {
  const { t } = useTranslation("buddy")
  const [query, setQuery] = useState("")
  const activeTools = new Set(draft.tools ?? config.tools)
  const selectedMcp = draft.mcp_servers ?? config.mcp_servers
  const knownNames = new Set(config.available_tools.map((tool) => tool.name))
  const unknown: BuddyToolMeta[] = Array.from(activeTools).filter((name) => !knownNames.has(name)).map((name) => ({ name, description: t("tools.unavailable_hint"), category: t("tools.unavailable") }))
  const catalog = [...config.available_tools, ...unknown]
  const needle = query.trim().toLowerCase()
  const filtered = catalog.filter((tool) => !needle || `${tool.name} ${tool.description} ${tool.category}`.toLowerCase().includes(needle))
  const categories = Array.from(new Set(filtered.map((tool) => tool.category || t("tools.other"))))
    .sort()
    .map((category) => ({
      category,
      tools: filtered.filter((tool) => (tool.category || t("tools.other")) === category),
    }))

  function toggle(tool: string) {
    const next = new Set(activeTools)
    if (next.has(tool)) next.delete(tool)
    else next.add(tool)
    onChange({ tools: Array.from(next) })
  }

  function toggleAll(enable: boolean) {
    const unknownActive = Array.from(activeTools).filter((name) => !knownNames.has(name))
    onChange({ tools: enable ? [...config.available_tools.map((tool) => tool.name), ...unknownActive] : [] })
  }

  function toggleMcp(id: string) {
    onChange({ mcp_servers: selectedMcp.includes(id) ? selectedMcp.filter((item) => item !== id) : [...selectedMcp, id] })
  }

  const unknownMcp = selectedMcp.filter((id) => !mcpServers.some((server) => server.id === id))

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-[#8d9ab0]">{t("tools.active_count", { active: activeTools.size, total: catalog.length })}</p>
          <div className="flex gap-2">
            <button type="button" onClick={() => toggleAll(true)} className="rounded-[4px] border border-[#2a364b] bg-[#172133] px-2 py-1 text-xs text-[#d7deea] hover:border-[#46617f]">{t("tools.enable_all")}</button>
            <button type="button" onClick={() => toggleAll(false)} className="rounded-[4px] border border-[#2a364b] bg-[#172133] px-2 py-1 text-xs text-[#d7deea] hover:border-[#46617f]">{t("tools.disable_all")}</button>
          </div>
        </div>
        <label className="mb-3 flex items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2">
          <Search size={14} className="text-[#718097]" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("tools.search")} className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] outline-none placeholder:text-[#59677d]" />
        </label>
        <div className="max-h-[52vh] space-y-4 overflow-y-auto pr-1">
          {categories.map(({ category, tools }) => <section key={category}>
            <h3 className="mb-2 text-[10px] font-black uppercase tracking-[0.14em] text-[#718097]">{category} · {tools.length}</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {tools.map((tool) => {
                const active = activeTools.has(tool.name)
                const missing = !knownNames.has(tool.name)
                return <button key={tool.name} type="button" onClick={() => toggle(tool.name)} className={`rounded-[4px] border p-3 text-left ${active ? "border-[#69d7ff]/50 bg-[#163248]" : "border-[#2a364b] bg-[#111827] hover:border-[#46617f]"}`}>
                  <span className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${active ? "bg-[#69d7ff]" : "bg-[#59677d]"}`} />{missing && <AlertTriangle size={13} className="text-amber-300" />}<span className="min-w-0 truncate font-mono text-xs font-semibold text-[#e8eef8]">{tool.name}</span></span>
                  <span className="mt-1 block line-clamp-2 text-[11px] leading-4 text-[#8d9ab0]">{tool.description || t("tools.no_description")}</span>
                </button>
              })}
            </div>
          </section>)}
          {categories.length === 0 && <p className="py-8 text-center text-sm text-[#718097]">{t("tools.no_results")}</p>}
        </div>
      </div>

      <section className="border-t border-[#2a364b] pt-5">
        <h3 className="text-sm font-bold text-[#e8eef8]">{t("tools.mcp_title")}</h3>
        <p className="mb-3 text-xs text-[#718097]">{t("tools.mcp_hint")}</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {[...mcpServers, ...unknownMcp.map((id) => ({ id, name: id, enabled: false, connected: false }))].map((server) => {
            const active = selectedMcp.includes(server.id)
            return <button key={server.id} type="button" onClick={() => toggleMcp(server.id)} className={`flex items-center gap-2 rounded-[4px] border p-2 text-left ${active ? "border-[#69d7ff]/50 bg-[#163248]" : "border-[#2a364b] bg-[#111827]"}`}><Server size={14} className={active ? "text-[#69d7ff]" : "text-[#718097]"} /><span className="min-w-0 flex-1 truncate text-xs text-[#e8eef8]">{server.name}</span><span className={`h-2 w-2 rounded-full ${server.connected ? "bg-emerald-400" : "bg-[#59677d]"}`} /></button>
          })}
          {mcpServers.length === 0 && unknownMcp.length === 0 && <p className="text-xs text-[#718097]">{t("tools.no_mcp")}</p>}
        </div>
      </section>

      <section className="grid gap-3 border-t border-[#2a364b] pt-5 sm:grid-cols-2">
        <Toggle label={t("tools.longterm_memory")} hint={t("tools.longterm_hint")} checked={draft.longterm_memory ?? config.longterm_memory} onChange={(checked) => onChange({ longterm_memory: checked })} />
        <Toggle label={t("tools.confirm")} hint={t("tools.confirm_hint")} checked={draft.require_tool_confirm ?? config.require_tool_confirm} onChange={(checked) => onChange({ require_tool_confirm: checked })} />
      </section>
    </div>
  )
}

function Toggle({ label, hint, checked, onChange }: { label: string; hint: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex cursor-pointer items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-1 accent-[#69d7ff]" /><span><span className="block text-sm font-semibold text-[#e8eef8]">{label}</span><span className="mt-1 block text-xs leading-4 text-[#8d9ab0]">{hint}</span></span></label>
}
