import { readFileSync } from "node:fs"
import { resolve } from "node:path"

/**
 * Regression guard for scopes that have been migrated to the Admin-Cockpit
 * visual system. Add files only once their complete render tree follows the
 * rules in docs/specs/admin-cockpit-visual-system.md.
 */
const migratedFiles = [
  "src/features/cockpit/CockpitButton.tsx",
  "src/features/cockpit/AdminCockpitPage.tsx",
  "src/features/cockpit/admin/ui/AdminAction.tsx",
  "src/features/cockpit/admin/ui/adminActionClass.ts",
  "src/features/cockpit/admin/ui/AdminDialog.tsx",
  "src/features/cockpit/admin/ui/AdminConfirmDialog.tsx",
  "src/features/cockpit/admin/ui/AdminFeedback.tsx",
  "src/features/cockpit/admin/ui/AdminField.tsx",
  "src/features/cockpit/admin/ui/AdminPanel.tsx",
  "src/features/cockpit/admin/ui/AdminStat.tsx",
  "src/features/cockpit/admin/ui/AdminStatus.tsx",
  "src/features/cockpit/admin/SystemOverlay.tsx",
  "src/features/cockpit/admin/SystemSettingsOverlay.tsx",
  "src/features/system/SystemPage.tsx",
  "src/features/system/SettingsPage.tsx",
  "src/features/system/StatCard.tsx",
  "src/features/system/HealthBar.tsx",
  "src/features/system/_systemHelpers.tsx",
  "src/features/system/systemFormat.ts",
  "src/features/system/VoiceInstallModal.tsx",
  "src/features/system/AgentLinkCard.tsx",
  "src/features/system/_AgentLinkKnownAgents.tsx",
  "src/features/system/TailscaleCard.tsx",
  "src/features/system/_TailscaleConnectedView.tsx",
  "src/features/system/_TailscaleInviteSection.tsx",
  "src/features/system/_TailscaleLoginForm.tsx",
  "src/features/system/BridgeCard.tsx",
  "src/features/system/SambaCard.tsx",
  "src/features/system/BackupCard.tsx",
  "src/features/system/BackupRestoreModal.tsx",
  "src/features/system/MigrationCard.tsx",
  "src/features/system/MigrationModal.tsx",
  "src/features/cockpit/admin/UsersOverlay.tsx",
  "src/features/users/UsersPage.tsx",
  "src/features/users/NewUserDialog.tsx",
  "src/features/users/EditUserDialog.tsx",
  "src/features/users/ChangePasswordDialog.tsx",
  "src/features/users/ApiKeysSection.tsx",
  "src/i18n/HelpButton.tsx",
  "src/i18n/HelpDrawer.tsx",
  "src/shared/RestartModal.tsx",
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
