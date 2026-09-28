import { useTranslation } from "react-i18next"
import { AgentSelect, Field, Select, TextInput } from "./_helpers"
import type { FormProps } from "./_helpers"

export function HeartbeatForm({ params, onChange, agents }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelAgent")}>
        <AgentSelect field="agent_id" params={params} onChange={onChange}
          agents={agents} placeholder={t("allAgents")} allowAll />
      </Field>
      <Field label={t("labelTaskId")} hint={t("allHeartbeatTasks")}>
        <TextInput field="task_id" params={params} onChange={onChange}
          placeholder={t("placeholderTaskIdExample")} />
      </Field>
    </div>
  )
}

export function CronForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelCron")} hint={t("cronUtcHint")}>
      <TextInput field="cron" params={params} onChange={onChange}
        placeholder="0 8 * * *" mono />
    </Field>
  )
}

export function MessageReceivedForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelChannel")}>
      <Select field="channel" params={params} onChange={onChange} defaultValue="all"
        options={[
          { value: "all", label: t("allChannels") },
          { value: "whatsapp", label: "WhatsApp" },
          { value: "discord", label: "Discord" },
          { value: "email", label: "E-Mail" },
        ]} />
    </Field>
  )
}
