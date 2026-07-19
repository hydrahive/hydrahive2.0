import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { X } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { nodesApi } from "@/features/nodes/api"
import { isPlaceableStatus } from "@/features/nodes/NodeStatusBadge"
import type { ComputeNode } from "@/features/nodes/types"
import type { DiskInterface, ImportJob, ISO, MachineType, NetworkDevice, NetworkMode, VMCreateInput } from "./types"
import { vmsApi } from "./api"
import { formatBytes } from "./format"
import { Field, Slider, RadioCard } from "./_vmDialogHelpers"

interface Props {
  onClose: () => void
  onCreated: () => void
}

type BootSource = "iso" | "import" | "blank"

export function CreateVMDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("vms")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [cpu, setCpu] = useState(2)
  const [ramMb, setRamMb] = useState(2048)
  const [diskGb, setDiskGb] = useState(20)
  const [bootSrc, setBootSrc] = useState<BootSource>("iso")
  const [iso, setIso] = useState<string>("")
  const [importJobId, setImportJobId] = useState<string>("")
  const [network, setNetwork] = useState<NetworkMode>("bridged")
  const [diskInterface, setDiskInterface] = useState<DiskInterface>("virtio")
  const [machineType, setMachineType] = useState<MachineType>("q35")
  const [networkDevice, setNetworkDevice] = useState<NetworkDevice>("virtio-net-pci")
  const [isos, setIsos] = useState<ISO[]>([])
  const [imports, setImports] = useState<ImportJob[]>([])
  const [nodes, setNodes] = useState<ComputeNode[]>([])
  const [nodeId, setNodeId] = useState("local")
  const [image, setImage] = useState("images:debian/12")
  const [quickImages, setQuickImages] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    vmsApi.isos().then(setIsos).catch(() => setIsos([]))
    vmsApi.importJobs().then((j) => setImports(j.filter((x) => x.status === "done"))).catch(() => setImports([]))
    nodesApi.list().then(setNodes).catch(() => setNodes([]))
    vmsApi.quickImages().then(setQuickImages).catch(() => setQuickImages([]))
  }, [])

  const isRemote = nodeId !== "local"
  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,31}$/.test(name)
  // Only VM-capable (incus + kvm) online agent nodes can host image VMs.
  const vmNodes = nodes.filter((n) => n.node_id !== "local"
    && isPlaceableStatus(n.status)
    && Boolean((n.capabilities as Record<string, unknown>).incus)
    && Boolean((n.capabilities as Record<string, unknown>).kvm))

  async function submit() {
    if (!validName) { setError(t("create.error_name_invalid")); return }
    if (isRemote && !image.trim()) { setError(t("create.field_image")); return }
    if (!isRemote && bootSrc === "import" && !importJobId) { setError(t("create.field_import_job")); return }
    setBusy(true); setError(null)
    try {
      if (isRemote) {
        await vmsApi.create({
          name, description: description.trim() || null,
          cpu, ram_mb: ramMb, disk_gb: diskGb,
          network_mode: network,
          node_id: nodeId,
          image: image.trim(),
        })
        onCreated(); onClose()
        return
      }
      const input: VMCreateInput & { import_job_id?: string } = {
        name, description: description.trim() || null,
        cpu, ram_mb: ramMb, disk_gb: diskGb,
        iso_filename: bootSrc === "iso" && iso ? iso : null,
        network_mode: network,
        disk_interface: diskInterface,
        machine_type: machineType,
        network_device: networkDevice,
      }
      if (bootSrc === "import") (input as any).import_job_id = importJobId
      await vmsApi.create(input)
      onCreated(); onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="box overflow-hidden w-full max-w-2xl mx-4 flex flex-col max-h-[90vh]" style={{ "--c": rgbFor("/vms") } as CSSProperties}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
          <h2 className="text-lg font-bold text-white">{t("create.title")}</h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5"><X size={16} /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4 space-y-5">
          <Field label={t("create.field_name")} hint={t("create.field_name_hint")}>
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="z.B. metin2-prod"
              className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
          </Field>
          <Field label={t("create.field_desc")}>
            <input value={description} onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
          </Field>
          {vmNodes.length > 0 && (
            <Field label={t("create.field_node")} hint={t("create.node_hint")}>
              <select value={nodeId} onChange={(e) => setNodeId(e.target.value)}
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none">
                <option value="local">{t("create.node_local")}</option>
                {vmNodes.map((n) => <option key={n.node_id} value={n.node_id}>{n.name}</option>)}
              </select>
            </Field>
          )}
          {isRemote && (
            <>
              <Field label={t("create.field_image")} hint={t("create.image_hint")}>
                <select value={image} onChange={(e) => setImage(e.target.value)}
                  className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 font-mono focus:border-violet-500/50 outline-none">
                  {(quickImages.length > 0 ? quickImages : [image]).map((img) => <option key={img} value={img}>{img}</option>)}
                </select>
              </Field>
              <div className="text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2">{t("create.remote_note")}</div>
            </>
          )}
          {!isRemote && (
          <>
          <Field label={t("create.field_boot_src")}>
            <div className="grid grid-cols-3 gap-2">
              <RadioCard active={bootSrc === "iso"} onClick={() => setBootSrc("iso")}
                title={t("create.boot_iso_title")} desc={t("create.boot_iso_desc")} />
              <RadioCard active={bootSrc === "import"} onClick={() => setBootSrc("import")}
                title={t("create.boot_import_title")} desc={t("create.boot_import_desc")} />
              <RadioCard active={bootSrc === "blank"} onClick={() => setBootSrc("blank")}
                title={t("create.boot_blank_title")} desc={t("create.boot_blank_desc")} />
            </div>
          </Field>
          {bootSrc === "iso" && (
            <Field label={t("create.field_iso")}>
              <select value={iso} onChange={(e) => setIso(e.target.value)}
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none">
                <option value="">— Keine —</option>
                {isos.map((i) => (
                  <option key={i.filename} value={i.filename}>{i.filename} ({formatBytes(i.size_bytes)})</option>
                ))}
              </select>
              {isos.length === 0 && <p className="text-[11px] text-zinc-500 mt-1">{t("create.no_isos")}</p>}
            </Field>
          )}
          {bootSrc === "import" && (
            <Field label={t("create.field_import_job")} hint={t("create.field_import_hint")}>
              <select value={importJobId} onChange={(e) => setImportJobId(e.target.value)}
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none">
                <option value="">— Auswählen —</option>
                {imports.map((j) => {
                  const src = j.source_path.split("/").pop() ?? j.source_path
                  return <option key={j.job_id} value={j.job_id}>{src} ({formatBytes(j.bytes_total)})</option>
                })}
              </select>
              {imports.length === 0 && <p className="text-[11px] text-zinc-500 mt-1">{t("imports.empty")}</p>}
            </Field>
          )}
          </>
          )}
          <div className="grid grid-cols-3 gap-3">
            <Slider label="vCPU" value={cpu} min={1} max={16} step={1} onChange={setCpu} suffix={`${cpu}`} />
            <Slider label="RAM" value={ramMb} min={512} max={32768} step={512} onChange={setRamMb} suffix={`${(ramMb / 1024).toFixed(1)} GB`} />
            <Slider label="Disk" value={diskGb} min={5} max={500} step={5} onChange={setDiskGb} suffix={`${diskGb} GB`}
              disabled={bootSrc === "import"} />
          </div>
          {bootSrc === "import" && <p className="text-[11px] text-zinc-500 -mt-3">{t("create.disk_size_from_import")}</p>}
          <Field label={t("create.field_network")}>
            <div className="grid grid-cols-2 gap-2">
              <RadioCard active={network === "bridged"} onClick={() => setNetwork("bridged")}
                title={t("create.net_bridged_title")} desc={t("create.net_bridged_desc")} />
              <RadioCard active={network === "isolated"} onClick={() => setNetwork("isolated")}
                title={t("create.net_isolated_title")} desc={t("create.net_isolated_desc")} />
            </div>
          </Field>
          {!isRemote && (
          <>
          <Field
            label={t("create.field_disk_interface")}
            hint={bootSrc === "import" ? t("create.disk_hint_import") : t("create.disk_hint_iso")}>
            <div className="grid grid-cols-3 gap-2">
              <RadioCard active={diskInterface === "virtio"} onClick={() => setDiskInterface("virtio")}
                title={t("create.disk_virtio_title")} desc={t("create.disk_virtio_desc")} />
              <RadioCard active={diskInterface === "sata"} onClick={() => setDiskInterface("sata")}
                title="sata" desc={t("create.disk_sata_desc")} />
              <RadioCard active={diskInterface === "ide"} onClick={() => setDiskInterface("ide")}
                title="ide" desc={t("create.disk_ide_desc")} />
            </div>
          </Field>
          <Field
            label={t("create.field_machine_type")}
            hint={t("create.machine_hint")}>
            <div className="grid grid-cols-2 gap-2">
              <RadioCard active={machineType === "q35"} onClick={() => setMachineType("q35")}
                title="q35" desc={t("create.machine_q35_desc")} />
              <RadioCard active={machineType === "pc"} onClick={() => setMachineType("pc")}
                title="pc (i440FX)" desc={t("create.machine_pc_desc")} />
            </div>
          </Field>
          <Field
            label={t("create.field_network_device")}
            hint={t("create.netdev_hint")}>
            <div className="grid grid-cols-2 gap-2">
              <RadioCard active={networkDevice === "virtio-net-pci"} onClick={() => setNetworkDevice("virtio-net-pci")}
                title="virtio-net-pci" desc={t("create.netdev_virtio_desc")} />
              <RadioCard active={networkDevice === "e1000"} onClick={() => setNetworkDevice("e1000")}
                title="e1000" desc={t("create.netdev_e1000_desc")} />
            </div>
          </Field>
          </>
          )}
          {error && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">{error}</div>}
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-white/[6%]">
          <button onClick={onClose} disabled={busy} className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">{t("create.cancel")}</button>
          <button onClick={submit} disabled={busy || !validName}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40">
            {busy ? t("create.submitting") : t("create.submit")}
          </button>
        </div>
      </div>
    </div>
  )
}
