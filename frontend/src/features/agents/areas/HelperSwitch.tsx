import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toolPoolApi, type AgentToolPool } from "../api"
import type { Agent } from "../types"
import { enabledFromPool, extraPoolItems, helperPoolItems } from "./helperPool"
import { HelperView } from "./HelperView"
import type { AreaCatalog } from "./types"

interface Props { agent: Agent; catalog: AreaCatalog; mayEdit: boolean }

/** Helfer-Bereich (AB7) – nur bei Agenten vom Typ specialist/project. Speichert den Pool mit TOOL-NAMEN (PUT …/tool-pool). */
export function HelperSwitch({ agent, catalog, mayEdit }: Props) {
  const { t } = useTranslation("agents")
  const [pool, setPool] = useState<AgentToolPool | null>(null)
  const [enabled, setEnabled] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [saved, setSaved] = useState<string>("[]")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    let alive = true
    toolPoolApi.get(agent.id).then((p) => {
      if (!alive) return
      const ids = enabledFromPool(catalog.areas, p.items, p.forbidden ?? [])
      setPool(p); setSelected(ids); setEnabled(p.items.length > 0); setSaved(JSON.stringify(helperPoolItems(catalog.areas, ids, p.forbidden ?? [])))
    }).catch(() => { if (alive) setError(t("areas.load_failed")) })
    return () => { alive = false }
  }, [agent.id, catalog.areas, t])

  const forbidden = pool?.forbidden ?? []
  // Einträge, die keinem ganzen Bereich entsprechen (Expertenansicht), bleiben beim Speichern erhalten (Review #794)
  const extra = pool ? extraPoolItems(catalog.areas, pool.items, forbidden) : []
  const items = enabled ? [...helperPoolItems(catalog.areas, selected, forbidden), ...extra] : []
  const dirty = JSON.stringify(items) !== saved

  async function save() {
    setBusy(true); setError(null); setDone(false)
    try {
      const res = await toolPoolApi.put(agent.id, items)       // Tool-Namen, nie kategorie:x
      setSaved(JSON.stringify(res.items)); setDone(true)
    } catch (e) {
      // nie Rohtext des Servers (Tool-Namen, nur Deutsch) – Review #794
      const status = (e as { status?: number } | null)?.status
      setError(status === 403 ? t("areas.helper_forbidden") : t("catalog.pool_save_failed"))
    } finally { setBusy(false) }
  }

  if (!pool) return error ? <p className="text-[11px] text-rose-300" role="alert">{error}</p> : null
  return (
    <HelperView
      areas={catalog.areas} forbidden={forbidden} enabled={enabled} selected={selected} mayEdit={mayEdit} busy={busy} dirty={dirty}
      onToggleEnabled={() => { setDone(false); setEnabled((v) => !v) }}
      onToggleArea={(id) => { setDone(false); setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id])) }}
      onSave={save} error={error} done={done} extraCount={extra.length}
    />
  )
}
