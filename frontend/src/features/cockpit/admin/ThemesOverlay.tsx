import { useCallback, useEffect, useState } from "react"
import { Blocks, RefreshCw } from "lucide-react"
import type { ThemesIndex } from "@/features/themes/types"
import { listThemes } from "@/features/themes/api"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { AvailableThemeCockpitCard, InstalledThemeCockpitCard } from "./ThemeCockpitCards"

export function ThemesOverlay({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<ThemesIndex>({ installed: [], available: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setData(await listThemes()) } catch (e) { setError(String(e)) }
    setLoading(false)
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  const installedIds = new Set(data.installed.map((t) => t.id))
  const available = data.available.filter((t) => !installedIds.has(t.id))

  return (
    <AdminOverlay
      eyebrow="Admin"
      title="Themes"
      onClose={onClose}
      maxWidthClass="max-w-5xl"
      headerActions={
        <div className="flex items-center gap-2">
          <CockpitButton onClick={load}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </CockpitButton>
          <CockpitButton onClick={() => window.open("/theme-editor", "_self")}>
            <Blocks size={13} className="mr-1 inline" />Theme-Editor
          </CockpitButton>
        </div>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">
          Ein Theme wechselt das komplette Layout der Oberfläche (Menü oben ↔ links) und die Farbwelt.
          Nach der Installation ist es im Profil unter „Design" für jeden Nutzer wählbar.
          <span className="ml-1 text-[#5b6675]">· {data.installed.length} installiert</span>
        </p>

        {error && <div className="rounded-[6px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-400">{error}</div>}

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#8d9ab0]">Installiert</h2>
          {loading && data.installed.length === 0 ? (
            <p className="text-sm text-[#8d9ab0]">Lädt …</p>
          ) : data.installed.length === 0 ? (
            <p className="text-sm text-[#8d9ab0]">Noch keine Theme-Pakete installiert.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {data.installed.map((th) => <InstalledThemeCockpitCard key={th.id} th={th} onRefresh={load} />)}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#8d9ab0]">Verfügbar</h2>
          {loading && available.length === 0 ? (
            <p className="text-sm text-[#8d9ab0]">Lädt …</p>
          ) : available.length === 0 ? (
            <p className="text-sm text-[#8d9ab0]">Keine weiteren Themes im Hub.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {available.map((th) => <AvailableThemeCockpitCard key={th.id} th={th} onRefresh={load} />)}
            </div>
          )}
        </section>
      </div>
    </AdminOverlay>
  )
}
