import { useState } from "react"
import { Loader2, Save, X } from "lucide-react"
import type { Container } from "./types"
import { containersApi } from "./api"

interface Props {
  container: Container
  onClose: () => void
  onSaved: () => void
}

export function EditContainerDialog({ container, onClose, onSaved }: Props) {
  const editable = container.actual_state === "stopped" || container.actual_state === "created" || container.actual_state === "error"

  const [name, setName] = useState(container.name)
  const [description, setDescription] = useState(container.description ?? "")
  const [cpuSet, setCpuSet] = useState(container.cpu !== null && container.cpu !== undefined)
  const [cpu, setCpu] = useState(container.cpu ?? 2)
  const [ramSet, setRamSet] = useState(container.ram_mb !== null && container.ram_mb !== undefined)
  const [ramMb, setRamMb] = useState(container.ram_mb ?? 1024)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,62}$/.test(name)
  const origCpuSet = container.cpu !== null && container.cpu !== undefined
  const origRamSet = container.ram_mb !== null && container.ram_mb !== undefined
  const dirty =
    name !== container.name ||
    description !== (container.description ?? "") ||
    cpuSet !== origCpuSet || (cpuSet && cpu !== container.cpu) ||
    ramSet !== origRamSet || (ramSet && ramMb !== container.ram_mb)

  async function submit() {
    if (!validName) { setError("Name: 1-63 Zeichen, beginnt mit Buchstabe, nur a-z A-Z 0-9 -"); return }
    setBusy(true); setError(null)
    try {
      const patch: Parameters<typeof containersApi.update>[1] = {}
      if (name !== container.name) patch.name = name
      if (description !== (container.description ?? "")) patch.description = description.trim() || null
      if (cpuSet !== origCpuSet) {
        if (cpuSet) patch.cpu = cpu
        else patch.clear_cpu = true
      } else if (cpuSet && cpu !== container.cpu) {
        patch.cpu = cpu
      }
      if (ramSet !== origRamSet) {
        if (ramSet) patch.ram_mb = ramMb
        else patch.clear_ram = true
      } else if (ramSet && ramMb !== container.ram_mb) {
        patch.ram_mb = ramMb
      }
      await containersApi.update(container.container_id, patch)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border border-white/[8%] bg-zinc-900 p-5 shadow-2xl shadow-black/40 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Container bearbeiten: {container.name}</h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        {!editable && (
          <p className="text-xs text-amber-300 bg-amber-500/[8%] border border-amber-500/25 rounded-md px-3 py-2">
            Container muss gestoppt sein zum Bearbeiten. Aktuell: <strong>{container.actual_state}</strong>
          </p>
        )}

        <div className="space-y-2">
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
          </Field>
          <Field label="Beschreibung">
            <input value={description} onChange={(e) => setDescription(e.target.value)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
          </Field>
          <Field label="Image (read-only — Re-Create für anderes Image)">
            <input value={container.image} disabled
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-500 font-mono cursor-not-allowed" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="CPU-Kerne">
              <div className="flex items-center gap-1.5">
                <input type="checkbox" checked={cpuSet} onChange={(e) => setCpuSet(e.target.checked)} disabled={!editable}
                  className="accent-violet-500" />
                <input type="number" min={1} max={64} value={cpu} disabled={!editable || !cpuSet}
                  onChange={(e) => setCpu(parseInt(e.target.value) || 1)}
                  className="flex-1 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-30" />
              </div>
              <p className="text-[10px] text-zinc-600 mt-0.5">{cpuSet ? "" : "unbegrenzt"}</p>
            </Field>
            <Field label="RAM (MB)">
              <div className="flex items-center gap-1.5">
                <input type="checkbox" checked={ramSet} onChange={(e) => setRamSet(e.target.checked)} disabled={!editable}
                  className="accent-violet-500" />
                <input type="number" min={64} max={32768} step={64} value={ramMb} disabled={!editable || !ramSet}
                  onChange={(e) => setRamMb(parseInt(e.target.value) || 64)}
                  className="flex-1 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-30" />
              </div>
              <p className="text-[10px] text-zinc-600 mt-0.5">{ramSet ? "" : "unbegrenzt"}</p>
            </Field>
          </div>
        </div>

        {error && (
          <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            Abbrechen
          </button>
          <button onClick={submit} disabled={!editable || !dirty || busy}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            Speichern
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
    </div>
  )
}
