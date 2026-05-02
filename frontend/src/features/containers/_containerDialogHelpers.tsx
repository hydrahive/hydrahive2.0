export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-zinc-300">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-zinc-500">{hint}</p>}
    </div>
  )
}

export function RadioCard({ active, onClick, title, desc }: {
  active: boolean; onClick: () => void; title: string; desc: string
}) {
  return (
    <button type="button" onClick={onClick}
      className={`text-left p-3 rounded-lg border transition-colors ${
        active ? "bg-violet-500/15 border-violet-500/40" : "bg-white/[2%] border-white/[8%] hover:border-white/[15%]"
      }`}>
      <p className="text-sm font-medium text-zinc-100">{title}</p>
      <p className="text-[11px] text-zinc-500 mt-0.5">{desc}</p>
    </button>
  )
}
