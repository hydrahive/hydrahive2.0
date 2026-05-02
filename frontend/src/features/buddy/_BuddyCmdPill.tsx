const PILL_COLORS: Record<string, string> = {
  sky: "text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 border-sky-500/30",
  amber: "text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/30",
  emerald: "text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/30",
  violet: "text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 border-violet-500/30",
  pink: "text-pink-300 bg-pink-500/10 hover:bg-pink-500/20 border-pink-500/30",
}

interface Props {
  icon: React.ReactNode
  label: string
  color: keyof typeof PILL_COLORS
  onClick: () => void
}

export function CmdPill({ icon, label, color, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={`/${label}`}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] font-medium transition-colors ${PILL_COLORS[color]}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
