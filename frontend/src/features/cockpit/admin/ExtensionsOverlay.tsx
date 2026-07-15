import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Container, RefreshCw, Terminal } from "lucide-react"
import { fetchExtensions } from "@/features/extensions/api"
import { ExtensionCard } from "@/features/extensions/ExtensionCard"
import { InstallModal } from "@/features/extensions/InstallModal"
import { CATEGORIES, type Extension, type InstallMode } from "@/features/extensions/types"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { useDockerInstall } from "./useDockerInstall"

interface ModalState { ext: Extension; action: "install" | "uninstall"; mode: InstallMode }

export function ExtensionsOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("extensions")
  const [extensions, setExtensions] = useState<Extension[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState("all")
  const [modal, setModal] = useState<ModalState | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setExtensions(await fetchExtensions()) } catch { /* leer bei Fehler */ }
    setLoading(false)
  }, [])
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  const docker = useDockerInstall(load)
  const visible = category === "all" ? extensions : extensions.filter((e) => e.category === category)
  const categoriesWithCount = CATEGORIES.map((c) => ({
    ...c, count: c.id === "all" ? extensions.length : extensions.filter((e) => e.category === c.id).length,
  })).filter((c) => c.count > 0 || c.id === "all")
  const dockerAvailable = extensions.some((e) => e.docker_available)

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-5xl"
      headerActions={
        <CockpitButton onClick={load}>
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </CockpitButton>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-[#8d9ab0]">
          {t("installed_count", { installed: extensions.filter((e) => e.installed).length, total: extensions.length })}
        </p>

        <div className="flex gap-4">
          <nav className="hidden w-40 shrink-0 flex-col gap-0.5 md:flex">
            {categoriesWithCount.map((c) => (
              <button key={c.id} onClick={() => setCategory(c.id)}
                className={`flex items-center justify-between rounded-[4px] px-3 py-1.5 text-left text-xs font-medium transition-colors ${
                  category === c.id ? "bg-violet-500/15 text-violet-300" : "text-[#8d9ab0] hover:bg-white/[4%] hover:text-[#e8eef8]"
                }`}>
                <span>{c.label}</span>
                <span className={`text-[10px] ${category === c.id ? "text-violet-400" : "text-[#5b6675]"}`}>{c.count}</span>
              </button>
            ))}
          </nav>

          <div className="w-full md:hidden">
            <select value={category} onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8] focus:border-violet-500/60 focus:outline-none">
              {categoriesWithCount.map((c) => <option key={c.id} value={c.id}>{c.label} ({c.count})</option>)}
            </select>
          </div>

          <div className="min-w-0 flex-1 space-y-4">
            {category === "dockertools" && (
              <div className={`flex items-start gap-3 rounded-[6px] border p-4 ${dockerAvailable ? "border-emerald-500/20 bg-emerald-500/5" : "border-blue-500/20 bg-blue-500/5"}`}>
                <Container size={18} className={dockerAvailable ? "mt-0.5 text-emerald-400" : "mt-0.5 text-blue-400"} />
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-medium ${dockerAvailable ? "text-emerald-300" : "text-blue-300"}`}>
                    {dockerAvailable ? t("docker.available") : t("docker.not_installed")}
                  </p>
                  <p className="mt-0.5 text-xs text-[#8d9ab0]">{dockerAvailable ? t("docker.available_hint") : t("docker.not_installed_hint")}</p>
                </div>
                {!dockerAvailable && (
                  <button onClick={docker.install} disabled={docker.installing}
                    className="flex shrink-0 items-center gap-1.5 rounded-[4px] bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50">
                    <Terminal size={12} />{docker.installing ? t("docker.installing") : t("docker.install_button")}
                  </button>
                )}
              </div>
            )}

            {category === "dockertools" && docker.log && (
              <div className="max-h-48 overflow-y-auto rounded-[6px] border border-[#2a364b] bg-[#0b111c] p-4 font-mono text-xs leading-relaxed">
                {docker.log.map((l, i) => (
                  <div key={i} className={l.startsWith("[OK]") ? "text-emerald-400" : l.startsWith("[FEHLER]") ? "text-rose-400" : "text-[#d7deea]"}>{l}</div>
                ))}
              </div>
            )}

            {loading && extensions.length === 0 ? (
              <p className="text-sm text-[#8d9ab0]">{t("loading")}</p>
            ) : visible.length === 0 ? (
              <p className="text-sm text-[#8d9ab0]">{t("empty_category")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {visible.map((ext) => (
                  <ExtensionCard key={ext.id} ext={ext}
                    onInstall={(mode) => setModal({ ext, action: "install", mode })}
                    onUninstall={(mode) => setModal({ ext, action: "uninstall", mode })}
                    onRefresh={load} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {modal && (
        <InstallModal ext={modal.ext} action={modal.action} mode={modal.mode}
          onClose={(refresh) => { setModal(null); if (refresh) load() }} />
      )}
    </AdminOverlay>
  )
}
