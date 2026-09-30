/** Fehlerleiste unter dem Chat-Verlauf: Lauf-Abbrüche (refusal, leere
 * Antwort, LLM-Fehler, max_iterations). Genutzt von ChatPane und Buddy. */
export function RunErrorBanner({
  error,
  errorKind,
  continueLabel,
  onContinue,
}: {
  error: string | null
  errorKind: string | null
  continueLabel: string
  onContinue: () => void
}) {
  if (!error) return null
  return (
    <div role="alert" className="shrink-0 px-4 py-2 text-xs text-rose-400 bg-rose-500/10 border-t border-rose-500/20 flex items-center justify-between gap-3">
      <span className="break-words">{error}</span>
      {errorKind === "max_iterations" && (
        <button
          onClick={onContinue}
          className="px-2 py-1 rounded-md text-xs text-rose-200 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 whitespace-nowrap"
        >
          {continueLabel}
        </button>
      )}
    </div>
  )
}
