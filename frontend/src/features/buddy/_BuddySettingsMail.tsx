import { MailAccountFields } from "@/features/agents/_MailAccountFields"
import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
}

/**
 * Eigenes Postfach für diesen Buddy. Leer = globale Mail-Settings. Teilt die
 * Felder-Komponente mit dem Agent-Editor.
 */
export function BuddySettingsMail({ config, draft, onChange }: Props) {
  const value = draft.tool_config ?? config.tool_config ?? {}
  return (
    <MailAccountFields value={value} onChange={(tool_config) => onChange({ tool_config })} />
  )
}
