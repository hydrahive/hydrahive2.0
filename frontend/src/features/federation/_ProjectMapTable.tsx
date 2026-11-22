import { useTranslation } from "react-i18next"
import { hintFor, rowKey, type OriginProject } from "./_projectMap"

export interface ProjectOption {
  id: string
  name: string
}

interface Props {
  origins: OriginProject[]
  projects: ProjectOption[]
  busy: string | null
  errors: Record<string, string>
  onChange: (o: OriginProject, target: string) => void
}

// Föderation → Katalog → „Projekt-Zuordnung“ (federation-shared-tasks.md §Korrektur im Cockpit):
// Instanz · Ursprungsprojekt · Anzahl · Zuordnung (automatisch / Projekt … / nicht anzeigen) · Hinweis.
export function ProjectMapTable({ origins, projects, busy, errors, onChange }: Props) {
  const { t } = useTranslation("federationMap")
  if (origins.length === 0) {
    return <p className="text-xs text-zinc-500">{t("map.empty")}</p>
  }
  const known = new Set(projects.map(p => p.id))
  return (
    <div className="overflow-x-auto rounded-lg border border-white/[6%]">
      <table className="w-full text-xs">
        <thead className="text-left text-zinc-500 bg-white/[2%]">
          <tr>
            <th className="px-2.5 py-1.5 font-normal">{t("map.col_instance")}</th>
            <th className="px-2.5 py-1.5 font-normal">{t("map.col_origin_project")}</th>
            <th className="px-2.5 py-1.5 font-normal text-right">{t("map.col_count")}</th>
            <th className="px-2.5 py-1.5 font-normal">{t("map.col_target")}</th>
            <th className="px-2.5 py-1.5 font-normal">{t("map.col_hint")}</th>
          </tr>
        </thead>
        <tbody>
          {origins.map(o => {
            const key = rowKey(o)
            const hint = hintFor(o)
            const stale = o.setting !== "auto" && o.setting !== "hidden" && !known.has(o.setting)
            return (
              <tr key={key} className="border-t border-white/[4%] text-zinc-300" data-testid="map-row">
                <td className="px-2.5 py-1.5">{o.origin_name || o.origin_fp.slice(0, 12)}</td>
                <td className="px-2.5 py-1.5">{o.project_name || o.origin_project_id}</td>
                <td className="px-2.5 py-1.5 text-right tabular-nums">{o.count}</td>
                <td className="px-2.5 py-1.5">
                  <select
                    aria-label={t("map.col_target")}
                    value={o.setting}
                    disabled={busy === key}
                    onChange={e => onChange(o, e.target.value)}
                    className="bg-zinc-900 border border-white/10 rounded px-1.5 py-0.5 text-xs text-zinc-200"
                  >
                    <option value="auto">{t("map.target_auto")}</option>
                    {projects.map(p => <option key={p.id} value={p.id}>{t("map.target_project", { name: p.name })}</option>)}
                    {stale && <option value={o.setting}>{t("map.target_unavailable_option")}</option>}
                    <option value="hidden">{t("map.target_hidden")}</option>
                  </select>
                  {errors[key] && <p className="text-red-400 mt-0.5">{errors[key]}</p>}
                </td>
                <td className="px-2.5 py-1.5 text-amber-300/90">{hint ? t(`reason.${hint}`) : ""}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
