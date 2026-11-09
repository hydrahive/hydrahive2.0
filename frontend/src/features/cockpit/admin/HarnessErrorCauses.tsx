import { useTranslation } from "react-i18next"
import { AdminPanel } from "./ui"
import type { HarnessErrorCauses as Causes } from "./harnessDoctorApi"

/** Häufigste Tool-Fehlerursachen (Task 2123ef7e). Pfade, IDs und Zahlen sind serverseitig maskiert. */
export function HarnessErrorCauses({ causes }: { causes: Causes }) {
  const { t } = useTranslation("system")
  return <AdminPanel title={t("harness.error_causes")} bodyClassName="space-y-2">
    <p className="text-[10px] text-[#69778c]">
      {t("harness.error_causes_summary", {
        errors: causes.errors_total, interrupted: causes.interrupted, cancelled: causes.cancelled,
      })}
    </p>
    {causes.clusters.length === 0 && <p className="text-sm text-emerald-400">{t("harness.no_error_causes")}</p>}
    {causes.clusters.length > 0 && <table className="w-full text-xs"><thead className="text-left text-[#69778c]"><tr>
      <th className="py-1 text-right">{t("harness.count")}</th><th className="text-right">{t("harness.share")}</th>
      <th className="pl-3">{t("harness.tool")}</th><th>{t("harness.cause")}</th>
    </tr></thead><tbody>{causes.clusters.map((cluster) =>
      <tr key={`${cluster.tool}|${cluster.cause}`} className="border-t border-white/5">
        <td className="py-1.5 text-right text-white">{cluster.count}</td>
        <td className="text-right text-[#9aa7bc]">{Math.round(cluster.share * 100)} %</td>
        <td className="pl-3 font-mono text-[#9aa7bc]">{cluster.tool}</td>
        <td className="break-all text-white">{cluster.cause}</td>
      </tr>)}</tbody></table>}
  </AdminPanel>
}
