import { useState, useEffect } from "react"
import { CollapsiblePanel } from "./CollapsiblePanel"

interface PanelState { left: boolean; right: boolean }
const STORAGE_KEY = "hh2.chat.panels"

function loadState(): PanelState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { left: true, right: true }
}

interface Props {
  left: React.ReactNode
  center: React.ReactNode
  right: React.ReactNode
}

export function ThreePanelLayout({ left, center, right }: Props) {
  const [panels, setPanels] = useState<PanelState>(loadState)

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(panels)) } catch { /* ignore */ }
  }, [panels])

  return (
    <div className="flex h-[calc(100%+2rem)] md:h-[calc(100%+3rem)] -m-4 md:-m-6 overflow-hidden">
      <CollapsiblePanel side="left" open={panels.left} width={280}
        onToggle={() => setPanels((p) => ({ ...p, left: !p.left }))}>
        {left}
      </CollapsiblePanel>
      <main className="flex-1 flex flex-col min-w-0">{center}</main>
      <CollapsiblePanel side="right" open={panels.right} width={300}
        onToggle={() => setPanels((p) => ({ ...p, right: !p.right }))}>
        {right}
      </CollapsiblePanel>
    </div>
  )
}
