export interface InstallParam {
  key: string
  label: string
  type: "string" | "password" | "number"
  placeholder?: string
  required: boolean
  description?: string
}

export interface Extension {
  id: string
  name: string
  description: string
  icon: string
  category: string
  install_script: string
  uninstall_script?: string
  service?: string
  health_url?: string | null
  open_url?: string | null
  installed_check: string
  install_params: InstallParam[]
  installed: boolean
  active: boolean
  healthy: boolean
}

export const CATEGORIES: { id: string; label: string }[] = [
  { id: "all", label: "Alle" },
  { id: "tools", label: "Tools" },
  { id: "ai", label: "KI" },
  { id: "network", label: "Netzwerk" },
  { id: "security", label: "Sicherheit" },
  { id: "productivity", label: "Produktivität" },
  { id: "media", label: "Media" },
  { id: "gaming", label: "Gaming" },
]
