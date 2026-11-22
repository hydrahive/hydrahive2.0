import { useTranslation } from "react-i18next"
import { BookOpen } from "lucide-react"
import type { CatalogMirrorItem } from "./types"
import { formatDate } from "./_catalogMirror"

interface Props {
  items: CatalogMirrorItem[]
  loading: boolean
  loadingMore: boolean
  hasMore: boolean
  onLoadMore: () => void
}

// Tabelle + Leerzustand + „Mehr laden“ des Katalog-Reiters (rein darstellend, Zustand
// liegt in CatalogTab — gleiches Muster wie CatalogSyncForm/CatalogSyncSection).
export function CatalogTable({ items, loading, loadingMore, hasMore, onLoadMore }: Props) {
  const { t } = useTranslation("federation")

  if (loading) {
    return <div className="text-xs text-zinc-500 py-4 text-center">{t("loading")}</div>
  }
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-8 text-center">
        <BookOpen size={24} className="text-zinc-700 mx-auto mb-2" />
        <p className="text-xs text-zinc-500">{t("catalog_tab.empty")}</p>
      </div>
    )
  }
  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-white/[5%]">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-zinc-500 border-b border-white/[5%]">
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_kind")}</th>
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_short_id")}</th>
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_title")}</th>
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_status")}</th>
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_project")}</th>
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_instance")}</th>
              <th className="px-2.5 py-1.5 font-normal">{t("catalog_tab.col_updated")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map(it => (
              <tr key={`${it.origin_fp}-${it.kind}-${it.item_id}`} className="border-b border-white/[3%] text-zinc-300">
                <td className="px-2.5 py-1.5">{t(`catalog_tab.kind_${it.kind}`)}</td>
                <td className="px-2.5 py-1.5 font-mono text-zinc-500">{it.short_id}</td>
                <td className="px-2.5 py-1.5 text-zinc-200">{it.title}</td>
                <td className="px-2.5 py-1.5">{t(`catalog_tab.status.${it.status}`)}</td>
                <td className="px-2.5 py-1.5 text-zinc-500">{it.project_name ?? "—"}</td>
                <td className="px-2.5 py-1.5 text-zinc-500">{it.origin_name}</td>
                <td className="px-2.5 py-1.5 text-zinc-500">{formatDate(it.updated_at, t("catalog.never"))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasMore && (
        <div className="flex justify-center">
          <button type="button" onClick={onLoadMore} disabled={loadingMore}
            className="px-3 py-1 rounded-lg text-xs border border-violet-500/40 text-violet-200 hover:bg-violet-600/20 disabled:opacity-40">
            {loadingMore ? t("catalog_tab.loading_more") : t("catalog_tab.load_more")}
          </button>
        </div>
      )}
    </>
  )
}
