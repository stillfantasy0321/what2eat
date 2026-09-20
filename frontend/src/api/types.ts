export interface ApiFailure { error?: { code?: string; message?: string; request_id?: string } }
export interface SseEvent { event: string; data: Record<string, unknown> }
export interface ServiceStatus {
  app_name: string
  slug: string
  missing: string[]
  capabilities: Record<string, { ready?: boolean; configured?: boolean; model?: string }>
}
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  status: string
  sources?: Record<string, unknown>[]
}
export interface Ingredient { name: string; raw: string; amount?: string | null; unit?: string | null }
export interface Page<T> { items: T[]; page: number; page_size: number; total: number; total_pages: number }
export interface Recipe { id: string; title: string; category: string; ingredients: Ingredient[]; source_url?: string | null; ingredient_status: string; raw_text: string }
