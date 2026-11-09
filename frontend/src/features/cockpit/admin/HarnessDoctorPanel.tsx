import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminPanel } from "./ui"
import { harnessDoctorApi, type HarnessDoctorResult } from "./harnessDoctorApi"
import { scoreTone } from "./harnessDoctorScore"
import { HarnessErrorCauses } from "./HarnessErrorCauses"

export function HarnessDoctorPanel() {
  const { t } = useTranslation("system")
  const [hours, setHours] = useState(168)
  const [data, setData] = useState<HarnessDoctorResult | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    setLoading(true); setError("")
    harnessDoctorApi.read(hours).then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [hours])
  useEffect(() => {
    const timer = window.setTimeout(load, 0)
    return () => window.clearTimeout(timer)
  }, [load])

  return <div className="space-y-5">
    <div className="flex flex-wrap items-center gap-2">
      <p className="mr-auto text-sm text-[#9aa7bc]">{t("harness.subtitle")}</p>
      {[24, 168, 720].map((value) => <button key={value} onClick={() => setHours(value)}
        className={`rounded-md px-2.5 py-1 text-xs ${hours === value ? "bg-white/15 text-white" : "bg-white/5 text-[#9aa7bc]"}`}>
        {value === 24 ? "24 h" : value === 168 ? "7 d" : "30 d"}
      </button>)}
      <button onClick={load} disabled={loading} className="rounded-md bg-white/5 p-1.5 text-[#9aa7bc] hover:text-white">
        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
      </button>
    </div>
    {error && <p className="text-sm text-rose-400">{error}</p>}
    {!data && !error && <p className="text-sm text-[#9aa7bc]">{t("harness.loading")}</p>}
    {data && <>
      <div className="grid gap-3 md:grid-cols-6">
        <div className="rounded-lg border border-white/10 bg-white/[3%] p-4 md:col-span-1">
          <p className="text-[10px] uppercase tracking-wider text-[#9aa7bc]">{t("harness.overall")}</p>
          <p className={`text-4xl font-bold ${scoreTone(data.overall_score)}`}>{data.overall_score}</p>
        </div>
        {data.dimensions.map((dimension) => <div key={dimension.id}
          className="rounded-lg border border-white/10 bg-white/[3%] p-3 md:col-span-1">
          <p className="text-[10px] uppercase tracking-wider text-[#9aa7bc]">{dimension.label}</p>
          <p className={`text-2xl font-semibold ${scoreTone(dimension.score)}`}>{dimension.score}</p>
          <p className="text-[10px] text-[#69778c]">{dimension.findings.length} {t("harness.findings")}</p>
        </div>)}
      </div>
      <AdminPanel title={t("harness.priorities")} bodyClassName="space-y-2">
        {data.priorities.length === 0 && <p className="text-sm text-emerald-400">{t("harness.no_priorities")}</p>}
        {data.priorities.map((finding) => <div key={finding.rule_id} className="rounded-md border border-white/10 p-3">
          <div className="flex items-center gap-2">
            {finding.severity === "critical" ? <AlertTriangle size={14} className="text-rose-400" /> : <CheckCircle2 size={14} className="text-amber-400" />}
            <strong className="text-sm text-white">{finding.title}</strong>
            <span className="ml-auto text-xs text-rose-300">−{finding.deduction}</span>
          </div>
          <p className="mt-1 text-xs text-[#9aa7bc]">{finding.recommendation}</p>
          <p className="mt-1 text-[10px] text-[#69778c]">{finding.rule_id} · {t("harness.actual")}: {String(finding.actual)} · {t("harness.target")}: {finding.target} · {finding.source}</p>
        </div>)}
      </AdminPanel>
      {data.error_causes && <HarnessErrorCauses causes={data.error_causes} />}
      <AdminPanel title={t("harness.outliers")} bodyClassName="overflow-x-auto">
        <table className="w-full text-xs"><thead className="text-left text-[#69778c]"><tr>
          <th className="py-1">Agent</th><th>Typ</th><th className="text-right">Tools</th><th className="text-right">Schemas</th><th className="text-right">Schema-Zeichen</th><th className="text-right">Skills</th>
        </tr></thead><tbody>{data.agent_outliers.map((agent) => <tr key={agent.id} className="border-t border-white/5">
          <td className="py-1.5 text-white">{agent.name}{agent.collection_error ? " ⚠" : ""}</td><td>{agent.type}</td>
          <td className="text-right">{agent.configured_tools}</td><td className="text-right">{agent.tool_schemas}</td>
          <td className="text-right">{agent.tool_schema_chars.toLocaleString()}</td><td className="text-right">{agent.skills}</td>
        </tr>)}</tbody></table>
      </AdminPanel>
      <div className="space-y-1 text-[10px] text-[#69778c]">{data.notes.map((note) => <p key={note}>• {note}</p>)}</div>
    </>}
  </div>
}
