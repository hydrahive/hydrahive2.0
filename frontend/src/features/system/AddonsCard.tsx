import { AddonsView } from "./AddonsView"
import { useAddons } from "./useAddons"

/** Admin-Cockpit → System → „Zusatz-Module“ (docs/specs/installer-core-first.md §3). */
export function AddonsCard() {
  const a = useAddons()
  return (
    <AddonsView items={a.items} running={a.running} target={a.target} phase={a.phase} log={a.log} error={a.error}
      onAsk={a.ask} onConfirm={a.confirm} onClose={a.close} />
  )
}
