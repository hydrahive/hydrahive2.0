import { useCallback, useEffect, useState } from "react"
import { ExternalLink, Globe, Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi, type PreviewStatus } from "./api"
import { openPreviewTab } from "./preview"

interface ViewProps {
  status: PreviewStatus | null
  containerMode?: boolean
  loading: boolean
  opening: boolean
  error: string | null
  onRecheck: () => void
  onOpen: () => void
}

/** Reine Anzeige (testbar ohne Browser). Knopf „Testseite öffnen“ nur, wenn unter dem Port etwas antwortet. */
export function PreviewSectionView({ status, containerMode, loading, opening, error, onRecheck, onOpen }: ViewProps) {
  const { t } = useTranslation("projects")
  return (
    <div className="space-y-2 rounded-[4px] border border-s-rand bg-s-innen p-3" data-part="testseite">
      <div className="flex items-center gap-2">
        <Globe size={14} className="text-[#69d7ff]" />
        <p className="flex-1 text-sm font-medium text-[#e8eef8]">{t("preview.title")}</p>
        {!containerMode && (
          <button type="button" onClick={onRecheck} disabled={loading} data-action="recheck"
            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] text-[#9aa7bc] hover:bg-white/5 hover:text-[#e8eef8] disabled:opacity-50">
            {loading ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}{t("preview.recheck")}
          </button>
        )}
      </div>
      {containerMode ? (
        <p className="text-xs text-[#9aa7bc]">{t("preview.container_mode")}</p>
      ) : status && (
        <>
          <p className={`text-xs ${status.running ? "text-emerald-300" : "text-[#9aa7bc]"}`}>
            {status.running ? t("preview.running") : t("preview.not_running")}
          </p>
          <p className="text-[11px] text-[#9aa7bc]">{t("preview.port", { port: status.port })}</p>
          {status.running && (
            <button type="button" onClick={onOpen} disabled={opening} data-action="open"
              className="flex items-center gap-2 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-3 py-1.5 text-xs font-bold text-[#69d7ff] hover:bg-[#69d7ff]/15 disabled:opacity-50">
              {opening ? <Loader2 size={12} className="animate-spin" /> : <ExternalLink size={12} />}{t("preview.open")}
            </button>
          )}
          {!status.running && <p className="text-[11px] text-[#9aa7bc]">{t("preview.how_to_start")}</p>}
          <p className="text-[10px] text-zinc-500">{t("preview.last_wins")}</p>
          <p className="text-[10px] text-zinc-500">{t("preview.certificate")}</p>
        </>
      )}
      {error && <p className="rounded-md border border-rose-500/20 bg-rose-500/[6%] px-2 py-1 text-xs text-rose-300">{error}</p>}
    </div>
  )
}

/** Testseite des Projekts (ziele/projekt-testumgebung.md §4): Status beim Öffnen, „Neu prüfen“, kein Dauer-Abfragen. */
export function PreviewSection({ projectId, containerMode }: { projectId: string; containerMode?: boolean }) {
  const { t } = useTranslation("projects")
  const [status, setStatus] = useState<PreviewStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setStatus(await projectsApi.getPreview(projectId)) }
    catch (e) { setStatus(null); setError(e instanceof Error ? e.message : String(e)) }
    finally { setLoading(false) }
  }, [projectId])

  useEffect(() => { if (!containerMode) void load() }, [load, containerMode])

  async function onOpen() {
    setOpening(true); setError(null)
    try {
      const opened = await openPreviewTab((url, target) => window.open(url, target),
        () => projectsApi.openPreview(projectId), window.location.hostname)
      if (!opened) setError(t("preview.popup_blocked"))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setOpening(false) }
  }

  return <PreviewSectionView status={status} containerMode={containerMode} loading={loading} opening={opening}
    error={error} onRecheck={() => void load()} onOpen={() => void onOpen()} />
}
