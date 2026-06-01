import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Package, RefreshCw, Container, Terminal } from "lucide-react"
import { fetchExtensions, authHeaders } from "./api"
import { ExtensionCard } from "./ExtensionCard"
import { InstallModal } from "./InstallModal"
import { CATEGORIES, type Extension, type InstallMode } from "./types"

interface ModalState {
  ext: Extension
  action: "install" | "uninstall"
  mode: InstallMode
}

export function ExtensionsPage() {
  const { t } = useTranslation("extensions")
  const [extensions, setExtensions] = useState<Extension[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState("all")
  const [modal, setModal] = useState<ModalState | null>(null)
  const [dockerInstallLog, setDockerInstallLog] = useState<string[] | null>(null)
  const [dockerInstalling, setDockerInstalling] = useState(false)

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

  const dockerAvailable = extensions.some((e) => e.docker_available)

  async function installDocker() {
    setDockerInstalling(true)
    setDockerInstallLog([t("docker.log_starting")])
    try {
      const res = await fetch("/api/admin/extensions/install-docker", {
        method: "POST",
        headers: authHeaders(),
      })
      if (!res.ok || !res.body) {
        setDockerInstallLog((l) => [...(l ?? []), `[FEHLER] HTTP ${res.status}`])
        setDockerInstalling(false)
        return
      }
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split("\n\n")
        buf = parts.pop() ?? ""
        for (const part of parts) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data:"))
          if (!dataLine) continue
          try {
            const obj = JSON.parse(dataLine.slice(5).trim())
            if (obj.line !== undefined) setDockerInstallLog((l) => [...(l ?? []), obj.line])
            if (obj.done) { load(); break }
          } catch {}
        }
      }
    } catch (e) {
      setDockerInstallLog((l) => [...(l ?? []), `[FEHLER] ${String(e)}`])
    }
    setDockerInstalling(false)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Package className="text-violet-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <span className="text-xs text-zinc-500">
            {t("installed_count", { installed: extensions.filter((e) => e.installed).length, total: extensions.length })}
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
        <div className="flex-1 min-w-0 space-y-4">
          {/* Docker-Banner im Docker-Tools-Tab */}
          {category === "dockertools" && (
            <div className={`flex items-start gap-3 p-4 rounded-xl border ${
              dockerAvailable
                ? "bg-emerald-500/5 border-emerald-500/20"
                : "bg-blue-500/5 border-blue-500/20"
            }`}>
              <Container size={18} className={dockerAvailable ? "text-emerald-400 mt-0.5" : "text-blue-400 mt-0.5"} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${dockerAvailable ? "text-emerald-300" : "text-blue-300"}`}>
                  {dockerAvailable ? t("docker.available") : t("docker.not_installed")}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {dockerAvailable ? t("docker.available_hint") : t("docker.not_installed_hint")}
                </p>
              </div>
              {!dockerAvailable && (
                <button
                  onClick={installDocker}
                  disabled={dockerInstalling}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shrink-0">
                  <Terminal size={12} />
                  {dockerInstalling ? t("docker.installing") : t("docker.install_button")}
                </button>
              )}
            </div>
          )}

          {/* Docker-Install-Log */}
          {category === "dockertools" && dockerInstallLog && (
            <div className="rounded-xl border border-white/[6%] bg-zinc-950/50 p-4 font-mono text-xs leading-relaxed max-h-48 overflow-y-auto">
              {dockerInstallLog.map((l, i) => (
                <div key={i} className={
                  l.startsWith("[OK]") ? "text-emerald-400" :
                  l.startsWith("[FEHLER]") ? "text-rose-400" :
                  "text-zinc-300"
                }>{l}</div>
              ))}
            </div>
          )}

          {loading && extensions.length === 0 ? (
            <p className="text-zinc-500 text-sm">{t("loading")}</p>
          ) : visible.length === 0 ? (
            <p className="text-zinc-500 text-sm">{t("empty_category")}</p>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
              {visible.map((ext) => (
                <ExtensionCard
                  key={ext.id}
                  ext={ext}
                  onInstall={(mode) => setModal({ ext, action: "install", mode })}
                  onUninstall={(mode) => setModal({ ext, action: "uninstall", mode })}
                  onRefresh={load}
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
