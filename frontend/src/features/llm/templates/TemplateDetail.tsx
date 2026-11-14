import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import type { RegistryModel } from "@/features/llm/api"
import { CockpitButton } from "@/features/cockpit/CockpitButton"
import { templatesApi } from "./api"
import { TemplateBudget } from "./TemplateBudget"
import { TemplateChain } from "./TemplateChain"
import { TemplateFooter } from "./TemplateFooter"
import { toBody } from "./templateLogic"
import type { AgentTemplate, BoundAgent, ChainTestResult, TemplateDetail as Detail } from "./types"

const section = "space-y-2 border-t border-white/[6%] pt-4"
const heading = "text-xs font-semibold uppercase tracking-widest text-[#9aa7bc]"

/** Rechte Seite: ein Template bearbeiten (Admin) bzw. ansehen (Nutzer). */
export function TemplateDetail({ id, draft, models, isAdmin, onSaved }: {
  id: string; draft?: AgentTemplate; models: RegistryModel[]; isAdmin: boolean; onSaved: (id: string) => void
}) {
  const { t } = useTranslation("llm")
  const [detail, setDetail] = useState<Detail | null>(null)
  const [edit, setEdit] = useState<AgentTemplate | null>(draft ?? null)
  const [preview, setPreview] = useState<{ changed: string[]; affected: BoundAgent[] } | null>(null)
  const [tests, setTests] = useState<ChainTestResult[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setPreview(null); setTests(null); setError(null)
    if (draft) { setDetail(null); setEdit(draft); return }
    templatesApi.get(id).then((d) => { setDetail(d); setEdit(d) }).catch((e) => setError(String(e?.message ?? e)))
  }, [id, draft])

  if (!edit) return <p className="text-sm text-[#9aa7bc]">{error ?? "…"}</p>
  const readOnly = !isAdmin
  const update = (patch: Partial<AgentTemplate>) => { setEdit({ ...edit, ...patch }); setPreview(null) }

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true); setError(null)
    try { return await fn() } catch (e) { setError(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }
  const askPreview = () => run(async () => setPreview(await templatesApi.preview(id, toBody(edit))))
  const save = () => run(async () => { await templatesApi.save(id, toBody(edit)); setPreview(null); onSaved(id) })
  const test = () => run(async () => setTests((await templatesApi.test(id)).results))
  const revert = (rev: number) => run(async () => { await templatesApi.revert(id, rev); onSaved(id) })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <input value={edit.label} disabled={readOnly} onChange={(e) => update({ label: e.target.value })}
          className="flex-1 rounded-[4px] border border-white/[8%] bg-transparent px-2 py-1 text-lg text-[#e8eef8] disabled:border-transparent" />
        <span className="text-xs text-zinc-500">
          {t("templates.revision", { n: edit.revision })} · {readOnly ? t("templates.read_only") : t("templates.hard_bound")}
        </span>
      </div>

      <div className={section}>
        <p className={heading}>{t("templates.chain.title")}</p>
        <TemplateChain chain={edit.chain} models={models} readOnly={readOnly} onChange={(chain) => update({ chain })} />
        <label className="flex items-center gap-2 text-xs text-zinc-400">
          <input type="checkbox" checked={edit.on_demand} disabled={readOnly}
            onChange={(e) => update({ on_demand: e.target.checked })} />
          {t("templates.on_demand")}
        </label>
      </div>

      <div className={section}>
        <p className={heading}>{t("templates.budget.title")}</p>
        <TemplateBudget budget={edit.budget} reply={edit.reply} readOnly={readOnly}
          onBudget={(budget) => update({ budget })} onReply={(reply) => update({ reply })} />
      </div>

      <TemplateFooter detail={detail} preview={preview} tests={tests} isAdmin={isAdmin} busy={busy} error={error}
        onRevert={revert} />

      {isAdmin && (
        <div className="flex flex-wrap justify-end gap-2 border-t border-white/[6%] pt-3">
          {!draft && <CockpitButton onClick={test} disabled={busy}>{t("templates.actions.test")}</CockpitButton>}
          {preview
            ? <CockpitButton tone="primary" onClick={save} disabled={busy}>
                {t("templates.actions.confirm", { n: preview.affected.length })}
              </CockpitButton>
            : <CockpitButton tone="primary" onClick={askPreview} disabled={busy}>{t("templates.actions.save")}</CockpitButton>}
        </div>
      )}
    </div>
  )
}
