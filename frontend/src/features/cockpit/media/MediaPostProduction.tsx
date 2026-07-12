import { Pause, Play, Scissors, SkipBack, SkipForward, Square } from "lucide-react"
import { useEffect, useState, type ComponentType } from "react"
import { buildAssetMedia, loadAtelierRoot, type ClipMedia } from "./videocut/api"
import { ClipLibrary } from "./videocut/ClipLibrary"
import { CutPointInspector } from "./videocut/CutPointInspector"
import { InputMonitor } from "./videocut/InputMonitor"
import { OutputMonitor } from "./videocut/OutputMonitor"
import { PlaybackAudio } from "./videocut/PlaybackAudio"
import { TrackArea } from "./videocut/TrackArea"
import { timecode, useCutPlayback } from "./videocut/useCutPlayback"
import { useCutTimeline } from "./videocut/useCutTimeline"

/** Videoschnitt (V3c): A/B-Roll mit Übergangseffekten. Input 1/2 zeigen vid1/vid2
 *  am roten Cut-Cursor; Clips überlappen; Schnittpunkte schalten den Output um,
 *  mit optionalem Übergang (Crossfade/Wipe/Schwarzblende). */

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
  const {
    timeline, assets, loading, saving, error,
    addClip, removeClip, previewClipStart, moveClip,
    addCutPoint, previewCutPoint, moveCutPoint, updateCutPoint, removeCutPoint,
  } = useCutTimeline(projectId)
  const { currentTime, duration, playing, play, pause, stop, seek, toStart, toEnd } = useCutPlayback(timeline)

  // Roter Cut-Cursor (Justage-Position der Input-Monitore).
  const [cursorTime, setCursorTime] = useState(0)
  // Ausgewählter Schnittpunkt (für Inspector).
  const [selectedCutId, setSelectedCutId] = useState<string | null>(null)
  const selectedCut = timeline?.cut_points?.find((cp) => cp.id === selectedCutId) ?? null

  // Atelier-Root → asset_id-Medien-Map für Playback + Frozen-Frames.
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
        {/* 3 Monitore: Input 1 (vid1), Input 2 (vid2), Output (Ergebnis) */}
        <div className="grid gap-3 lg:grid-cols-3">
          {timeline ? (
            <>
              <InputMonitor title="Input · Vid 1" trackId="vid1" timeline={timeline} media={media} cursorTime={cursorTime} accent="#5aa9ff" />
              <InputMonitor title="Input · Vid 2" trackId="vid2" timeline={timeline} media={media} cursorTime={cursorTime} accent="#7c9cff" />
              <OutputMonitor timeline={timeline} media={media} currentTime={currentTime} playing={playing} />
            </>
          ) : (
            <p className="col-span-3 text-xs text-[#7a869c]">Monitore werden geladen…</p>
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

          {/* Schnittpunkt am roten Cursor setzen und direkt auswählen */}
          <button
            type="button"
            onClick={() => { const id = addCutPoint(cursorTime); if (id) setSelectedCutId(id) }}
            disabled={!timeline || saving}
            title="Schnittpunkt am Cut-Cursor hinzufügen"
            className="ml-3 inline-flex items-center gap-1.5 rounded-[4px] border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-[11px] font-semibold text-rose-200 transition-colors hover:bg-rose-500/20 disabled:opacity-40"
          >
            <Scissors size={13} /> Schnittpunkt
          </button>
          <span className="font-mono text-[11px] text-rose-300">{timecode(cursorTime)}</span>
          {timeline && (timeline.cut_points?.length ?? 0) > 0 ? (
            <span className="text-[10px] uppercase tracking-[0.12em] text-[#68758a]">· {timeline.cut_points!.length} Schnitte</span>
          ) : null}

          <span className="ml-auto text-[10px] uppercase tracking-[0.12em] text-[#68758a]">
            {loading ? "Lade…" : saving ? "Speichere…" : "Gespeichert"}
          </span>
        </div>

        {error ? <p className="mt-2 text-xs text-rose-300">{error}</p> : null}

        {/* Spuren mit verschiebbaren Clips + roter Cut-Cursor + Playhead */}
        <div className="mt-3">
          {timeline ? (
            <TrackArea
              timeline={timeline}
              assets={assets}
              onRemoveClip={removeClip}
              currentTime={currentTime}
              onSeek={seek}
              cursorTime={cursorTime}
              onCursorChange={setCursorTime}
              onClipPreview={previewClipStart}
              onClipCommit={moveClip}
              onCutPreview={previewCutPoint}
              onCutCommit={moveCutPoint}
              onCutRemove={(id) => { removeCutPoint(id); if (id === selectedCutId) setSelectedCutId(null) }}
              selectedCutId={selectedCutId}
              onSelectCut={setSelectedCutId}
            />
          ) : (
            <p className="text-xs text-[#7a869c]">{loading ? "Timeline wird geladen…" : "Keine Timeline verfügbar."}</p>
          )}
        </div>

        {/* Inspector für den ausgewählten Schnittpunkt (Übergangseffekt + Dauer) */}
        {selectedCut ? (
          <CutPointInspector
            cut={selectedCut}
            onChange={(patch) => updateCutPoint(selectedCut.id, patch)}
            onRemove={() => { removeCutPoint(selectedCut.id); setSelectedCutId(null) }}
            onClose={() => setSelectedCutId(null)}
          />
        ) : null}
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
