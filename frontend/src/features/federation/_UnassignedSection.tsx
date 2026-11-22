import { useTranslation } from "react-i18next"
import { canCreateHere, groupUnassigned, newProjectName, rowKey, type OriginProject } from "./_projectMap"

interface Props {
  origins: OriginProject[]
  isAdmin: boolean
  busy: string | null
  errors: Record<string, string>
  onCreate: (o: OriginProject) => void
}

// Föderation → Katalog → „Nicht zugeordnet“ (federation-shared-tasks.md §Projekte, die es nur auf
// einer Seite gibt): gruppiert nach Instanz und Ursprungsprojekt. „Projekt hier anlegen“ nur für
// Admins und nur bei „kein gleichnamiges Projekt“; andere Nutzer sehen einen Hinweis.
export function UnassignedSection({ origins, isAdmin, busy, errors, onCreate }: Props) {
  const { t } = useTranslation("federationMap")
  const groups = groupUnassigned(origins)
  if (groups.length === 0) {
    return <p className="text-xs text-zinc-500">{t("unassigned.empty")}</p>
  }
  return (
    <div className="space-y-3">
      {groups.map(g => (
        <div key={g.instance} className="space-y-1">
          <div className="text-xs font-medium text-zinc-400">{g.instance}</div>
          <ul className="space-y-1">
            {g.rows.map(o => {
              const key = rowKey(o)
              return (
                <li key={key} data-testid="unassigned-row"
                    className="flex flex-wrap items-center gap-2 rounded border border-white/[6%] px-2.5 py-1.5 text-xs">
                  <span className="text-zinc-200">{o.project_name || o.origin_project_id}</span>
                  <span className="text-zinc-500">{t("unassigned.count", { count: o.count })}</span>
                  <span className="text-amber-300/90">{t(`reason.${o.reason}`)}</span>
                  <span className="ml-auto">
                    {canCreateHere(o) && (isAdmin ? (
                      <button
                        type="button"
                        disabled={busy === key}
                        onClick={() => onCreate(o)}
                        className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-200 hover:bg-violet-500/30 disabled:opacity-50"
                      >
                        {busy === key ? t("unassigned.creating") : t("unassigned.create", { name: newProjectName(o) })}
                      </button>
                    ) : (
                      <span className="text-zinc-500">{t("unassigned.admin_can_create")}</span>
                    ))}
                  </span>
                  {errors[key] && <p className="basis-full text-red-400">{errors[key]}</p>}
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}
