import { Film, Pause, Play, SkipBack, SkipForward, Square } from "lucide-react"
import type { ComponentType } from "react"
import { ClipLibrary } from "./videocut/ClipLibrary"
import { TrackArea } from "./videocut/TrackArea"
import { useCutTimeline } from "./videocut/useCutTimeline"

/** Videoschnitt (V1): Clip-Bibliothek + Spuren mit Persistenz.
 *  Monitore + Transport sind noch Platzhalter (V2). */

function Monitor({ title, kind }: { title: string; kind: "input" | "output" }) {
  const accent = kind === "output" ? "#ffb86b" : "#5aa9ff"
  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em]" style={{ color: accent }}>{title}</span>
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

function TransportButton({ icon: Icon, label, primary }: { icon: ComponentType<{ size?: number | string }>; label: string; primary?: boolean }) {
  return (
    <button type="button" title={label} aria-label={label} disabled
      className={["grid h-8 w-8 place-items-center rounded-[4px] border transition-colors",
        primary ? "border-[#ffb86b]/50 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-[#2a364b] bg-[#111827] text-[#8d9ab0]"].join(" ")}>
      <Icon size={15} />
    </button>
  )
}

interface Props {
  projectId: string
}

export function MediaPostProduction({ projectId }: Props) {
  const { timeline, assets, loading, saving, error, addClip, removeClip } = useCutTimeline(projectId)

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_260px]">
      <div className="min-w-0">
        {/* 3 Monitore: Input 1, Input 2, Output */}
        <div className="grid gap-3 lg:grid-cols-3">
          <Monitor title="Input · Vid 1" kind="input" />
          <Monitor title="Input · Vid 2" kind="input" />
          <Monitor title="Output" kind="output" />
        </div>

        {/* Transport (V2) + Status */}
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#2a364b] pt-3">
          <TransportButton icon={SkipBack} label="Zum Anfang" />
          <TransportButton icon={Play} label="Abspielen" primary />
          <TransportButton icon={Pause} label="Pause" />
          <TransportButton icon={Square} label="Stopp" />
          <TransportButton icon={SkipForward} label="Zum Ende" />
          <span className="ml-1 font-mono text-[11px] text-[#8d9ab0]">00:00:00 / 00:00:00</span>
          <span className="ml-auto text-[10px] uppercase tracking-[0.12em] text-[#68758a]">
            {loading ? "Lade…" : saving ? "Speichere…" : "Gespeichert"}
          </span>
        </div>

        {error ? <p className="mt-2 text-xs text-rose-300">{error}</p> : null}

        {/* Spuren mit echten Clips */}
        <div className="mt-3">
          {timeline ? (
            <TrackArea timeline={timeline} assets={assets} onRemoveClip={removeClip} />
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
    </div>
  )
}
