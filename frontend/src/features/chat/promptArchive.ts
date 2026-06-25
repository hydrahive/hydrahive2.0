import { api } from "@/shared/api-client"

/** Eine Prompt-Kategorie. Spiegelt das Backend-Enum (db/prompt_archive.py). */
export type PromptCategory = "image" | "music" | "system" | "video" | "speech" | "other"

export const PROMPT_CATEGORIES: PromptCategory[] = [
  "image", "music", "system", "video", "speech", "other",
]

/** Ein gespeichertes Prompt-Rezept (volle Form, wie vom Backend geliefert). */
export interface PromptEntry {
  id: string
  user_id: string
  title: string
  category: PromptCategory
  prompt: string
  style_anchor: string | null
  model: string | null
  params: Record<string, unknown>
  seed: number | null
  tags: string[]
  notes: string | null
  sample_path: string | null
  is_public: boolean
  use_count: number
  created_at: string
  updated_at: string
}

/** Felder die beim Anlegen/Bearbeiten gesendet werden. */
export interface PromptInput {
  title: string
  category: PromptCategory
  prompt: string
  style_anchor?: string | null
  model?: string | null
  params?: Record<string, unknown> | null
  seed?: number | null
  tags?: string[] | null
  notes?: string | null
  sample_path?: string | null
  is_public?: boolean
}

export const promptArchiveApi = {
  list: (opts?: { category?: PromptCategory; q?: string; include_public?: boolean }) => {
    const p = new URLSearchParams()
    if (opts?.category) p.set("category", opts.category)
    if (opts?.q) p.set("q", opts.q)
    if (opts?.include_public === false) p.set("include_public", "false")
    const qs = p.toString()
    return api.get<{ prompts: PromptEntry[]; count: number }>(`/prompts${qs ? `?${qs}` : ""}`)
  },
  create: (body: PromptInput) => api.post<PromptEntry>("/prompts", body),
  update: (id: string, body: Partial<PromptInput>) => api.patch<PromptEntry>(`/prompts/${id}`, body),
  remove: (id: string) => api.delete<void>(`/prompts/${id}`),
  markUsed: (id: string) => api.post<{ ok: boolean }>(`/prompts/${id}/use`, {}),
}
