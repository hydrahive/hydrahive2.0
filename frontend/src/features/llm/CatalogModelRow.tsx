import type { CSSProperties } from "react"
import { useState } from "react"
import { CheckCircle, HelpCircle, Loader2, XCircle, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import type { AgentBrief } from "@/features/chat/types"
import type { CatalogModel, CatalogTestResult } from "./api"

export function CatalogModelRow({
  model, testResult, testing, onTest, onUse,
}: { model: CatalogModel; testResult?: CatalogTestResult; testing: boolean; onTest: () => void; onUse: () => void }) {
  const { t } = useTranslation("llm")
  return (
    <tr className="border-t border-white/[5%] hover:bg-white/[2%]">
      <td className="px-3 py-2 font-mono text-xs text-zinc-200 break-all">
        {model.id}
        {model.is_free === true && <span className="text-[10px] text-emerald-400 ml-1">{t("catalog.free")}</span>}
      </td>
      <td className="px-3 py-2 text-right text-xs tabular-nums text-zinc-400">
        {model.context_window ? model.context_window.toLocaleString("de") : "—"}
      </td>
      <td className="px-3 py-2 text-center">
        {model.tool_use === true && <CheckCircle size={14} className="inline text-emerald-400" />}
        {model.tool_use === false && <XCircle size={14} className="inline text-rose-400" />}
        {model.tool_use === null && <HelpCircle size={14} className="inline text-zinc-600" />}
      </td>
      <td className="px-3 py-2 text-xs text-zinc-400">{model.category}</td>
      <td className="px-3 py-2 text-xs text-zinc-500">{model.params ?? "—"}</td>
      <td className="px-3 py-2 text-right">
        <button onClick={onTest} disabled={testing}
          className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5 disabled:opacity-50">
          {testing ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />} Test
        </button>
        {testResult && (
          <span className={`ml-2 text-[10px] ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}
            title={testResult.ok ? testResult.response : testResult.error}>
            {testResult.ok ? `✓ ${testResult.latency_ms}ms` : `✗ ${testResult.latency_ms}ms`}
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-right">
        <button onClick={onUse} className="px-2 py-1 rounded text-[11px] text-violet-300 hover:text-violet-200 hover:bg-violet-500/10">
          Im Agent nutzen
        </button>
      </td>
    </tr>
  )
}

export function UseInAgentDialog({
  model, agents, onSubmit, onCancel, error,
}: { model: string; agents: AgentBrief[]; onSubmit: (aid: string) => void; onCancel: () => void; error: string | null }) {
  const { t } = useTranslation("llm")
  const [pick, setPick] = useState<string>(agents[0]?.id ?? "")
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div className="box overflow-hidden p-5 max-w-md w-full m-4 space-y-3" style={{ "--c": rgbFor("/llm") } as CSSProperties} onClick={(event) => event.stopPropagation()}>
        <h3 className="text-sm font-medium text-zinc-100">{t("catalog.set_for_agent")}</h3>
        <p className="text-xs text-zinc-400 break-all">→ <span className="font-mono">{model}</span></p>
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Agent</label>
          <select value={pick} onChange={(event) => setPick(event.target.value)} className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 text-zinc-200 text-sm">
            {agents.map((agent) => <option key={agent.id} value={agent.id} className="bg-zinc-900">{agent.name} · {agent.type} · {agent.llm_model}</option>)}
          </select>
        </div>
        {error && <p className="text-xs text-rose-400">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onCancel} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:bg-white/5">Abbrechen</button>
          <button onClick={() => onSubmit(pick)} disabled={!pick} className="px-4 py-1.5 rounded-lg text-sm text-white bg-violet-600 hover:bg-violet-500 disabled:opacity-50">Speichern</button>
        </div>
      </div>
    </div>
  )
}
