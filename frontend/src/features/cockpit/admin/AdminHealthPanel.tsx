import { useEffect, useState } from "react"
import { CheckCircle2, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { systemApi, type HealthCheck } from "@/features/system/api"
import { CockpitButton } from "../CockpitButton"
import { CockpitPanel } from "../CockpitPanel"

interface ViewProps {
  /** null = noch nicht geladen. */
  checks: HealthCheck[] | null
  onOpenSystem: () => void
  onOpenAgent: () => void
}

/** Zustand auf der Admin-Startseite (Plan admin-cockpit-kompakt): echte Prüfungen statt Erklärtext, Probleme oben. */
export function AdminHealthView({ checks, onOpenSystem, onOpenAgent }: ViewProps) {
  const { t } = useTranslation("system")
  const sortiert = [...(checks ?? [])].sort((a, b) => Number(a.ok) - Number(b.ok))
  const status = checks === null || checks.length === 0 ? undefined : checks.every((c) => c.ok) ? "ok" : "fehler"
  return (
    <CockpitPanel theme="status" title={t("health.title")} eyebrow={t("health.eyebrow")} status={status}>
      {checks === null && <p className="text-xs text-[#9aa7bc]">{t("health.loading")}</p>}
      <ul className="space-y-1">
        {sortiert.map((c, i) => {
          const name = c.name_code ? t(`checks.${c.name_code}`) : (c.name ?? "?")
          const detail = c.detail_code ? t(`checks.${c.detail_code}`, c.params ?? {}) : (c.detail ?? "")
          return (
            <li key={c.name_code ?? c.name ?? i}>
              <button type="button" onClick={onOpenSystem} data-check={name} data-ok={String(c.ok)}
                className="flex w-full items-start gap-2 rounded-[4px] px-2 py-1.5 text-left text-xs hover:bg-s-hebung">
                {c.ok
                  ? <CheckCircle2 size={13} className="mt-px shrink-0 text-emerald-300" aria-hidden="true" />
                  : <XCircle size={13} className="mt-px shrink-0 text-rose-300" aria-hidden="true" />}
                <span className="min-w-0">
                  <span className={`block font-bold ${c.ok ? "text-[#e8eef8]" : "text-rose-200"}`}>{name}</span>
                  {!c.ok && detail && <span className="block text-[#9aa7bc]">{detail}</span>}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <CockpitButton onClick={onOpenAgent} className="mt-3">{t("health.agent")}</CockpitButton>
    </CockpitPanel>
  )
}

/** Lädt die Prüfungen einmal beim Öffnen (kein Dauer-Abfragen auf der Startseite). */
export function AdminHealthPanel(props: Omit<ViewProps, "checks">) {
  const [checks, setChecks] = useState<HealthCheck[] | null>(null)
  useEffect(() => {
    let alive = true
    systemApi.health().then((h) => { if (alive) setChecks(h.checks) }).catch(() => { if (alive) setChecks([]) })
    return () => { alive = false }
  }, [])
  return <AdminHealthView checks={checks} {...props} />
}
