import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

interface Props {
  draft: Agent
  onChange: (patch: Partial<Agent>) => void
}

// Kompakte Sub-Box: kleiner Rahmen + Mini-Label, fließt im Masonry-Mini-Grid.
function SubBox({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-2.5 break-inside-avoid rounded-lg border border-white/[7%] bg-white/[2%] p-2.5 space-y-1.5">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">{label}</p>
      {children}
    </div>
  )
}

export function OverviewTab({ draft, onChange }: Props) {
  const { t } = useTranslation("agents")
  const isSpecialist = draft.type === "specialist"

  const info: { label: string; value: string | null }[] = [
    { label: t("info.id"), value: draft.id },
    { label: t("info.owner"), value: draft.owner },
    { label: t("info.created_by"), value: draft.created_by },
    { label: t("info.created_at"), value: formatDate(draft.created_at) },
    { label: t("info.workspace"), value: draft.workspace ?? null },
    { label: t("info.project"), value: draft.project_id ?? null },
  ].filter((r) => r.value)

  return (
    <div className="columns-1 sm:columns-2 xl:columns-3 gap-2.5">
      <SubBox label={t("fields.type")}>
        <p className="text-xs text-zinc-300 font-mono">{t(`type.${draft.type}`)}</p>
        {isSpecialist && (
          <input
            value={draft.domain ?? ""}
            onChange={(e) => onChange({ domain: e.target.value || null })}
            placeholder={t("fields.domain_placeholder")}
            className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
          />
        )}
      </SubBox>

      <SubBox label={t("fields.description")}>
        <textarea
          value={draft.description}
          onChange={(e) => onChange({ description: e.target.value })}
          rows={3}
          className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50"
        />
      </SubBox>

      <SubBox label={t("fields.require_tool_confirm")}>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!draft.require_tool_confirm}
            onChange={(e) => onChange({ require_tool_confirm: e.target.checked })}
            className="mt-0.5 accent-violet-500"
          />
          <span className="text-[10px] text-zinc-500">{t("fields.require_tool_confirm_hint")}</span>
        </label>
      </SubBox>

      <SubBox label={t("info.title")}>
        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
          {info.map((r) => (
            <div key={r.label} className="contents">
              <span className="text-zinc-600">{r.label}</span>
              <span className="text-zinc-300 font-mono truncate" title={r.value ?? undefined}>{r.value}</span>
            </div>
          ))}
        </div>
      </SubBox>
    </div>
  )
}

function formatDate(iso: string): string {
  if (!iso) return ""
  try { return new Date(iso).toLocaleString() } catch { return iso }
}
