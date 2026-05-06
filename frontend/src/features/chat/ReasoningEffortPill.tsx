import { useState } from "react"
import { Brain } from "lucide-react"

interface Props {
  current: string | null | undefined
  onSelect: (effort: "low" | "medium" | "high" | null) => Promise<void>
}

const EFFORTS = [
  { value: null, label: "Aus", title: "Kein Extended Thinking" },
  { value: "low" as const, label: "Low", title: "1K Tokens Reasoning Budget" },
  { value: "medium" as const, label: "Med", title: "4K Tokens Reasoning Budget" },
  { value: "high" as const, label: "High", title: "16K Tokens Reasoning Budget" },
]

/** Reasoning-Effort-Pill für Anthropic Extended Thinking. */
export function ReasoningEffortPill({ current, onSelect }: Props) {
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  const currentLabel = EFFORTS.find((e) => e.value === current)?.label || "Aus"

  async function handleSelect(value: "low" | "medium" | "high" | null) {
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
        title="Reasoning Effort (Extended Thinking)"
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
          <div className="absolute top-full right-0 mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-20 min-w-[140px] overflow-hidden">
            {EFFORTS.map((effort) => (
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
