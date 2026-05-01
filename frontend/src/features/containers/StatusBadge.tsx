import type { ActualState } from "./types"

const PRESETS: Record<ActualState, { label: string; cls: string; pulse: boolean }> = {
  created:  { label: "Erstellt", cls: "bg-zinc-500/[8%] border-zinc-500/20 text-zinc-400",          pulse: false },
  starting: { label: "Startet…", cls: "bg-amber-500/[8%] border-amber-500/25 text-amber-300",       pulse: true  },
  running:  { label: "Läuft",    cls: "bg-emerald-500/[8%] border-emerald-500/25 text-emerald-300", pulse: false },
  stopping: { label: "Stoppt…",  cls: "bg-amber-500/[8%] border-amber-500/25 text-amber-300",       pulse: true  },
  stopped:  { label: "Gestoppt", cls: "bg-zinc-500/[8%] border-zinc-500/20 text-zinc-400",          pulse: false },
  error:    { label: "Fehler",   cls: "bg-rose-500/[8%] border-rose-500/25 text-rose-300",          pulse: false },
}

export function ContainerStatusBadge({ state }: { state: ActualState }) {
  const p = PRESETS[state]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${p.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full bg-current ${p.pulse ? "animate-pulse" : ""}`} />
      {p.label}
    </span>
  )
}
