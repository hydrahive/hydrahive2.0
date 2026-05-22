import { useState } from "react"
import { Activity, ChevronDown, ChevronUp, RefreshCw, Shield, ShieldOff, Terminal, Trash2 } from "lucide-react"
import type { Workstation } from "./types"
import { federationApi } from "./api"

interface Props {
  ws: Workstation
  onRefresh: () => void
  onDelete: (id: string) => void
  onToggle: (id: string, enabled: boolean) => void
}

export function WorkstationCard({ ws, onRefresh, onDelete, onToggle }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [auditRows, setAuditRows] = useState<unknown[] | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)

  const card = ws.card
  const agents = card?.agents ?? []

  async function handleRefresh() {
    setRefreshing(true)
    try { await federationApi.refresh(ws.id); onRefresh() } catch { /* ignore */ }
    finally { setRefreshing(false) }
  }

  async function loadAudit() {
    setAuditLoading(true)
    try {
      const rows = await federationApi.audit(ws.id)
      setAuditRows(rows)
    } catch { setAuditRows([]) }
    finally { setAuditLoading(false) }
  }

  const statusDot = ws.last_seen
    ? "bg-emerald-400"
    : "bg-zinc-600"

  return (
    <div className={`rounded-xl border ${ws.enabled ? "border-white/10" : "border-white/5 opacity-60"} bg-zinc-900/60 overflow-hidden`}>
      <div className="flex items-center gap-3 px-4 py-3">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-zinc-100 text-sm truncate">{ws.name}</span>
            {card && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-mono">
                {card.protocol}
              </span>
            )}
          </div>
          <div className="text-xs text-zinc-500 truncate">{ws.url}</div>
        </div>
        <div className="flex items-center gap-1">
          {ws.has_token ? (
            <span title="Token konfiguriert"><Shield size={13} className="text-emerald-400" /></span>
          ) : (
            <span title="Kein Token"><ShieldOff size={13} className="text-zinc-600" /></span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="A2A-Card neu laden"
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
          </button>
          <button
            onClick={() => onToggle(ws.id, !ws.enabled)}
            className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-zinc-200 transition-colors"
            title={ws.enabled ? "Deaktivieren" : "Aktivieren"}
          >
            <Activity size={13} className={ws.enabled ? "text-emerald-400" : "text-zinc-600"} />
          </button>
          <button
            onClick={() => onDelete(ws.id)}
            className="p-1.5 rounded-lg hover:bg-rose-500/10 text-zinc-500 hover:text-rose-400 transition-colors"
          >
            <Trash2 size={13} />
          </button>
          <button
            onClick={() => setExpanded(v => !v)}
            className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-white/5 px-4 py-3 space-y-3">
          {card ? (
            <>
              <div className="text-xs text-zinc-400">{card.description}</div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(card.capabilities ?? {}).map(([cap, val]) => (
                  <span
                    key={cap}
                    className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                      val ? "bg-emerald-500/15 text-emerald-300" : "bg-zinc-800 text-zinc-600"
                    }`}
                  >
                    {cap}
                  </span>
                ))}
              </div>
              {agents.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-zinc-600 mb-1.5">Personas / Agents</div>
                  <div className="space-y-1">
                    {agents.map(a => (
                      <div key={a.id} className="flex items-center gap-2 text-xs">
                        <code className="text-violet-300 font-mono">{a.id}@{ws.name}</code>
                        {a.description && (
                          <span className="text-zinc-500 truncate">{a.description}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {ws.last_seen && (
                <div className="text-[10px] text-zinc-600">
                  Zuletzt gesehen: {new Date(ws.last_seen).toLocaleString("de")}
                </div>
              )}
            </>
          ) : (
            <div className="text-xs text-zinc-500 italic">
              Keine A2A-Card — bitte Token prüfen und «Refresh» klicken
            </div>
          )}

          {ws.has_token && (
            <div>
              <button
                onClick={loadAudit}
                disabled={auditLoading}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <Terminal size={12} />
                {auditLoading ? "Lade…" : "Remote-Audit-Log"}
              </button>
              {auditRows && (
                <div className="mt-2 max-h-48 overflow-y-auto rounded-lg bg-black/30 p-2 font-mono text-[10px] text-zinc-400 space-y-1">
                  {auditRows.length === 0 && <div>Keine Einträge</div>}
                  {(auditRows as any[]).map((r, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-zinc-600 flex-shrink-0">
                        {new Date(r.timestamp).toLocaleTimeString("de")}
                      </span>
                      <span className={r.status >= 400 ? "text-rose-400" : "text-emerald-400"}>
                        {r.status}
                      </span>
                      <span className="text-zinc-300">{r.path}</span>
                      <span className="text-zinc-600 truncate">{r.caller}</span>
                      {r.error && <span className="text-rose-400">{r.error}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
