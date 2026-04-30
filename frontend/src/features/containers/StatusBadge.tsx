import type { ActualState } from "./types"

const PRESETS: Record<ActualState, { label: string; ring: string; text: string; pulse: boolean }> = {
  created:  { label: "Erstellt",     ring: "ring-zinc-500/40",   text: "text-zinc-400",   pulse: false },
  starting: { label: "Startet…",     ring: "ring-amber-500/50",  text: "text-amber-300",  pulse: true  },
  running:  { label: "Läuft",        ring: "ring-emerald-500/60", text: "text-emerald-300", pulse: false },
  stopping: { label: "Stoppt…",      ring: "ring-amber-500/50",  text: "text-amber-300",  pulse: true  },
  stopped:  { label: "Gestoppt",     ring: "ring-zinc-500/40",   text: "text-zinc-400",   pulse: false },
  error:    { label: "Fehler",       ring: "ring-rose-500/60",   text: "text-rose-300",   pulse: false },
}

export function ContainerStatusBadge({ state }: { state: ActualState }) {
  const p = PRESETS[state]
  return (
    <span className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-white/[3%] ring-1 ${p.ring} ${p.text}`}>
      <span className={`w-2 h-2 rounded-full bg-current ${p.pulse ? "animate-pulse" : ""}`} />
      {p.label}
    </span>
  )
}
