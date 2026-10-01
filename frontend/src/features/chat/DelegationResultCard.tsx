/* Automatische Nachricht mit Spezialisten-Ergebnissen. Steht technisch als
   user-Nachricht im Verlauf (damit der Agent sie auswertet), ist aber NICHT
   vom Nutzer — deshalb eigene Karte statt Nutzer-Blase. */
import { ChevronDown, ChevronRight, Users } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "./Markdown"
import type { DelegationResultMeta } from "./delegationsApi"
import type { Message } from "./types"

const STATUS_TONE: Record<string, string> = {
  done: "text-emerald-300 border-emerald-400/30 bg-emerald-400/10",
  error: "text-rose-300 border-rose-400/30 bg-rose-400/10",
  timeout: "text-amber-300 border-amber-400/30 bg-amber-400/10",
  paused: "text-amber-300 border-amber-400/30 bg-amber-400/10",
  lost: "text-zinc-300 border-zinc-400/30 bg-zinc-400/10",
}

function resultBody(text: string): string {
  // Nur die Ergebnis-Abschnitte zeigen, nicht Kopf/Fußzeile für das Modell.
  const parts = text.split(/\n\n(?=### )/).slice(1)
  if (parts.length === 0) return text
  const last = parts[parts.length - 1]
  const cut = last.lastIndexOf("--- Ende ---")
  parts[parts.length - 1] = cut >= 0 ? last.slice(0, cut + "--- Ende ---".length) : last
  return parts.join("\n\n")
}

export function DelegationResultCard({ message }: { message: Message }) {
  const { t } = useTranslation("chat")
  const [open, setOpen] = useState(false)
  const meta = message.metadata as unknown as DelegationResultMeta
  const text = typeof message.content === "string"
    ? message.content
    : (message.content ?? []).filter((b) => b.type === "text").map((b) => (b as { text: string }).text).join("\n")
  const items = meta?.delegations ?? []

  return (
    <div data-msg-id={message.id} className="my-1 rounded-[14px] border border-[#2a364b] bg-[#141c2b] px-3 py-2 text-sm">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-2 text-left text-[#c7d2e5]">
        <Users size={14} className="text-sky-300 shrink-0" />
        <span className="font-medium">{t("delegation.result_title", { count: items.length })}</span>
        <span className="flex flex-wrap gap-1">
          {items.map((d) => (
            <span key={d.id} className={`rounded-full border px-2 py-0.5 text-[11px] ${STATUS_TONE[d.status] ?? STATUS_TONE.lost}`}>
              {d.target_name} · {t(`delegation.status.${d.status}`)}
            </span>
          ))}
        </span>
        <span className="ml-auto text-zinc-500">{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
      </button>
      {open && (
        <div className="mt-2 border-t border-white/[6%] pt-2 text-[#e8eef8]">
          <Markdown text={resultBody(text)} />
        </div>
      )}
    </div>
  )
}
