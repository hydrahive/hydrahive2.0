import { useEffect, useState } from "react"
import { X } from "lucide-react"
import type { ImportJob, ISO, NetworkMode, VMCreateInput } from "./types"
import { vmsApi } from "./api"
import { formatBytes } from "./format"

interface Props {
  onClose: () => void
  onCreated: () => void
}

type BootSource = "iso" | "import" | "blank"

export function CreateVMDialog({ onClose, onCreated }: Props) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [cpu, setCpu] = useState(2)
  const [ramMb, setRamMb] = useState(2048)
  const [diskGb, setDiskGb] = useState(20)
  const [bootSrc, setBootSrc] = useState<BootSource>("iso")
  const [iso, setIso] = useState<string>("")
  const [importJobId, setImportJobId] = useState<string>("")
  const [network, setNetwork] = useState<NetworkMode>("bridged")
  const [isos, setIsos] = useState<ISO[]>([])
  const [imports, setImports] = useState<ImportJob[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    vmsApi.isos().then(setIsos).catch(() => setIsos([]))
    vmsApi.importJobs().then((j) => setImports(j.filter((x) => x.status === "done"))).catch(() => setImports([]))
  }, [])

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,31}$/.test(name)

  async function submit() {
    if (!validName) { setError("Name: 1–32 Zeichen, beginnt mit Buchstabe, nur a-z A-Z 0-9 -"); return }
    if (bootSrc === "import" && !importJobId) { setError("Bitte einen Import-Job auswählen"); return }
    setBusy(true); setError(null)
    try {
      const input: VMCreateInput & { import_job_id?: string } = {
        name,
        description: description.trim() || null,
        cpu, ram_mb: ramMb, disk_gb: diskGb,
        iso_filename: bootSrc === "iso" && iso ? iso : null,
        network_mode: network,
      }
      if (bootSrc === "import") (input as any).import_job_id = importJobId
      await vmsApi.create(input)
      onCreated()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-2xl mx-4 rounded-2xl border border-white/[8%] bg-zinc-900 shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
          <h2 className="text-lg font-bold text-white">Neue VM erstellen</h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5"><X size={16} /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4 space-y-5">
          <Field label="Name" hint="1–32 Zeichen, beginnt mit Buchstabe, nur a-z A-Z 0-9 -">
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="z.B. metin2-prod"
              className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
          </Field>
          <Field label="Beschreibung (optional)">
            <input value={description} onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
          </Field>

          <Field label="Boot-Quelle">
            <div className="grid grid-cols-3 gap-2">
              <RadioCard active={bootSrc === "iso"} onClick={() => setBootSrc("iso")}
                title="Aus ISO booten" desc="Neue Disk + ISO als Boot-Medium" />
              <RadioCard active={bootSrc === "import"} onClick={() => setBootSrc("import")}
                title="Importierte Disk" desc="qcow2 aus Import-Job übernehmen" />
              <RadioCard active={bootSrc === "blank"} onClick={() => setBootSrc("blank")}
                title="Leere Disk" desc="Boot-loop bis Setup nachgereicht wird" />
            </div>
          </Field>

          {bootSrc === "iso" && (
            <Field label="ISO auswählen">
              <select value={iso} onChange={(e) => setIso(e.target.value)}
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none">
                <option value="">— Keine —</option>
                {isos.map((i) => (
                  <option key={i.filename} value={i.filename}>{i.filename} ({formatBytes(i.size_bytes)})</option>
                ))}
              </select>
              {isos.length === 0 && <p className="text-[11px] text-zinc-500 mt-1">Keine ISOs vorhanden — erst hochladen.</p>}
            </Field>
          )}

          {bootSrc === "import" && (
            <Field label="Import-Job auswählen" hint="qcow2 wird in die VM verschoben, der Job verschwindet danach.">
              <select value={importJobId} onChange={(e) => setImportJobId(e.target.value)}
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none">
                <option value="">— Auswählen —</option>
                {imports.map((j) => {
                  const src = j.source_path.split("/").pop() ?? j.source_path
                  return <option key={j.job_id} value={j.job_id}>{src} ({formatBytes(j.bytes_total)})</option>
                })}
              </select>
              {imports.length === 0 && <p className="text-[11px] text-zinc-500 mt-1">Keine fertigen Import-Jobs — erst Disk-Image hochladen oder importieren.</p>}
            </Field>
          )}

          <div className="grid grid-cols-3 gap-3">
            <Slider label="vCPU" value={cpu} min={1} max={16} step={1} onChange={setCpu} suffix={`${cpu}`} />
            <Slider label="RAM" value={ramMb} min={512} max={32768} step={512} onChange={setRamMb} suffix={`${(ramMb / 1024).toFixed(1)} GB`} />
            <Slider label="Disk" value={diskGb} min={5} max={500} step={5} onChange={setDiskGb} suffix={`${diskGb} GB`}
              disabled={bootSrc === "import"} />
          </div>
          {bootSrc === "import" && <p className="text-[11px] text-zinc-500 -mt-3">Disk-Größe kommt aus der importierten Datei.</p>}

          <Field label="Netzwerk">
            <div className="grid grid-cols-2 gap-2">
              <RadioCard active={network === "bridged"} onClick={() => setNetwork("bridged")}
                title="Bridged (br0)" desc="VM bekommt DHCP-IP aus dem LAN" />
              <RadioCard active={network === "isolated"} onClick={() => setNetwork("isolated")}
                title="Isoliert" desc="Kein Netzwerk-Zugang" />
            </div>
          </Field>

          {error && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">{error}</div>}
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-white/[6%]">
          <button onClick={onClose} disabled={busy} className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">Abbrechen</button>
          <button onClick={submit} disabled={busy || !validName}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40">
            {busy ? "Erstelle…" : "VM erstellen"}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-zinc-300">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-zinc-500">{hint}</p>}
    </div>
  )
}

function Slider({ label, value, min, max, step, onChange, suffix, disabled }: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (n: number) => void; suffix: string; disabled?: boolean
}) {
  return (
    <div className={disabled ? "opacity-40 pointer-events-none" : ""}>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-zinc-300 font-medium">{label}</span>
        <span className="text-violet-300 font-mono">{suffix}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="w-full mt-1 accent-violet-500" />
    </div>
  )
}

function RadioCard({ active, onClick, title, desc }: { active: boolean; onClick: () => void; title: string; desc: string }) {
  return (
    <button type="button" onClick={onClick}
      className={`text-left p-3 rounded-lg border transition-colors ${active ? "bg-violet-500/15 border-violet-500/40" : "bg-white/[2%] border-white/[8%] hover:border-white/[15%]"}`}>
      <p className="text-sm font-medium text-zinc-100">{title}</p>
      <p className="text-[11px] text-zinc-500 mt-0.5">{desc}</p>
    </button>
  )
}
