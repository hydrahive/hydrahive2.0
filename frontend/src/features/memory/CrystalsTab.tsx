import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Gem } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { memoryApi } from "./api"
import type { Crystal } from "./types"

interface Props {
  agentId: string
}

export function CrystalsTab({ agentId }: Props) {
  const { t } = useTranslation("memory")
  const [crystals, setCrystals] = useState<Crystal[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    memoryApi.getCrystals(agentId, { limit: 100 })
      .then((res) => { setCrystals(res.crystals); setTotal(res.total) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [agentId])

  if (loading) return <p className="text-xs text-zinc-600 p-4">{t("loading")}</p>

  return (
    <div className="space-y-3 p-4">
      <p className="text-[10px] text-zinc-600">{t("crystal_count", { count: total })}</p>

      {crystals.length === 0 ? (
        <p className="text-xs text-zinc-600 text-center py-8">{t("no_crystals")}</p>
      ) : (
        <div className="space-y-2">
          {crystals.map((c) => {
            const open = expanded === c.id
            return (
              <div
                key={c.id}
                className="box overflow-hidden"
                style={{ "--c": rgbFor("/agents") } as CSSProperties}
              >
                {/* Header */}
                <button
                  onClick={() => setExpanded(open ? null : c.id)}
                  className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-white/[2%] transition-colors"
                >
                  <Gem size={14} className="text-violet-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-zinc-200 leading-relaxed line-clamp-2">{c.narrative}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[10px] text-zinc-600">
                        {c.created_at ? formatDate(c.created_at) : "—"}
                      </span>
                      {c.project && (
                        <span className="text-[10px] font-mono text-violet-400/70">{c.project}</span>
                      )}
                      <span className="text-[10px] text-zinc-700">
                        {t("observations", { count: c.observation_count })}
                      </span>
                    </div>
                  </div>
                  <span className="text-zinc-600 text-[10px] flex-shrink-0 mt-0.5">{open ? "▲" : "▼"}</span>
                </button>

                {/* Expanded detail */}
                {open && (
                  <div className="px-4 pb-4 space-y-3 border-t border-white/[4%] pt-3">
                    {c.key_outcomes.length > 0 && (
                      <Section label={t("crystal.key_outcomes")}>
                        <ul className="space-y-1">
                          {c.key_outcomes.map((o, i) => (
                            <li key={i} className="flex gap-2 text-xs text-zinc-300">
                              <span className="text-violet-500 flex-shrink-0">•</span>
                              {o}
                            </li>
                          ))}
                        </ul>
                      </Section>
                    )}

                    {c.lessons.length > 0 && (
                      <Section label={t("crystal.lessons")}>
                        <ul className="space-y-1">
                          {c.lessons.map((l, i) => (
                            <li key={i} className="flex gap-2 text-xs text-zinc-400">
                              <span className="text-amber-500/70 flex-shrink-0">→</span>
                              {l}
                            </li>
                          ))}
                        </ul>
                      </Section>
                    )}

                    {c.files_affected.length > 0 && (
                      <Section label={t("crystal.files")}>
                        <div className="flex flex-wrap gap-1">
                          {c.files_affected.map((f, i) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] font-mono text-zinc-400"
                            >
                              {f}
                            </span>
                          ))}
                        </div>
                      </Section>
                    )}

                    <p className="text-[10px] font-mono text-zinc-700">
                      session: {c.session_id}
                    </p>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">{label}</p>
      {children}
    </div>
  )
}

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }) }
  catch { return iso }
}
