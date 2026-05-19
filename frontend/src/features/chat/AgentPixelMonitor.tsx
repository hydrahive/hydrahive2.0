import { useEffect, useRef, useState } from "react"
import { getCharForAgent, type CharTemplate } from "./_mcCharacters"

const S = 3
const CW = 10 * S
const CH = 20 * S
const H = 200

const TOOL_BUBBLE: Record<string, string> = {
  shell_exec: "Running command...", bash: "Running command...",
  file_read: "Reading file...", read_file: "Reading file...",
  file_write: "Writing file...", write_file: "Writing file...",
  file_patch: "Patching file...", list_files: "Listing files...",
  web_search: "Searching web...", fetch_url: "Fetching page...",
  read_memory: "Checking memory...", write_memory: "Saving memory...",
  ask_agent: "Delegating task...", send_task: "Sending task...",
  datamining_search: "Searching data...", datamining_semantic: "Semantic search...",
  load_skill: "Loading skill...", list_skills: "Listing skills...",
}

interface AgentState {
  name: string; tmpl: CharTemplate
  x: number; y: number; homeX: number
  frame: number; facing: "left" | "right" | "front"
  status: "active" | "waiting" | "done"
  bubble: string; interacting: boolean
}

function drawChar(ctx: CanvasRenderingContext2D, agent: AgentState) {
  const { x, y, tmpl, frame, facing } = agent
  const mirror = facing === "left"
  for (let row = 0; row < tmpl.pixels.length; row++) {
    const line = tmpl.pixels[row]
    for (let col = 0; col < line.length; col++) {
      const ch = line[col]
      if (ch === "_" || ch === " ") continue
      const color = tmpl.palette[ch]
      if (!color) continue
      ctx.fillStyle = color
      const dc = mirror ? 9 - col : col
      const offY = frame === 1 && row >= 16 ? (col < 5 ? -1 : 1) : 0
      ctx.fillRect(x + dc * S, y + (row + offY) * S, S, S)
    }
  }
}

function drawBubble(ctx: CanvasRenderingContext2D, text: string, cx: number, y: number, cw: number) {
  ctx.font = "11px 'Courier New', monospace"
  const words = text.split(" ")
  const lines: string[] = []
  let line = ""
  for (const w of words) {
    const t = line ? `${line} ${w}` : w
    if (ctx.measureText(t).width > 144) { if (line) lines.push(line); line = w } else line = t
  }
  if (line) lines.push(line)
  if (lines.length > 2) { lines.length = 2; lines[1] = lines[1].slice(0, -3) + "…" }
  const bw = Math.min(160, Math.max(...lines.map(l => ctx.measureText(l).width)) + 16)
  const bh = lines.length * 14 + 10
  const bx = Math.max(4, Math.min(cx - bw / 2, cw - 4 - bw))
  const by = y - bh - 8
  ctx.fillStyle = "rgba(20,20,30,0.92)"; ctx.strokeStyle = "rgba(255,255,255,0.25)"; ctx.lineWidth = 1
  ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 5); ctx.fill(); ctx.stroke()
  ctx.fillStyle = "rgba(20,20,30,0.92)"; ctx.beginPath()
  ctx.moveTo(cx - 4, by + bh); ctx.lineTo(cx, by + bh + 5); ctx.lineTo(cx + 4, by + bh); ctx.fill()
  ctx.fillStyle = "#d4d4d4"; ctx.textAlign = "left"; ctx.textBaseline = "top"
  lines.forEach((l, i) => ctx.fillText(l, bx + 8, by + 5 + i * 14))
}

function hexRgb(hex: string) {
  return `${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)}`
}

function homePositions(count: number, cw: number): number[] {
  if (count === 1) return [cw / 2 - CW / 2]
  return Array.from({ length: count }, (_, i) => {
    const margin = 60
    return margin + (i / (count - 1)) * (cw - margin * 2) - CW / 2
  })
}

export interface Props {
  agentTools: Record<string, string[]>
  activeAgents: string[]
  doneAgents: string[]
}

export function AgentPixelMonitor({ agentTools, activeAgents, doneAgents }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const agentsRef = useRef<Map<string, AgentState>>(new Map())
  const tickRef = useRef(0)
  const animRef = useRef(0)
  const [cw, setCw] = useState(500)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const obs = new ResizeObserver(e => setCw(Math.floor(e[0].contentRect.width)))
    obs.observe(canvas.parentElement!)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    const names = Object.keys(agentTools)
    const positions = homePositions(names.length, cw)
    const map = agentsRef.current
    const groundY = H - 22 - CH
    const activeSet = new Set(activeAgents)
    const doneSet = new Set(doneAgents)

    names.forEach((name, i) => {
      const hx = positions[i]
      const existing = map.get(name)
      const tools = agentTools[name] ?? []
      const lastTool = tools[tools.length - 1] ?? ""
      const isActive = activeSet.has(name)
      const isDone = doneSet.has(name)

      if (!existing) {
        map.set(name, {
          name, tmpl: getCharForAgent(name),
          x: hx, y: groundY, homeX: hx,
          frame: 0, facing: "front",
          status: isActive ? "active" : isDone ? "done" : "waiting",
          bubble: isActive && lastTool ? (TOOL_BUBBLE[lastTool] ?? `${lastTool}…`) : "Bereit",
          interacting: false,
        })
      } else {
        existing.homeX = hx
        existing.status = isActive ? "active" : isDone ? "done" : "waiting"
        if (isActive && lastTool) existing.bubble = TOOL_BUBBLE[lastTool] ?? `${lastTool}…`
        if (!isActive) existing.bubble = isDone ? "Fertig!" : "Bereit"
      }
    })
    for (const key of map.keys()) if (!names.includes(key)) map.delete(key)
  }, [agentTools, activeAgents, doneAgents, cw])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    canvas.width = cw; canvas.height = H
    let running = true

    const render = () => {
      if (!running) return
      tickRef.current++
      const tick = tickRef.current
      ctx.clearRect(0, 0, cw, H)
      const grad = ctx.createLinearGradient(0, 0, 0, H)
      grad.addColorStop(0, "rgba(8,12,22,0.97)"); grad.addColorStop(1, "rgba(15,28,15,0.97)")
      ctx.fillStyle = grad; ctx.fillRect(0, 0, cw, H)
      ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(0, H - 18); ctx.lineTo(cw, H - 18); ctx.stroke()

      const agents = [...agentsRef.current.values()]

      // Connection lines between interacting agents
      for (let i = 0; i < agents.length; i++) {
        const a = agents[i]
        if (a.status !== "active" || !a.interacting) continue
        for (let j = i + 1; j < agents.length; j++) {
          const b = agents[j]
          if (!b.interacting) continue
          const ax = a.x + CW / 2, ay = a.y + CH / 2
          const bx = b.x + CW / 2, by = b.y + CH / 2
          ctx.save()
          ctx.strokeStyle = `rgba(${hexRgb(Object.values(a.tmpl.palette)[0] || "#888")},0.3)`
          ctx.lineWidth = 1; ctx.setLineDash([3, 3])
          ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke()
          ctx.setLineDash([]); ctx.restore()
        }
      }

      for (const a of agents) {
        a.x += (a.homeX - a.x) * 0.06
        if (a.status === "active" && tick % 10 === 0) a.frame = a.frame === 0 ? 1 : 0
        else if (a.status !== "active") { a.frame = 0; if (!a.interacting) a.facing = "front" }

        const cx = a.x + CW / 2
        ctx.fillStyle = "rgba(0,0,0,0.2)"
        ctx.beginPath(); ctx.ellipse(cx, a.y + CH + 2, 14, 4, 0, 0, Math.PI * 2); ctx.fill()

        ctx.globalAlpha = a.status === "waiting" ? 0.55 : 1
        drawChar(ctx, a)
        ctx.globalAlpha = 1

        if (a.status === "active") {
          const fc = Object.values(a.tmpl.palette)[0] || "#fff"
          ctx.fillStyle = `rgba(${hexRgb(fc)},${0.12 + 0.1 * Math.sin(tick * 0.1)})`
          ctx.beginPath(); ctx.ellipse(cx, a.y + CH + 2, 18, 5, 0, 0, Math.PI * 2); ctx.fill()
        }
        if (a.status === "done") {
          ctx.fillStyle = "#10b981"; ctx.font = "bold 14px sans-serif"
          ctx.textAlign = "center"; ctx.textBaseline = "alphabetic"
          ctx.fillText("✓", cx, a.y - 4)
        }

        ctx.font = "bold 9px 'Courier New', monospace"; ctx.textAlign = "center"
        ctx.fillStyle = a.status === "done" ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.75)"
        ctx.textBaseline = "alphabetic"; ctx.fillText(a.name, cx, a.y + CH + 13)
        ctx.font = "7px 'Courier New', monospace"; ctx.fillStyle = "rgba(255,255,255,0.3)"
        ctx.fillText(a.tmpl.name, cx, a.y + CH + 23)

        if (a.status === "active") drawBubble(ctx, a.bubble, cx, a.y, cw)
        else if (a.status === "done") {
          ctx.globalAlpha = 0.45; drawBubble(ctx, "Fertig!", cx, a.y, cw); ctx.globalAlpha = 1
        }
      }

      animRef.current = requestAnimationFrame(render)
    }
    animRef.current = requestAnimationFrame(render)
    return () => { running = false; cancelAnimationFrame(animRef.current) }
  }, [cw])

  if (Object.keys(agentTools).length === 0) return null

  return (
    <div className="border-b border-white/[6%]">
      <canvas ref={canvasRef} style={{ width: "100%", height: H, display: "block", imageRendering: "pixelated" }} />
    </div>
  )
}
