import { FileText, X } from "lucide-react"

interface Props { file: File; onRemove: () => void }

export function MessageFileChip({ file, onRemove }: Props) {
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
