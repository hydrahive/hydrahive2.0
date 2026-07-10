import { readFileSync } from "node:fs"
import { join } from "node:path"

const root = new URL("..", import.meta.url).pathname
const checks = [
  {
    file: "src/features/buddy/BuddyPage.tsx",
    forbidden: [
      "onClick={() => handleSend(\"Was liegt an",
      "onClick={() => handleSend(\"Idee merken",
      "onClick={() => onSend(\"/game",
      "onClick={() => onSend(\"/music",
      "onClick={() => onSend(\"Was liegt",
    ],
  },
  {
    file: "src/features/cockpit/MediaCockpitPage.tsx",
    forbidden: ["handleSend(", "chat.send(", "buddyApi.logCmd("],
  },
  {
    file: "src/features/cockpit/VaultCockpitPage.tsx",
    forbidden: ["handleSend(", "chat.send(", "buddyApi.logCmd("],
  },
  {
    file: "src/features/cockpit/AdminCockpitPage.tsx",
    forbidden: ["handleSend(", "chat.send(", "buddyApi.logCmd("],
  },
]

const failures = []
for (const check of checks) {
  const text = readFileSync(join(root, check.file), "utf8")
  for (const needle of check.forbidden) {
    if (text.includes(needle)) failures.push(`${check.file}: forbidden auto-LLM trigger: ${needle}`)
  }
}

if (failures.length) {
  console.error("Cockpit offline-first guard failed:")
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log("Cockpit offline-first guard passed")
