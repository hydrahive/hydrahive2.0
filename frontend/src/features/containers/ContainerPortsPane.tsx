import { useCallback, useEffect, useState } from "react"
import { Globe, Lock, Plus, PowerOff, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminFeedback, adminInputClass } from "@/features/cockpit/admin/ui"
import { cn } from "@/shared/cn"
import { containersApi } from "./api"
import type { PortList, PortProtocol, PortRule, PortScope } from "./types"

// Portfreigaben für NAT-Container (docs/specs/container-nat-ports.md).
const SCOPES: { scope: PortScope; icon: typeof Globe }[] = [
  { scope: "public", icon: Globe },
  { scope: "tailnet", icon: Lock },
  { scope: "off", icon: PowerOff },
]

function range(a: number, b: number) {
  return a === b ? String(a) : `${a}–${b}`
}

export function ContainerPortsPane({ containerId }: { containerId: string }) {
  const { t } = useTranslation("containers")
  const [data, setData] = useState<PortList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [label, setLabel] = useState("")
  const [protocol, setProtocol] = useState<PortProtocol | "both">("tcp")
  const [hostStart, setHostStart] = useState("")
  const [hostEnd, setHostEnd] = useState("")
  const [inner, setInner] = useState("")
  const [scope, setScope] = useState<PortScope>("public")

  const load = useCallback(async () => {
    try {
      setData(await containersApi.ports(containerId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    }
  }, [containerId])

  useEffect(() => { void load() }, [load])

  async function run(fn: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await fn()
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
      await load()
    } finally {
      setBusy(false)
    }
  }

  function add(event: React.FormEvent) {
    event.preventDefault()
    const start = parseInt(hostStart, 10)
    if (!start) return
    const end = hostEnd ? parseInt(hostEnd, 10) : null
    const target = inner ? parseInt(inner, 10) : null
    const protos: PortProtocol[] = protocol === "both" ? ["tcp", "udp"] : [protocol]
    void run(async () => {
      for (const p of protos) {
        await containersApi.addPort(containerId, {
          protocol: p, host_port_start: start, host_port_end: end,
          container_port_start: target, scope, label: label.trim(),
        })
      }
      setLabel(""); setHostStart(""); setHostEnd(""); setInner("")
    })
  }

  if (!data) return <div className="p-4"><AdminFeedback loading={!error} tone={error ? "danger" : undefined}>{error ?? t("ports.loading")}</AdminFeedback></div>
  if (data.network_mode !== "nat") return <div className="p-4"><AdminFeedback>{t("ports.only_nat")}</AdminFeedback></div>

  const publicUdp = data.ports.some((p) => p.scope === "public" && p.protocol === "udp")
  const publicAny = data.ports.some((p) => p.scope === "public")

  return (
    <div className="h-full space-y-4 overflow-auto p-4">
      <p className="text-xs text-[#8d9ab0]">{t("ports.ip")} <code className="text-[#c8f2ff]">{data.ipv4}</code></p>

      <table className="w-full text-left text-xs">
        <thead className="text-[#8d9ab0]">
          <tr><th className="py-1">{t("ports.col_label")}</th><th>{t("ports.col_protocol")}</th><th>{t("ports.col_ports")}</th><th>{t("ports.col_scope")}</th><th /></tr>
        </thead>
        <tbody>
          {data.ports.length === 0 && <tr><td colSpan={5} className="py-3 text-[#8d9ab0]">{t("ports.empty")}</td></tr>}
          {data.ports.map((p) => <PortRow key={p.id} rule={p} busy={busy}
            onScope={(s) => run(() => containersApi.setPortScope(containerId, p.id, s))}
            onDelete={() => run(() => containersApi.removePort(containerId, p.id))} />)}
        </tbody>
      </table>

      <form onSubmit={add} className="grid grid-cols-2 gap-2 rounded-[6px] border border-[#2a364b] p-3 md:grid-cols-6">
        <input className={cn(adminInputClass, "md:col-span-2")} placeholder={t("ports.label_ph")} value={label} onChange={(e) => setLabel(e.target.value)} maxLength={64} />
        <select className={adminInputClass} value={protocol} onChange={(e) => setProtocol(e.target.value as PortProtocol | "both")}>
          <option value="tcp">TCP</option><option value="udp">UDP</option><option value="both">TCP + UDP</option>
        </select>
        <input className={adminInputClass} inputMode="numeric" placeholder={t("ports.host_start_ph")} value={hostStart} onChange={(e) => setHostStart(e.target.value.replace(/\D/g, ""))} />
        <input className={adminInputClass} inputMode="numeric" placeholder={t("ports.host_end_ph")} value={hostEnd} onChange={(e) => setHostEnd(e.target.value.replace(/\D/g, ""))} />
        <input className={adminInputClass} inputMode="numeric" placeholder={t("ports.inner_ph")} value={inner} onChange={(e) => setInner(e.target.value.replace(/\D/g, ""))} />
        <div className="col-span-2 flex items-center gap-1 md:col-span-4">
          {SCOPES.map(({ scope: s, icon: Icon }) => (
            <button key={s} type="button" onClick={() => setScope(s)} aria-pressed={scope === s}
              className={cn("flex items-center gap-1 rounded-[4px] border px-2 py-1 text-[11px]",
                scope === s ? "border-[#69d7ff]/60 bg-[#163248] text-[#c8f2ff]" : "border-[#2a364b] text-[#8d9ab0]")}>
              <Icon size={12} />{t(`ports.scope_${s}`)}
            </button>
          ))}
        </div>
        <button type="submit" disabled={busy || !hostStart}
          className="col-span-2 flex items-center justify-center gap-1 rounded-[4px] bg-[#1f6f93] px-3 py-1.5 text-xs font-bold text-white disabled:opacity-40">
          <Plus size={12} />{t("ports.add")}
        </button>
      </form>

      {publicAny && <AdminFeedback tone="warning">{t("ports.hint_provider")}{publicUdp ? ` ${t("ports.hint_udp")}` : ""}</AdminFeedback>}
      <p className="text-[11px] text-[#8d9ab0]">{t("ports.hint_reserved")}</p>
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
    </div>
  )
}

function PortRow({ rule, busy, onScope, onDelete }: {
  rule: PortRule; busy: boolean; onScope: (s: PortScope) => void; onDelete: () => void
}) {
  const { t } = useTranslation("containers")
  const innerEnd = rule.container_port_start + (rule.host_port_end - rule.host_port_start)
  return (
    <tr className="border-t border-[#2a364b] align-middle text-[#e8eef8]">
      <td className="py-1.5">{rule.label || "—"}{rule.last_error && <p className="text-[10px] text-red-400">{rule.last_error}</p>}</td>
      <td className="uppercase">{rule.protocol}</td>
      <td className="font-mono">{range(rule.host_port_start, rule.host_port_end)} → {range(rule.container_port_start, innerEnd)}</td>
      <td>
        <div className="flex gap-1">
          {SCOPES.map(({ scope: s, icon: Icon }) => (
            <button key={s} type="button" disabled={busy || rule.scope === s} onClick={() => onScope(s)}
              title={t(`ports.scope_${s}`)} aria-pressed={rule.scope === s}
              className={cn("rounded-[4px] border p-1",
                rule.scope === s ? "border-[#69d7ff]/60 bg-[#163248] text-[#c8f2ff]" : "border-[#2a364b] text-[#5d6a80] hover:text-[#e8eef8]")}>
              <Icon size={12} />
            </button>
          ))}
        </div>
      </td>
      <td className="text-right">
        <button type="button" disabled={busy} onClick={() => confirm(t("ports.delete_confirm")) && onDelete()}
          className="p-1 text-[#5d6a80] hover:text-red-400"><Trash2 size={12} /></button>
      </td>
    </tr>
  )
}
