import { FileText, Mic, MicOff, Paperclip, Send, Square, X } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useVoiceInput } from "./useVoiceInput"

const MAX_FILES = 5
const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const MAX_TEXT_BYTES = 100 * 1024

interface Props {
  onSend: (text: string, files: File[]) => void
  onCancel?: () => void
  busy: boolean
  disabled?: boolean
}

export function MessageInput({ onSend, onCancel, busy, disabled }: Props) {
  const { t } = useTranslation("chat")
  const [text, setText] = useState("")
  const voice = useVoiceInput((transcript) => {
    setText((prev) => (prev ? prev + " " + transcript : transcript))
  })
  const [files, setFiles] = useState<File[]>([])
  const [dragOver, setDragOver] = useState(false)
  const textRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  function submit() {
    const trimmed = text.trim()
    if ((!trimmed && files.length === 0) || busy) return
    onSend(trimmed, files)
    setText("")
    setFiles([])
    if (textRef.current) textRef.current.style.height = "auto"
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit() }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value)
    const el = e.target
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 200) + "px"
  }

  function addFiles(incoming: FileList | null) {
    if (!incoming) return
    const next = [...files]
    for (const f of Array.from(incoming)) {
      if (next.length >= MAX_FILES) break
      const limit = f.type.startsWith("image/") ? MAX_IMAGE_BYTES : MAX_TEXT_BYTES * 500
      if (f.size <= limit) next.push(f)
    }
    setFiles(next)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files)
  }

  return (
    <div className="border-t border-white/[6%] p-4"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {files.map((f, i) => <FileChip key={i} file={f} onRemove={() => setFiles(files.filter((_, j) => j !== i))} />)}
        </div>
      )}
      <div className={`flex items-end gap-2 rounded-2xl border bg-white/[3%] px-3 py-2 transition-all
        ${dragOver ? "border-violet-500/60 bg-violet-500/[5%]" : "border-white/[8%] focus-within:border-violet-500/40 focus-within:bg-white/[5%]"}`}>
        <button
          type="button"
          disabled={disabled || busy}
          onClick={() => fileRef.current?.click()}
          title={t("upload.button_title")}
          className="flex-shrink-0 p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <Paperclip size={15} />
        </button>
        <input ref={fileRef} type="file" multiple className="hidden"
          onChange={(e) => { addFiles(e.target.files); e.target.value = "" }} />
        <button
          type="button"
          disabled={disabled || busy || voice.state === "transcribing"}
          onClick={voice.toggle}
          title={voice.state === "recording" ? "Klicken zum Beenden" : "Klicken zum Sprechen"}
          className={`flex-shrink-0 p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed
            ${voice.state === "recording"
              ? "text-rose-400 bg-rose-500/20 animate-pulse"
              : voice.state === "transcribing"
              ? "text-amber-400 bg-amber-500/10"
              : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"}`}
        >
          {voice.state === "recording" ? <MicOff size={15} /> : <Mic size={15} />}
        </button>
        <textarea
          ref={textRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKey}
          placeholder={disabled ? t("input.placeholder_disabled") : t("input.placeholder")}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 resize-none focus:outline-none py-1.5 disabled:opacity-50"
        />
        {busy && onCancel ? (
          <button onClick={onCancel} type="button" title={t("input.stop_title")}
            className="flex-shrink-0 p-2 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 transition-all">
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button onClick={submit} disabled={busy || (!text.trim() && files.length === 0) || disabled}
            className="flex-shrink-0 p-2 rounded-xl bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md shadow-black/30">
            <Send size={15} />
          </button>
        )}
      </div>
      <p className="text-[10px] text-zinc-600 mt-1.5 px-1">{t("input.hint")}</p>
    </div>
  )
}

function FileChip({ file, onRemove }: { file: File; onRemove: () => void }) {
  const isImage = file.type.startsWith("image/")
  return (
    <div className="relative group flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[4%] px-2 py-1 text-xs text-zinc-300 max-w-[160px]">
      {isImage ? (
        <img src={URL.createObjectURL(file)} className="w-6 h-6 rounded object-cover flex-shrink-0" alt="" />
      ) : (
        <FileText size={14} className="flex-shrink-0 text-zinc-400" />
      )}
      <span className="truncate">{file.name}</span>
      <button onClick={onRemove}
        className="flex-shrink-0 p-0.5 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/10">
        <X size={11} />
      </button>
    </div>
  )
}
