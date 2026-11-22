import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { BookOpen } from "lucide-react"
import { catalogApi } from "./api"
import type { CatalogMirrorFacets, CatalogMirrorItem } from "./types"
import { CatalogFilters } from "./_CatalogFilters"
import { CatalogTable } from "./_CatalogTable"
import { ProjectMapSection } from "./_ProjectMapSection"
import { EMPTY_FILTERS, toMirrorQuery, type MirrorFilters } from "./_catalogMirror"

const EMPTY_FACETS: CatalogMirrorFacets = { instances: [], projects: [] }
const SEARCH_DEBOUNCE_MS = 300

// Reiter „Katalog“ auf Clients (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit):
// nur lesend aus der Kopie (federation_catalog_mirror). Keine Detailansicht, kein Bearbeiten (G4).
// Darunter Projekt-Zuordnung und „Nicht zugeordnet“ (G3/P3).
export function CatalogTab() {
  const { t } = useTranslation("federation")
  const [filters, setFilters] = useState<MirrorFilters>(EMPTY_FILTERS)
  const [items, setItems] = useState<CatalogMirrorItem[]>([])
  const [facets, setFacets] = useState<CatalogMirrorFacets>(EMPTY_FACETS)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState("")
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const first = useRef(true)

  function load(f: MirrorFilters) {
    setLoading(true)
    setError("")
    catalogApi.getMirror(toMirrorQuery(f, 0))
      .then(page => { setItems(page.items); setFacets(page.facets); setHasMore(page.has_more) })
      .catch(e => setError(e instanceof Error ? e.message : t("catalog_tab.load_error")))
      .finally(() => setLoading(false))
  }

  // Erster Ladevorgang sofort, danach entprellt (Suchfeld tippt man oft).
  useEffect(() => {
    if (first.current) { first.current = false; load(filters); return }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => load(filters), SEARCH_DEBOUNCE_MS)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters])

  async function loadMore() {
    setLoadingMore(true)
    try {
      const page = await catalogApi.getMirror(toMirrorQuery(filters, items.length))
      setItems(prev => [...prev, ...page.items])
      setHasMore(page.has_more)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("catalog_tab.load_error"))
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <BookOpen size={15} className="text-violet-400" />
        <span className="text-sm font-medium text-zinc-200">{t("catalog_tab.title")}</span>
        <span className="text-xs text-zinc-500 ml-1">{t("catalog_tab.subtitle")}</span>
      </div>
      <CatalogFilters filters={filters} facets={facets} onChange={setFilters} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <CatalogTable items={items} loading={loading} loadingMore={loadingMore} hasMore={hasMore} onLoadMore={loadMore} />
      <div className="pt-4 border-t border-white/[6%]">
        <ProjectMapSection />
      </div>
    </div>
  )
}
