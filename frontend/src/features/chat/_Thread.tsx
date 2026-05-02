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
import { ImageBlock, ToolResultCard, ToolUseCard } from "./ToolCards"
import { extractMedia, MediaPreview } from "./MediaPreview"
import { useVoiceOutput } from "./useVoiceOutput"
import type { ContentBlock, Message } from "./types"

// ─── User Message ────────────────────────────────────────────────────────────

function HydraUserMessage() {
  const { t } = useTranslation("chat")
  const msg = useMessage()
  const originals = getExternalStoreMessages<Message>(msg)
  const original = originals[0]
  const blocks: ContentBlock[] = original
    ? Array.isArray(original.content) ? original.content : []
    : []
  const text = blocks.find((b) => b.type === "text")?.text ?? ""
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
            <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-gradient-to-br from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] text-white text-sm whitespace-pre-wrap shadow-lg shadow-black/30">
              {text}
            </div>
            <div className="flex items-center justify-end gap-1.5">
              <ActionBarPrimitive.Edit asChild>
                <button title={t("bubble.edit")} className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                  <Check size={11} className="hidden group-data-[editing]:block text-violet-400" />
                  <span className="group-data-[editing]:hidden">✎</span>
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

// ─── Assistant Message ────────────────────────────────────────────────────────

function HydraAssistantMessage() {
  const { t } = useTranslation("chat")
  const msg = useMessage()
  const originals = getExternalStoreMessages<Message>(msg)
  const original = originals[0]
  const blocks: ContentBlock[] = original
    ? Array.isArray(original.content) ? original.content : []
    : []
  const isLive = msg.status?.type === "running"
  const fullText = blocks.filter((b) => b.type === "text").map((b) => (b as any).text ?? "").join(" ")
  const [copied, setCopied] = useState(false)
  const [showRaw, setShowRaw] = useState(false)
  const tts = useVoiceOutput()

  return (
    <MessagePrimitive.Root className="flex items-start gap-3 py-1">
      <div className={`w-8 h-8 rounded-full bg-gradient-to-br from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] flex items-center justify-center flex-shrink-0 shadow-md shadow-black/30 ${isLive ? "animate-pulse" : ""}`}>
        <Bot size={14} className="text-white" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {original && <BubbleHeader createdAt={original.created_at} align="left" />}
        {showRaw ? (
          <pre className="text-xs text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap bg-white/[3%] border border-white/[6%] rounded-lg p-3">
            {JSON.stringify(original?.content ?? blocks, null, 2)}
          </pre>
        ) : (
          blocks.map((b, i) => {
            if (b.type === "text" && b.text) return <Markdown key={i} text={b.text} />
            if (b.type === "image") return <ImageBlock key={i} block={b} />
            if (b.type === "tool_use") return <ToolUseCard key={i} block={b} defaultOpen={isLive} />
            if (b.type === "tool_result") return <ToolResultCard key={i} block={b} />
            return null
          })
        )}
        {original && <MediaPreview media={extractMedia(fullText)} />}
        {original && <AssistantFooter metadata={original.metadata} />}
        {/* Branch picker — zeigt ◀ 1/2 ▶ wenn mehrere Antworten vorhanden */}
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
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${tts.speaking ? "text-rose-300 bg-rose-500/15 border-rose-500/30 hover:bg-rose-500/25" : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"}`}>
              {tts.speaking ? <VolumeX size={12} /> : <Volume2 size={12} />}
            </button>
          )}
          {fullText && (
            <button onClick={() => { navigator.clipboard.writeText(fullText); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%] transition-colors">
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            </button>
          )}
          {!isLive && (
            <ActionBarPrimitive.Reload asChild>
              <button className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/30 transition-colors">
                <RotateCw size={12} /> {t("bubble.retry")}
              </button>
            </ActionBarPrimitive.Reload>
          )}
          <button onClick={() => setShowRaw((r) => !r)}
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${showRaw ? "text-amber-300 bg-amber-500/15 border-amber-500/30" : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"}`}>
            <Code size={12} />
          </button>
        </div>
      </div>
    </MessagePrimitive.Root>
  )
}

// ─── System Message (Compaction) ─────────────────────────────────────────────

function HydraSystemMessage() {
  const msg = useMessage()
  const originals = getExternalStoreMessages<Message>(msg)
  const original = originals[0]
  if (!original || original.role !== "compaction") return null
  return <CompactionBlock message={original} />
}

// ─── Thread ───────────────────────────────────────────────────────────────────

export function HydraThread() {
  return (
    <ThreadPrimitive.Root className="flex-1 overflow-hidden flex flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto px-4 py-3 space-y-1 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent">
        <ThreadPrimitive.Messages
          components={{
            UserMessage: HydraUserMessage,
            AssistantMessage: HydraAssistantMessage,
            SystemMessage: HydraSystemMessage,
          }}
        />
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  )
}
