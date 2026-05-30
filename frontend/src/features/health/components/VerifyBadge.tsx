interface Props {
  verifiziert: number
  onVerify?: () => void
}

export function VerifyBadge({ verifiziert, onVerify }: Props) {
  if (verifiziert) {
    return (
      <span
        title="Manuell verifiziert"
        className="text-emerald-400 cursor-default"
      >
        ●
      </span>
    )
  }
  return (
    <span
      title="Nicht verifiziert — klicken zum Verifizieren"
      className="text-orange-400 cursor-pointer hover:text-orange-300"
      role="button"
      onClick={onVerify}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onVerify?.() }}
      tabIndex={0}
    >
      ●
    </span>
  )
}