import { useEffect, useState } from "react"
import { Loader2, Save, X } from "lucide-react"
import type { ISO, VM } from "./types"
import { vmsApi } from "./api"

interface Props {
  vm: VM
  onClose: () => void
  onSaved: () => void
}

export function EditVMDialog({ vm, onClose, onSaved }: Props) {
  const editable = vm.actual_state === "stopped" || vm.actual_state === "created" || vm.actual_state === "error"

  const [name, setName] = useState(vm.name)
  const [description, setDescription] = useState(vm.description ?? "")
  const [cpu, setCpu] = useState(vm.cpu)
  const [ramMb, setRamMb] = useState(vm.ram_mb)
  const [iso, setIso] = useState<string>(vm.iso_filename ?? "")
  const [isos, setIsos] = useState<ISO[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    vmsApi.isos().then(setIsos).catch(() => setIsos([]))
  }, [])

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,31}$/.test(name)
  const dirty =
    name !== vm.name ||
    description !== (vm.description ?? "") ||
    cpu !== vm.cpu ||
    ramMb !== vm.ram_mb ||
    iso !== (vm.iso_filename ?? "")

  async function submit() {
    if (!validName) { setError("Name: 1-32 Zeichen, beginnt mit Buchstabe, nur a-z A-Z 0-9 -"); return }
    setBusy(true); setError(null)
    try {
      const patch: Parameters<typeof vmsApi.update>[1] = {}
      if (name !== vm.name) patch.name = name
      if (description !== (vm.description ?? "")) patch.description = description.trim() || null
      if (cpu !== vm.cpu) patch.cpu = cpu
      if (ramMb !== vm.ram_mb) patch.ram_mb = ramMb
      if (iso !== (vm.iso_filename ?? "")) {
        if (iso === "") patch.clear_iso = true
        else patch.iso_filename = iso
      }
      await vmsApi.update(vm.vm_id, patch)
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
          <h2 className="text-lg font-bold text-white">VM bearbeiten: {vm.name}</h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        {!editable && (
          <p className="text-xs text-amber-300 bg-amber-500/[8%] border border-amber-500/25 rounded-md px-3 py-2">
            VM muss gestoppt sein zum Bearbeiten. Aktuell: <strong>{vm.actual_state}</strong>
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
          <div className="grid grid-cols-2 gap-2">
            <Field label="CPU-Kerne">
              <input type="number" min={1} max={64} value={cpu}
                onChange={(e) => setCpu(parseInt(e.target.value) || 1)} disabled={!editable}
                className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
            </Field>
            <Field label="RAM (MB)">
              <input type="number" min={128} max={131072} step={128} value={ramMb}
                onChange={(e) => setRamMb(parseInt(e.target.value) || 128)} disabled={!editable}
                className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
            </Field>
          </div>
          <Field label="Boot-ISO (leer = keine ISO eingelegt)">
            <select value={iso} onChange={(e) => setIso(e.target.value)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50">
              <option value="">— keine ISO —</option>
              {isos.map((i) => <option key={i.filename} value={i.filename}>{i.filename}</option>)}
              {iso && !isos.find((i) => i.filename === iso) && (
                <option value={iso}>{iso} (nicht in Library)</option>
              )}
            </select>
          </Field>
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
