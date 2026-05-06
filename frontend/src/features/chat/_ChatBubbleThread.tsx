/* Bubble-Thread für Card-Layout (Buddy-Look) — volle Ausstattung:
   AssistantFooter (Tokens/Cost/Modell), Edit am User, Raw-JSON-Toggle. */
import { Bot, Check, Code, Copy, RotateCw, User, Volume2, VolumeX } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  ActionBarPrimitive,
  BranchPickerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  getExternalStoreMessages,
  useMessage,
} from "@assistant-ui/react"
import { AssistantFooter, BubbleHeader } from "./BubbleMeta"
import { CompactionBlock } from "./CompactionBlock"
import { Markdown } from "./Markdown"
import { ThinkingBlock } from "./ThinkingBlock"
import { ImageBlock, ToolResultCard, ToolUseCard } from "./ToolCards"
import { extractMedia, MediaPreview } from "./MediaPreview"
import { useVoiceOutput } from "./useVoiceOutput"
import type { ContentBlock, Message } from "./types"

function ChatUserMessage() {
  const { t } = useTranslation("chat")
  const msg = useMessage()
  const originals = getExternalStoreMessages<Message>(msg)
  const original = originals[0]
  const blocks: ContentBlock[] = original && Array.isArray(original.content) ? original.content : []
  const text = typeof original?.content === "string"
    ? original.content
    : blocks.find((b) => b.type === "text")?.text ?? ""
  const images = blocks.filter((b) => b.type === "image")
  const toolResults = blocks.filter((b) => b.type === "tool_result")
  const [copied, setCopied] = useState(false)

  if (toolResults.length > 0) {
    return (
      <MessagePrimitive.Root className="space-y-1.5 py-1">
        {toolResults.map((tr, i) => (
          <ToolResultCard key={i} block={tr as ContentBlock & { type: "tool_result" }} />
        ))}
      </MessagePrimitive.Root>
    )
  }

  return (
    <MessagePrimitive.Root className="flex items-start gap-3 justify-end py-1">
      <div className="max-w-[80%] space-y-1">
        {original && <BubbleHeader createdAt={original.created_at} align="right" />}
        {images.map((b, i) => <ImageBlock key={i} block={b as ContentBlock & { type: "image" }} />)}
        {text && (
          <>
            <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-violet-500/15 border border-violet-500/40 text-violet-50 text-sm whitespace-pre-wrap">
              {text}
            </div>
            <div className="flex items-center justify-end gap-1.5">
              <ActionBarPrimitive.Edit asChild>
                <button title={t("bubble.edit")} className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                  ✎
                </button>
              </ActionBarPrimitive.Edit>
              <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
                title={t("bubble.copy")} className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
              </button>
            </div>
          </>
        )}
      </div>
      <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
        <User size={14} className="text-zinc-400" />
      </div>
    </MessagePrimitive.Root>
  )
}

function ChatAssistantMessage() {
  const { t } = useTranslation("chat")
  const msg = useMessage()
  const originals = getExternalStoreMessages<Message>(msg)
  const original = originals[0]
  const blocks: ContentBlock[] = original ? Array.isArray(original.content) ? original.content : [] : []
  const isLive = msg.status?.type === "running"
  const isLocalCmd = original?.id?.startsWith("local-cmd-") ?? false
  const isSlashCmd = original?.metadata?.source === "slash_command"
  const fullText = blocks.filter((b) => b.type === "text").map((b) => (b as { type: "text"; text: string }).text ?? "").join(" ")
  const [copied, setCopied] = useState(false)
  const [showRaw, setShowRaw] = useState(false)
  const tts = useVoiceOutput()
  const monoMode = isLocalCmd || isSlashCmd

  return (
    <MessagePrimitive.Root className="flex items-start gap-3 py-1">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 bg-zinc-800 ${isLive ? "animate-pulse" : ""}`}>
        <Bot size={14} className="text-emerald-400" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {original && <BubbleHeader createdAt={original.created_at} align="left" />}
        {showRaw ? (
          <pre className="text-xs text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap bg-white/[3%] border border-white/[6%] rounded-lg p-3">
            {JSON.stringify(original?.content ?? blocks, null, 2)}
          </pre>
        ) : blocks.map((b, i) => {
          if (b.type === "text" && b.text) return (
            <div key={i} className="px-4 py-2.5 rounded-2xl rounded-tl-md bg-emerald-500/10 border border-emerald-500/25 text-emerald-50">
              {monoMode
                ? <pre className="font-mono text-xs whitespace-pre-wrap break-words m-0">{b.text}</pre>
                : <Markdown text={b.text} />}
            </div>
          )
          if (b.type === "thinking" && b.thinking) return <ThinkingBlock key={i} text={b.thinking} />
          if (b.type === "image") return <ImageBlock key={i} block={b} />
          if (b.type === "tool_use") return <ToolUseCard key={i} block={b} defaultOpen={isLive} />
          if (b.type === "tool_result") return <ToolResultCard key={i} block={b} />
          return null
        })}
        {original && <MediaPreview media={extractMedia(fullText)} />}
        {original && !monoMode && <AssistantFooter metadata={original.metadata} />}
        {msg.branchCount > 1 && (
          <div className="flex items-center gap-1 text-[11px] text-zinc-500">
            <BranchPickerPrimitive.Previous asChild>
              <button className="hover:text-zinc-300 transition-colors px-1">◀</button>
            </BranchPickerPrimitive.Previous>
            <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
            <BranchPickerPrimitive.Next asChild>
              <button className="hover:text-zinc-300 transition-colors px-1">▶</button>
            </BranchPickerPrimitive.Next>
          </div>
        )}
        <div className="flex items-center gap-1.5 flex-wrap">
          {fullText && (
            <button onClick={() => tts.speaking ? tts.stop() : tts.speak(fullText)}
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${tts.speaking ? "text-rose-300 bg-rose-500/15 border-rose-500/30" : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"}`}>
              {tts.speaking ? <VolumeX size={12} /> : <Volume2 size={12} />}
            </button>
          )}
          {fullText && (
            <button onClick={() => { navigator.clipboard.writeText(fullText); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%] transition-colors">
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            </button>
          )}
          {!isLive && !isSlashCmd && (
            <ActionBarPrimitive.Reload asChild>
              <button className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/30 transition-colors">
                <RotateCw size={12} /> {t("bubble.retry")}
              </button>
            </ActionBarPrimitive.Reload>
          )}
          <button onClick={() => setShowRaw((r) => !r)} title="Raw JSON"
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${showRaw ? "text-amber-300 bg-amber-500/15 border-amber-500/30" : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"}`}>
            <Code size={12} />
          </button>
        </div>
      </div>
    </MessagePrimitive.Root>
  )
}

function ChatSystemMessage() {
  const msg = useMessage()
  const originals = getExternalStoreMessages<Message>(msg)
  const original = originals[0]
  if (!original || original.role !== "compaction") return null
  return <CompactionBlock message={original} />
}

export function ChatBubbleThread() {
  return (
    <ThreadPrimitive.Root className="flex-1 overflow-hidden flex flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <ThreadPrimitive.Messages
          components={{
            UserMessage: ChatUserMessage,
            AssistantMessage: ChatAssistantMessage,
            SystemMessage: ChatSystemMessage,
          }}
        />
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  )
}
