import { MailAccountFields } from "./_MailAccountFields"
import type { Agent } from "./types"

interface Props {
  draft: Agent
  onChange: (patch: Partial<Agent>) => void
}

/**
 * Per-Agent Postfach (Schicht 2) im vollen Agent-Editor. Leer = globale
 * Mail-Settings. Gefüllt = dieser Agent nutzt sein eigenes Konto.
 */
export function MailTab({ draft, onChange }: Props) {
  return (
    <MailAccountFields
      value={draft.tool_config ?? {}}
      onChange={(tool_config) => onChange({ tool_config })}
    />
  )
}
