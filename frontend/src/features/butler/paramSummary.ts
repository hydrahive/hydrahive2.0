/**
 * Kurzbeschreibung pro Subtype für die Node-Vorschau auf dem Canvas.
 * Wird vom NodeRenderer aufgerufen — `t` ist der i18n-Translator.
 */
export function paramSummary(
  subtype: string,
  params: Record<string, unknown>,
  t: (key: string) => string,
): string {
  switch (subtype) {
    case "message_received": {
      const ch = (params.channel as string) || "all"
      return ch === "all" ? t("allChannels") : ch.charAt(0).toUpperCase() + ch.slice(1)
    }
    case "webhook_received":
      return (params.hook_id as string) ? `/${params.hook_id}` : t("hookIdMissing")
    case "heartbeat_fired": {
      const agent = (params.agent_id as string) || "all"
      const task  = (params.task_id as string) || ""
      return agent === "all"
        ? (task ? `${t("allAgents")} · ${task}` : t("allAgents"))
        : (task ? `${agent} · ${task}` : agent)
    }
    case "git_event_received": {
      const evt = (params.git_event as string) || "push"
      const ch  = (params.channel as string) || "both"
      const repo = (params.repo as string) || ""
      return `${ch === "both" ? "GitHub/Gitea" : ch} · ${evt}${repo ? ` · ${repo}` : ""}`
    }
    case "payload_field_contains":
      return params.field ? `${params.field} ≈ "${params.value}"` : "—"
    case "git_branch_is":
      return (params.branch as string) || "—"
    case "git_author_is":
      return (params.author as string) || "—"
    case "git_action_is":
      return (params.action as string) || "—"
    case "time_window":
      return `${params.from ?? "?"}–${params.to ?? "?"}`
    case "day_of_week": {
      const days = (params.days as string[]) ?? []
      return days.map((d) => d.charAt(0).toUpperCase() + d.slice(1)).join(" ")
    }
    case "message_contains":
      return params.keyword ? `"${params.keyword}"` : "—"
    case "agent_reply":
    case "forward":
      return (params.agent_id as string) || "—"
    case "agent_reply_guided":
      return (params.instruction as string)?.slice(0, 30) || "—"
    case "reply_fixed":
      return (params.text as string)?.slice(0, 30) || "—"
    case "http_post":
      return (params.url as string)?.slice(0, 35) || t("urlMissing")
    case "send_email":
      return (params.to as string) || t("toMissing")
    case "git_create_issue":
      return (params.repo as string)
        ? `${params.repo}: ${(params.title as string)?.slice(0, 20) || ""}`
        : t("repoMissing")
    case "git_add_comment":
      return (params.repo as string)
        ? `${params.repo} #${params.issue_number || "?"}`
        : t("repoMissing")
    case "discord_post":
      return (params.channel_id as string) ? `#${params.channel_id}` : t("channelMissing")
    case "discord_event_received": {
      const evt = (params.discord_event as string) || "reaction_add"
      const ch  = (params.channel_id as string) || ""
      return ch ? `${evt} · #${ch}` : evt
    }
    case "email_received": {
      const folder = (params.folder as string) || "INBOX"
      const from   = (params.from_filter as string) || ""
      return from ? `${folder} · ${t("fromLabel")} ${from}` : folder
    }
    case "email_from_contains":
    case "email_subject_contains":
    case "email_body_contains":
      return (params.keyword as string) ? `"${params.keyword}"` : "—"
    case "discord_event_is":
      return (params.discord_event as string) || "—"
    case "discord_emoji_is":
      return (params.emoji as string) || "—"
    default:
      return ""
  }
}
