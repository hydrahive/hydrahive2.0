export interface WikiPage {
  slug: string
  title: string
  body: string
  tags: string[]
  entities: string[]
  source_url: string
  author: string
  created_at: string
  updated_at: string
  backlinks: string[]
  snippet?: string
}

export interface WikiPageIn {
  title: string
  body: string
  tags: string[]
  entities: string[]
  source_url: string
  slug?: string
}
