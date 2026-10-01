/* Statusleiste über dem Eingabefeld: laufende Hintergrund-Aufträge (mit
   Dauer, Runden, aktuellem Werkzeug, Abbrechen) und wartende Ergebnisse
   („Jetzt auswerten“). Unsichtbar, wenn nichts läuft und nichts wartet. */
import { Loader2, Play, Users, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { delegationsApi } from "./delegationsApi"
import { useDelegations } from "./useDelegations"

function minutesSince(iso: string, now: number): number {
  return Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60000))
}

export function DelegationStrip({ sessionId, busy }: { sessionId: string | null; busy: boolean }) {
  const { t } = useTranslation("chat")
  const { running, waiting, now, refresh } = useDelegations(sessionId, busy)
  if (!sessionId || (running.length === 0 && !waiting)) return null

  const cancel = async (id: string) => {
    await delegationsApi.cancel(sessionId, id).catch(() => {})
    void refresh()
  }
  const deliver = async () => {
    await delegationsApi.deliver(sessionId).catch(() => {})
    void refresh()
  }

  return (
    <div className="border-t border-[#2a364b] bg-[#101826] px-4 py-1.5 text-xs text-[#c7d2e5] space-y-1">
      {running.map((d) => (
        <div key={d.id} className="flex items-center gap-2">
          <Loader2 size={12} className="animate-spin text-sky-300 shrink-0" />
          <span className="font-medium">{d.target_name}</span>
          <span className="text-zinc-400 truncate" title={d.task}>
            {t("delegation.running", { minutes: minutesSince(d.created_at, now), rounds: d.rounds ?? 0 })}
            {d.current_tool ? ` · ${d.current_tool}` : ""}
          </span>
          <button onClick={() => cancel(d.id)} title={t("delegation.cancel")}
            className="ml-auto p-0.5 rounded text-zinc-500 hover:text-rose-300 transition-colors">
            <X size={12} />
          </button>
        </div>
      ))}
      {waiting && !busy && (
        <div className="flex items-center gap-2">
          <Users size={12} className="text-amber-300 shrink-0" />
          <span className="text-amber-200">{t("delegation.waiting")}</span>
          <button onClick={deliver}
            className="ml-auto flex items-center gap-1 rounded-full border border-amber-400/30 px-2 py-0.5 text-amber-200 hover:bg-amber-400/10">
            <Play size={10} /> {t("delegation.deliver_now")}
          </button>
        </div>
      )}
    </div>
  )
}
