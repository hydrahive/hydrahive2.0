import { useSearchParams } from "react-router-dom"
import { isAdminOverlayId, type AdminOverlayId } from "./adminOverlayRegistry"

export function useAdminOverlayNavigation() {
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedOverlay = searchParams.get("section")
  const overlay = isAdminOverlayId(requestedOverlay) ? requestedOverlay : null

  function setOverlay(nextOverlay: AdminOverlayId | null) {
    const next = new URLSearchParams(searchParams)
    if (nextOverlay) next.set("section", nextOverlay)
    else next.delete("section")
    next.delete("container")
    setSearchParams(next, { replace: true })
  }

  function setContainerDetail(containerId: string | null) {
    const next = new URLSearchParams(searchParams)
    next.set("section", "containers")
    if (containerId) next.set("container", containerId)
    else next.delete("container")
    setSearchParams(next, { replace: true })
  }

  return { overlay, selectedContainerId: searchParams.get("container"), setOverlay, setContainerDetail }
}
