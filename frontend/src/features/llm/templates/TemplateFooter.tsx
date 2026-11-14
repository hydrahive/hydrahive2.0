import { useTranslation } from "react-i18next"
import type { BoundAgent, ChainTestResult, TemplateDetail } from "./types"

const heading = "text-xs font-semibold uppercase tracking-widest text-[#9aa7bc]"

/** Unterer Teil der Detailseite: Vorschau, Testlauf, gebundene Agenten, Verlauf. */
export function TemplateFooter({ detail, preview, tests, isAdmin, busy, error, onRevert }: {
  detail: TemplateDetail | null
  preview: { changed: string[]; affected: BoundAgent[] } | null
  tests: ChainTestResult[] | null
  isAdmin: boolean; busy: boolean; error: string | null
  onRevert: (revision: number) => void
}) {
  const { t } = useTranslation("llm")
  return (
    <div className="space-y-4">
      {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}

      {preview && (
        <div className="rounded-[4px] border border-amber-400/30 bg-amber-400/5 p-3 text-sm text-amber-200">
          {t("templates.preview", { n: preview.affected.length, fields: preview.changed.join(", ") || "—" })}
        </div>
      )}

      {tests && (
        <ul className="space-y-1 text-sm">
          {tests.map((r) => (
            <li key={r.model} className={r.ok ? "text-emerald-400" : "text-rose-400"}>
              {r.ok ? "✓" : "✗"} {r.model} — {r.ok ? r.answer : t(`templates.test_reason.${r.reason ?? "error"}`)}
            </li>
          ))}
        </ul>
      )}

      {detail && (
        <div className="space-y-2 border-t border-white/[6%] pt-4">
          <p className={heading}>{t("templates.bound", { n: detail.bound.length })}</p>
          {detail.bound.length === 0
            ? <p className="text-sm text-zinc-500">{t("templates.bound_none")}</p>
            : <ul className="max-h-48 space-y-0.5 overflow-auto text-sm text-zinc-300">
                {detail.bound.map((a) => (
                  <li key={a.id} className="flex gap-2">
                    <span className="flex-1 truncate">{a.name}</span>
                    <span className="text-xs text-zinc-500">{a.owner}{a.managed_by ? ` · ${a.managed_by}` : ""}</span>
                  </li>
                ))}
              </ul>}
        </div>
      )}

      {detail && isAdmin && detail.history.length > 0 && (
        <div className="space-y-1 border-t border-white/[6%] pt-4">
          <p className={heading}>{t("templates.history")}</p>
          {[...detail.history].reverse().map((h) => (
            <div key={h.revision} className="flex items-center gap-2 text-xs text-zinc-400">
              <span className="flex-1">{t("templates.revision", { n: h.revision })} · {h.updated_by ?? ""} · {h.updated_at?.slice(0, 16) ?? ""}</span>
              <button type="button" disabled={busy} onClick={() => onRevert(h.revision)}
                className="rounded-[4px] px-2 py-0.5 hover:bg-white/5 hover:text-[#e8eef8]">{t("templates.actions.revert")}</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
