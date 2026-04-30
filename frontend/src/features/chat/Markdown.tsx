import { useState } from "react"
import { Copy, Check } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"

function CopyCodeButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)
  function handleCopy() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 bg-white/[4%] hover:bg-white/[8%] border border-white/[6%] transition-colors"
    >
      {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
    </button>
  )
}

export function Markdown({ text }: { text: string }) {
  return (
    <div className="prose prose-invert prose-sm max-w-none prose-pre:p-0 prose-pre:bg-transparent prose-headings:text-zinc-100 prose-strong:text-zinc-100 prose-a:text-violet-300 prose-code:text-violet-200 prose-code:bg-violet-500/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "")
            if (!inline && match) {
              const code = String(children).replace(/\n$/, "")
              return (
                <div className="relative">
                  <CopyCodeButton code={code} />
                  <SyntaxHighlighter
                    style={vscDarkPlus as any}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: "0.5rem",
                      padding: "0.75rem 1rem",
                      fontSize: "0.8rem",
                    }}
                    {...props}
                  >
                    {code}
                  </SyntaxHighlighter>
                </div>
              )
            }
            return <code className={className} {...props}>{children}</code>
          },
          table({ children, ...props }: any) {
            return (
              <div className="overflow-x-auto">
                <table className="border-collapse" {...props}>{children}</table>
              </div>
            )
          },
          th({ children, ...props }: any) {
            return <th className="border border-white/[8%] px-3 py-1.5 bg-white/[3%] text-left font-semibold" {...props}>{children}</th>
          },
          td({ children, ...props }: any) {
            return <td className="border border-white/[8%] px-3 py-1.5" {...props}>{children}</td>
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
