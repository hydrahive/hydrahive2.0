import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Trash2 } from "lucide-react"
import { memoryApi } from "./api"
import type { MemoryEntry } from "./types"

interface Props {
  agentId: string
}

export function MemoryTab({ agentId }: Props) {
  const { t } = useTranslation("memory")
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [q, setQ] = useState("")
  const [project, setProject] = useState("")
  const [includeExpired, setIncludeExpired] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try {
      const res = await memoryApi.getMemory(agentId, {
        q: q || undefined,
        project: project || undefined,
        include_expired: includeExpired || undefined,
        limit: 200,
      })
      setEntries(res.entries)
      setTotal(res.total)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [agentId, includeExpired])

  async function handleDelete(key: string) {
    setDeleting(key)
    try {
      await memoryApi.deleteEntry(agentId, key)
      setEntries((cur) => cur.filter((e) => e.key !== key))
      setTotal((n) => n - 1)
    } catch {
      // ignore
    } finally {
      setDeleting(null)
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    load()
  }

  return (
    <div className="space-y-3 p-4">
      {/* Filter-Bar */}
      <form onSubmit={handleSearch} className="flex flex-wrap gap-2 items-end">
        <div className="flex flex-col gap-1 flex-1 min-w-40">
          <label className="text-[10px] font-medium text-zinc-500">{t("filter.search")}</label>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("filter.search_placeholder")}
            className="px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
          />
        </div>
        <div className="flex flex-col gap-1 w-36">
          <label className="text-[10px] font-medium text-zinc-500">{t("filter.project")}</label>
          <input
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder={t("filter.project_placeholder")}
            className="px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
          />
        </div>
        <label className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer pb-1">
          <input
            type="checkbox"
            checked={includeExpired}
            onChange={(e) => setIncludeExpired(e.target.checked)}
            className="accent-violet-500"
          />
          {t("filter.include_expired")}
        </label>
        <button
          type="submit"
          className="px-3 py-1 rounded-md bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 text-xs transition-colors"
        >
          {t("filter.apply")}
        </button>
      </form>

      {/* Count */}
      <p className="text-[10px] text-zinc-600">
        {loading ? t("loading") : t("entry_count", { count: total })}
      </p>

      {/* Table */}
      {entries.length === 0 && !loading ? (
        <p className="text-xs text-zinc-600 text-center py-8">{t("no_entries")}</p>
      ) : (
        <div className="rounded-md border border-white/[6%] overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/[6%] bg-white/[2%]">
                <th className="text-left px-3 py-2 text-[10px] font-medium text-zinc-500 w-48">{t("col.key")}</th>
                <th className="text-left px-3 py-2 text-[10px] font-medium text-zinc-500">{t("col.content")}</th>
                <th className="text-left px-3 py-2 text-[10px] font-medium text-zinc-500 w-20">{t("col.confidence")}</th>
                <th className="text-left px-3 py-2 text-[10px] font-medium text-zinc-500 w-24">{t("col.project")}</th>
                <th className="text-left px-3 py-2 text-[10px] font-medium text-zinc-500 w-32">{t("col.updated")}</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const expired = entry.expires_at ? new Date(entry.expires_at) < new Date() : false
                return (
                  <tr
                    key={entry.key}
                    className={`border-b border-white/[4%] hover:bg-white/[2%] transition-colors ${expired ? "opacity-50" : ""}`}
                  >
                    <td className="px-3 py-2 font-mono text-violet-300 truncate max-w-[12rem]" title={entry.key}>
                      {entry.key}
                    </td>
                    <td className="px-3 py-2 text-zinc-300 truncate max-w-xs" title={entry.content}>
                      {entry.content}
                    </td>
                    <td className="px-3 py-2 text-zinc-500">
                      {entry.confidence !== null ? (
                        <ConfidencePill value={entry.confidence} />
                      ) : (
                        <span className="text-zinc-700">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-zinc-500 font-mono text-[10px] truncate">
                      {entry.project ?? <span className="text-zinc-700">—</span>}
                    </td>
                    <td className="px-3 py-2 text-zinc-600 text-[10px]">
                      {entry.updated_at ? formatDate(entry.updated_at) : "—"}
                    </td>
                    <td className="px-2 py-2">
                      <button
                        onClick={() => handleDelete(entry.key)}
                        disabled={deleting === entry.key}
                        className="p-1 rounded text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40"
                        title={t("delete")}
                      >
                        <Trash2 size={11} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? "text-emerald-400 bg-emerald-500/10" :
    pct >= 50 ? "text-amber-400 bg-amber-500/10" :
    "text-red-400 bg-red-500/10"
  return (
    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${color}`}>
      {pct}%
    </span>
  )
}

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }) }
  catch { return iso }
}
