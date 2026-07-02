import type { TFunction } from "i18next"
import type { NAV_ITEMS } from "@/shared/nav-config"

export type NavItems = typeof NAV_ITEMS

/** Alles, was ein Layout-Gerüst zum Rendern braucht. Vom LayoutHost gebaut,
 *  an das aktive Layout-Gerüst durchgereicht — so bleibt jedes Gerüst schlank
 *  und die Logik (Update-State, Nav-Filterung) lebt an EINER Stelle. */
export interface LayoutChrome {
  role: string | null
  t: TFunction
  pathname: string
  /** Sichtbare Nav-Items (rollen-gefiltert). */
  visible: NavItems
  /** Schnellzugriff-Links für die Top-/Seitennavigation. */
  quickLinks: NavItems
  /** Aktuell aktive Seite (für Breadcrumb/Highlight). */
  currentPage: NavItems[number] | undefined
  /** Bento-App-Menü öffnen/schließen. */
  onBentoToggle: () => void
  /** Footer-Update-Infos. */
  footer: {
    version: string | null
    commit: string | null
    updateBehind: number | null
    isAdmin: boolean
    onUpdateClick: () => void
  }
}

/** Ein Layout-Gerüst ist eine React-Komponente, die das Chrome bekommt und
 *  <Outlet/> selbst rendert. */
export type LayoutComponent = (props: { chrome: LayoutChrome }) => React.ReactNode
