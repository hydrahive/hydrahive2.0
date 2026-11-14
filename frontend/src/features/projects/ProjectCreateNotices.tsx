import { AlertTriangle, ExternalLink } from "lucide-react"
import { useTranslation } from "react-i18next"
import { type CreateWarning, createWarningKey, isTemplateLink, type TemplateHint } from "./createWarnings"

/** Warnungen nach dem Anlegen bzw. Hinweis bei abgelehntem Anlegen – mit Anleitung und Link zur Template-Seite. */
export function ProjectCreateNotices({ warnings = [], hint = null, onContinue }: {
  warnings?: CreateWarning[]; hint?: TemplateHint | null; onContinue?: () => void
}) {
  const { t } = useTranslation("projects")
  const link = hint?.link ?? warnings.map((w) => w.link).find(isTemplateLink)
  if (!hint && warnings.length === 0) return null
  return (
    <div role={hint ? "alert" : "status"}
      className="space-y-2 rounded-[4px] border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
      {!hint && (
        <p className="flex items-center gap-2 font-bold"><AlertTriangle size={15} />{t("create_warning.title")}</p>
      )}
      {warnings.map((w, i) => (
        <p key={`${w.code}-${w.model}-${i}`}>{t(createWarningKey(w.code), { template: w.template, model: w.model })}</p>
      ))}
      {hint && <p>{t("create_warning.primary_how_to")}</p>}
      <p className="text-xs text-amber-200/90">{t("create_warning.how_to")}</p>
      <div className="flex flex-wrap gap-2">
        {link && (
          <a href={link} className="inline-flex items-center gap-1.5 rounded-[4px] border border-amber-400/50 px-3 py-1.5
            text-xs font-bold text-amber-100 hover:bg-amber-500/20">
            <ExternalLink size={13} />{t("create_warning.open_templates")}
          </a>
        )}
        {onContinue && (
          <button type="button" onClick={onContinue}
            className="rounded-[4px] border border-s-rand px-3 py-1.5 text-xs font-bold text-[#e8eef8] hover:bg-s-tief">
            {t("create_warning.continue")}
          </button>
        )}
      </div>
    </div>
  )
}
