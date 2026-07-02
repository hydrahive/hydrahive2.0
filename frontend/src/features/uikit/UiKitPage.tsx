import type { CSSProperties } from "react"
import { useState } from "react"
import { Check, Layers, Palette, Rocket, Save, Search, Settings, Trash2 } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { applyTheme, getStoredTheme, THEMES, type ThemeId } from "@/shared/theme"
import { applyLook, getStoredLook, LOOKS, type LookId } from "@/shared/look"
import { Badge, Button, Card, CardHeader, Input, Select, Textarea } from "@/shared/ui"

/**
 * Lebende Vorschau des HydraHive UI-Kits. Zeigt alle Basis-Komponenten und
 * erlaubt oben das Live-Umschalten von Farbe UND Look — damit sichtbar wird,
 * wie stark ein Theme-Wechsel die komplette Optik verändert (WordPress-artig).
 */
export function UiKitPage() {
  const [theme, setTheme] = useState<ThemeId>(getStoredTheme())
  const [look, setLook] = useState<LookId>(getStoredLook())

  function pickTheme(id: ThemeId) {
    applyTheme(id)
    setTheme(id)
  }
  function pickLook(id: LookId) {
    applyLook(id)
    setLook(id)
  }

  const c = rgbFor("/settings")

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-white">UI-Kit — Vorschau</h1>
        <p className="text-zinc-500 text-sm mt-0.5">
          Konsistente Basis-Komponenten. Schalte oben Farbe &amp; Stil um — alle Elemente ändern sich live mit.
        </p>
      </div>

      {/* ── Umschalter ──────────────────────────────────────────── */}
      <Card color={c} style={{ ["--c" as string]: c } as CSSProperties}>
        <CardHeader icon={<Palette size={15} />} title="Farbe" />
        <div className="flex flex-wrap gap-2">
          {THEMES.map((th) => (
            <button
              key={th.id}
              onClick={() => pickTheme(th.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all ${
                th.id === theme
                  ? "border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)] text-zinc-100"
                  : "border-white/[8%] text-zinc-400 hover:border-white/20 hover:bg-white/[3%]"
              }`}
            >
              <span
                className="w-4 h-4 rounded-full"
                style={{ background: `linear-gradient(135deg, ${th.preview.from}, ${th.preview.to})` }}
              />
              {th.name}
              {th.id === theme && <Check size={11} className="text-[var(--hh-accent-text)]" />}
            </button>
          ))}
        </div>

        <div className="mt-4 mb-2 flex items-center gap-2 text-zinc-100">
          <Layers size={15} className="text-[var(--hh-accent-text)]" />
          <h3 className="text-sm font-semibold">Stil</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {LOOKS.map((lk) => (
            <button
              key={lk.id}
              onClick={() => pickLook(lk.id)}
              className={`px-3 py-1.5 rounded-lg border text-xs transition-all ${
                lk.id === look
                  ? "border-[var(--hh-accent-border)] bg-[var(--hh-accent-soft)] text-zinc-100"
                  : "border-white/[8%] text-zinc-400 hover:border-white/20 hover:bg-white/[3%]"
              }`}
            >
              {lk.name}
              {lk.id === look && <Check size={11} className="inline ml-1 text-[var(--hh-accent-text)]" />}
            </button>
          ))}
        </div>
      </Card>

      {/* ── Buttons ─────────────────────────────────────────────── */}
      <Card color={c} style={{ ["--c" as string]: c } as CSSProperties}>
        <CardHeader icon={<Rocket size={15} />} title="Buttons" />
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger" icon={<Trash2 size={14} />}>Löschen</Button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm">Small</Button>
            <Button size="md" icon={<Save size={14} />}>Medium</Button>
            <Button size="lg">Large</Button>
            <Button disabled>Disabled</Button>
          </div>
        </div>
      </Card>

      {/* ── Formular-Elemente ───────────────────────────────────── */}
      <Card color={c} style={{ ["--c" as string]: c } as CSSProperties}>
        <CardHeader icon={<Settings size={15} />} title="Eingaben" />
        <div className="grid sm:grid-cols-2 gap-3">
          <Input placeholder="Normales Textfeld…" />
          <Input placeholder="Mit Icon…" icon={<Search size={15} />} />
          <Input placeholder="Fehlerzustand" invalid defaultValue="ungültig" />
          <Select defaultValue="">
            <option value="" disabled>Bitte wählen…</option>
            <option>Option A</option>
            <option>Option B</option>
            <option>Option C</option>
          </Select>
          <Textarea placeholder="Mehrzeiliger Text…" rows={3} className="sm:col-span-2" />
        </div>
      </Card>

      {/* ── Badges ──────────────────────────────────────────────── */}
      <Card color={c} style={{ ["--c" as string]: c } as CSSProperties}>
        <CardHeader title="Badges" />
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="accent">Accent</Badge>
          <Badge variant="neutral">Neutral</Badge>
          <Badge variant="success" icon={<Check size={11} />}>Erfolg</Badge>
          <Badge variant="warning">Warnung</Badge>
          <Badge variant="danger">Fehler</Badge>
        </div>
      </Card>

      {/* ── Karten in Domain-Farben ─────────────────────────────── */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Card color={rgbFor("/chat")}>
          <CardHeader title="Werkstatt" />
          <p className="text-xs text-zinc-400">Karte mit eigener Domain-Farbe.</p>
        </Card>
        <Card color={rgbFor("/atelier")}>
          <CardHeader title="Atelier" />
          <p className="text-xs text-zinc-400">Jede Box trägt ihre Bereichsfarbe.</p>
        </Card>
        <Card color={rgbFor("/cryptoboard")}>
          <CardHeader title="Cryptoboard" />
          <p className="text-xs text-zinc-400">Glow &amp; Rand folgen dem Stil-Preset.</p>
        </Card>
      </div>
    </div>
  )
}
