import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { HardDrive, Loader2, Plus, Save, Trash2, X } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import type { DiskInterface, HostDisk, ISO, MachineType, NetworkDevice, PassthroughDisk, VM } from "./types"
import { vmsApi } from "./api"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Props {
  vm: VM
  onClose: () => void
  onSaved: () => void
}

export function EditVMDialog({ vm, onClose, onSaved }: Props) {
  const { t } = useTranslation("vms")
  const editable = vm.actual_state === "stopped" || vm.actual_state === "created" || vm.actual_state === "error"

  const [name, setName] = useState(vm.name)
  const [description, setDescription] = useState(vm.description ?? "")
  const [cpu, setCpu] = useState(vm.cpu)
  const [ramMb, setRamMb] = useState(vm.ram_mb)
  const [diskGb, setDiskGb] = useState(vm.disk_gb)
  const [iso, setIso] = useState<string>(vm.iso_filename ?? "")
  const [diskInterface, setDiskInterface] = useState<DiskInterface>(vm.disk_interface)
  const [machineType, setMachineType] = useState<MachineType>(vm.machine_type)
  const [networkDevice, setNetworkDevice] = useState<NetworkDevice>(vm.network_device)
  const [isos, setIsos] = useState<ISO[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const [passthroughDisks, setPassthroughDisks] = useState<PassthroughDisk[]>([])
  const [hostDisks, setHostDisks] = useState<HostDisk[]>([])
  const [attachedPaths, setAttachedPaths] = useState<string[]>([])
  const [selectedHostDisk, setSelectedHostDisk] = useState("")
  const [ptBusy, setPtBusy] = useState(false)
  const [ptError, setPtError] = useState<string | null>(null)

  useEffect(() => {
    vmsApi.isos().then(setIsos).catch(() => setIsos([]))
    if (isAdmin) {
      vmsApi.listPassthroughDisks(vm.vm_id).then(setPassthroughDisks).catch(() => {})
      vmsApi.hostDisks().then((r) => { setHostDisks(r.disks); setAttachedPaths(r.attached_paths) }).catch(() => {})
    }
  }, [])

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,31}$/.test(name)
  const dirty =
    name !== vm.name ||
    description !== (vm.description ?? "") ||
    cpu !== vm.cpu ||
    ramMb !== vm.ram_mb ||
    diskGb !== vm.disk_gb ||
    iso !== (vm.iso_filename ?? "") ||
    diskInterface !== vm.disk_interface ||
    machineType !== vm.machine_type ||
    networkDevice !== vm.network_device

  async function submit() {
    if (!validName) { setError(t("edit.error_name_invalid")); return }
    if (diskGb < vm.disk_gb) {
      setError(`Disk-Verkleinerung nicht unterstützt (aktuell ${vm.disk_gb} GB).`)
      return
    }
    setBusy(true); setError(null)
    try {
      const patch: Parameters<typeof vmsApi.update>[1] = {}
      if (name !== vm.name) patch.name = name
      if (description !== (vm.description ?? "")) patch.description = description.trim() || null
      if (cpu !== vm.cpu) patch.cpu = cpu
      if (ramMb !== vm.ram_mb) patch.ram_mb = ramMb
      if (diskGb !== vm.disk_gb) patch.disk_gb = diskGb
      if (iso !== (vm.iso_filename ?? "")) {
        if (iso === "") patch.clear_iso = true
        else patch.iso_filename = iso
      }
      if (diskInterface !== vm.disk_interface) patch.disk_interface = diskInterface
      if (machineType !== vm.machine_type) patch.machine_type = machineType
      if (networkDevice !== vm.network_device) patch.network_device = networkDevice
      await vmsApi.update(vm.vm_id, patch)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : t("edit.error"))
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="box overflow-hidden w-full max-w-lg p-5 space-y-3" style={{ "--c": rgbFor("/vms") } as CSSProperties}>
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
          <Field label={t("edit.field_name")}>
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
          </Field>
          <Field label={t("edit.field_desc")}>
            <input value={description} onChange={(e) => setDescription(e.target.value)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label={t("edit.field_cpu")}>
              <input type="number" min={1} max={64} value={cpu}
                onChange={(e) => setCpu(parseInt(e.target.value) || 1)} disabled={!editable}
                className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
            </Field>
            <Field label={t("edit.field_ram")}>
              <input type="number" min={128} max={131072} step={128} value={ramMb}
                onChange={(e) => setRamMb(parseInt(e.target.value) || 128)} disabled={!editable}
                className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
            </Field>
          </div>
          <Field label={`Disk (GB) — nur vergrößern, aktuell ${vm.disk_gb} GB`}>
            <input type="number" min={vm.disk_gb} max={4096} step={1} value={diskGb}
              onChange={(e) => setDiskGb(parseInt(e.target.value) || vm.disk_gb)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50" />
            <p className="text-[10px] text-zinc-600 mt-0.5">
              Erweitert nur die qcow2-Disk. Im Gast danach Filesystem ausbauen
              (<code className="font-mono">growpart /dev/sda 1 && resize2fs /dev/sda1</code>).
            </p>
          </Field>
          <Field label={t("edit.field_boot_iso")}>
            <select value={iso} onChange={(e) => setIso(e.target.value)} disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50">
              <option value="">— keine ISO —</option>
              {isos.map((i) => <option key={i.filename} value={i.filename}>{i.filename}</option>)}
              {iso && !isos.find((i) => i.filename === iso) && (
                <option value={iso}>{iso} (nicht in Library)</option>
              )}
            </select>
          </Field>
          <Field label={t("edit.field_disk_interface")}>
            <select value={diskInterface}
              onChange={(e) => setDiskInterface(e.target.value as DiskInterface)}
              disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50">
              <option value="virtio">{t("edit.disk_virtio_label")}</option>
              <option value="sata">{t("edit.disk_sata_label")}</option>
              <option value="ide">{t("edit.disk_ide_label")}</option>
            </select>
            <p className="text-[10px] text-zinc-600 mt-0.5">
              Bei Boot-Problemen mit importierten qcow2 (HH1/VirtualBox/etc.) auf <code className="font-mono">sata</code> umstellen — VM stoppen, hier ändern, wieder starten.
            </p>
          </Field>
          <Field label={t("edit.field_machine_type")}>
            <select value={machineType}
              onChange={(e) => setMachineType(e.target.value as MachineType)}
              disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50">
              <option value="q35">q35 (modern, ICH9, Default)</option>
              <option value="pc">pc (i440FX — FreeBSD/Windows-XP/VBox-Imports)</option>
            </select>
            <p className="text-[10px] text-zinc-600 mt-0.5">
              Bei <code className="font-mono">cannot read MOS</code> (FreeBSD-ZFS) oder Boot-Hängern alter Gäste auf <code className="font-mono">pc</code> umstellen.
            </p>
          </Field>
          <Field label={t("edit.field_network_device")}>
            <select value={networkDevice}
              onChange={(e) => setNetworkDevice(e.target.value as NetworkDevice)}
              disabled={!editable}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50">
              <option value="virtio-net-pci">virtio-net-pci (schnell, Default)</option>
              <option value="e1000">e1000 (Intel-NIC, in jedem Gast-OS)</option>
            </select>
            <p className="text-[10px] text-zinc-600 mt-0.5">
              Wenn die VM kein Netz hat (kein DHCP-IP, kein Ping), <code className="font-mono">e1000</code> versuchen — fast jedes OS hat den Treiber drin.
            </p>
          </Field>
        </div>

        {isAdmin && (
          <PassthroughSection
            vm={vm}
            editable={editable}
            disks={passthroughDisks}
            hostDisks={hostDisks}
            attachedPaths={attachedPaths}
            selected={selectedHostDisk}
            onSelect={setSelectedHostDisk}
            busy={ptBusy}
            error={ptError}
            onAdd={async () => {
              if (!selectedHostDisk) return
              setPtBusy(true); setPtError(null)
              try {
                const disk = hostDisks.find((d) => d.path === selectedHostDisk)
                const label = disk ? `${disk.model ?? disk.name} (${disk.size})` : undefined
                const added = await vmsApi.addPassthroughDisk(vm.vm_id, selectedHostDisk, label ?? undefined)
                setPassthroughDisks((prev) => [...prev, added])
                setAttachedPaths((prev) => [...prev, selectedHostDisk])
                setSelectedHostDisk("")
              } catch (e) {
                setPtError(e instanceof Error ? e.message : "Fehler")
              } finally { setPtBusy(false) }
            }}
            onRemove={async (id) => {
              setPtBusy(true); setPtError(null)
              try {
                await vmsApi.removePassthroughDisk(vm.vm_id, id)
                setPassthroughDisks((prev) => prev.filter((d) => d.passthrough_id !== id))
                const removed = passthroughDisks.find((d) => d.passthrough_id === id)
                if (removed) setAttachedPaths((prev) => prev.filter((p) => p !== removed.device_path))
              } catch (e) {
                setPtError(e instanceof Error ? e.message : "Fehler")
              } finally { setPtBusy(false) }
            }}
          />
        )}

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

interface PassthroughSectionProps {
  vm: VM
  editable: boolean
  disks: PassthroughDisk[]
  hostDisks: HostDisk[]
  attachedPaths: string[]
  selected: string
  onSelect: (path: string) => void
  busy: boolean
  error: string | null
  onAdd: () => void
  onRemove: (id: string) => void
}

function PassthroughSection({
  vm, editable, disks, hostDisks, attachedPaths, selected, onSelect,
  busy, error, onAdd, onRemove,
}: PassthroughSectionProps) {
  const availableDisks = hostDisks.filter(
    (d) => !attachedPaths.includes(d.path) || disks.some((pd) => pd.device_path === d.path && pd.vm_id === vm.vm_id)
  )

  return (
    <div className="border-t border-white/[5%] pt-3 space-y-2">
      <div className="flex items-center gap-1.5 text-[10px] font-medium text-zinc-400">
        <HardDrive size={11} />
        <span>Passthrough-Disks</span>
        <span className="text-zinc-600 font-normal">(physische Block-Devices direkt in VM)</span>
      </div>

      {disks.length > 0 && (
        <div className="space-y-1">
          {disks.map((d) => (
            <div key={d.passthrough_id}
              className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-zinc-950 border border-white/[6%]">
              <div className="flex items-center gap-2 min-w-0">
                <HardDrive size={11} className="text-indigo-400 shrink-0" />
                <span className="text-xs text-zinc-200 font-mono truncate">{d.device_path}</span>
                {d.label && <span className="text-[10px] text-zinc-500 truncate">{d.label}</span>}
              </div>
              <button
                onClick={() => onRemove(d.passthrough_id)}
                disabled={busy || !editable}
                className="p-1 rounded text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30 shrink-0">
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      )}

      {editable && (
        <div className="flex gap-1.5">
          <select
            value={selected}
            onChange={(e) => onSelect(e.target.value)}
            disabled={busy || availableDisks.length === 0}
            className="flex-1 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 disabled:opacity-50">
            <option value="">
              {availableDisks.length === 0 ? "— keine freien Disks —" : "— Disk wählen —"}
            </option>
            {availableDisks.map((d) => (
              <option key={d.path} value={d.path}>
                {d.path} — {d.model ?? d.name} ({d.size})
              </option>
            ))}
          </select>
          <button
            onClick={onAdd}
            disabled={busy || !selected}
            className="flex items-center gap-1 px-3 py-1 rounded-md bg-indigo-600/80 hover:bg-indigo-500/80 text-white text-xs disabled:opacity-30">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />}
            Hinzufügen
          </button>
        </div>
      )}

      {!editable && disks.length === 0 && (
        <p className="text-[10px] text-zinc-600">Keine Passthrough-Disks. VM stoppen zum Bearbeiten.</p>
      )}

      {error && (
        <p className="text-[10px] text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded px-2 py-1">{error}</p>
      )}

      <p className="text-[10px] text-zinc-600">
        Nur unmountete Disks. VM muss gestoppt sein. Änderungen werden beim nächsten Start der VM aktiv.
      </p>
    </div>
  )
}
