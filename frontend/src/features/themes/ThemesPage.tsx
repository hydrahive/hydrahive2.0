import { useCallback, useEffect, useState } from "react"
import { Palette, RefreshCw, Blocks } from "lucide-react"
import type { ThemesIndex } from "./types"
import { listThemes } from "./api"
import { InstalledThemeCard, AvailableThemeCard } from "./ThemeCard"

export function ThemesPage() {
  const [data, setData] = useState<ThemesIndex>({ installed: [], available: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await listThemes())
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }, [])

  // load() ist async — setState nach dem await; die Regel über-feuert hier.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  // Bereits installierte Themes nicht doppelt als "verfügbar" zeigen.
  const installedIds = new Set(data.installed.map((t) => t.id))
  const available = data.available.filter((t) => !installedIds.has(t.id))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Palette className="text-violet-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">Themes</h1>
          <span className="text-xs text-zinc-500">{data.installed.length} installiert</span>
        </div>
        <button
          onClick={load}
          className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
        <a
          href="/theme-editor"
          className="ml-1 inline-flex items-center gap-1.5 rounded-lg border border-teal-500/30 bg-teal-500/10 px-2.5 py-1.5 text-xs font-medium text-teal-300 hover:bg-teal-500/20 transition-colors"
        >
          <Blocks size={14} /> Theme-Editor
        </a>
      </div>

      <p className="text-sm text-zinc-500 -mt-3">
        Ein Theme wechselt das komplette Layout der Oberfläche (Menü oben ↔ links) und die Farbwelt.
        Nach der Installation ist es im Profil unter „Design" für jeden Nutzer wählbar.
      </p>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">Installiert</h2>
        {loading && data.installed.length === 0 ? (
          <p className="text-zinc-500 text-sm">Lädt …</p>
        ) : data.installed.length === 0 ? (
          <p className="text-zinc-500 text-sm">Noch keine Theme-Pakete installiert.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            {data.installed.map((th) => (
              <InstalledThemeCard key={th.id} th={th} onRefresh={load} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">Verfügbar</h2>
        {loading && available.length === 0 ? (
          <p className="text-zinc-500 text-sm">Lädt …</p>
        ) : available.length === 0 ? (
          <p className="text-zinc-500 text-sm">Keine weiteren Themes im Hub.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            {available.map((th) => (
              <AvailableThemeCard key={th.id} th={th} onRefresh={load} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
