export type Article = {
  id: number
  category: string
  source_url: string
  title: string
  summary?: string | null
  published_at?: string | null
  scraped_at: string
}

export type ArticleDetail = Article & {
  content_html?: string | null
  content_text?: string | null
}

export type Agent = { id: string; name: string }

export type ChatResponse = {
  agent_id: string
  reply: string
  citations: Array<{
    article_id: number
    title: string
    source_url: string
    score: number
    snippet: string
  }>
  session_key?: string | null
  trace?: Array<{
    agent: string
    name?: string
    output?: any
  }>
}

export type TechStatus = {
  ok: boolean
  app: string
  llm?: { enabled: boolean; provider: string; model: string | null }
  langchain?: { enabled: boolean }
  mcp?: { tools: string[] }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

export const api = {
  health: () => apiFetch<TechStatus>('/api/health'),

  listArticles: (params: { category?: string; q?: string; limit?: number }) => {
    const usp = new URLSearchParams()
    if (params.category) usp.set('category', params.category)
    if (params.q) usp.set('q', params.q)
    if (params.limit) usp.set('limit', String(params.limit))
    return apiFetch<Article[]>(`/api/articles?${usp.toString()}`)
  },

  getArticle: (id: number) => apiFetch<ArticleDetail>(`/api/articles/${id}`),

  listAgents: () => apiFetch<Agent[]>('/api/agents'),

  chat: (req: { agent_id: string; message: string; session_key?: string }) =>
    apiFetch<ChatResponse>('/api/agents/chat', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  chatHistory: (session_key: string, limit = 80) =>
    apiFetch<Array<{ role: 'user' | 'agent'; content: string; created_at: string }>>(
      `/api/agents/history?session_key=${encodeURIComponent(session_key)}&limit=${limit}`,
    ),

  clearChat: (session_key: string, delete_session = false) =>
    apiFetch<{ ok: boolean; cleared: number; deleted_session?: boolean }>(
      `/api/agents/clear?session_key=${encodeURIComponent(session_key)}&delete_session=${delete_session ? 'true' : 'false'}`,
      { method: 'POST' },
    ),

  purgeAllChats: () =>
    apiFetch<{ ok: boolean; deleted_messages: number; deleted_sessions: number }>(`/api/agents/purge`, {
      method: 'POST',
    }),

  adminScrape: (req: { categories?: string[]; max_pages: number }, token: string) =>
    apiFetch<{ created: number; updated: number; skipped: number; errors: string[] }>('/api/admin/scrape', {
      method: 'POST',
      headers: { 'X-Admin-Token': token },
      body: JSON.stringify(req),
    }),

  adminPing: (token: string) => apiFetch<{ ok: boolean }>('/api/admin/ping', { headers: { 'X-Admin-Token': token } }),

  adminListArticles: (token: string) =>
    apiFetch<
      Array<{
        id: number
        category: string
        title: string
        summary: string | null
        published_at: string | null
        source_url: string
        is_manual: boolean
      }>
    >('/api/admin/articles?limit=200', { headers: { 'X-Admin-Token': token } }),

  adminCreateArticle: (
    token: string,
    payload: {
      category: string
      title: string
      summary?: string | null
      content_text?: string | null
      content_html?: string | null
      published_at?: string | null
    },
  ) =>
    apiFetch<{ id: number }>('/api/admin/articles', {
      method: 'POST',
      headers: { 'X-Admin-Token': token },
      body: JSON.stringify(payload),
    }),

  adminUpdateArticle: (
    token: string,
    id: number,
    payload: {
      category?: string
      title?: string
      summary?: string | null
      content_text?: string | null
      content_html?: string | null
      published_at?: string | null
    },
  ) =>
    apiFetch<{ ok: boolean }>(`/api/admin/articles/${id}`, {
      method: 'PATCH',
      headers: { 'X-Admin-Token': token },
      body: JSON.stringify(payload),
    }),

  adminDeleteArticle: (token: string, id: number) =>
    apiFetch<{ ok: boolean }>(`/api/admin/articles/${id}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Token': token },
    }),

  adminPurgeChat: (token: string) =>
    apiFetch<{ ok: boolean; deleted_messages: number; deleted_sessions: number }>('/api/admin/chat/purge', {
      method: 'POST',
      headers: { 'X-Admin-Token': token },
    }),
}

