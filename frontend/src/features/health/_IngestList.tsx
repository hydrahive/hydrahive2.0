import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { ChevronDown, ChevronRight, Package } from "lucide-react"
import type { IngestRecord } from "./api"
import { healthApi } from "./api"

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("de-DE", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

function MetricRow({ name, data }: { name: string; data: unknown[] }) {
  return (
    <div className="text-xs text-zinc-400 flex items-center gap-2 py-0.5">
      <span className="text-zinc-600 w-40 truncate font-mono">{name}</span>
      <span>{Array.isArray(data) ? `${data.length} Messwerte` : "—"}</span>
    </div>
  )
}

function RecordDetail({ id }: { id: string }) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    healthApi.detail(id)
      .then((r) => setPayload(r.payload))
      .catch(() => setPayload(null))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-xs text-zinc-600 py-2 pl-4">Lade…</div>
  if (!payload) return null

  const data = (payload.data ?? payload) as Record<string, unknown>
  const metrics = (data.metrics ?? []) as Array<{ name: string; data: unknown[] }>
  const workouts = (data.workouts ?? []) as unknown[]

  return (
    <div className="pl-4 pt-1 pb-2 border-l border-white/[6%] ml-2 mt-1">
      {metrics.map((m) => (
        <MetricRow key={m.name} name={m.name} data={m.data} />
      ))}
      {workouts.length > 0 && (
        <div className="text-xs text-zinc-500 mt-1">{workouts.length} Workout(s)</div>
      )}
    </div>
  )
}

interface Props {
  records: IngestRecord[]
}

export function IngestList({ records }: Props) {
  const { t } = useTranslation("health")
  const [expanded, setExpanded] = useState<string | null>(null)

  if (records.length === 0) {
    return (
      <p className="text-zinc-600 text-sm text-center py-8">
        {t("empty")}
      </p>
    )
  }

  return (
    <div className="divide-y divide-white/[4%]">
      {records.map((r) => {
        const open = expanded === r.id
        return (
          <div key={r.id}>
            <button
              onClick={() => setExpanded(open ? null : r.id)}
              className="w-full flex items-center gap-2 px-2 py-2.5 hover:bg-white/[2%] transition-colors text-left"
            >
              {open ? (
                <ChevronDown size={14} className="text-zinc-500 shrink-0" />
              ) : (
                <ChevronRight size={14} className="text-zinc-500 shrink-0" />
              )}
              <Package size={13} className="text-zinc-600 shrink-0" />
              <span className="text-sm text-zinc-300">{formatDate(r.received_at)}</span>
              {r.automation_name && (
                <span className="text-xs text-zinc-600 truncate ml-auto">
                  {r.automation_name}
                </span>
              )}
            </button>
            {open && <RecordDetail id={r.id} />}
          </div>
        )
      })}
    </div>
  )
}
