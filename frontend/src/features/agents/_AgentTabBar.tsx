interface Props {
  tabs: { id: string; label: string }[]
  active: string
  onChange: (id: string) => void
}

export function AgentTabBar({ tabs, active, onChange }: Props) {
  return (
    <div className="flex gap-1 px-5 pt-2 pb-0 border-b border-white/[6%] bg-zinc-950/60">
      {tabs.map((tb) => (
        <button
          key={tb.id}
          onClick={() => onChange(tb.id)}
          className={`px-3 py-1.5 text-xs font-medium rounded-t-md transition-colors border-b-2 -mb-px ${
            tb.id === active
              ? "text-violet-300 border-violet-500"
              : "text-zinc-500 border-transparent hover:text-zinc-300"
          }`}
        >
          {tb.label}
        </button>
      ))}
    </div>
  )
}
