import { CircleCheck, CircleDashed } from "lucide-react"
import { CockpitPanel } from "./CockpitPanel"
import { VAULT_ACTIVE, VAULT_PLANNED } from "./vaultStatusText"

/** Rechte Spalte der Vault-Seite: was heute schützt, was noch kommt (docs/specs/vault.md §7). */
export function VaultStatusPanel() {
  return (
    <>
      <CockpitPanel theme="status" title="Schon aktiv" eyebrow="Schutz">
        <ul className="space-y-2">
          {VAULT_ACTIVE.map((t) => (
            <li key={t} className="flex gap-2 text-xs leading-4 text-[#d7deea]">
              <CircleCheck size={14} className="mt-px shrink-0 text-emerald-300" />{t}
            </li>
          ))}
        </ul>
      </CockpitPanel>
      <CockpitPanel theme="status" title="In Arbeit" eyebrow="Geplant">
        <ul className="space-y-2">
          {VAULT_PLANNED.map((t) => (
            <li key={t} className="flex gap-2 text-xs leading-4 text-[#8d9ab0]">
              <CircleDashed size={14} className="mt-px shrink-0 text-amber-300" />{t}
            </li>
          ))}
        </ul>
      </CockpitPanel>
    </>
  )
}
