import { Download, Play, Trash2 } from "lucide-react"
import { useState } from "react"
import type { MediaExportEntry } from "../../mediaWorkspaceApi"
import { MediaLightbox, type LightboxSource } from "./MediaLightbox"
import { timecode } from "./useCutPlayback"

interface Props {
  exports: MediaExportEntry[]
  downloadUrl: (path: string) => string
  onRemove: (name: string) => void
}

function fmtSize(bytes?: number): string {
  if (!bytes) return ""
  const mb = bytes / (1024 * 1024)
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}

function fmtWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  return d.toLocaleString(undefined, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
}

/** „Fertige Filme": persistente Liste der exportierten MP4s mit Download + Löschen. */
export function ExportLibrary({ exports, downloadUrl, onRemove }: Props) {
  const [preview, setPreview] = useState<LightboxSource | null>(null)
  return (
    <div className="mt-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-2">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-[#68758a]">Fertige Filme</p>
      {exports.length === 0 ? (
        <p className="text-[11px] text-[#7a869c]">Noch keine Exporte — oben „Film exportieren".</p>
      ) : (
        <ul className="space-y-1.5">
          {exports.map((exp) => (
            <li key={exp.name} className="flex items-center gap-2 rounded-[3px] border border-[#223048] bg-[#0d1420] p-1.5">
              <button
                type="button"
                onClick={() => setPreview({ url: downloadUrl(exp.path), kind: "video", label: exp.name })}
                title="Vorschau ansehen"
                className="group/thumb relative h-9 w-16 shrink-0 overflow-hidden rounded-[3px] border border-[#2a364b] bg-black"
              >
                <video src={downloadUrl(exp.path)} className="h-full w-full object-cover" preload="metadata" muted />
                <span className="absolute inset-0 grid place-items-center bg-black/25 transition-colors group-hover/thumb:bg-black/40">
                  <Play size={14} className="text-white drop-shadow" />
                </span>
              </button>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[11px] font-semibold text-[#c3ccdd]" title={exp.name}>{exp.name}</p>
                <p className="font-mono text-[9px] text-[#68758a]">
                  {exp.duration != null ? timecode(exp.duration) : "—"} · {fmtSize(exp.size)} · {fmtWhen(exp.created_at)}
                </p>
              </div>
              <a
                href={downloadUrl(exp.path)}
                download={exp.name}
                title="Herunterladen"
                className="grid h-6 w-6 shrink-0 place-items-center rounded-[3px] border border-cyan-400/40 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20"
              >
                <Download size={12} />
              </a>
              <button
                type="button"
                onClick={() => onRemove(exp.name)}
                title="Löschen"
                className="grid h-6 w-6 shrink-0 place-items-center rounded-[3px] border border-[#2a364b] text-[#8d9ab0] hover:border-rose-500/40 hover:text-rose-300"
              >
                <Trash2 size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <MediaLightbox source={preview} onClose={() => setPreview(null)} />
    </div>
  )
}
