import { Info } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

interface Props {
  agent: Agent
  onChange: (patch: Partial<Agent>) => void
}

/**
 * Per-Agent Memory-Injection-Settings (#115/#113). Steuert wie viele Crystals
 * und Lessons in den System-Prompt injiziert werden, ab welcher Confidence
 * Lessons sichtbar sind, und ob Crystals strikt projektisoliert oder global
 * sichtbar sind.
 */
export function MemorySection({ agent, onChange }: Props) {
  const { t } = useTranslation("agents")
  const maxCrystals = agent.memory_max_crystals ?? 5
  const maxLessons = agent.memory_max_lessons ?? 10
  const minConf = agent.memory_min_lesson_confidence ?? 0.6
  const maxChars = agent.memory_max_chars ?? 4000
  const scope = agent.memory_crystal_scope ?? "project_and_global"

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <p className="text-xs font-medium text-zinc-400">{t("memory.section_title")}</p>
        <span title={t("memory.help")} className="text-zinc-600 hover:text-zinc-400 cursor-help">
          <Info size={11} />
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500" title={t("memory.max_crystals_help")}>
            {t("memory.max_crystals")}
          </label>
          <input
            type="number"
            min={0}
            max={50}
            step={1}
            value={maxCrystals}
            onChange={(e) => onChange({ memory_max_crystals: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </div>

        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500" title={t("memory.max_lessons_help")}>
            {t("memory.max_lessons")}
          </label>
          <input
            type="number"
            min={0}
            max={50}
            step={1}
            value={maxLessons}
            onChange={(e) => onChange({ memory_max_lessons: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        </div>

        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500" title={t("memory.min_confidence_help")}>
            {t("memory.min_confidence", { value: minConf.toFixed(2) })}
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minConf}
            onChange={(e) => onChange({ memory_min_lesson_confidence: parseFloat(e.target.value) })}
            className="w-full"
          />
        </div>

        <div className="space-y-0.5">
          <label className="block text-[10px] text-zinc-500" title={t("memory.max_chars_help")}>
            {t("memory.max_chars")}
          </label>
          <select
            value={maxChars}
            onChange={(e) => onChange({ memory_max_chars: parseInt(e.target.value) })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          >
            <option value={0}>{t("memory.max_chars_unlimited")}</option>
            <option value={2000}>2 000</option>
            <option value={4000}>4 000 ({t("memory.default")})</option>
            <option value={8000}>8 000</option>
            <option value={16000}>16 000</option>
          </select>
        </div>

        <div className="space-y-0.5 col-span-2">
          <label className="block text-[10px] text-zinc-500" title={t("memory.crystal_scope_help")}>
            {t("memory.crystal_scope")}
          </label>
          <select
            value={scope}
            onChange={(e) => onChange({ memory_crystal_scope: e.target.value as Agent["memory_crystal_scope"] })}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          >
            <option value="project_and_global">{t("memory.scope_project_and_global")}</option>
            <option value="project_only">{t("memory.scope_project_only")}</option>
          </select>
        </div>
      </div>
    </div>
  )
}
