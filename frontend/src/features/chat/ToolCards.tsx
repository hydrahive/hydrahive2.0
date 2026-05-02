import { useState } from "react"
import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Wrench } from "lucide-react"
import { useTranslation } from "react-i18next"
import { extractMedia, mediaFromBlocks, MediaPreview } from "./MediaPreview"
import { ShellExecCard } from "./tool_cards/ShellExecCard"
import { WebSearchCard } from "./tool_cards/WebSearchCard"
import { FileSearchCard } from "./tool_cards/FileSearchCard"
import { GitDiffCard } from "./tool_cards/GitDiffCard"
import type { ContentBlock } from "./types"

/** Plugin-Prefix abstreifen: 'plugin__git-stats__git_diff' → 'git_diff'. */
function strip(name: string | undefined): string {
  if (!name) return ""
  const m = name.match(/^plugin__[^_]+(?:[^_]*_)*__(.+)$/)
  return (m ? m[1] : name).toLowerCase()
}

function specializedCard(toolName: string | undefined, content: string, isError?: boolean) {
  const n = strip(toolName)
  if (n === "shell_exec") return <ShellExecCard content={content} isError={isError} />
  if (n === "web_search") return <WebSearchCard content={content} />
  if (n === "file_search") return <FileSearchCard content={content} />
  if (n === "git_diff") return <GitDiffCard content={content} />
  return null
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`
}

export function ToolUseCard({
  block,
  defaultOpen = false,
}: {
  block: ContentBlock & { type: "tool_use" }
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-violet-500/20 bg-violet-500/[6%] px-3 py-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 text-xs text-violet-300 font-mono text-left"
      >
        <Wrench size={12} />
        <span className="flex-1">{block.name}</span>
        {block.duration_ms !== undefined && (
          <span className="text-[10.5px] text-violet-400/60 tabular-nums">{formatDuration(block.duration_ms)}</span>
        )}
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </button>
      {open && (
        <pre className="mt-1.5 text-xs text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(block.input, null, 2)}
        </pre>
      )}
    </div>
  )
}

const COLLAPSE_THRESHOLD_CHARS = 300
const COLLAPSE_THRESHOLD_LINES = 8

export function ToolResultCard({ block }: { block: ContentBlock & { type: "tool_result" } }) {
  const { t } = useTranslation("chat")
  const content = block.content || ""
  const media = block.media && block.media.length > 0
    ? mediaFromBlocks(block.media) : extractMedia(content)
  const special = specializedCard(block.tool_name, content, block.is_error)

  // Spezialisierte Card-Renderer für bekannte Tools (shell_exec, web_search, …).
  // Fallback: generisches Pre-Block.
  if (special) {
    return (
      <div className="ml-11 space-y-2">
        {special}
        <MediaPreview media={media} />
        {block.duration_ms !== undefined && (
          <div className="text-[10.5px] text-zinc-500 tabular-nums px-1">
            {formatDuration(block.duration_ms)}
          </div>
        )}
      </div>
    )
  }

  const lineCount = content.split("\n").length
  const isLong = content.length > COLLAPSE_THRESHOLD_CHARS || lineCount > COLLAPSE_THRESHOLD_LINES
  const [open, setOpen] = useState(!isLong)
  const Icon = block.is_error ? AlertCircle : CheckCircle2
  const color = block.is_error ? "rose" : "emerald"

  return (
    <div className={`rounded-lg border border-${color}-500/15 bg-${color}-500/[4%] px-3 py-2 ml-11 space-y-2`}>
      <div className="flex items-center gap-2">
        <Icon size={13} className={`text-${color}-400 flex-shrink-0`} />
        {isLong ? (
          <button onClick={() => setOpen(o => !o)}
            className="flex-1 flex items-center gap-1.5 text-left text-[11px] text-zinc-400 hover:text-zinc-200">
            {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            <span>{t("tool_result.collapsed", { chars: content.length, lines: lineCount })}</span>
          </button>
        ) : <div className="flex-1" />}
        {block.duration_ms !== undefined && (
          <span className={`text-[10.5px] text-${color}-400/60 tabular-nums`}>{formatDuration(block.duration_ms)}</span>
        )}
      </div>
      <MediaPreview media={media} />
      {open && (
        <pre className="text-xs text-zinc-300 font-mono overflow-x-auto whitespace-pre-wrap">
          {content}
        </pre>
      )}
    </div>
  )
}

export function ImageBlock({ block }: { block: ContentBlock & { type: "image" } }) {
  const src = block.source.type === "base64"
    ? `data:${block.source.media_type};base64,${block.source.data}`
    : block.source.url
  return (
    <img src={src} alt="" className="max-w-xs max-h-64 rounded-xl object-contain border border-white/10 shadow-md" />
  )
}
