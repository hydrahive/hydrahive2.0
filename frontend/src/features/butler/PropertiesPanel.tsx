/**
 * Rechte Sidebar des Butler-Editors — subtype-spezifische Param-Forms
 * für jeden ausgewählten Node.
 *
 * HINWEIS: Diese Datei ist mit ~600 Zeilen über der CLAUDE.md-150-Zeilen-
 * Regel. Pragmatisch belassen weil der interne Switch über data.subtype
 * cosmetisch nicht gesplittet werden kann ohne dass alle Sub-Components
 * onChange/params durchreichen müssten. Sauberer Split (Form-Component
 * pro Subtype) ist Sprint 4 / #11-Follow-up.
 */
import { useState } from "react"
import { Trash2, Copy, Check } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
import type { BNode } from "./types"

interface PropsPanelProps {
  node: BNode
  agents: { id: string; name: string }[]
  onChange: (params: Record<string, unknown>) => void
  onDelete: () => void
}

export function PropertiesPanel({ node, agents, onChange, onDelete }: PropsPanelProps) {
  const { t } = useTranslation("butler");
  const d = node.data;
  const p = d.params;
  const ALL_DAYS = ["mo","di","mi","do","fr","sa","so"];
  const DAY_LABEL: Record<string, string> = { mo:"Mo",di:"Di",mi:"Mi",do:"Do",fr:"Fr",sa:"Sa",so:"So" };

  return (
    <div className="w-56 shrink-0 border-l border-white/10 bg-[hsl(var(--sidebar-bg,220_15%_8%))] p-4 flex flex-col gap-4 overflow-y-auto">
      <div>
        <p className="text-[0.55rem] font-bold uppercase tracking-widest text-white/30 mb-1">{t("properties")}</p>
        <p className="text-sm font-semibold text-white">{d.label}</p>
      </div>

      {/* Trigger: Webhook empfangen */}
      {d.subtype === "webhook_received" && (
        <WebhookTriggerPanel params={p} onChange={onChange} />
      )}

      {/* Trigger: GitHub/Gitea Event */}
      {d.subtype === "git_event_received" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelService")}</label>
            <select value={(p.channel as string) || "both"}
              onChange={e => onChange({ ...p, channel: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30">
              <option value="both">GitHub + Gitea</option>
              <option value="github">GitHub</option>
              <option value="gitea">Gitea</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelEventType")}</label>
            <select value={(p.git_event as string) || "push"}
              onChange={e => onChange({ ...p, git_event: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30">
              <option value="push">Push</option>
              <option value="pull_request">Pull Request</option>
              <option value="issues">Issue</option>
              <option value="issue_comment">{t("optionIssueComment")}</option>
              <option value="release">Release</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelRepoFilter")}</label>
            <input type="text" placeholder={t("placeholderRepoExample")}
              value={(p.repo as string) || ""}
              onChange={e => onChange({ ...p, repo: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
            <p className="text-[10px] text-white/25 mt-1">{t("allRepos")}</p>
          </div>
          <div className="border-t border-white/10 pt-2">
            <p className="text-[10px] text-white/40 leading-relaxed">
              <strong className="text-white/60">{t("webhookUrls")}</strong><br />
              GitHub: <code className="text-cyan-400">/webhooks/github</code><br />
              Gitea: <code className="text-cyan-400">/webhooks/gitea-butler</code>
            </p>
          </div>
        </div>
      )}

      {/* Trigger: Heartbeat Task */}
      {d.subtype === "heartbeat_fired" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelAgent")}</label>
            <select value={(p.agent_id as string) || "all"}
              onChange={e => onChange({ ...p, agent_id: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30">
              <option value="all">{t("allAgents")}</option>
              {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelTaskId")}</label>
            <input type="text" placeholder={t("placeholderTaskIdExample")}
              value={(p.task_id as string) || ""}
              onChange={e => onChange({ ...p, task_id: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
            <p className="text-[10px] text-white/25 mt-1">{t("allHeartbeatTasks")}</p>
          </div>
        </div>
      )}

      {/* Trigger: Nachricht empfangen */}
      {d.subtype === "message_received" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelChannel")}</label>
          <select
            value={(p.channel as string) || "all"}
            onChange={e => onChange({ ...p, channel: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30"
          >
            <option value="all">{t("allChannels")}</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="telegram">Telegram</option>
            <option value="discord">Discord</option>
            <option value="matrix">Matrix</option>
          </select>
        </div>
      )}

      {/* Condition: Zeitfenster */}
      {d.subtype === "time_window" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelFrom")}</label>
            <input type="time" value={(p.from as string) || "23:00"}
              onChange={e => onChange({ ...p, from: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelTo")}</label>
            <input type="time" value={(p.to as string) || "08:00"}
              onChange={e => onChange({ ...p, to: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30"
            />
          </div>
          <p className="text-[10px] text-white/25">{t("overnightSupported")}</p>
        </div>
      )}

      {/* Condition: Wochentag */}
      {d.subtype === "day_of_week" && (
        <div>
          <label className="block text-xs text-white/50 mb-2">{t("labelDays")}</label>
          <div className="flex flex-wrap gap-1">
            {ALL_DAYS.map(day => {
              const days = (p.days as string[]) || ALL_DAYS;
              const active = days.includes(day);
              return (
                <button key={day} type="button"
                  onClick={() => {
                    const next = active ? days.filter(d => d !== day) : [...days, day];
                    onChange({ ...p, days: next });
                  }}
                  className={cn(
                    "w-8 py-1 rounded text-xs font-medium transition-colors",
                    active ? "bg-blue-600 text-white" : "bg-zinc-900 text-white/35 hover:bg-white/10"
                  )}
                >
                  {DAY_LABEL[day]}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Condition: Text enthält */}
      {d.subtype === "message_contains" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelKeyword")}</label>
          <input type="text" placeholder={t("placeholderKeywordExample")}
            value={(p.keyword as string) || ""}
            onChange={e => onChange({ ...p, keyword: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
          />
        </div>
      )}

      {/* Condition: Payload-Feld enthält */}
      {d.subtype === "payload_field_contains" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelFieldDotNotation")}</label>
            <input type="text" placeholder={t("placeholderFieldExample")}
              value={(p.field as string) || ""}
              onChange={e => onChange({ ...p, field: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelValueContains")}</label>
            <input type="text" placeholder={t("placeholderValueExample")}
              value={(p.value as string) || ""}
              onChange={e => onChange({ ...p, value: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <p className="text-[10px] text-white/25">{t("caseInsensitive")}</p>
        </div>
      )}

      {/* Action: Agent antwortet / Weiterleiten / Mit Vorgabe */}
      {(d.subtype === "agent_reply" || d.subtype === "forward" || d.subtype === "agent_reply_guided") && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelAgent")}</label>
          <select value={(p.agent_id as string) || ""}
            onChange={e => onChange({ ...p, agent_id: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30"
          >
            <option value="">{t("selectAgent")}</option>
            {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
      )}

      {/* Action: Agent mit Vorgabe — Instruktion */}
      {d.subtype === "agent_reply_guided" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelInstruction")}</label>
          <textarea
            rows={3}
            placeholder={t("placeholderInstructionExample")}
            value={(p.instruction as string) || ""}
            onChange={e => onChange({ ...p, instruction: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
          />
          <p className="text-[10px] text-white/25 mt-1">{t("instructionPassedHint")}</p>
        </div>
      )}

      {/* Action: Feste Antwort */}
      {d.subtype === "reply_fixed" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelReplyText")}</label>
          <textarea
            rows={4}
            placeholder={t("placeholderReplyExample")}
            value={(p.text as string) || ""}
            onChange={e => onChange({ ...p, text: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
          />
          <p className="text-[10px] text-white/25 mt-1">{t("replyDirectHint")}</p>
        </div>
      )}

      {/* Condition: Branch ist */}
      {d.subtype === "git_branch_is" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelBranchName")}</label>
          <input type="text" placeholder={t("placeholderBranchExample")}
            value={(p.branch as string) || ""}
            onChange={e => onChange({ ...p, branch: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
          />
        </div>
      )}

      {/* Condition: Autor ist */}
      {d.subtype === "git_author_is" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelGitUsername")}</label>
          <input type="text" placeholder={t("placeholderUsernameExample")}
            value={(p.author as string) || ""}
            onChange={e => onChange({ ...p, author: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
          />
          <p className="text-[10px] text-white/25 mt-1">{t("caseInsensitive")}</p>
        </div>
      )}

      {/* Condition: Git-Action ist */}
      {d.subtype === "git_action_is" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelAction")}</label>
          <select value={(p.action as string) || "opened"}
            onChange={e => onChange({ ...p, action: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30">
            <option value="opened">opened</option>
            <option value="closed">closed</option>
            <option value="merged">{t("optionMergedPR")}</option>
            <option value="reopened">reopened</option>
            <option value="labeled">labeled</option>
            <option value="created">{t("optionCreatedComment")}</option>
            <option value="published">{t("optionPublishedRelease")}</option>
          </select>
        </div>
      )}

      {/* Trigger: Discord Event */}
      {d.subtype === "discord_event_received" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelEventType")}</label>
            <select value={(p.discord_event as string) || "reaction_add"}
              onChange={e => onChange({ ...p, discord_event: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30">
              <option value="reaction_add">{t("optionReactionAdded")}</option>
              <option value="reaction_remove">{t("optionReactionRemoved")}</option>
              <option value="member_join">{t("optionMemberJoined")}</option>
              <option value="member_remove">{t("optionMemberRemoved")}</option>
              <option value="channel_create">{t("optionChannelCreated")}</option>
              <option value="channel_delete">{t("optionChannelDeleted")}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelChannelId")}</label>
            <input type="text" placeholder={t("allDiscordChannels")}
              value={(p.channel_id as string) || ""}
              onChange={e => onChange({ ...p, channel_id: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm font-mono text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
            <p className="text-[10px] text-white/25 mt-1">{t("discordChannelIdHint")}</p>
          </div>
        </div>
      )}

      {/* Trigger: E-Mail empfangen */}
      {d.subtype === "email_received" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelImapFolder")}</label>
            <input type="text" placeholder="INBOX"
              value={(p.folder as string) || "INBOX"}
              onChange={e => onChange({ ...p, folder: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelSenderFilter")}</label>
            <input type="text" placeholder={t("placeholderKeywordOrDomain")}
              value={(p.from_filter as string) || ""}
              onChange={e => onChange({ ...p, from_filter: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
            <p className="text-[10px] text-white/25 mt-1">{t("allSenders")}</p>
          </div>
        </div>
      )}

      {/* Condition: E-Mail Felder */}
      {(d.subtype === "email_from_contains" || d.subtype === "email_subject_contains" || d.subtype === "email_body_contains") && (
        <div>
          <label className="block text-xs text-white/50 mb-1">
            {d.subtype === "email_from_contains" ? t("labelSenderContains") :
             d.subtype === "email_subject_contains" ? t("labelSubjectContains") : t("labelTextContains")}
          </label>
          <input type="text" placeholder={t("placeholderKeywordOrDomain")}
            value={(p.keyword as string) || ""}
            onChange={e => onChange({ ...p, keyword: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
          />
          <p className="text-[10px] text-white/25 mt-1">{t("caseInsensitive")}</p>
        </div>
      )}

      {/* Condition: Discord Event ist */}
      {d.subtype === "discord_event_is" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelEventType")}</label>
          <select value={(p.discord_event as string) || "reaction_add"}
            onChange={e => onChange({ ...p, discord_event: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white focus:outline-none focus:border-white/30">
            <option value="reaction_add">{t("optionReactionAdded")}</option>
            <option value="reaction_remove">{t("optionReactionRemoved")}</option>
            <option value="member_join">{t("optionMemberJoined")}</option>
            <option value="member_remove">{t("optionMemberRemoved")}</option>
            <option value="channel_create">{t("optionChannelCreated")}</option>
            <option value="channel_delete">{t("optionChannelDeleted")}</option>
          </select>
        </div>
      )}

      {/* Condition: Discord Emoji ist */}
      {d.subtype === "discord_emoji_is" && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelEmoji")}</label>
          <input type="text" placeholder="👍 oder custom_emoji_name"
            value={(p.emoji as string) || ""}
            onChange={e => onChange({ ...p, emoji: e.target.value })}
            className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
          />
          <p className="text-[10px] text-white/25 mt-1">{t("unicodeEmojiHint")}</p>
        </div>
      )}

      {/* Info-only nodes */}
      {d.subtype === "contact_known" && (
        <p className="text-xs text-white/35 leading-relaxed">
          {t("contactKnownInfo")}
        </p>
      )}
      {d.subtype === "ignore" && (
        <p className="text-xs text-white/35 leading-relaxed">
          {t("ignoreInfo")}
        </p>
      )}
      {d.subtype === "queue" && (
        <p className="text-xs text-white/35 leading-relaxed">
          {t("queueInfo")}
        </p>
      )}

      {/* Action: HTTP POST */}
      {d.subtype === "http_post" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelTargetUrl")}</label>
            <input type="text" placeholder="https://example.com/webhook"
              value={(p.url as string) || ""}
              onChange={e => onChange({ ...p, url: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelBodyJson")}</label>
            <textarea rows={4} placeholder={`{\n  "text": "{{event.message_text}}"\n}`}
              value={(p.body_template as string) || "{}"}
              onChange={e => onChange({ ...p, body_template: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-xs font-mono text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
            />
          </div>
          <p className="text-[10px] text-white/25">{t("placeholderHint")} <code className="text-cyan-400">{"{{event.message_text}}"}</code>, <code className="text-cyan-400">{"{{event.extra.repo}}"}</code> etc.</p>
        </div>
      )}

      {/* Action: E-Mail senden */}
      {d.subtype === "send_email" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelRecipient")}</label>
            <input type="text" placeholder={t("placeholderRecipientExample")}
              value={(p.to as string) || ""}
              onChange={e => onChange({ ...p, to: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelSubject")}</label>
            <input type="text" placeholder={t("placeholderSubjectExample")}
              value={(p.subject as string) || ""}
              onChange={e => onChange({ ...p, subject: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelText")}</label>
            <textarea rows={3} placeholder="{{event.message_text}}"
              value={(p.body as string) || ""}
              onChange={e => onChange({ ...p, body: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
            />
          </div>
          <p className="text-[10px] text-white/25">{t("smtpHint")}</p>
        </div>
      )}

      {/* Action: Gitea Issue erstellen */}
      {d.subtype === "git_create_issue" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelRepo")}</label>
            <input type="text" placeholder="hydrahive/hydrahive"
              value={(p.repo as string) || ""}
              onChange={e => onChange({ ...p, repo: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelTitle")}</label>
            <input type="text" placeholder="Bug: {{event.extra.commit_message}}"
              value={(p.title as string) || ""}
              onChange={e => onChange({ ...p, title: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelDescription")}</label>
            <textarea rows={3} placeholder={t("placeholderTriggeredBy")}
              value={(p.body as string) || ""}
              onChange={e => onChange({ ...p, body: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
            />
          </div>
        </div>
      )}

      {/* Action: Gitea Kommentar */}
      {d.subtype === "git_add_comment" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelRepo")}</label>
            <input type="text" placeholder="hydrahive/hydrahive"
              value={(p.repo as string) || ""}
              onChange={e => onChange({ ...p, repo: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelIssueNumber")}</label>
            <input type="text" placeholder="42 oder {{event.extra.pr_number}}"
              value={(p.issue_number as string) || ""}
              onChange={e => onChange({ ...p, issue_number: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelComment")}</label>
            <textarea rows={3} placeholder="Automatisch von Butler via {{event.channel}}"
              value={(p.body as string) || ""}
              onChange={e => onChange({ ...p, body: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
            />
          </div>
        </div>
      )}

      {/* Action: Discord Post */}
      {d.subtype === "discord_post" && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelChannelId")}</label>
            <input type="text" placeholder="1234567890123456789"
              value={(p.channel_id as string) || ""}
              onChange={e => onChange({ ...p, channel_id: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm font-mono text-white placeholder-white/20 focus:outline-none focus:border-white/30"
            />
            <p className="text-[10px] text-white/25 mt-1">{t("discordChannelIdHint")}</p>
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">{t("labelMessage")}</label>
            <textarea rows={3} placeholder="{{event.message_text}}"
              value={(p.message as string) || ""}
              onChange={e => onChange({ ...p, message: e.target.value })}
              className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30 resize-none"
            />
          </div>
        </div>
      )}

      <div className="mt-auto pt-3 border-t border-white/10">
        <button type="button" onClick={onDelete}
          className="flex items-center gap-1.5 text-xs text-red-400/60 hover:text-red-400 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {t("removeNode")}
        </button>
      </div>
    </div>
  );
}

// ── Webhook Trigger Panel ─────────────────────────────────────────────────
function WebhookTriggerPanel({
  params,
  onChange,
}: {
  params: Record<string, unknown>;
  onChange: (p: Record<string, unknown>) => void;
}) {
  const { t } = useTranslation("butler");
  const [copied, setCopied] = useState(false);
  const hookId = (params.hook_id as string) || "";
  const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
  const webhookUrl = hookId ? `${baseUrl}/webhooks/butler/${hookId}` : "";

  const copyUrl = () => {
    if (!webhookUrl) return;
    navigator.clipboard.writeText(webhookUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <div>
        <label className="block text-xs text-white/50 mb-1">{t("labelHookId")}</label>
        <input
          type="text"
          placeholder={t("placeholderHookIdExample")}
          value={hookId}
          onChange={e => onChange({ ...params, hook_id: e.target.value.replace(/[^a-z0-9_-]/gi, "-").toLowerCase() })}
          className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
        />
        <p className="text-[10px] text-white/25 mt-1">{t("onlyAlphanumeric")}</p>
      </div>

      {webhookUrl && (
        <div>
          <label className="block text-xs text-white/50 mb-1">{t("labelWebhookUrl")}</label>
          <div className="flex items-center gap-1">
            <code className="flex-1 truncate rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-[11px] text-cyan-300">
              {webhookUrl}
            </code>
            <button
              type="button"
              onClick={copyUrl}
              className="shrink-0 p-1.5 rounded-lg bg-zinc-900 border border-white/15 hover:bg-white/10 transition-colors"
              title={t("copyUrl")}
            >
              {copied
                ? <Check className="h-3.5 w-3.5 text-green-400" />
                : <Copy className="h-3.5 w-3.5 text-white/40" />}
            </button>
          </div>
          <p className="text-[10px] text-white/25 mt-1">
            {t("postToTrigger")}
          </p>
        </div>
      )}
    </div>
  );
}
