/**
 * Darf gerade gespeichert werden? Reine Bedingung, ausgelagert aus ProjectAgentEditOverlay,
 * damit die Sperre bei laufendem/gestartetem Lösch-Auftrag (deleteStarted) ohne Overlay-Setup
 * testbar ist — siehe ProjectAgentDeleteSection.onDeleteStarted: ein PATCH könnte sonst
 * `status: "active"` zurückschreiben und die Sperre aus dem Lösch-Auftrag (Backend) aufheben.
 */
export function canSaveAgent(opts: {
  dirty: boolean
  saving: boolean
  deleteStarted: boolean
  name: string
  llmModel: string
  promptDirty: boolean
  prompt: string
}): boolean {
  if (!opts.dirty || opts.saving || opts.deleteStarted) return false
  if (!opts.name.trim() || !opts.llmModel.trim()) return false
  if (opts.promptDirty && !opts.prompt.trim()) return false
  return true
}
