import { readFileSync } from "node:fs"
import { resolve } from "node:path"

/**
 * Regression guard for scopes that have been migrated to the Admin-Cockpit
 * visual system. Add files only once their complete render tree follows the
 * rules in docs/specs/admin-cockpit-visual-system.md.
 */
const migratedFiles = [
  "src/features/cockpit/admin/SystemOverlay.tsx",
  "src/features/cockpit/admin/SystemSettingsOverlay.tsx",
  "src/features/system/StatCard.tsx",
  "src/features/system/HealthBar.tsx",
  "src/features/system/VoiceInstallModal.tsx",
]

const forbidden = [
  { label: "legacy box class", pattern: /className=(?:"|\{`)[^"`]*\bbox(?:\s|\b|-)/g },
  { label: "dynamic route color", pattern: /\brgbFor\s*\(/g },
  { label: "legacy --c accent", pattern: /["']--c["']|var\(--c\)/g },
  { label: "decorative gradient", pattern: /\b(?:bg-gradient|from-(?:violet|indigo|fuchsia|cyan|yellow|teal|purple|pink|orange|sky)-|to-(?:violet|indigo|fuchsia|cyan|yellow|teal|purple|pink|orange|sky)-)/g },
  { label: "non-system domain color", pattern: /\b(?:violet|indigo|fuchsia|cyan|yellow|teal|purple|pink|orange|sky)-(?:[0-9]{2,3})(?:\/[0-9]+|\/\[[^\]]+\])?/g },
  { label: "parallel zinc palette", pattern: /\bzinc-(?:[0-9]{2,3})\b/g },
  { label: "legacy translucent white surface", pattern: /\b(?:border|bg)-white\/(?:\[[^\]]+\]|[0-9]+)/g },
]

const failures = []
for (const relativePath of migratedFiles) {
  const absolutePath = resolve(process.cwd(), relativePath)
  const source = readFileSync(absolutePath, "utf8")
  for (const rule of forbidden) {
    for (const match of source.matchAll(rule.pattern)) {
      const line = source.slice(0, match.index).split("\n").length
      failures.push(`${relativePath}:${line}  ${rule.label}: ${match[0]}`)
    }
  }
}

if (failures.length > 0) {
  console.error("Admin visual-system guard failed:\n")
  for (const failure of failures) console.error(`- ${failure}`)
  console.error(`\n${failures.length} violation(s). See docs/specs/admin-cockpit-visual-system.md.`)
  process.exit(1)
}

console.log(`Admin visual-system guard passed (${migratedFiles.length} files).`)
