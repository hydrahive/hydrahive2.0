import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitButton } from "@/features/cockpit/CockpitButton"
import { templatesApi } from "./api"
import { pendingAssignments } from "./templateLogic"
import type { AgentTemplate, BindingProposal } from "./types"

const cell = "px-2 py-1.5 align-top"

/** Reiter „Zuordnung“: bestehende Agenten an Templates binden (Plan E3). Nur Admin. */
export function BindingsTab({ templates }: { templates: AgentTemplate[] }) {
  const { t } = useTranslation("llm")
  const [rows, setRows] = useState<BindingProposal[]>([])
  const [backups, setBackups] = useState<string[]>([])
  const [choice, setChoice] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const r = await templatesApi.proposal()
    setRows(r.proposal); setBackups(r.backups)
    setChoice(Object.fromEntries(r.proposal.map((p) => [p.id, p.proposed])))
  }, [])
  useEffect(() => { load().catch((e) => setMsg(String(e?.message ?? e))) }, [load])

  const pending = useMemo(() => pendingAssignments(rows, choice), [rows, choice])
  const count = Object.keys(pending).length

  async function apply() {
    if (!count || !window.confirm(t("bindings.confirm", { n: count }))) return
    setBusy(true)
    try { const r = await templatesApi.apply(pending); setMsg(t("bindings.done", { n: r.written, backup: r.backup })); await load() }
    catch (e) { setMsg(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }
  async function undo(stamp: string) {
    if (!window.confirm(t("bindings.undo_confirm", { backup: stamp }))) return
    setBusy(true)
    try { const r = await templatesApi.undo(stamp); setMsg(t("bindings.undone", { n: r.restored })); await load() }
    catch (e) { setMsg(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-[#9aa7bc]">{t("bindings.intro")}</p>
      {msg && <p role="status" className="text-sm text-amber-200">{msg}</p>}
      <div className="max-h-[55vh] overflow-auto rounded-[4px] border border-white/[8%]">
        <table className="w-full text-xs text-zinc-300">
          <thead className="sticky top-0 bg-[#10141c] text-left text-[10px] uppercase tracking-widest text-[#9aa7bc]">
            <tr><th className={cell}>{t("bindings.agent")}</th><th className={cell}>{t("bindings.today")}</th>
              <th className={cell}>{t("bindings.template")}</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-white/[5%]">
                <td className={cell}>
                  <div className="text-zinc-200">{r.name}</div>
                  <div className="text-[10px] text-zinc-500">{r.type} · {r.owner}{r.managed_by ? ` · ${r.managed_by}` : ""}</div>
                </td>
                <td className={`${cell} break-all text-zinc-400`}>
                  {r.current_template ? t("bindings.bound_to", { id: r.current_template })
                    : [r.llm_model, ...r.fallback_models].filter(Boolean).join(" → ")}
                </td>
                <td className={cell}>
                  <select value={choice[r.id] ?? ""} onChange={(e) => setChoice({ ...choice, [r.id]: e.target.value })}
                    className="w-full rounded-[4px] border border-white/[8%] bg-zinc-900 px-1.5 py-1 text-xs text-zinc-200">
                    {templates.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
                  </select>
                  {r.unsure && !r.current_template && <p className="mt-0.5 text-[10px] text-amber-400">{t("bindings.unsure")}</p>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1 text-[11px] text-zinc-500">
          {backups.slice(0, 3).map((b) => (
            <button key={b} type="button" disabled={busy} onClick={() => undo(b)}
              className="rounded-[4px] border border-white/[8%] px-2 py-0.5 hover:bg-white/5">{t("bindings.undo", { backup: b })}</button>
          ))}
        </div>
        <CockpitButton tone="primary" onClick={apply} disabled={busy || !count}>{t("bindings.apply", { n: count })}</CockpitButton>
      </div>
    </div>
  )
}
