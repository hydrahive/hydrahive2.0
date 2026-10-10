// Verknüpfte Projekte (docs/specs/linked-projects.md): Projekt-Agent und Spezialisten dieses Projekts dürfen die
// gewählten Projekte LESEN (Dateien, Wissen) – nur wenn der Nutzer des Chats dort selbst Mitglied ist. Speichern
// erlaubt der Server nur Projekt-Admins mit Schreibrecht in jedem verknüpften Projekt.
import { useEffect, useState } from "react"
import { Link2, Loader2, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { projectsApi } from "./api"
import { linkCandidates, linksChanged, toggleLink } from "./linkedProjects"
import type { Project } from "./types"

/** ``bare``: ohne eigene Trennlinie (im Cockpit steckt der Abschnitt in einer Karte). */
interface Props { project: Project; onSaved: (p: Project) => void; bare?: boolean }

export function LinkedProjectsSection({ project, onSaved, bare = false }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const username = useAuthStore((s) => s.username)
  const role = useAuthStore((s) => s.role)
  const saved = project.linked_projects ?? []
  // Nur was gerade geändert wird, liegt hier; sonst gilt der gespeicherte Stand (auch nach Speichern/Neuladen).
  const [edit, setEdit] = useState<string[] | null>(null)
  const draft = edit ?? saved
  const setDraft = (f: (d: string[]) => string[]) => setEdit(f(draft))
  const [all, setAll] = useState<Project[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => { projectsApi.list().then(setAll).catch(() => setAll([])) }, [])

  async function save() {
    setSaving(true); setError("")
    try {
      onSaved(await projectsApi.putLinked(project.id, draft))
      setEdit(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setSaving(false) }
  }

  const candidates = linkCandidates(all, project.id, { username, role }, saved)
  return (
    <div className={bare ? "space-y-3" : "space-y-3 pt-4 border-t border-white/[6%]"}>
      <p className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
        <Link2 size={13} />{t("linked.title")}
      </p>
      <p className="text-[11px] text-zinc-500">{t("linked.hint")}</p>
      {candidates.length === 0 ? <p className="text-xs text-zinc-600">{t("linked.none")}</p> : (
        <ul className="max-h-56 space-y-1 overflow-y-auto">
          {candidates.map((p) => (
            <li key={p.id}>
              <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-300">
                <input type="checkbox" className="h-4 w-4 accent-violet-500" checked={draft.includes(p.id)}
                  onChange={() => setDraft((d) => toggleLink(d, p.id))} />
                {p.name}
              </label>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="text-xs text-rose-300" role="alert">{error}</p>}
      <button onClick={() => { void save() }} disabled={saving || !linksChanged(saved, draft)}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 transition-all">
        {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
        {tCommon("actions.save")}
      </button>
    </div>
  )
}
