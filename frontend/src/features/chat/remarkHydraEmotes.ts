import { HYDRA_EMOTES, EMOTE_RE } from "./hydraEmotes"

// remark-Plugin: ersetzt :hydra-NAME: in Text-Knoten durch Bild-Knoten.
// Arbeitet nur auf `text`-Knoten — Code/InlineCode sind eigene Typen und bleiben
// daher unangetastet (Kürzel in Code-Blöcken bleiben Literal).

interface MdNode {
  type: string
  value?: string
  url?: string
  alt?: string
  title?: string
  children?: MdNode[]
}

function splitTextNode(value: string): MdNode[] {
  const nodes: MdNode[] = []
  let last = 0
  const re = new RegExp(EMOTE_RE.source, "g")
  let m: RegExpExecArray | null
  while ((m = re.exec(value)) !== null) {
    const src = HYDRA_EMOTES[m[1]]
    if (!src) continue
    if (m.index > last) nodes.push({ type: "text", value: value.slice(last, m.index) })
    nodes.push({ type: "image", url: src, alt: `:hydra-${m[1]}:`, title: m[1] })
    last = m.index + m[0].length
  }
  if (last < value.length) nodes.push({ type: "text", value: value.slice(last) })
  return nodes
}

export function remarkHydraEmotes() {
  return (tree: MdNode) => {
    const walk = (node: MdNode) => {
      if (!Array.isArray(node.children)) return
      const next: MdNode[] = []
      for (const child of node.children) {
        if (child.type === "text" && child.value?.includes(":hydra-")) {
          next.push(...splitTextNode(child.value))
        } else {
          walk(child)
          next.push(child)
        }
      }
      node.children = next
    }
    walk(tree)
  }
}
