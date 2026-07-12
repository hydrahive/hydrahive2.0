import { Film } from "lucide-react"
import { useEffect, useRef } from "react"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import type { ClipMedia } from "./api"
import { clipAt, timecode } from "./useCutPlayback"

interface Props {
  title: string
  /** Video-Spur, an die dieser Monitor gekoppelt ist (vid1 / vid2). */
  trackId: string
  timeline: MediaTimeline
  media: Map<string, ClipMedia>
  /** Position des roten Cut-Cursors in Sekunden. */
  cursorTime: number
  accent: string
}

/** Setzt ein pausiertes <video> auf ein einzelnes Frame (localTime + source_in). */
function FrozenFrame({ url, seekTo }: { url: string; seekTo: number }) {
  const ref = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const apply = () => {
      try { el.currentTime = seekTo } catch { /* metadata noch nicht bereit */ }
    }
    if (el.readyState >= 1) apply()
    else el.addEventListener("loadedmetadata", apply, { once: true })
  }, [seekTo, url])
  return <video ref={ref} src={url} className="h-full w-full object-contain" preload="metadata" muted playsInline />
}

/** Input-Monitor: zeigt das Frame der gekoppelten Video-Spur am Cut-Cursor. */
export function InputMonitor({ title, trackId, timeline, media, cursorTime, accent }: Props) {
  const track = timeline.tracks.find((t) => t.id === trackId)
  const active = track ? clipAt(track, cursorTime) : null
  const clipMedia = active ? media.get(active.clip.asset_id) ?? null : null

  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em]" style={{ color: accent }}>{title}</span>
        <span className="font-mono text-[10px] text-[#68758a]">{timecode(cursorTime)}</span>
      </div>
      <div className="relative aspect-video overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        {clipMedia && clipMedia.kind === "video" ? (
          <FrozenFrame key={active!.clip.id} url={clipMedia.url} seekTo={active!.localTime + active!.clip.source_in} />
        ) : clipMedia && clipMedia.kind === "image" ? (
          <img key={active!.clip.id} src={clipMedia.url} alt="" className="h-full w-full object-contain" />
        ) : (
          <>
            <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
            <div className="absolute inset-0 grid place-items-center">
              <div className="flex flex-col items-center gap-1 text-[#3f4b60]">
                <Film size={26} />
                <span className="text-[10px] uppercase tracking-[0.14em]">kein Signal</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
