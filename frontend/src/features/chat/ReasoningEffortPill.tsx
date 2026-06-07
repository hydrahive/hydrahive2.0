import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Brain } from "lucide-react"

export type EffortLevel = "low" | "medium" | "high" | "xhigh" | "max"

interface Props {
  current: string | null | undefined
  extended?: boolean
  dropUp?: boolean
  onSelect: (effort: EffortLevel | null) => Promise<void>
}

interface EffortOption {
  value: EffortLevel | null
  label: string
  title: string
}

export function ReasoningEffortPill({ current, extended = false, dropUp = false, onSelect }: Props) {
  const { t } = useTranslation("chat")
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  const BASE_EFFORTS: EffortOption[] = [
    { value: null,     label: t("effort.off_label"), title: t("effort.off_title") },
    { value: "low",    label: "Low",   title: t("effort.low_title") },
    { value: "medium", label: "Med",   title: t("effort.medium_title") },
    { value: "high",   label: "High",  title: t("effort.high_title") },
  ]
  const EXTENDED_EFFORTS: EffortOption[] = [
    { value: "xhigh", label: "XHigh", title: t("effort.xhigh_title") },
    { value: "max",   label: "Max",   title: t("effort.max_title") },
  ]

  const efforts = extended ? [...BASE_EFFORTS, ...EXTENDED_EFFORTS] : BASE_EFFORTS
  const currentLabel = efforts.find((e) => e.value === current)?.label || t("effort.off_label")

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
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className={`absolute right-0 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-20 min-w-[160px] overflow-hidden ${dropUp ? "bottom-full mb-1" : "top-full mt-1"}`}>
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
