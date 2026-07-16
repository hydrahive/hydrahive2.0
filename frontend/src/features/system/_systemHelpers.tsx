export function PathRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-3 text-xs">
      <span className="w-16 shrink-0 text-[#8d9ab0]">{label}</span>
      <span className="truncate font-mono text-[#d4deeb]" title={value}>{value}</span>
    </div>
  )
}
