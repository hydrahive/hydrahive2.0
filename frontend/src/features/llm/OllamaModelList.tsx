import { Bot, Download, Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { OllamaModel, OllamaPullJob } from "./ollamaApi"

interface Props {
  models: OllamaModel[]
  jobs: Record<string, OllamaPullJob>
  busyModel: string | null
  onInstall: (model: string) => void
  onDelete: (model: string) => void
  onUse: (model: string) => void
}

const FIT_COLORS: Record<string, string> = {
  perfect: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  good: "bg-sky-500/15 text-sky-300 border-sky-500/25",
  marginal: "bg-amber-500/15 text-amber-300 border-amber-500/25",
  too_tight: "bg-rose-500/15 text-rose-300 border-rose-500/25",
  unknown: "bg-zinc-500/10 text-zinc-500 border-white/10",
}

function formatBytes(value: number | null | undefined): string {
  if (!value) return "—"
  const units = ["B", "KB", "MB", "GB", "TB"]
  let amount = value
  let index = 0
  while (amount >= 1000 && index < units.length - 1) {
    amount /= 1000
    index += 1
  }
  return `${amount >= 10 || index === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[index]}`
}

function progress(job?: OllamaPullJob): number | null {
  if (!job?.total || job.completed == null) return null
  return Math.max(0, Math.min(100, Math.round((job.completed / job.total) * 100)))
}

function metric(value: number | null | undefined, suffix: string): string {
  return value == null ? "—" : `${value.toFixed(1)} ${suffix}`
}

/** Zeigt das genutzte Fenster, wenn es unter dem theoretischen liegt.
 *  Sonst verspricht der Katalog mehr Kontext als der Agent wirklich bekommt. */
function contextLabel(model: OllamaModel): string {
  const full = model.context_window
  if (!full) return "— ctx"
  const used = model.effective_context_window
  if (used != null && used < full) {
    return `${used.toLocaleString()} / ${full.toLocaleString()} ctx`
  }
  return `${full.toLocaleString()} ctx`
}

function contextTitle(model: OllamaModel, t: (key: string) => string): string | undefined {
  const full = model.context_window
  const used = model.effective_context_window
  if (!full || used == null || used >= full) return undefined
  return t("ollama.context_capped")
}

export function OllamaModelList({ models, jobs, busyModel, onInstall, onDelete, onUse }: Props) {
  const { t } = useTranslation("llm")
  if (!models.length) return <p className="py-6 text-center text-sm text-zinc-600">{t("ollama.no_variants")}</p>

  return (
    <div className="divide-y divide-white/[6%]">
      {models.map((model) => {
        const job = jobs[model.ollama_name]
        const pct = progress(job)
        const running = job?.status === "queued" || job?.status === "pulling"
        const speed = model.measured_tps ?? model.estimated_tps
        return (
          <div key={model.ollama_name} className="px-4 py-3 space-y-2 hover:bg-white/[2%]">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm text-zinc-100 break-all">{model.ollama_name}</span>
                  {model.installed && (
                    <span className="rounded border border-emerald-500/25 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-300">
                      {t("ollama.installed")}
                    </span>
                  )}
                  <span className={`rounded border px-1.5 py-0.5 text-[10px] ${FIT_COLORS[model.fit]}`}>
                    {t(`ollama.fit.${model.fit}`)}
                  </span>
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-500">
                  <span>{formatBytes(model.size)}</span>
                  <span title={contextTitle(model, t)}>{contextLabel(model)}</span>
                  <span>{model.parameter_size || model.best_quant || "—"}</span>
                  <span>{metric(model.memory_required_gb, "GB VRAM")}</span>
                  <span>{metric(speed, "tok/s")}{model.measured_tps != null ? " ✓" : ""}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {[...new Set([...model.capabilities, ...model.input_modalities])].map((capability) => (
                    <span key={capability} className="rounded bg-white/[5%] px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {capability}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {model.installed ? (
                  <>
                    {model.output_modalities.includes("text") && (
                      <button onClick={() => onUse(model.id)} className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-violet-300 hover:bg-violet-500/10">
                        <Bot size={12} /> {t("ollama.use")}
                      </button>
                    )}
                    <button disabled={busyModel === model.ollama_name} onClick={() => onDelete(model.ollama_name)}
                      className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-rose-300 hover:bg-rose-500/10 disabled:opacity-50">
                      {busyModel === model.ollama_name ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                      {t("ollama.remove")}
                    </button>
                  </>
                ) : (
                  <button disabled={running || busyModel === model.ollama_name} onClick={() => onInstall(model.ollama_name)}
                    className="inline-flex items-center gap-1 rounded bg-violet-600 px-2.5 py-1.5 text-xs text-white hover:bg-violet-500 disabled:opacity-50">
                    {running ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                    {t("ollama.install")}
                  </button>
                )}
              </div>
            </div>
            {job && (
              <div className="space-y-1">
                <div className="h-1.5 overflow-hidden rounded bg-white/[6%]">
                  <div className={`h-full ${job.status === "failed" ? "bg-rose-500" : "bg-violet-500"}`} style={{ width: `${pct ?? (running ? 15 : 100)}%` }} />
                </div>
                <p className={`text-[10px] ${job.status === "failed" ? "text-rose-400" : "text-zinc-500"}`}>
                  {job.status === "failed" ? t("ollama.pull_failed") : `${job.phase}${pct == null ? "" : ` · ${pct}%`}`}
                </p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
