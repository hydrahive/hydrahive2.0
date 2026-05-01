import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

interface Props {
  draft: Agent
  onChange: (patch: Partial<Agent>) => void
}

export function OverviewTab({ draft, onChange }: Props) {
  const { t } = useTranslation("agents")
  const isSpecialist = draft.type === "specialist"

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Field label={t("fields.type")}>
          <p className="px-2 py-1 text-xs text-zinc-300 font-mono">{t(`type.${draft.type}`)}</p>
        </Field>
        {isSpecialist && (
          <Field label={t("fields.domain")}>
            <input
              value={draft.domain ?? ""}
              onChange={(e) => onChange({ domain: e.target.value || null })}
              placeholder={t("fields.domain_placeholder")}
              className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
            />
          </Field>
        )}
      </div>

      <Field label={t("fields.description")}>
        <textarea
          value={draft.description}
          onChange={(e) => onChange({ description: e.target.value })}
          rows={3}
          className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50"
        />
      </Field>

      <InfoBlock agent={draft} />
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

function InfoBlock({ agent }: { agent: Agent }) {
  const { t } = useTranslation("agents")
  const rows: { label: string; value: string | null }[] = [
    { label: t("info.id"), value: agent.id },
    { label: t("info.owner"), value: agent.owner },
    { label: t("info.created_by"), value: agent.created_by },
    { label: t("info.created_at"), value: formatDate(agent.created_at) },
    { label: t("info.workspace"), value: agent.workspace ?? null },
    { label: t("info.project"), value: agent.project_id ?? null },
  ].filter((r) => r.value)
  return (
    <div className="rounded-md border border-white/[6%] bg-white/[2%] p-2 space-y-0.5">
      <p className="text-[10px] font-medium text-zinc-500 mb-1">{t("info.title")}</p>
      <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
        {rows.map((r) => (
          <div key={r.label} className="contents">
            <span className="text-zinc-600">{r.label}</span>
            <span className="text-zinc-300 font-mono truncate" title={r.value ?? undefined}>
              {r.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatDate(iso: string): string {
  if (!iso) return ""
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
