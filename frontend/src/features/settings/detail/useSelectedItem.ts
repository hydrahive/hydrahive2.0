import { useEffect } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import type { PickerItem } from "../pickerFilter"
import { selectedItem, withItem } from "../settingsTabs"

/** Auswahl aus der URL (?item=); ohne gültige Auswahl wird der erste Eintrag vorgewählt. */
export function useSelectedItem(items: PickerItem[], loading: boolean) {
  const location = useLocation()
  const navigate = useNavigate()
  const wanted = selectedItem(location.search)
  const valid = items.some((i) => i.id === wanted)

  const select = (id: string | null) =>
    navigate({ pathname: location.pathname, search: withItem(location.search, id) }, { replace: true })

  useEffect(() => {
    if (!loading && !valid && items.length > 0) select(items[0].id)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- nur bei geänderter Liste/Auswahl
  }, [loading, valid, items])

  return { value: valid ? wanted : null, select }
}
