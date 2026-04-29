import { Wrench, User, Bot, AlertCircle, CheckCircle2, Archive, ChevronDown, ChevronRight, Volume2, VolumeX } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "./Markdown"
import { useVoiceOutput } from "./useVoiceOutput"
import type { ContentBlock, Message } from "./types"

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === "compaction") {
    return <CompactionBlock message={message} />
  }

  const blocks = normalizeContent(message.content)

  if (message.role === "user") {
    const text = blocks.find((b) => b.type === "text")?.text ?? ""
    const images = blocks.filter((b) => b.type === "image")
    const tool_results = blocks.filter((b) => b.type === "tool_result")

    if (tool_results.length > 0) {
      return (
        <div className="space-y-1.5">
          {tool_results.map((tr, i) => <ToolResultCard key={i} block={tr as ContentBlock & { type: "tool_result" }} />)}
        </div>
      )
    }

    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="max-w-[80%] space-y-2">
          {images.map((b, i) => <ImageBlock key={i} block={b as ContentBlock & { type: "image" }} />)}
          {text && (
            <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-gradient-to-br from-indigo-600 to-violet-600 text-white text-sm whitespace-pre-wrap shadow-lg shadow-violet-900/20">
              {text}
            </div>
          )}
        </div>
        <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
          <User size={14} className="text-zinc-400" />
        </div>
      </div>
    )
  }

  const tts = useVoiceOutput()
  const fullText = blocks.filter((b) => b.type === "text").map((b) => b.text ?? "").join(" ")

  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-violet-900/30">
        <Bot size={14} className="text-white" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {blocks.map((b, i) => {
          if (b.type === "text" && b.text)
            return <Markdown key={i} text={b.text} />
          if (b.type === "tool_use") return <ToolUseCard key={i} block={b} />
          return null
        })}
        {fullText && (
          <button
            onClick={() => tts.speaking ? tts.stop() : tts.speak(fullText)}
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${
              tts.speaking
                ? "text-rose-300 bg-rose-500/15 border-rose-500/30 hover:bg-rose-500/25"
                : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"
            }`}
            title={tts.speaking ? "Stop" : "Vorlesen"}
          >
            {tts.speaking ? <VolumeX size={12} /> : <Volume2 size={12} />}
            <span>{tts.speaking ? "Stop" : "Vorlesen"}</span>
          </button>
        )}
      </div>
    </div>
  )
}

function ToolUseCard({ block }: { block: ContentBlock & { type: "tool_use" } }) {
  return (
    <div className="rounded-lg border border-violet-500/20 bg-violet-500/[6%] px-3 py-2">
      <div className="flex items-center gap-2 text-xs text-violet-300 font-mono">
        <Wrench size={12} />
        <span>{block.name}</span>
      </div>
      <pre className="mt-1.5 text-xs text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap">
        {JSON.stringify(block.input, null, 2)}
      </pre>
    </div>
  )
}

function ToolResultCard({ block }: { block: ContentBlock & { type: "tool_result" } }) {
  const Icon = block.is_error ? AlertCircle : CheckCircle2
  const color = block.is_error ? "rose" : "emerald"
  return (
    <div className={`flex items-start gap-2 rounded-lg border border-${color}-500/15 bg-${color}-500/[4%] px-3 py-2 ml-11`}>
      <Icon size={13} className={`text-${color}-400 mt-0.5 flex-shrink-0`} />
      <pre className={`text-xs text-zinc-300 font-mono overflow-x-auto whitespace-pre-wrap flex-1`}>
        {block.content}
      </pre>
    </div>
  )
}

function ImageBlock({ block }: { block: ContentBlock & { type: "image" } }) {
  const src = block.source.type === "base64"
    ? `data:${block.source.media_type};base64,${block.source.data}`
    : block.source.url
  return (
    <img src={src} alt="" className="max-w-xs max-h-64 rounded-xl object-contain border border-white/10 shadow-md" />
  )
}

function normalizeContent(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === "string") return [{ type: "text", text: content }]
  return content
}

function CompactionBlock({ message }: { message: Message }) {
  const { t, i18n } = useTranslation("chat")
  const [open, setOpen] = useState(false)
  const meta = message.metadata as { tokensBefore?: number; readFiles?: string[]; modifiedFiles?: string[] }
  const summary = typeof message.content === "string" ? message.content : JSON.stringify(message.content)
  const tokensSaved = meta.tokensBefore ?? 0
  const readCount = meta.readFiles?.length ?? 0
  const modifiedCount = meta.modifiedFiles?.length ?? 0
  const stats = tokensSaved > 0
    ? t("compaction_block.stats_with_tokens", {
        tokens: tokensSaved.toLocaleString(i18n.language),
        read: readCount,
        modified: modifiedCount,
      })
    : t("compaction_block.stats", { read: readCount, modified: modifiedCount })

  return (
    <div className="my-2 rounded-xl border border-amber-500/20 bg-amber-500/[5%]">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-amber-500/[3%] transition-colors">
        {open ? <ChevronDown size={14} className="text-amber-300" /> : <ChevronRight size={14} className="text-amber-300" />}
        <Archive size={14} className="text-amber-300" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-amber-200">
            {t("compaction_block.title")}
          </p>
          <p className="text-[10.5px] text-amber-400/70 mt-0.5">
            {stats}
          </p>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1 space-y-2 border-t border-amber-500/10">
          {meta.readFiles && meta.readFiles.length > 0 && (
            <div>
              <p className="text-[10.5px] font-semibold uppercase tracking-wider text-amber-400/60 mb-1">{t("compaction_block.files_read")}</p>
              <pre className="text-[11px] text-amber-200/80 font-mono whitespace-pre-wrap">{meta.readFiles.join("\n")}</pre>
            </div>
          )}
          {meta.modifiedFiles && meta.modifiedFiles.length > 0 && (
            <div>
              <p className="text-[10.5px] font-semibold uppercase tracking-wider text-amber-400/60 mb-1">{t("compaction_block.files_modified")}</p>
              <pre className="text-[11px] text-amber-200/80 font-mono whitespace-pre-wrap">{meta.modifiedFiles.join("\n")}</pre>
            </div>
          )}
          <div>
            <p className="text-[10.5px] font-semibold uppercase tracking-wider text-amber-400/60 mb-1">{t("compaction_block.summary")}</p>
            <pre className="text-xs text-amber-100/90 whitespace-pre-wrap leading-relaxed">{summary}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
