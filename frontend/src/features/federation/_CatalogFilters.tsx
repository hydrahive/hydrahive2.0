import { useTranslation } from "react-i18next"
import { Search } from "lucide-react"
import { STATUS_OPTIONS, setKind, toggleInstance, toggleStatus, type MirrorFilters } from "./_catalogMirror"
import type { CatalogMirrorFacets } from "./types"

interface Props {
  filters: MirrorFilters
  facets: CatalogMirrorFacets
  onChange: (next: MirrorFilters) => void
}

const chip = (on: boolean) =>
  `px-2 py-0.5 rounded-md text-[11px] border transition-colors ${on
    ? "bg-violet-600/30 border-violet-500/50 text-violet-200"
    : "bg-zinc-950/40 border-white/[6%] text-zinc-500 hover:text-zinc-300"}`

// Filter des Katalog-Reiters (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit):
// Instanz/Projekt aus den Facets, Status, Art, Suche. Rein darstellend.
export function CatalogFilters({ filters: f, facets, onChange }: Props) {
  const { t } = useTranslation("federation")
  const statusOptions = f.kind ? STATUS_OPTIONS[f.kind] : [...STATUS_OPTIONS.task, ...STATUS_OPTIONS.idea]

  return (
    <div className="space-y-2.5">
      <div className="relative">
        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
        <input
          value={f.q} onChange={e => onChange({ ...f, q: e.target.value })}
          placeholder={t("catalog_tab.search_placeholder")}
          className="w-full rounded-lg bg-zinc-950/60 border border-white/[8%] pl-8 pr-2.5 py-1.5 text-xs text-zinc-200"
        />
      </div>

      <div className="flex flex-wrap gap-1.5" data-part="kind-filter">
        <button type="button" aria-pressed={f.kind === null} className={chip(f.kind === null)}
          onClick={() => onChange(setKind(f, null))}>{t("catalog_tab.kind_all")}</button>
        <button type="button" aria-pressed={f.kind === "task"} className={chip(f.kind === "task")}
          onClick={() => onChange(setKind(f, "task"))}>{t("catalog_tab.kind_task")}</button>
        <button type="button" aria-pressed={f.kind === "idea"} className={chip(f.kind === "idea")}
          onClick={() => onChange(setKind(f, "idea"))}>{t("catalog_tab.kind_idea")}</button>
      </div>

      {facets.instances.length > 0 && (
        <div className="space-y-1" data-part="instance-filter">
          <p className="text-[11px] text-zinc-400">{t("catalog_tab.instance_label")}</p>
          <div className="flex flex-wrap gap-1.5">
            {facets.instances.map(i => (
              <button key={i.origin_fp} type="button" aria-pressed={f.instances.includes(i.origin_fp)}
                className={chip(f.instances.includes(i.origin_fp))}
                onClick={() => onChange(toggleInstance(f, i.origin_fp))}>
                {i.origin_name} ({i.count})
              </button>
            ))}
          </div>
        </div>
      )}

      {facets.projects.length > 0 && (
        <div className="space-y-1" data-part="project-filter">
          <p className="text-[11px] text-zinc-400">{t("catalog_tab.project_label")}</p>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {facets.projects.map(p => (
              <button key={p} type="button" aria-pressed={f.project === p} className={chip(f.project === p)}
                onClick={() => onChange({ ...f, project: f.project === p ? null : p })}>{p}</button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-1" data-part="status-filter">
        <p className="text-[11px] text-zinc-400">{t("catalog_tab.status_label")}</p>
        <div className="flex flex-wrap gap-1.5">
          {statusOptions.map(s => (
            <button key={s} type="button" aria-pressed={f.statuses.includes(s)}
              className={chip(f.statuses.includes(s))}
              onClick={() => onChange(toggleStatus(f, s))}>{t(`catalog_tab.status.${s}`)}</button>
          ))}
        </div>
      </div>
    </div>
  )
}
