/** Bedienbare Modul-Ansicht im Chat, abgeschottet (docs/specs/module-view-sandbox.md §2.3).
 *  Lädt erst beim Hinscrollen, holt die signierte Adresse beim Modul und zeigt sie in einem
 *  Sandbox-Rahmen ohne Zugriff auf HydraHive. */
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Maximize2, RefreshCw, X } from "lucide-react"
import { api } from "@/shared/api-client"
import { FRAME_SANDBOX, isSandboxUrl, viewLinkPath } from "./moduleView"

interface Props { module: string; viewId: string; title: string }

function Frame({ url, title, height }: { url: string; title: string; height: string }) {
  return (
    <iframe src={url} title={title} sandbox={FRAME_SANDBOX} referrerPolicy="no-referrer" loading="lazy"
      className="w-full rounded-lg border border-white/10 bg-white" style={{ height }} />
  )
}

export function ModuleViewFrame({ module, viewId, title }: Props) {
  const { t } = useTranslation("chat")
  const box = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const [big, setBig] = useState(false)
  const name = title || t("module_view.untitled")

  const load = useCallback(async () => {
    const path = viewLinkPath(module, viewId)
    setFailed(false)
    if (!path) { setFailed(true); return }
    try {
      const res = await api.get<{ url?: unknown }>(path)
      if (isSandboxUrl(module, res.url)) setUrl(res.url)
      else setFailed(true)
    } catch {
      setFailed(true)
    }
  }, [module, viewId])

  // Erst laden, wenn der Rahmen ins Bild kommt – lange Chats bleiben flüssig.
  useEffect(() => {
    const el = box.current
    if (!el || visible) return
    const obs = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return
      obs.disconnect()
      setVisible(true)
      void load()
    }, { rootMargin: "200px" })
    obs.observe(el)
    return () => obs.disconnect()
  }, [visible, load])

  const openBig = async () => { await load(); setBig(true) }

  return (
    <div ref={box} className="space-y-1.5 max-w-3xl">
      <div className="flex items-center gap-2 text-xs text-zinc-300">
        <span className="flex-1 truncate font-medium">{name}</span>
        {url && !failed && (
          <button onClick={openBig} className="flex items-center gap-1 text-zinc-400 hover:text-zinc-100">
            <Maximize2 size={12} />{t("module_view.open_big")}
          </button>
        )}
      </div>
      {failed ? (
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-3 text-xs text-zinc-400">
          <span className="flex-1">{t("module_view.unavailable")}</span>
          <button onClick={() => void load()} className="flex items-center gap-1 text-zinc-300 hover:text-white">
            <RefreshCw size={12} />{t("module_view.reload")}
          </button>
        </div>
      ) : url ? (
        <Frame url={url} title={name} height="480px" />
      ) : (
        <div className="rounded-lg border border-white/10 bg-white/5" style={{ height: "480px" }} />
      )}
      {big && url && (
        <div role="dialog" aria-modal="true" aria-label={name}
          className="fixed inset-0 z-50 flex flex-col gap-2 bg-black/80 p-4">
          <div className="flex items-center gap-2 text-sm text-zinc-200">
            <span className="flex-1 truncate">{name}</span>
            <button onClick={() => setBig(false)} aria-label={t("module_view.close")}
              className="rounded p-1 hover:bg-white/10"><X size={16} /></button>
          </div>
          <Frame url={url} title={name} height="100%" />
        </div>
      )}
    </div>
  )
}
