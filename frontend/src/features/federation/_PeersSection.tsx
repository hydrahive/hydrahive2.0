import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Plus, Server } from "lucide-react"
import { peersApi } from "./api"
import type { Peer } from "./types"
import { agentsApi } from "@/features/agents/api"
import { PeerCard } from "./_PeerCard"
import { PeerPairDialog } from "./_PeerPairDialog"

// Gekoppelte HydraHive-Server (docs/specs/server-peering.md).
export function PeersSection() {
  const { t } = useTranslation("federation")
  const [peers, setPeers] = useState<Peer[]>([])
  const [agents, setAgents] = useState<{ id: string; name: string; autoTools: boolean }[]>([])
  const [loading, setLoading] = useState(true)
  const [showPair, setShowPair] = useState(false)

  async function load() {
    try {
      setPeers(await peersApi.list())
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    agentsApi.list()
      .then(list => setAgents(list.map(a => ({ id: a.id, name: a.name, autoTools: !a.require_tool_confirm }))))
      .catch(() => {})
  }, [])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server size={15} className="text-violet-400" />
          <span className="text-sm font-medium text-zinc-200">{t("peers.title")}</span>
          <span className="text-xs text-zinc-600 ml-1">{t("peers.subtitle")}</span>
        </div>
        <button
          onClick={() => setShowPair(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 border border-white/[6%] transition-colors"
        >
          <Plus size={12} />
          {t("peers.pair")}
        </button>
      </div>

      {loading ? (
        <div className="text-xs text-zinc-600 py-4 text-center">{t("loading")}</div>
      ) : peers.length === 0 ? (
        <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-8 text-center">
          <Server size={24} className="text-zinc-700 mx-auto mb-2" />
          <p className="text-xs text-zinc-600">{t("peers.empty")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {peers.map(p => <PeerCard key={p.id} peer={p} agents={agents} onChange={load} />)}
        </div>
      )}

      {showPair && (
        <PeerPairDialog onClose={() => setShowPair(false)} onAdded={() => { setShowPair(false); load() }} />
      )}
    </div>
  )
}
