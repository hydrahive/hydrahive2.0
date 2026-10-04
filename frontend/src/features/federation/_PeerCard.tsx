import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Ban, CheckCircle2, Server, Trash2 } from "lucide-react"
import { peersApi } from "./api"
import type { Peer } from "./types"

interface Props {
  peer: Peer
  agents: { id: string; name: string }[]
  onChange: () => void
}

const DOT: Record<Peer["status"], string> = {
  pending: "bg-amber-400",
  active: "bg-emerald-500",
  blocked: "bg-red-500",
}

export function PeerCard({ peer, agents, onChange }: Props) {
  const { t } = useTranslation("federation")
  const [fp, setFp] = useState("")
  const [error, setError] = useState("")

  async function run(fn: () => Promise<unknown>) {
    setError("")
    try {
      await fn()
      onChange()
    } catch (e) {
      setError(e instanceof Error ? e.message : t("peers.error"))
    }
  }

  function toggleAgent(id: string) {
    const next = peer.allowed_agents.includes(id)
      ? peer.allowed_agents.filter(a => a !== id)
      : [...peer.allowed_agents, id]
    run(() => peersApi.setAgents(peer.id, next))
  }

  return (
    <div className="rounded-lg border border-white/[5%] bg-zinc-900/60 p-3 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <Server size={15} className="text-violet-400 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${DOT[peer.status]}`} />
              <span className="text-sm text-zinc-200">{peer.name}</span>
              <span className="text-[11px] text-zinc-500">{t(`peers.status_${peer.status}`)}</span>
            </div>
            <p className="text-[11px] text-zinc-500 truncate">{peer.url}</p>
            <p className="text-[11px] text-zinc-500">
              {t("peers.fp")} <code className="text-zinc-300">{peer.fingerprint}</code>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {peer.status !== "blocked" && (
            <button onClick={() => run(() => peersApi.block(peer.id))} title={t("peers.block")}
              className="p-1 text-zinc-600 hover:text-amber-400"><Ban size={13} /></button>
          )}
          <button
            onClick={() => confirm(t("peers.delete_confirm", { name: peer.name })) && run(() => peersApi.delete(peer.id))}
            title={t("peers.delete")} className="p-1 text-zinc-600 hover:text-red-400"
          ><Trash2 size={13} /></button>
        </div>
      </div>

      {peer.status !== "active" && (
        <div className="space-y-1.5">
          <p className="text-[11px] text-zinc-400">{t("peers.confirm_hint")}</p>
          <div className="flex gap-2">
            <input
              value={fp} onChange={e => setFp(e.target.value)} placeholder="xxxx xxxx xxxx …"
              className="flex-1 rounded-lg bg-zinc-950/60 border border-white/[8%] px-2.5 py-1.5 text-xs font-mono text-zinc-200"
            />
            <button onClick={() => run(() => peersApi.confirm(peer.id, fp))} disabled={!fp.trim()}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-white">
              <CheckCircle2 size={12} /> {t("peers.confirm")}
            </button>
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        <p className="text-[11px] text-zinc-400">{t("peers.agents_hint")}</p>
        <div className="flex flex-wrap gap-1.5">
          {agents.map(a => {
            const on = peer.allowed_agents.includes(a.id)
            return (
              <button key={a.id} onClick={() => toggleAgent(a.id)}
                className={`px-2 py-0.5 rounded-md text-[11px] border transition-colors ${on
                  ? "bg-violet-600/30 border-violet-500/50 text-violet-200"
                  : "bg-zinc-950/40 border-white/[6%] text-zinc-500 hover:text-zinc-300"}`}>
                {a.name}
              </button>
            )
          })}
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
