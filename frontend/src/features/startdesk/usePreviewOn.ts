// VORSCHAU Startdesktop: reagiert, wenn die Bereichs-Leiste ein- oder ausgeschaltet wird.
import { useEffect, useState } from "react"
import { previewOn } from "./areaState"

export function usePreviewOn(): boolean {
  const [on, setOn] = useState(previewOn)
  useEffect(() => {
    const sync = () => setOn(previewOn())
    window.addEventListener("hh-startdesk-change", sync)
    window.addEventListener("storage", sync)
    return () => { window.removeEventListener("hh-startdesk-change", sync); window.removeEventListener("storage", sync) }
  }, [])
  return on
}
