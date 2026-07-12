import { Film, Pause, Play, SkipBack, SkipForward, Square } from "lucide-react"
import { useEffect, useState, type ComponentType } from "react"
import { buildAssetMedia, loadAtelierRoot, type ClipMedia } from "./videocut/api"
import { ClipLibrary } from "./videocut/ClipLibrary"
import { OutputMonitor } from "./videocut/OutputMonitor"
import { PlaybackAudio } from "./videocut/PlaybackAudio"
import { TrackArea } from "./videocut/TrackArea"
import { timecode, useCutPlayback } from "./videocut/useCutPlayback"
import { useCutTimeline } from "./videocut/useCutTimeline"

/** Videoschnitt (V2): Playback im Output-Monitor, Playhead + Transport.
 *  Die beiden Input-Monitore bleiben Platzhalter (Feintrim ab V3/V4). */

function InputMonitor({ title }: { title: string }) {
  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#5aa9ff]">{title}</span>
        <span className="font-mono text-[10px] text-[#68758a]">00:00:00</span>
      </div>
      <div className="relative aspect-video overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
        <div className="absolute inset-0 grid place-items-center">
          <div className="flex flex-col items-center gap-1 text-[#3f4b60]">
            <Film size={26} />
            <span className="text-[10px] uppercase tracking-[0.14em]">kein Signal</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function TransportButton({ icon: Icon, label, onClick, primary, disabled }: {
  icon: ComponentType<{ size?: number | string }>
  label: string
  onClick: () => void
  primary?: boolean
  disabled?: boolean
}) {
  return (
    <button type="button" title={label} aria-label={label} onClick={onClick} disabled={disabled}
      className={["grid h-8 w-8 place-items-center rounded-[4px] border transition-colors disabled:opacity-40",
        primary ? "border-[#ffb86b]/50 bg-[#ffb86b]/10 text-[#ffb86b] hover:bg-[#ffb86b]/20" : "border-[#2a364b] bg-[#111827] text-[#8d9ab0] hover:text-[#c3ccdd]"].join(" ")}>
      <Icon size={15} />
    </button>
  )
}

interface Props {
  projectId: string
}

export function MediaPostProduction({ projectId }: Props) {
  const { timeline, assets, loading, saving, error, addClip, removeClip } = useCutTimeline(projectId)
  const { currentTime, duration, playing, play, pause, stop, seek, toStart, toEnd } = useCutPlayback(timeline)

  // Atelier-Root → asset_id-Medien-Map für das Playback.
  const [media, setMedia] = useState<Map<string, ClipMedia>>(new Map())
  useEffect(() => {
    if (!projectId) return
    let alive = true
    void loadAtelierRoot(projectId).then((root) => {
      if (alive) setMedia(buildAssetMedia(assets, root))
    })
    return () => { alive = false }
  }, [projectId, assets])

  const canPlay = duration > 0

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_260px]">
      <div className="min-w-0">
        {/* 3 Monitore: Input 1, Input 2, Output (live) */}
        <div className="grid gap-3 lg:grid-cols-3">
          <InputMonitor title="Input · Vid 1" />
          <InputMonitor title="Input · Vid 2" />
          {timeline ? (
            <OutputMonitor timeline={timeline} media={media} currentTime={currentTime} playing={playing} />
          ) : (
            <InputMonitor title="Output" />
          )}
        </div>

        {/* Transport + Zeitanzeige */}
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#2a364b] pt-3">
          <TransportButton icon={SkipBack} label="Zum Anfang" onClick={toStart} disabled={!canPlay} />
          {playing ? (
            <TransportButton icon={Pause} label="Pause" onClick={pause} primary disabled={!canPlay} />
          ) : (
            <TransportButton icon={Play} label="Abspielen" onClick={play} primary disabled={!canPlay} />
          )}
          <TransportButton icon={Square} label="Stopp" onClick={stop} disabled={!canPlay} />
          <TransportButton icon={SkipForward} label="Zum Ende" onClick={toEnd} disabled={!canPlay} />
          <span className="ml-1 font-mono text-[11px] text-[#8d9ab0]">{timecode(currentTime)} / {timecode(duration)}</span>
          <span className="ml-auto text-[10px] uppercase tracking-[0.12em] text-[#68758a]">
            {loading ? "Lade…" : saving ? "Speichere…" : "Gespeichert"}
          </span>
        </div>

        {error ? <p className="mt-2 text-xs text-rose-300">{error}</p> : null}

        {/* Spuren mit Clips + Playhead */}
        <div className="mt-3">
          {timeline ? (
            <TrackArea timeline={timeline} assets={assets} onRemoveClip={removeClip} currentTime={currentTime} onSeek={seek} />
          ) : (
            <p className="text-xs text-[#7a869c]">{loading ? "Timeline wird geladen…" : "Keine Timeline verfügbar."}</p>
          )}
        </div>
      </div>

      {/* Clip-Bibliothek rechts */}
      <aside className="min-h-0 rounded-[4px] border border-[#2a364b] bg-[#111827] p-2 xl:max-h-[calc(100vh-220px)]">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-[#68758a]">Bibliothek</p>
        <ClipLibrary projectId={projectId} onAdd={(item, trackId, url) => void addClip(item, trackId, url)} disabled={!timeline || saving} />
      </aside>

      {/* Parallele Audio-Wiedergabe (versteckt) */}
      {timeline ? <PlaybackAudio timeline={timeline} media={media} currentTime={currentTime} playing={playing} /> : null}
    </div>
  )
}
