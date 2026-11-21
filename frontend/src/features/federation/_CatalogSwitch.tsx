interface Props {
  checked: boolean
  label: string
  hint?: string
  disabled?: boolean
  onChange: (next: boolean) => void
}

// Kleiner Schalter für den Föderations-Katalog (Hub, Annehmen, Sync an/aus).
export function CatalogSwitch({ checked, label, hint, disabled, onChange }: Props) {
  return (
    <label className={`flex items-start gap-2 ${disabled ? "opacity-50" : "cursor-pointer"}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 h-4 w-7 shrink-0 rounded-full transition-colors ${checked ? "bg-violet-600" : "bg-zinc-700"}`}
      >
        <span className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${checked ? "left-3.5" : "left-0.5"}`} />
      </button>
      <span className="min-w-0">
        <span className="block text-xs text-zinc-200">{label}</span>
        {hint && <span className="block text-[11px] text-zinc-500">{hint}</span>}
      </span>
    </label>
  )
}
