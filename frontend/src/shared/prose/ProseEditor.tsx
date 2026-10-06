import { useEffect, useRef } from "react"
import { EditorContent, useEditor, type Editor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import { Markdown } from "@tiptap/markdown"
import { Placeholder, CharacterCount } from "@tiptap/extensions"
import Typography from "@tiptap/extension-typography"
import { typographyFor } from "./typography"

/**
 * Prosa-Editor (TipTap) für Fließtext – Bücher, Notizen, längere Texte.
 * Ein- und Ausgabe sind Markdown. Bewusst schlicht: Absatz, Überschrift,
 * fett/kursiv, Zitat, Liste, Trennlinie. Kein Code, keine Bilder.
 */
export interface ProseEditorProps {
  /** Markdown-Inhalt. Ändert sich der Wert von außen (anderes Dokument), wird neu geladen. */
  value: string
  /** Schlüssel des Dokuments; ein Wechsel lädt `value` neu und leert den Rückgängig-Verlauf. */
  docKey: string
  onChange?: (markdown: string) => void
  onStats?: (s: { words: number; characters: number }) => void
  onReady?: (editor: Editor) => void
  placeholder?: string
  /** Sprache für Anführungszeichen und Strich beim Tippen („…“ und – bei de). */
  language?: string
  typography?: boolean
  readOnly?: boolean
  className?: string
}

export function ProseEditor({
  value, docKey, onChange, onStats, onReady, placeholder, language = "de",
  typography = true, readOnly = false, className,
}: ProseEditorProps) {
  const cb = useRef({ onChange, onStats })
  useEffect(() => { cb.current = { onChange, onStats } }, [onChange, onStats])

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ code: false, codeBlock: false, link: false, heading: { levels: [2, 3] } }),
      Markdown,
      Placeholder.configure({ placeholder: placeholder ?? "" }),
      CharacterCount,
      ...(typography ? [Typography.configure(typographyFor(language))] : []),
    ],
    content: value,
    contentType: "markdown",
    editable: !readOnly,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "prose-editor prose prose-invert max-w-none focus:outline-none",
        spellcheck: "true",
        lang: language,
      },
    },
    onUpdate: ({ editor: e }) => {
      cb.current.onChange?.(e.getMarkdown())
      cb.current.onStats?.(statsOf(e))
    },
    onCreate: ({ editor: e }) => cb.current.onStats?.(statsOf(e)),
  }, [docKey, language, typography])

  useEffect(() => { if (editor) onReady?.(editor) }, [editor, onReady])
  useEffect(() => { editor?.setEditable(!readOnly) }, [editor, readOnly])

  return <EditorContent editor={editor} className={className} />
}

function statsOf(e: Editor): { words: number; characters: number } {
  const cc = e.storage.characterCount
  return { words: cc.words(), characters: cc.characters() }
}
