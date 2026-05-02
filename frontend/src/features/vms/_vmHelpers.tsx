export function Bar({ label, pct, suffix, color }: {
  label: string; pct: number; suffix: string; color: "violet" | "emerald"
}) {
  const fillCls = color === "violet" ? "bg-violet-500" : "bg-emerald-500"
  return (
    <div>
      <div className="flex items-baseline justify-between text-zinc-400">
        <span>{label}</span>
        <span className="font-mono text-zinc-300">{suffix}</span>
      </div>
      <div className="mt-0.5 h-1 rounded-full bg-zinc-800 overflow-hidden">
        <div className={`h-full ${fillCls} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function Spec({ icon: Icon, label }: {
  icon?: React.ComponentType<{ size?: number; className?: string }>
  label: string
}) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/[4%] border border-white/[6%] text-zinc-400">
      {Icon && <Icon size={11} />}
      {label}
    </span>
  )
}
