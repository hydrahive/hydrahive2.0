import { Loader2, Plug, PlugZap, Save, Server, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { mcpApi } from "./api"
import { McpToolList } from "./McpToolList"
import type { McpServer, McpTool } from "./types"

interface Props {
  server: McpServer
  onSaved: (s: McpServer) => void
  onDeleted: () => void
}

export function McpServerForm({ server, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("mcp")
  const { t: tCommon } = useTranslation("common")
  const [draft, setDraft] = useState(server)
  const [argsText, setArgsText] = useState((server.args ?? []).join(" "))
  const [envText, setEnvText] = useState(
    Object.entries(server.env ?? {}).map(([k, v]) => `${k}=${v}`).join("\n"),
  )
  const [tools, setTools] = useState<McpTool[]>([])
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(server)
    setArgsText((server.args ?? []).join(" "))
    setEnvText(Object.entries(server.env ?? {}).map(([k, v]) => `${k}=${v}`).join("\n"))
    setTools([])
    setError(null)
    if (server.connected) loadTools()
  }, [server.id])

  async function loadTools() {
    try { setTools(await mcpApi.tools(server.id)) } catch { /* ignore */ }
  }

  async function save() {
    setSaving(true); setError(null)
    try {
      const env = Object.fromEntries(
        envText.split("\n").map((l) => l.trim()).filter(Boolean)
          .map((l) => l.split("=", 2)).filter((p) => p.length === 2)
      )
      const updated = await mcpApi.update(server.id, {
        name: draft.name, description: draft.description, enabled: draft.enabled,
        command: draft.command, args: argsText.split(/\s+/).filter(Boolean),
        env, url: draft.url,
      })
      onSaved(updated)
    } catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
    finally { setSaving(false) }
  }

  async function toggleConnect() {
    setBusy(true); setError(null)
    try {
      if (server.connected) {
        await mcpApi.disconnect(server.id)
        onSaved({ ...server, connected: false })
        setTools([])
      } else {
        const r = await mcpApi.connect(server.id)
        setTools(r.tools)
        onSaved({ ...server, connected: r.connected })
      }
    } catch (e) { setError(e instanceof Error ? e.message : t("actions.connection_failed")) }
    finally { setBusy(false) }
  }

  async function remove() {
    if (!confirm(t("actions.delete_confirm", { name: server.name }))) return
    await mcpApi.delete(server.id)
    onDeleted()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[6%] flex items-center gap-3">
        <Server size={18} className="text-violet-300 flex-shrink-0" />
        <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          className="flex-1 bg-transparent text-lg font-bold text-white focus:outline-none" />
        <button onClick={toggleConnect} disabled={busy || !server.enabled}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            server.connected
              ? "bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30"
              : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-white/[8%]"
          } disabled:opacity-30`}>
          {busy ? <Loader2 size={14} className="animate-spin" /> :
            (server.connected ? <PlugZap size={14} /> : <Plug size={14} />)}
          {server.connected ? t("actions.connected") : t("actions.connect")}
        </button>
        <button onClick={save} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 shadow-md shadow-violet-900/20">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {tCommon("actions.save")}
        </button>
        <button onClick={remove} className="p-2 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
          <Trash2 size={15} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-sm text-rose-300">{error}</div>
        )}

        <div className="grid grid-cols-3 gap-4">
          <Field label={t("fields.transport")}><p className="text-sm text-zinc-300 font-mono">{server.transport}</p></Field>
          <Field label={t("fields.id")}><p className="text-sm text-zinc-300 font-mono">{server.id}</p></Field>
          <Field label={tCommon("labels.status")}>
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" checked={draft.enabled} onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
                className="w-4 h-4 accent-violet-600" />
              {draft.enabled ? tCommon("status.active") : tCommon("status.disabled")}
            </label>
          </Field>
        </div>

        <Field label={tCommon("labels.description")}>
          <input value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200" />
        </Field>

        {server.transport === "stdio" && (
          <>
            <Field label={t("fields.command")}>
              <input value={draft.command ?? ""} onChange={(e) => setDraft({ ...draft, command: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200 font-mono" />
            </Field>
            <Field label={t("fields.args")}>
              <input value={argsText} onChange={(e) => setArgsText(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200 font-mono" />
            </Field>
            <Field label={t("fields.env")}>
              <textarea value={envText} onChange={(e) => setEnvText(e.target.value)} rows={3}
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200 font-mono leading-relaxed" />
            </Field>
          </>
        )}

        {(server.transport === "http" || server.transport === "sse") && (
          <Field label={t("fields.url")}>
            <input value={draft.url ?? ""} onChange={(e) => setDraft({ ...draft, url: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-200 font-mono" />
          </Field>
        )}

        <Field label={t("fields.tools_count", { count: tools.length })}>
          <McpToolList tools={tools} />
        </Field>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</label>
      {children}
    </div>
  )
}
