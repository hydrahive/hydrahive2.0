import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Film, Search } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { streamingApi } from "./api"
import type { ScrapeResult, StreamingCredentials, StreamingJob } from "./types"
import { CredentialsForm } from "./_CredentialsForm"
import { EpisodeList } from "./_EpisodeList"
import { JobList } from "./_JobList"

export function StreamingPage() {
  const { t } = useTranslation("streaming")
  const [creds, setCreds] = useState<StreamingCredentials | null>(null)
  const [url, setUrl] = useState("")
  const [scraping, setScraping] = useState(false)
  const [scrapeError, setScrapeError] = useState<string | null>(null)
  const [result, setResult] = useState<ScrapeResult | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [downloading, setDownloading] = useState(false)
  const [jobs, setJobs] = useState<StreamingJob[]>([])
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function loadCreds() {
    try { setCreds(await streamingApi.getCredentials()) } catch { /* ignore */ }
  }

  async function loadJobs() {
    try { setJobs(await streamingApi.listJobs()) } catch { /* ignore */ }
  }

  useEffect(() => {
    loadCreds()
    loadJobs()
    pollRef.current = setInterval(loadJobs, 2000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  async function handleScrape(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    setScraping(true); setScrapeError(null); setResult(null)
    try {
      const r = await streamingApi.scrape(url.trim())
      setResult(r)
      setSelected(new Set(r.episodes.map(ep => ep.key)))
    } catch (err: any) {
      setScrapeError(err?.message ?? "Fehler beim Laden")
    } finally {
      setScraping(false)
    }
  }

  function toggleEp(key: string) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  async function handleDownload() {
    if (!result || selected.size === 0) return
    setDownloading(true)
    try {
      const plexPath = creds?.plex_path ?? "/media/plex"
      const jobList = result.episodes
        .filter(ep => selected.has(ep.key))
        .map(ep => ({
          episode_key: ep.key,
          episode: ep.episode,
          bunny_video_id: ep.bunny_video_id,
          bunny_library_id: ep.bunny_library_id,
        }))
      await streamingApi.startDownload({
        series_title: result.title,
        series_url: url,
        season: result.season,
        plex_path: plexPath,
        jobs: jobList,
      })
      await loadJobs()
      setResult(null)
      setSelected(new Set())
      setUrl("")
    } catch (err: any) {
      setScrapeError(err?.message ?? t("error_download"))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center gap-3">
        <Film className="text-violet-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
        </div>
        <HelpButton topic="streaming" />
      </div>

      <CredentialsForm creds={creds} onSaved={loadCreds} />

      {creds && (
        <form onSubmit={handleScrape} className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"
            placeholder={t("url_placeholder")}
            value={url}
            onChange={e => setUrl(e.target.value)}
            required
          />
          <button
            type="submit"
            disabled={scraping || !url.trim()}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors flex-shrink-0"
          >
            <Search size={14} />
            {scraping ? t("loading") : t("load_episodes")}
          </button>
        </form>
      )}

      {scrapeError && (
        <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 px-3 py-2 text-xs text-rose-400">
          {scrapeError}
        </div>
      )}

      {result && (
        <EpisodeList
          result={result}
          selected={selected}
          onToggle={toggleEp}
          onSelectAll={() => setSelected(new Set(result.episodes.map(ep => ep.key)))}
          onClearAll={() => setSelected(new Set())}
          onDownload={handleDownload}
          downloading={downloading}
        />
      )}

      <JobList jobs={jobs} onDeleted={loadJobs} />
    </div>
  )
}
