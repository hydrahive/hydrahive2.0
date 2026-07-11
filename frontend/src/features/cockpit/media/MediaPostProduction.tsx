import { Film, Mic, Music, Pause, Play, Plus, SkipBack, SkipForward, Sparkles, Square, Video } from "lucide-react"
import type { ComponentType } from "react"

/** Dummy-Nachbearbeitung: 3 virtuelle Monitore (2× Input, 1× Output) + Mehrspur-Leiste.
 *  Reine Platzhalter-UI, keine Funktion — dient als Gerüst für den stückweisen Ausbau. */

interface TrackDef {
  id: string
  label: string
  icon: ComponentType<{ size?: number | string; className?: string }>
  tone: string // Rand-/Akzentfarbe der Spur
}

const TRACKS: TrackDef[] = [
  { id: "vid1", label: "Video 1", icon: Video, tone: "#5aa9ff" },
  { id: "vid2", label: "Video 2", icon: Video, tone: "#7c9cff" },
  { id: "music", label: "Musik", icon: Music, tone: "#4ade80" },
  { id: "fx", label: "Effekt", icon: Sparkles, tone: "#c084fc" },
  { id: "voice", label: "Sprache", icon: Mic, tone: "#ffb86b" },
]

function Monitor({ title, kind }: { title: string; kind: "input" | "output" }) {
  const accent = kind === "output" ? "#ffb86b" : "#5aa9ff"
  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em]" style={{ color: accent }}>{title}</span>
        <span className="font-mono text-[10px] text-[#68758a]">00:00:00</span>
      </div>
      <div className="relative aspect-video overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        {/* Platzhalter-Raster */}
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
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled
      className={["grid h-8 w-8 place-items-center rounded-[4px] border transition-colors",
        primary ? "border-[#ffb86b]/50 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-[#2a364b] bg-[#111827] text-[#8d9ab0]"].join(" ")}
    >
      <Icon size={15} />
    </button>
  )
}

export function MediaPostProduction() {
  return (
    <div>
      <div className="mb-3 flex justify-end">
        <span className="rounded-[3px] border border-[#2a364b] bg-[#111827] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-[#68758a]">Dummy · in Arbeit</span>
      </div>

      <div>
        {/* 3 Monitore: Input 1, Input 2, Output */}
        <div className="grid gap-3 lg:grid-cols-3">
          <Monitor title="Input · Vid 1" kind="input" />
          <Monitor title="Input · Vid 2" kind="input" />
          <Monitor title="Output" kind="output" />
        </div>

        {/* Transport + Dropdown */}
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#2a364b] pt-3">
          <TransportButton icon={SkipBack} label="Zum Anfang" />
          <TransportButton icon={Play} label="Abspielen" primary />
          <TransportButton icon={Pause} label="Pause" />
          <TransportButton icon={Square} label="Stopp" />
          <TransportButton icon={SkipForward} label="Zum Ende" />
          <span className="ml-1 font-mono text-[11px] text-[#8d9ab0]">00:00:00 / 00:00:00</span>

          <div className="ml-auto flex items-center gap-2">
            <label className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#68758a]">Auflösung</label>
            <select disabled className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-xs text-[#e8eef8]">
              <option>1080p · 25 fps</option>
              <option>720p · 25 fps</option>
              <option>4K · 25 fps</option>
            </select>
            <button type="button" disabled className="inline-flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#111827] px-2.5 py-1.5 text-xs font-semibold text-[#8d9ab0]">
              <Plus size={13} /> Clip
            </button>
          </div>
        </div>

        {/* Zeitleiste (Ruler) */}
        <div className="mt-3 grid grid-cols-[84px_1fr] gap-2">
          <div />
          <div className="flex justify-between rounded-[3px] border border-[#2a364b] bg-[#111827] px-2 py-1 font-mono text-[9px] text-[#68758a]">
            {["0s", "5s", "10s", "15s", "20s", "25s", "30s"].map((t) => <span key={t}>{t}</span>)}
          </div>
        </div>

        {/* Spuren: vid1, vid2, musik, effekt, sprache */}
        <div className="mt-2 space-y-1.5">
          {TRACKS.map((track) => {
            const Icon = track.icon
            return (
              <div key={track.id} className="grid grid-cols-[84px_1fr] gap-2">
                <div className="flex items-center gap-1.5 rounded-[3px] border border-[#2a364b] bg-[#111827] px-2 py-1.5" style={{ borderLeft: `3px solid ${track.tone}` }}>
                  <Icon size={13} className="shrink-0" />
                  <span className="truncate text-[11px] font-semibold text-[#c3ccdd]">{track.label}</span>
                </div>
                <div className="relative h-9 overflow-hidden rounded-[3px] border border-[#223048] bg-[#0d1420]">
                  <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: "48px 100%" }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
