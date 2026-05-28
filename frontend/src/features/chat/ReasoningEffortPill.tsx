import { useState } from "react"
import { Brain } from "lucide-react"

export type EffortLevel = "low" | "medium" | "high" | "xhigh" | "max"

interface Props {
  current: string | null | undefined
  /** Claude 4.6+ unterstützt xhigh/max (output_config.effort). Legacy-Modelle nur low/med/high. */
  extended?: boolean
  onSelect: (effort: EffortLevel | null) => Promise<void>
}

interface EffortOption {
  value: EffortLevel | null
  label: string
  title: string
}

const BASE_EFFORTS: EffortOption[] = [
  { value: null, label: "Aus", title: "Kein Reasoning-Effort" },
  { value: "low", label: "Low", title: "Schnell & günstig — einfache Aufgaben" },
  { value: "medium", label: "Med", title: "Ausgewogen zwischen Tempo und Tiefe" },
  { value: "high", label: "High", title: "Tiefes Reasoning (Standard auf Opus)" },
]

const EXTENDED_EFFORTS: EffortOption[] = [
  { value: "xhigh", label: "XHigh", title: "Long-Horizon — empfohlen für Agentic Coding" },
  { value: "max", label: "Max", title: "Maximale Tiefe, keine Token-Grenze" },
]

/** Reasoning-Effort-Pill. Claude 4.6+ (extended) zeigt zusätzlich XHigh/Max. */
export function ReasoningEffortPill({ current, extended = false, onSelect }: Props) {
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  const efforts = extended ? [...BASE_EFFORTS, ...EXTENDED_EFFORTS] : BASE_EFFORTS
  const currentLabel = efforts.find((e) => e.value === current)?.label || "Aus"

  async function handleSelect(value: EffortLevel | null) {
    setBusy(true)
    try {
      await onSelect(value)
      setOpen(false)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={busy}
        title="Reasoning Effort"
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all
          bg-indigo-500/15 text-indigo-200 border border-indigo-500/30 hover:bg-indigo-500/20 hover:border-indigo-500/40
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Brain size={12} />
        <span>{currentLabel}</span>
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute top-full right-0 mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-20 min-w-[160px] overflow-hidden">
            {efforts.map((effort) => (
              <button
                key={effort.label}
                onClick={() => handleSelect(effort.value)}
                disabled={busy}
                title={effort.title}
                className={`w-full px-3 py-2 text-left text-xs transition-colors
                  ${effort.value === current
                    ? "bg-indigo-500/20 text-indigo-200"
                    : "text-zinc-300 hover:bg-zinc-800"
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                {effort.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
