import { Info } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

interface Props {
  agent: Agent
  models: string[]
  onChange: (patch: Partial<Agent>) => void
}

/**
 * Per-Agent Compaction-Settings (#82) — alle optional, leer = System-Default.
 */
export function CompactionSection({ agent, models, onChange }: Props) {
  const { t } = useTranslation("agents")
  const compactModel = agent.compact_model ?? ""
  const toolLimit = agent.compact_tool_result_limit ?? 2000
  const reserve = agent.compact_reserve_tokens ?? 16384
  const thresholdPct = agent.compact_threshold_pct ?? 100

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <p className="text-xs font-medium text-zinc-400">{t("compaction.section_title")}</p>
        <span title={t("compaction.help")} className="text-zinc-600 hover:text-zinc-400 cursor-help">
          <Info size={11} />
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("compaction.model")}</label>
          <select
            value={compactModel}
            onChange={(e) => onChange({ compact_model: e.target.value })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          >
            <option value="">{t("compaction.model_main", { model: agent.llm_model })}</option>
            {models.filter(m => m !== agent.llm_model).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("compaction.tool_result_limit")}</label>
          <select
            value={toolLimit}
            onChange={(e) => onChange({ compact_tool_result_limit: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          >
            <option value={500}>500 ({t("compaction.aggressive")})</option>
            <option value={1000}>1000</option>
            <option value={2000}>2000 ({t("compaction.default")})</option>
            <option value={5000}>5000</option>
            <option value={10000}>10000</option>
          </select>
        </div>

        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">{t("compaction.reserve_tokens")}</label>
          <input
            type="number"
            min={1000}
            max={100000}
            step={1000}
            value={reserve}
            onChange={(e) => onChange({ compact_reserve_tokens: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </div>

        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500">
            {t("compaction.threshold_pct", { pct: thresholdPct })}
          </label>
          <input
            type="range"
            min={30}
            max={100}
            step={5}
            value={thresholdPct}
            onChange={(e) => onChange({ compact_threshold_pct: parseInt(e.target.value) })}
            className="w-full"
          />
        </div>
      </div>
    </div>
  )
}
