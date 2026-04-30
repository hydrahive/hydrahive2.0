import { useTranslation } from "react-i18next"
import { AgentSelect, Field, Select, TextInput } from "./_helpers"
import type { FormProps } from "./_helpers"

export function GitEventForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelService")}>
        <Select field="channel" params={params} onChange={onChange} defaultValue="both"
          options={[
            { value: "both", label: "GitHub + Gitea" },
            { value: "github", label: "GitHub" },
            { value: "gitea", label: "Gitea" },
          ]} />
      </Field>
      <Field label={t("labelEventType")}>
        <Select field="git_event" params={params} onChange={onChange} defaultValue="push"
          options={[
            { value: "push", label: "Push" },
            { value: "pull_request", label: "Pull Request" },
            { value: "issues", label: "Issue" },
            { value: "issue_comment", label: t("optionIssueComment") },
            { value: "release", label: "Release" },
          ]} />
      </Field>
      <Field label={t("labelRepoFilter")} hint={t("allRepos")}>
        <TextInput field="repo" params={params} onChange={onChange}
          placeholder={t("placeholderRepoExample")} />
      </Field>
      <div className="border-t border-white/10 pt-2">
        <p className="text-[10px] text-white/40 leading-relaxed">
          <strong className="text-white/60">{t("webhookUrls")}</strong><br />
          GitHub: <code className="text-cyan-400">/webhooks/github</code><br />
          Gitea: <code className="text-cyan-400">/webhooks/gitea-butler</code>
        </p>
      </div>
    </div>
  )
}

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

export function MessageReceivedForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelChannel")}>
      <Select field="channel" params={params} onChange={onChange} defaultValue="all"
        options={[
          { value: "all", label: t("allChannels") },
          { value: "whatsapp", label: "WhatsApp" },
          { value: "telegram", label: "Telegram" },
          { value: "discord", label: "Discord" },
          { value: "matrix", label: "Matrix" },
        ]} />
    </Field>
  )
}

const DISCORD_EVENT_OPTS = (t: (k: string) => string) => [
  { value: "reaction_add", label: t("optionReactionAdded") },
  { value: "reaction_remove", label: t("optionReactionRemoved") },
  { value: "member_join", label: t("optionMemberJoined") },
  { value: "member_remove", label: t("optionMemberRemoved") },
  { value: "channel_create", label: t("optionChannelCreated") },
  { value: "channel_delete", label: t("optionChannelDeleted") },
]

export function DiscordEventReceivedForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelEventType")}>
        <Select field="discord_event" params={params} onChange={onChange}
          defaultValue="reaction_add" options={DISCORD_EVENT_OPTS(t)} />
      </Field>
      <Field label={t("labelChannelId")} hint={t("discordChannelIdHint")}>
        <TextInput field="channel_id" params={params} onChange={onChange}
          placeholder={t("allDiscordChannels")} mono />
      </Field>
    </div>
  )
}

export function EmailReceivedForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelImapFolder")}>
        <TextInput field="folder" params={params} onChange={onChange} placeholder="INBOX" />
      </Field>
      <Field label={t("labelSenderFilter")} hint={t("allSenders")}>
        <TextInput field="from_filter" params={params} onChange={onChange}
          placeholder={t("placeholderKeywordOrDomain")} />
      </Field>
    </div>
  )
}

export { DISCORD_EVENT_OPTS }
