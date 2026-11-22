import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { FolderTree } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { projectsApi } from "@/features/projects/api"
import { createPayload, projectMapApi, rowKey, type OriginProject } from "./_projectMap"
import { ProjectMapTable, type ProjectOption } from "./_ProjectMapTable"
import { UnassignedSection } from "./_UnassignedSection"

const errText = (e: unknown, fallback: string) => (e instanceof Error && e.message ? e.message : fallback)

async function fetchAll(): Promise<{ origins: OriginProject[]; projects: ProjectOption[] }> {
  const [map, list] = await Promise.all([projectMapApi.list(), projectsApi.list()])
  const projects = list.map(p => ({ id: p.id, name: p.name })).sort((a, b) => a.name.localeCompare(b.name))
  return { origins: map.origins, projects }
}

// Bereiche „Projekt-Zuordnung“ und „Nicht zugeordnet“ im Katalog-Reiter (G3/P3). Jeder Nutzer
// korrigiert nur seine eigenen Zeilen (GET/PUT /api/federation/catalog/project-map); Projekte
// anlegen nur Admins über das bestehende POST /api/projects.
export function ProjectMapSection() {
  const { t } = useTranslation("federationMap")
  const username = useAuthStore(s => s.username)
  const isAdmin = useAuthStore(s => s.role) === "admin"
  const [origins, setOrigins] = useState<OriginProject[]>([])
  const [projects, setProjects] = useState<ProjectOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState<string | null>(null)
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({})

  function apply(d: { origins: OriginProject[]; projects: ProjectOption[] }) {
    setOrigins(d.origins)
    setProjects(d.projects)
  }

  useEffect(() => {
    let cancelled = false
    fetchAll()
      .then(d => { if (!cancelled) apply(d) })
      .catch(e => { if (!cancelled) setError(errText(e, t("load_error"))) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [t])

  function setRowError(key: string, msg: string) {
    setRowErrors(prev => {
      const next = { ...prev }
      if (msg) next[key] = msg
      else delete next[key]
      return next
    })
  }

  async function change(o: OriginProject, target: string) {
    const key = rowKey(o)
    setBusy(key)
    setRowError(key, "")
    try {
      const r = await projectMapApi.set({ origin_fp: o.origin_fp, origin_project_id: o.origin_project_id, target })
      setOrigins(r.origins)
    } catch (e) {
      setRowError(key, errText(e, t("save_error")))
    } finally {
      setBusy(null)
    }
  }

  async function create(o: OriginProject) {
    const key = rowKey(o)
    setBusy(key)
    setRowError(key, "")
    try {
      await projectsApi.create(createPayload(o, username))      // nichts sonst vom Ursprung übernehmen
      apply(await fetchAll())
    } catch (e) {
      setRowError(key, errText(e, t("create_error")))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FolderTree size={15} className="text-violet-400" />
        <span className="text-sm font-medium text-zinc-200">{t("map.title")}</span>
        <span className="text-xs text-zinc-500 ml-1">{t("map.subtitle")}</span>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {loading ? (
        <div className="text-xs text-zinc-500 py-2">{t("loading")}</div>
      ) : (
        <>
          <ProjectMapTable origins={origins} projects={projects} busy={busy} errors={rowErrors} onChange={change} />
          <div className="space-y-2">
            <div className="text-sm font-medium text-zinc-200">{t("unassigned.title")}</div>
            <p className="text-xs text-zinc-500">{t("unassigned.subtitle")}</p>
            <UnassignedSection origins={origins} isAdmin={isAdmin} busy={busy} errors={rowErrors} onCreate={create} />
          </div>
        </>
      )}
    </div>
  )
}
