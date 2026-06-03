export interface ParsedMxid {
  name: string
  isBot: boolean
}

/** "@till:server" → {name:"till"}; "@agent-buddy:server" → {name:"buddy", isBot:true}. */
export function mxidToName(mxid: string): ParsedMxid {
  const local = mxid.replace(/^@/, "").split(":")[0]
  if (local.startsWith("agent-")) {
    return { name: local.slice("agent-".length), isBot: true }
  }
  return { name: local, isBot: false }
}
