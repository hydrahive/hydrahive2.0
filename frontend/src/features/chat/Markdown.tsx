import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"

export function Markdown({ text }: { text: string }) {
  return (
    <div className="prose prose-invert prose-sm max-w-none prose-pre:p-0 prose-pre:bg-transparent prose-headings:text-zinc-100 prose-strong:text-zinc-100 prose-a:text-violet-300 prose-code:text-violet-200 prose-code:bg-violet-500/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "")
            if (!inline && match) {
              return (
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
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
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
