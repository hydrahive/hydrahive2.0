import { useEffect, useState } from "react"
import { Image as ImageIcon, Music, Video } from "lucide-react"
import { atelierApi } from "@/modules/atelier/api"
import { libraryFileUrl, loadLibrary, type LibraryItem } from "./api"

interface Props {
  projectId: string
  /** Item + Ziel-Spur-ID (vom User gewählt). */
  onAdd: (item: LibraryItem, trackId: string, previewUrl: string | null) => void
  disabled: boolean
}

const KIND_TABS = [
  { id: "video" as const, label: "Videos", icon: Video },
  { id: "image" as const, label: "Bilder", icon: ImageIcon },
  { id: "audio" as const, label: "Audio", icon: Music },
]

/** Ziel-Spuren je Medientyp. */
const TARGETS: Record<LibraryItem["kind"], { id: string; label: string }[]> = {
  video: [{ id: "vid1", label: "Video 1" }, { id: "vid2", label: "Video 2" }],
  image: [{ id: "vid1", label: "Video 1" }, { id: "vid2", label: "Video 2" }],
  audio: [{ id: "music", label: "Musik" }, { id: "fx", label: "Effekt" }, { id: "voice", label: "Sprache" }],
}

export function ClipLibrary({ projectId, onAdd, disabled }: Props) {
  const [items, setItems] = useState<LibraryItem[] | null>(null)
  const [kind, setKind] = useState<LibraryItem["kind"]>("video")
  const [pending, setPending] = useState<LibraryItem | null>(null)

  useEffect(() => {
    if (!projectId) return
    let alive = true
    ;(async () => {
      let root: string | null = null
      try { root = (await atelierApi.meta(projectId)).root } catch { /* ohne root keine previews */ }
      const list = await loadLibrary(projectId, root)
      if (alive) setItems(list)
    })()
    return () => { alive = false }
  }, [projectId])

  const loading = items === null

  const allItems = items ?? []
  const visible = allItems.filter((item) => item.kind === kind)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex gap-1">
        {KIND_TABS.map((tab) => {
          const Icon = tab.icon
          const count = allItems.filter((i) => i.kind === tab.id).length
          return (
            <button key={tab.id} onClick={() => { setKind(tab.id); setPending(null) }}
              className={["inline-flex items-center gap-1.5 rounded-[3px] px-2 py-1 text-[11px] font-semibold",
                kind === tab.id ? "bg-cyan-400/15 text-cyan-100" : "bg-white/[5%] text-zinc-500 hover:text-zinc-300"].join(" ")}>
              <Icon size={12} /> {tab.label} <span className="opacity-60">{count}</span>
            </button>
          )
        })}
      </div>

      {loading ? <p className="mt-2 text-xs text-[#7a869c]">Lade Bibliothek…</p> : null}
      {!loading && visible.length === 0 ? <p className="mt-2 text-xs text-[#7a869c]">Keine Einträge — im Atelier generieren.</p> : null}

      <div className="mt-2 grid min-h-0 flex-1 auto-rows-min grid-cols-2 gap-1.5 overflow-y-auto pr-1 sm:grid-cols-3">
        {visible.map((item) => (
          <div key={item.key} className="rounded-[3px] border border-[#223048] bg-[#111827] p-1">
            <div className="relative aspect-video overflow-hidden rounded-[2px] bg-black">
              {item.kind === "image" && item.absPath ? (
                <img src={libraryFileUrl(item.absPath)} alt="" className="h-full w-full object-cover" loading="lazy" />
              ) : item.kind === "video" && item.absPath ? (
                <video src={libraryFileUrl(item.absPath)} className="h-full w-full object-cover" preload="metadata" muted />
              ) : (
                <div className="grid h-full place-items-center text-[#3f4b60]"><Music size={18} /></div>
              )}
            </div>
            <p className="mt-1 truncate text-[10px] text-[#c3ccdd]" title={item.label}>{item.label}</p>
            {pending?.key === item.key ? (
              <div className="mt-1 flex flex-wrap gap-1">
                {TARGETS[item.kind].map((target) => (
                  <button key={target.id} disabled={disabled}
                    onClick={() => { onAdd(item, target.id, item.absPath ? libraryFileUrl(item.absPath) : null); setPending(null) }}
                    className="rounded-[2px] bg-cyan-400/15 px-1.5 py-0.5 text-[9px] font-bold uppercase text-cyan-100 hover:bg-cyan-400/25">
                    → {target.label}
                  </button>
                ))}
              </div>
            ) : (
              <button disabled={disabled} onClick={() => setPending(item)}
                className="mt-1 w-full rounded-[2px] bg-white/[5%] px-1.5 py-0.5 text-[9px] font-bold uppercase text-zinc-400 hover:text-zinc-200">
                + zur Spur
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
