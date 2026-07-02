import { Fragment, type ReactNode } from "react"
import { getBlock } from "./registry"

/** Erlaubte HTML-Tags im Designer-Markup. Bewusst konservativ — alles was
 *  Skripte/Styles einschleusen könnte (script, style, iframe, object, …) ist
 *  NICHT dabei und wird verworfen. Layout/Text/Grafik ist erlaubt. */
const ALLOWED_TAGS = new Set([
  "div", "section", "article", "header", "footer", "main", "aside", "nav",
  "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "a", "ul", "ol", "li",
  "img", "figure", "figcaption", "blockquote", "hr", "br", "strong", "em",
  "small", "b", "i", "button", "label",
])

/** Erlaubte Attribute. class/style für Design, href/src/alt für Inhalte.
 *  KEINE on*-Handler (kein Fremd-JS), kein srcset-Tricks nötig fürs Proof. */
const ALLOWED_ATTRS = new Set(["class", "style", "href", "src", "alt", "title", "id", "target", "rel"])

let _key = 0
function nextKey(): string {
  _key += 1
  return `t${_key}`
}

/** Wandelt einen DOM-Knoten rekursiv in React-Elemente.
 *  - <hh-xxx/> → echter Baustein aus dem Register
 *  - erlaubtes Tag → als React-Element mit gefilterten Attributen
 *  - alles andere (script, unbekannt) → verworfen (nur Textinhalt bleibt) */
function nodeToReact(node: Node): ReactNode {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null
  }
  const el = node as Element
  const tag = el.tagName.toLowerCase()

  // Platzhalter: <hh-chatbox agent="buddy"/>  →  Baustein
  if (tag.startsWith("hh-")) {
    const blockName = tag.slice(3)
    const block = getBlock(blockName)
    const attrs: Record<string, string> = {}
    for (const a of Array.from(el.attributes)) attrs[a.name] = a.value
    if (!block) {
      return (
        <span key={nextKey()} className="inline-block px-2 py-1 rounded bg-rose-500/15 text-rose-300 text-xs font-mono">
          unbekannter Baustein: &lt;{tag}/&gt;
        </span>
      )
    }
    return <Fragment key={nextKey()}>{block.render(attrs)}</Fragment>
  }

  // Nicht erlaubtes Tag (script/style/iframe/…): Inhalt behalten, Hülle weg.
  if (!ALLOWED_TAGS.has(tag)) {
    return <Fragment key={nextKey()}>{childrenToReact(el)}</Fragment>
  }

  // Erlaubtes Tag: Attribute filtern (class→className), Kinder rekursiv.
  const props: Record<string, string> = { key: nextKey() }
  for (const a of Array.from(el.attributes)) {
    const name = a.name.toLowerCase()
    if (name.startsWith("on")) continue // niemals Event-Handler aus Fremd-HTML
    if (!ALLOWED_ATTRS.has(name)) continue
    if (name === "class") props.className = a.value
    else props[name] = a.value
  }
  const voidTags = new Set(["img", "hr", "br"])
  if (voidTags.has(tag)) {
    return createElementByTag(tag, props, null)
  }
  return createElementByTag(tag, props, childrenToReact(el))
}

function childrenToReact(el: Element): ReactNode[] {
  return Array.from(el.childNodes).map((c) => nodeToReact(c))
}

/** Kleiner Tag-Dispatcher — hält den Renderer ohne dangerouslySetInnerHTML. */
function createElementByTag(tag: string, props: Record<string, unknown>, children: ReactNode): ReactNode {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Tag = tag as any
  return children === null ? <Tag {...props} /> : <Tag {...props}>{children}</Tag>
}

/** Parst Designer-HTML (String) zu sicheren React-Elementen mit eingesetzten
 *  Bausteinen. Nutzt den Browser-Parser (DOMParser) — kein eigener HTML-Parser. */
export function renderTemplate(html: string): ReactNode {
  _key = 0
  const doc = new DOMParser().parseFromString(html, "text/html")
  return <>{Array.from(doc.body.childNodes).map((n) => nodeToReact(n))}</>
}
