/** Theme-Editor-Seite (Admin): visuell Theme-Vorlagen bauen.
 *
 *  Toolbar: Theme + Route wählen, Forken (geschützte Vorlage → editierbare
 *  Kopie), Speichern (Export → Editor-API), Veröffentlichen (Build+Restart).
 *  Darunter der GrapesJS-Canvas mit Baustein-Palette + Attribut-Panel.
 */
import { useState } from "react"
import { Blocks, Save, Upload, Copy } from "lucide-react"
import { Button, Select } from "@/shared/ui"
import { GrapesEditor } from "./GrapesEditor"
import { useThemeEditor } from "./useThemeEditor"

export function ThemeEditorPage() {
  const s = useThemeEditor()
  const [forkOpen, setForkOpen] = useState(false)

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-0 flex-col gap-3">
      <header className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Blocks className="text-teal-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">Theme-Editor</h1>
        </div>

        <Select
          className="ml-auto w-44"
          value={s.themeId}
          onChange={(e) => s.setThemeId(e.target.value)}
        >
          {s.themes.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}{t.protected ? " (Vorlage)" : ""}
            </option>
          ))}
        </Select>

        <Select
          className="w-40"
          value={s.route}
          onChange={(e) => s.setRoute(e.target.value)}
          disabled={!s.routes.length}
        >
          {s.routes.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </Select>

        <Button variant="ghost" onClick={() => setForkOpen(true)} title="Als editierbare Kopie forken">
          <Copy size={15} /> Kopie
        </Button>
        <Button
          onClick={s.save}
          disabled={s.busy || s.isProtected || !s.route}
          title={s.isProtected ? "Vorlage ist schreibgeschützt — erst forken" : "Speichern"}
        >
          <Save size={15} /> Speichern
        </Button>
        <Button
          variant="ghost"
          onClick={s.publish}
          disabled={s.busy || s.isProtected}
          title="Ins laufende Frontend übernehmen (Build + Neustart)"
        >
          <Upload size={15} /> Veröffentlichen
        </Button>
      </header>

      {s.isProtected && (
        <p className="rounded-lg bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300">
          Dies ist eine geschützte Vorlage. Zum Bearbeiten oben „Kopie" anlegen.
        </p>
      )}
      {s.status && (
        <p className="rounded-lg bg-white/5 px-3 py-1.5 text-xs text-zinc-300">{s.status}</p>
      )}

      <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-white/10">
        {s.route ? (
          <GrapesEditor
            key={`${s.themeId}:${s.route}:${s.html.length}`}
            initialHtml={s.html}
            onReady={s.setEditor}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-zinc-500">
            Kein Template gewählt.
          </div>
        )}
      </div>

      {forkOpen && (
        <ForkDialog
          onClose={() => setForkOpen(false)}
          onFork={(id, name) => { s.fork(id, name); setForkOpen(false) }}
        />
      )}
    </div>
  )
}

function ForkDialog({ onClose, onFork }: { onClose: () => void; onFork: (id: string, name: string) => void }) {
  const [name, setName] = useState("")
  const id = name.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-+|-+$/g, "")
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="w-80 rounded-xl border border-white/10 bg-zinc-900 p-4" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-2 text-sm font-semibold text-zinc-100">Als Kopie forken</h2>
        <p className="mb-3 text-xs text-zinc-400">
          Legt ein neues, editierbares Theme aus der aktuellen Vorlage an.
        </p>
        <input
          autoFocus
          className="mb-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-zinc-100"
          placeholder="Name des neuen Themes"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <p className="mb-3 text-[11px] text-zinc-500">ID: {id || "—"}</p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Abbrechen</Button>
          <Button onClick={() => id && onFork(id, name)} disabled={!id}>Forken</Button>
        </div>
      </div>
    </div>
  )
}
