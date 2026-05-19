import { useEffect, useRef, useState } from "react"
import { getCharForAgent, type CharTemplate } from "./_mcCharacters"

const S = 3
const CW = 10 * S
const CH = 20 * S
const H = 180

const TOOL_BUBBLE: Record<string, string> = {
  shell_exec: "Running command...", bash: "Running command...",
  read_file: "Reading file...", write_file: "Writing file...", list_files: "Listing files...",
  web_search: "Searching web...", web_fetch: "Fetching page...",
  memory_read: "Checking memory...", memory_write: "Saving memory...",
  send_message: "Sending message...", send_task: "Delegating task...",
  spawn_subagent: "Spawning helper!", wait_result: "Waiting for result...",
  python_exec: "Running Python...", code_exec: "Executing code...",
}

interface AgentState {
  name: string; tmpl: CharTemplate
  x: number; y: number; targetX: number; targetY: number
  frame: number; facing: "left" | "right" | "front"
  status: "active" | "waiting" | "done"
  bubble: string
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
  let bx = Math.max(4, Math.min(cx - bw / 2, cw - 4 - bw))
  const by = y - bh - 8
  ctx.fillStyle = "rgba(20,20,30,0.92)"; ctx.strokeStyle = "rgba(255,255,255,0.25)"; ctx.lineWidth = 1
  ctx.beginPath()
  ctx.roundRect(bx, by, bw, bh, 5)
  ctx.fill(); ctx.stroke()
  ctx.fillStyle = "rgba(20,20,30,0.92)"; ctx.beginPath()
  ctx.moveTo(cx - 4, by + bh); ctx.lineTo(cx, by + bh + 5); ctx.lineTo(cx + 4, by + bh); ctx.fill()
  ctx.fillStyle = "#d4d4d4"; ctx.textAlign = "left"; ctx.textBaseline = "top"
  lines.forEach((l, i) => ctx.fillText(l, bx + 8, by + 5 + i * 14))
}

function hexRgb(hex: string) {
  return `${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)}`
}

interface Props {
  agentName: string
  currentTool: string | null
  busy: boolean
}

export function AgentPixelMonitor({ agentName, currentTool, busy }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const agentRef = useRef<AgentState | null>(null)
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
    if (!agentRef.current) {
      agentRef.current = {
        name: agentName, tmpl: getCharForAgent(agentName),
        x: 0, y: H / 2 - CH / 2, targetX: 0, targetY: H / 2 - CH / 2,
        frame: 0, facing: "front",
        status: busy ? "active" : "waiting",
        bubble: busy && currentTool ? (TOOL_BUBBLE[currentTool] ?? `${currentTool}…`) : "Bereit",
      }
    } else {
      const a = agentRef.current
      a.status = busy ? "active" : "waiting"
      if (busy && currentTool) a.bubble = TOOL_BUBBLE[currentTool] ?? `${currentTool}…`
      if (!busy) a.bubble = "Bereit"
    }
  }, [agentName, currentTool, busy])

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

      // Ground line
      ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(0, H - 18); ctx.lineTo(cw, H - 18); ctx.stroke()

      const a = agentRef.current
      if (a) {
        a.targetX = cw / 2 - CW / 2
        a.targetY = H - 18 - CH - 4
        a.x += (a.targetX - a.x) * 0.08
        a.y += (a.targetY - a.y) * 0.08
        if (a.status === "active" && tick % 10 === 0) a.frame = a.frame === 0 ? 1 : 0
        else if (a.status !== "active") a.frame = 0

        const cx = a.x + CW / 2
        // Shadow
        ctx.fillStyle = "rgba(0,0,0,0.25)"
        ctx.beginPath(); ctx.ellipse(cx, a.y + CH + 2, 14, 4, 0, 0, Math.PI * 2); ctx.fill()
        // Character
        ctx.globalAlpha = a.status === "waiting" ? 0.55 : 1
        drawChar(ctx, a)
        ctx.globalAlpha = 1
        // Glow
        if (a.status === "active") {
          const fc = Object.values(a.tmpl.palette)[0] || "#fff"
          ctx.fillStyle = `rgba(${hexRgb(fc)},${0.12 + 0.1 * Math.sin(tick * 0.1)})`
          ctx.beginPath(); ctx.ellipse(cx, a.y + CH + 2, 18, 5, 0, 0, Math.PI * 2); ctx.fill()
        }
        // Name
        ctx.font = "bold 9px 'Courier New', monospace"; ctx.textAlign = "center"
        ctx.fillStyle = "rgba(255,255,255,0.75)"; ctx.textBaseline = "alphabetic"
        ctx.fillText(a.name, cx, a.y + CH + 13)
        ctx.font = "7px 'Courier New', monospace"; ctx.fillStyle = "rgba(255,255,255,0.3)"
        ctx.fillText(a.tmpl.name, cx, a.y + CH + 22)
        // Bubble
        if (a.status === "active") drawBubble(ctx, a.bubble, cx, a.y, cw)
      }

      animRef.current = requestAnimationFrame(render)
    }
    animRef.current = requestAnimationFrame(render)
    return () => { running = false; cancelAnimationFrame(animRef.current) }
  }, [cw])

  return (
    <div className="border-b border-white/[6%]">
      <canvas ref={canvasRef} style={{ width: "100%", height: H, display: "block", imageRendering: "pixelated" }} />
    </div>
  )
}
