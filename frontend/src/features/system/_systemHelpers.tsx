export function PathRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-3 text-xs">
      <span className="w-16 shrink-0 text-[#9aa7bc]">{label}</span>
      <span className="truncate font-mono text-[#d4deeb]" title={value}>{value}</span>
    </div>
  )
}
