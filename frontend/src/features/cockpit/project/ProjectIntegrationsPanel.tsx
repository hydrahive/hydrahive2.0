import { useEffect, useState } from "react"
import { CheckCircle2, Copy, Eye, EyeOff, Loader2, Save } from "lucide-react"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"

interface SambaInfo {
  enabled: boolean
  share_name: string
  user: string
  password: string
}

type CopiedField = "url" | "user" | "password" | null

export function ProjectIntegrationsPanel({ project, onSaved }: {
  project: Project
  onSaved: (project: Project) => void
}) {
  const [mcpIds, setMcpIds] = useState((project.mcp_server_ids ?? []).join(", "))
  const [plugins, setPlugins] = useState((project.allowed_plugins ?? []).join(", "))
  const [apiKey, setApiKey] = useState("")
  const [removeKey, setRemoveKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [samba, setSamba] = useState<SambaInfo | null>(null)
  const [sambaBusy, setSambaBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<CopiedField>(null)

  useEffect(() => {
    projectsApi.getSamba(project.id)
      .then(setSamba)
      .catch(() => setSamba(null))
  }, [project.id])

  async function save() {
    setSaving(true); setError(null)
    try {
      const fields: { mcp_server_ids: string[]; allowed_plugins: string[]; llm_api_key?: string } = {
        mcp_server_ids: mcpIds.split(",").map((value) => value.trim()).filter(Boolean),
        allowed_plugins: plugins.split(",").map((value) => value.trim()).filter(Boolean),
      }
      if (apiKey.trim()) fields.llm_api_key = apiKey.trim()
      else if (removeKey) fields.llm_api_key = ""
      const updated = await projectsApi.update(project.id, fields)
      setApiKey(""); setRemoveKey(false); onSaved(updated)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Integrationen konnten nicht gespeichert werden.")
    } finally { setSaving(false) }
  }

  async function toggleSamba() {
    if (!samba) return
    setSambaBusy(true); setError(null); setShowPassword(false)
    try {
      await projectsApi.putSamba(project.id, !samba.enabled)
      setSamba(await projectsApi.getSamba(project.id))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Samba konnte nicht geändert werden.")
    } finally { setSambaBusy(false) }
  }

  async function copy(value: string, key: Exclude<CopiedField, null>) {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopied(key)
      window.setTimeout(() => setCopied(null), 1500)
    } catch {
      setError("Der Wert konnte nicht in die Zwischenablage kopiert werden.")
    }
  }

  const sambaUrl = samba ? `\\\\${window.location.hostname}\\${samba.share_name}` : ""

  return <div className="space-y-5">
    {samba && <section className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-medium text-[#e8eef8]">Samba-Projektfreigabe</h3>
          <p className="text-[11px] text-[#718097]">Workspace dieses Projekts im Netzwerk bereitstellen.</p>
        </div>
        <label className="flex items-center gap-2 text-xs text-[#b8c4d8]">
          <input type="checkbox" checked={samba.enabled} disabled={sambaBusy} onChange={toggleSamba} />
          Aktiv {sambaBusy && <Loader2 size={12} className="animate-spin" />}
        </label>
      </div>
      {samba.enabled && <div className="space-y-2">
        <CopyRow label="Adresse" value={sambaUrl} copied={copied === "url"} onCopy={() => copy(sambaUrl, "url")} />
        <CopyRow label="Benutzer" value={samba.user} copied={copied === "user"} onCopy={() => copy(samba.user, "user")} />
        <SecretRow
          value={samba.password}
          visible={showPassword}
          copied={copied === "password"}
          onToggle={() => setShowPassword((visible) => !visible)}
          onCopy={() => copy(samba.password, "password")}
        />
        <p className="text-[11px] text-[#718097]">Dieses Samba-Login gilt für alle aktivierten Projektfreigaben.</p>
      </div>}
    </section>}
    <section className="space-y-3 border-t border-[#2a364b] pt-4">
      <div><label className="text-xs font-medium text-[#b8c4d8]">MCP-Server-IDs</label><input value={mcpIds} onChange={(event) => setMcpIds(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8]" /><p className="mt-1 text-[11px] text-[#718097]">Kommagetrennte IDs der für dieses Projekt erlaubten MCP-Server.</p></div>
      <div><label className="text-xs font-medium text-[#b8c4d8]">Erlaubte Plugins</label><input value={plugins} onChange={(event) => setPlugins(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8]" /><p className="mt-1 text-[11px] text-[#718097]">Kommagetrennte Plugin-IDs; leer bedeutet kein Projekt-Override.</p></div>
      <div><label className="text-xs font-medium text-[#b8c4d8]">LLM-API-Key ersetzen</label><input type="password" value={apiKey} onChange={(event) => { setApiKey(event.target.value); if (event.target.value) setRemoveKey(false) }} placeholder={project.llm_api_key ? "Gespeicherter Key bleibt unverändert" : "Optionaler neuer API-Key"} autoComplete="new-password" className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8]" /><label className="mt-2 flex items-center gap-2 text-xs text-[#8d9ab0]"><input type="checkbox" checked={removeKey} onChange={(event) => { setRemoveKey(event.target.checked); if (event.target.checked) setApiKey("") }} />Gespeicherten Projekt-Key entfernen</label></div>
      <button onClick={save} disabled={saving} className="flex items-center gap-2 rounded-[4px] bg-[#6d5dfc] px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}Integrationen speichern</button>
    </section>
    {error && <p className="rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
  </div>
}

function CopyRow({ label, value, copied, onCopy }: { label: string; value: string; copied: boolean; onCopy: () => void }) {
  return <div className="grid grid-cols-[80px_1fr_auto] items-center gap-2"><span className="text-xs text-[#718097]">{label}</span><code className="truncate rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-2 py-1 text-xs text-[#d6deeb]">{value}</code><button type="button" onClick={onCopy} aria-label={`${label} kopieren`} className="rounded p-1.5 text-[#8d9ab0] hover:bg-white/5 hover:text-white">{copied ? <CheckCircle2 size={13} className="text-emerald-400" /> : <Copy size={13} />}</button></div>
}

function SecretRow({ value, visible, copied, onToggle, onCopy }: { value: string; visible: boolean; copied: boolean; onToggle: () => void; onCopy: () => void }) {
  return <div className="grid grid-cols-[80px_1fr_auto] items-center gap-2"><span className="text-xs text-[#718097]">Passwort</span><code className="truncate rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-2 py-1 text-xs text-[#d6deeb]">{value ? (visible ? value : "••••••••••••") : "Nicht eingerichtet"}</code><div className="flex"><button type="button" onClick={onToggle} disabled={!value} aria-label={visible ? "Passwort verbergen" : "Passwort anzeigen"} className="rounded p-1.5 text-[#8d9ab0] hover:bg-white/5 hover:text-white disabled:opacity-40">{visible ? <EyeOff size={13} /> : <Eye size={13} />}</button><button type="button" onClick={onCopy} disabled={!value} aria-label="Passwort kopieren" className="rounded p-1.5 text-[#8d9ab0] hover:bg-white/5 hover:text-white disabled:opacity-40">{copied ? <CheckCircle2 size={13} className="text-emerald-400" /> : <Copy size={13} />}</button></div></div>
}
