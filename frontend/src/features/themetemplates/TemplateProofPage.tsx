import { useState } from "react"
import { Code2, Eye } from "lucide-react"
import { renderTemplate } from "./TemplateRenderer"
import { SAMPLE_TEMPLATE } from "./_sampleTemplate"
import { SLOT_BLOCKS } from "./registry"

/** Proof-Seite für das Template-System (Weg: Mittelweg).
 *  Zeigt: Designer-HTML mit <hh-…/>-Platzhaltern wird zu echtem UI, Bausteine
 *  werden eingesetzt, Fremd-Scripts werden verworfen. Bearbeitbares Textfeld,
 *  damit man live sieht wie ein Designer arbeiten würde. */
export function TemplateProofPage() {
  const [html, setHtml] = useState(SAMPLE_TEMPLATE.trim())
  const [showSource, setShowSource] = useState(true)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-white">Template-Proof</h1>
        <p className="text-zinc-500 text-sm mt-0.5">
          Freies HTML/CSS + <code className="text-zinc-400">&lt;hh-…/&gt;</code>-Platzhalter →
          echte Bausteine. Scripts werden entfernt.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 items-center text-xs text-zinc-400">
        <span className="text-zinc-500">Verfügbare Bausteine:</span>
        {SLOT_BLOCKS.map((b) => (
          <code key={b.name} className="px-1.5 py-0.5 rounded bg-white/[6%] text-[var(--hh-accent-text)]">
            &lt;hh-{b.name}/&gt;
          </code>
        ))}
        <button
          onClick={() => setShowSource((s) => !s)}
          className="ml-auto flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/[5%] transition-colors"
        >
          {showSource ? <Eye size={13} /> : <Code2 size={13} />}
          {showSource ? "Nur Vorschau" : "Quelltext zeigen"}
        </button>
      </div>

      <div className={`grid gap-4 ${showSource ? "lg:grid-cols-2" : "grid-cols-1"}`}>
        {showSource && (
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-1.5">
              <Code2 size={12} /> Designer-HTML (editierbar)
            </div>
            <textarea
              value={html}
              onChange={(e) => setHtml(e.target.value)}
              spellCheck={false}
              className="flex-1 min-h-[420px] p-3 rounded-xl bg-zinc-950/70 border border-white/[8%] font-mono text-[12px] leading-relaxed text-zinc-200 resize-none focus:outline-none focus:border-[var(--hh-accent-border)]"
            />
          </div>
        )}

        <div className="flex flex-col">
          <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-1.5">
            <Eye size={12} /> Live-Vorschau
          </div>
          <div className="flex-1 p-4 rounded-xl bg-[#0b0e16] border border-white/[8%] overflow-y-auto">
            {renderTemplate(html)}
          </div>
        </div>
      </div>
    </div>
  )
}
