import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Activity } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { healthApi } from "../api"

const QUICK_PROMPTS = [
  { label: "📊 Tagesauswertung", prompt: "Werte meinen heutigen Gesundheitstag aus. Schau dir Schritte, Herzfrequenz, Schlaf und Kalorien an." },
  { label: "📈 Wochentrend",     prompt: "Analysiere meinen Gesundheitstrend der letzten 7 Tage. Gibt es Muster oder Auffälligkeiten?" },
  { label: "😴 Schlafqualität",  prompt: "Wie war meine Schlafqualität diese Woche? Gibt es Optimierungspotenzial?" },
]

interface Props {
  onPrompt: (text: string) => void
}

export function HealthBuddyBox({ onPrompt }: Props) {
  const [lastIngest, setLastIngest] = useState<string | null>(null)

  useEffect(() => {
    healthApi.metrics(1)
      .then((s) => setLastIngest(s.last_ingest))
      .catch(() => {})
  }, [])

  const formattedDate = lastIngest
    ? new Date(lastIngest).toLocaleString("de-DE", {
        day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
      })
    : null

  return (
    <CollapsibleBox
      boxId="buddy-health"
      icon={<Activity size={14} className="text-rose-400" />}
      title="Gesundheit"
      color={rgbFor("/akte")}
      defaultCollapsed
      className="w-60"
      headerRight={
        <Link to="/akte/tracking" className="text-[10px] text-zinc-600 hover:text-zinc-400 transition-colors">
          → /akte
        </Link>
      }
    >
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${formattedDate ? "bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]" : "bg-zinc-600"}`} />
          <span className="text-[11px] text-zinc-500">
            {formattedDate ? `${formattedDate} · aktiv` : "Keine Daten"}
          </span>
        </div>
        <div className="flex flex-col gap-1.5">
          {QUICK_PROMPTS.map(({ label, prompt }) => (
            <button
              key={label}
              onClick={() => onPrompt(prompt)}
              className="text-left text-xs px-2.5 py-1.5 rounded-lg border border-white/[6%] hover:border-rose-500/30 hover:bg-rose-500/[3%] text-zinc-400 hover:text-zinc-300 transition-all"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </CollapsibleBox>
  )
}
