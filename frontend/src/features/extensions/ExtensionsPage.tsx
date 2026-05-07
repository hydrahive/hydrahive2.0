import { useCallback, useEffect, useState } from "react"
import { Package, RefreshCw } from "lucide-react"
import { fetchExtensions } from "./api"
import { ExtensionCard } from "./ExtensionCard"
import { InstallModal } from "./InstallModal"
import { CATEGORIES, type Extension, type InstallMode } from "./types"

interface ModalState {
  ext: Extension
  action: "install" | "uninstall"
  mode: InstallMode
}

export function ExtensionsPage() {
  const [extensions, setExtensions] = useState<Extension[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState("all")
  const [modal, setModal] = useState<ModalState | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setExtensions(await fetchExtensions()) } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const visible = category === "all"
    ? extensions
    : extensions.filter((e) => e.category === category)

  const categoriesWithCount = CATEGORIES.map((c) => ({
    ...c,
    count: c.id === "all"
      ? extensions.length
      : extensions.filter((e) => e.category === c.id).length,
  })).filter((c) => c.count > 0 || c.id === "all")

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Package className="text-violet-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">Extensions</h1>
          <span className="text-xs text-zinc-500">
            {extensions.filter((e) => e.installed).length} von {extensions.length} installiert
          </span>
        </div>
        <button onClick={load}
          className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="flex gap-4">
        {/* Kategorie-Sidebar */}
        <nav className="hidden md:flex flex-col gap-0.5 w-40 shrink-0">
          {categoriesWithCount.map((c) => (
            <button key={c.id} onClick={() => setCategory(c.id)}
              className={`flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors text-left ${
                category === c.id
                  ? "bg-violet-500/15 text-violet-300"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[4%]"
              }`}>
              <span>{c.label}</span>
              <span className={`text-[10px] ${category === c.id ? "text-violet-400" : "text-zinc-600"}`}>
                {c.count}
              </span>
            </button>
          ))}
        </nav>

        {/* Mobile: Kategorie-Dropdown */}
        <div className="md:hidden w-full">
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/60">
            {categoriesWithCount.map((c) => (
              <option key={c.id} value={c.id}>{c.label} ({c.count})</option>
            ))}
          </select>
        </div>

        {/* Grid */}
        <div className="flex-1 min-w-0">
          {loading && extensions.length === 0 ? (
            <p className="text-zinc-500 text-sm">Lade Extensions…</p>
          ) : visible.length === 0 ? (
            <p className="text-zinc-500 text-sm">Keine Extensions in dieser Kategorie.</p>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
              {visible.map((ext) => (
                <ExtensionCard
                  key={ext.id}
                  ext={ext}
                  onInstall={(mode) => setModal({ ext, action: "install", mode })}
                  onUninstall={(mode) => setModal({ ext, action: "uninstall", mode })}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {modal && (
        <InstallModal
          ext={modal.ext}
          action={modal.action}
          mode={modal.mode}
          onClose={(refresh) => {
            setModal(null)
            if (refresh) load()
          }}
        />
      )}
    </div>
  )
}
