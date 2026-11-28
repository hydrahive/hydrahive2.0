import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback } from "@/features/cockpit/admin/ui"
import { api } from "@/shared/api-client"
import { AreaSwitchList } from "./AreaSwitchList"
import { toggleArea, wouldEmpty } from "./areaItems"
import { useAreaCatalog } from "./areasApi"

interface Props {
  /** Liest und speichert die Tool-Namen-Liste (Besitzer-Freigabe oder Projekt-Pool). */
  path: string
  readOnly?: boolean
  title: string
  hint: string
  /** Projekt-Pool: leer heißt „keine Einschränkung“ – Hinweis, wenn ein Klick ihn leeren würde. */
  emptyMeansOpen?: boolean
}

/** Gemeinsamer Kern von Besitzer-Freigabe und Projekt-Pool: Bereichs-Schalter, gespeichert werden Tool-Namen. */
export function PoolAreasEditor({ path, readOnly, title, hint, emptyMeansOpen }: Props) {
  const { t } = useTranslation("agents")
  const { catalog, error } = useAreaCatalog()
  const [items, setItems] = useState<string[] | null>(null)
  const [saved, setSaved] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    let alive = true
    setItems(null)
    api.get<{ items: string[] }>(path).then((r) => { if (alive) { setItems(r.items); setSaved(r.items) } })
      .catch(() => { if (alive) setMsg({ ok: false, text: t("areas.load_failed") }) })
    return () => { alive = false }
  }, [path, t])

  const set = useMemo(() => new Set(items ?? []), [items])
  const dirty = items !== null && JSON.stringify([...items].sort()) !== JSON.stringify([...saved].sort())

  function toggle(areaId: string, on: boolean) {
    if (!catalog || items === null) return
    setItems(toggleArea(items, catalog, areaId, on))
    setMsg(null)
  }

  async function save() {
    if (items === null) return
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.put<{ items: string[] }>(path, { items })
      setItems(r.items)
      setSaved(r.items)
      setMsg({ ok: true, text: t("areas.saved") })
    } catch (e) {
      // nie Rohtext des Servers (Tool-Namen, nur Deutsch) – Review #795
      const status = (e as { status?: number } | null)?.status
      setMsg({ ok: false, text: status === 403 ? t("areas.save_forbidden") : t("areas.save_failed") })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-3">
      <div>
        <h3 className="text-sm font-bold text-[#e8eef8]">{title}</h3>
        <p className="text-xs text-[#9aa7bc]">{hint}</p>
      </div>
      {error && <AdminFeedback tone="danger">{t("areas.load_failed")}</AdminFeedback>}
      {!catalog || items === null
        ? !error && !msg && <AdminFeedback loading>{t("areas.loading")}</AdminFeedback>
        : <AreaSwitchList catalog={catalog} items={set} onToggle={toggle} disabled={busy || readOnly} />}
      {emptyMeansOpen && items !== null && wouldEmpty(saved, items) && <AdminFeedback tone="warning">{t("areas.project_empty_warning")}</AdminFeedback>}
      {msg && <AdminFeedback tone={msg.ok ? "success" : "danger"}>{msg.text}</AdminFeedback>}
      {!readOnly && items !== null && (
        <AdminAction tone="primary" onClick={() => void save()} disabled={busy || !dirty}>{t("areas.save")}</AdminAction>
      )}
    </section>
  )
}
