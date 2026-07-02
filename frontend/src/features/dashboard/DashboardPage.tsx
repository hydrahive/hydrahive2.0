import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, RotateCcw, SlidersHorizontal } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { dashboardApi, type DashboardSummary } from "./api"
import { UpdateBanner } from "./_UpdateBanner"
import { EmptyState } from "@/shared/EmptyState"
import { getWidget } from "./widgets"
import { useDashboardLayout } from "./useDashboardLayout"
import { WidgetFrame } from "./WidgetFrame"

const REFRESH_MS = 30_000

export function DashboardPage() {
  const { t } = useTranslation("dashboard")
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [editing, setEditing] = useState(false)
  const { layout, move, toggle, reset, isHidden } = useDashboardLayout()

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const s = await dashboardApi.summary()
        if (alive) setData(s)
      } catch { /* leise */ }
    }
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])

  const orderedWidgets = layout.order
    .map((id) => getWidget(id))
    .filter((w): w is NonNullable<typeof w> => Boolean(w))

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-1.5">
          {editing && (
            <button
              onClick={reset}
              title="Standard wiederherstellen"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-100 hover:bg-white/[5%] transition-colors"
            >
              <RotateCcw size={13} /> Zurücksetzen
            </button>
          )}
          <button
            onClick={() => setEditing((e) => !e)}
            title={editing ? "Anpassen beenden" : "Dashboard anpassen"}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              editing
                ? "bg-[var(--hh-accent-soft)] text-[var(--hh-accent-text)] border border-[var(--hh-accent-border)]"
                : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[5%]"
            }`}
          >
            {editing ? <Check size={13} /> : <SlidersHorizontal size={13} />}
            {editing ? "Fertig" : "Anpassen"}
          </button>
          <HelpButton topic="dashboard" />
        </div>
      </div>

      {data && (
        <>
          {(data.version.update_behind ?? 0) > 0 && (
            <UpdateBanner behind={data.version.update_behind!} />
          )}

          {orderedWidgets.map((w, idx) => {
            const hidden = isHidden(w.id)
            if (editing) {
              return (
                <WidgetFrame
                  key={w.id}
                  label={w.label}
                  hidden={hidden}
                  isFirst={idx === 0}
                  isLast={idx === orderedWidgets.length - 1}
                  onUp={() => move(w.id, -1)}
                  onDown={() => move(w.id, 1)}
                  onToggle={() => toggle(w.id)}
                >
                  {w.render(data)}
                </WidgetFrame>
              )
            }
            return hidden ? null : <div key={w.id}>{w.render(data)}</div>
          })}
        </>
      )}

      {!data && (
        <EmptyState
          src="/illustrations/empty-dashboard.png"
          size={150}
          hint={t("loading")}
          className="min-h-[50vh]"
        />
      )}
    </div>
  )
}
