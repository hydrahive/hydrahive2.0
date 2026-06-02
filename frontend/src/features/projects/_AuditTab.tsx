import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { ClipboardList, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { rgbFor } from "@/shared/colors"
import type { ProjectAuditAction, ProjectAuditEntry } from "./types"

interface Props {
  projectId: string
}

const ACTION_KEYS: Record<ProjectAuditAction, string> = {
  project_updated: "audit.actions.project_updated",
  member_added: "audit.actions.member_added",
  member_removed: "audit.actions.member_removed",
  server_assigned: "audit.actions.server_assigned",
  server_unassigned: "audit.actions.server_unassigned",
}

const ALL_ACTIONS: ProjectAuditAction[] = [
  "project_updated",
  "member_added",
  "member_removed",
  "server_assigned",
  "server_unassigned",
]

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso)
  return d.toLocaleString(locale, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

interface EntryRowProps {
  entry: ProjectAuditEntry
  actionLabel: string
  locale: string
}

function EntryRow({ entry, actionLabel, locale }: EntryRowProps) {
  return (
    <div className="flex items-start gap-3 px-3 py-2.5 box overflow-hidden" style={{ "--c": rgbFor("/projects") } as CSSProperties}>
      <ClipboardList size={13} className="text-zinc-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <span className="text-sm text-zinc-200 font-medium">{actionLabel}</span>
        {entry.target && (
          <span className="ml-1.5 text-sm text-zinc-400 truncate">
            — {entry.target}
          </span>
        )}
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-zinc-500">{entry.user}</span>
          <span className="text-xs text-zinc-600">{formatDate(entry.created_at, locale)}</span>
        </div>
      </div>
    </div>
  )
}

export function AuditTab({ projectId }: Props) {
  const { t, i18n } = useTranslation("projects")
  const [entries, setEntries] = useState<ProjectAuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterAction, setFilterAction] = useState("")
  const [filterUser, setFilterUser] = useState("")
  const [pendingUser, setPendingUser] = useState("")

  function load(action: string, user: string) {
    setLoading(true)
    setError(null)
    projectsApi
      .getAudit(projectId, {
        action: action || undefined,
        user: user || undefined,
      })
      .then((res) => setEntries(res.entries))
      .catch((e) => {
        setError(e instanceof Error ? e.message : t("audit.load_error"))
        setEntries([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    setFilterAction("")
    setFilterUser("")
    setPendingUser("")
    load("", "")
  }, [projectId])

  function handleActionChange(value: string) {
    setFilterAction(value)
    load(value, filterUser)
  }

  function handleUserSearch() {
    setFilterUser(pendingUser)
    load(filterAction, pendingUser)
  }

  function handleUserKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleUserSearch()
  }

  const locale = i18n.language

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={filterAction}
          onChange={(e) => handleActionChange(e.target.value)}
          className="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-white/[6%] text-xs text-zinc-300 focus:outline-none focus:border-violet-500/50"
        >
          <option value="">{t("audit.filter.all_actions")}</option>
          {ALL_ACTIONS.map((a) => (
            <option key={a} value={a}>
              {t(ACTION_KEYS[a])}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-1">
          <input
            value={pendingUser}
            onChange={(e) => setPendingUser(e.target.value)}
            onKeyDown={handleUserKeyDown}
            placeholder={t("audit.filter.user_placeholder")}
            className="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-white/[6%] text-xs text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-violet-500/50 w-36"
          />
          <button
            onClick={handleUserSearch}
            className="px-2.5 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 border border-white/[6%] text-xs text-zinc-300 transition-colors"
          >
            {t("audit.filter.search")}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={20} className="animate-spin text-zinc-500" />
        </div>
      ) : entries.length === 0 ? (
        <p className="text-sm text-zinc-500 py-8 text-center">{t("audit.empty")}</p>
      ) : (
        <div className="space-y-1.5">
          {entries.map((entry) => {
            const actionLabel = ACTION_KEYS[entry.action as ProjectAuditAction]
              ? t(ACTION_KEYS[entry.action as ProjectAuditAction])
              : entry.action
            return (
              <EntryRow
                key={entry.id}
                entry={entry}
                actionLabel={actionLabel}
                locale={locale}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
