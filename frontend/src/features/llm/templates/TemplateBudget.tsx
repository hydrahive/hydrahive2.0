import { useTranslation } from "react-i18next"
import { withOverrun } from "./templateLogic"
import type { TemplateBudget as Budget, TemplateReply } from "./types"

const field = "w-full rounded-[4px] border border-white/[8%] bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200 disabled:opacity-60"
const NUMBERS: { key: keyof Budget; min: number; max: number }[] = [
  { key: "max_iterations", min: 1, max: 250 },
  { key: "max_tokens", min: 1, max: 200000 },
  { key: "timeout_seconds", min: 30, max: 3600 },
  { key: "compact_threshold_pct", min: 30, max: 100 },
  { key: "cooldown_seconds", min: 0, max: 3600 },
]
const EFFORTS = ["", "low", "medium", "high", "xhigh", "max"]

function Num({ label, value, min, max, readOnly, onChange }: {
  label: string; value: number; min: number; max: number; readOnly: boolean; onChange: (v: number) => void
}) {
  return (
    <label className="space-y-1">
      <span className="text-[11px] text-zinc-500">{label}</span>
      <input type="number" min={min} max={max} value={value} disabled={readOnly} className={field}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  )
}

/** Budget, Überschreitung und Antwortformat eines Templates. */
export function TemplateBudget({ budget, reply, readOnly, onBudget, onReply }: {
  budget: Budget; reply: TemplateReply; readOnly: boolean
  onBudget: (b: Budget) => void; onReply: (r: TemplateReply) => void
}) {
  const { t } = useTranslation("llm")
  const set = <K extends keyof Budget>(k: K, v: Budget[K]) => onBudget({ ...budget, [k]: v })

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {NUMBERS.map(({ key, min, max }) => (
          <Num key={key} label={t(`templates.budget.${key}`)} value={budget[key] as number} min={min} max={max}
            readOnly={readOnly} onChange={(v) => set(key, v as never)} />
        ))}
        <label className="space-y-1">
          <span className="text-[11px] text-zinc-500">{t("templates.budget.reasoning_effort")}</span>
          <select value={budget.reasoning_effort} disabled={readOnly} className={field}
            onChange={(e) => set("reasoning_effort", e.target.value)}>
            {EFFORTS.map((e) => <option key={e} value={e}>{e || t("templates.budget.effort_default")}</option>)}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[11px] text-zinc-500">{t("templates.budget.cache_ttl")}</span>
          <select value={budget.cache_ttl} disabled={readOnly} className={field}
            onChange={(e) => set("cache_ttl", e.target.value as Budget["cache_ttl"])}>
            <option value="5m">5 min</option><option value="1h">1 h</option>
          </select>
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-[4px] border border-white/[8%] bg-white/[2%] p-3">
        <label className="flex items-center gap-2 text-sm text-zinc-200">
          <input type="checkbox" checked={budget.overrun_pct > 0} disabled={readOnly}
            onChange={(e) => set("overrun_pct", e.target.checked ? 20 : 0)} />
          {t("templates.budget.overrun")}
        </label>
        {budget.overrun_pct > 0 && (
          <>
            <input type="number" min={1} max={100} value={budget.overrun_pct} disabled={readOnly}
              className={`${field} w-20`} onChange={(e) => set("overrun_pct", Number(e.target.value))} />
            <span className="text-xs text-zinc-500">
              {t("templates.budget.overrun_hint", {
                it: withOverrun(budget.max_iterations, budget.overrun_pct),
                tok: withOverrun(budget.max_tokens, budget.overrun_pct),
              })}
            </span>
          </>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Num label={t("templates.reply.summary_max_chars")} value={reply.summary_max_chars} min={200} max={20000}
          readOnly={readOnly} onChange={(v) => onReply({ ...reply, summary_max_chars: v })} />
        <label className="space-y-1">
          <span className="text-[11px] text-zinc-500">{t("templates.reply.full_report")}</span>
          <select value={reply.full_report} disabled={readOnly} className={field}
            onChange={(e) => onReply({ ...reply, full_report: e.target.value as TemplateReply["full_report"] })}>
            <option value="file">{t("templates.reply.file")}</option>
            <option value="inline">{t("templates.reply.inline")}</option>
          </select>
        </label>
      </div>
    </div>
  )
}
