import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ChatResponse } from '../lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Msg = { role: 'user' | 'agent'; content: string }
type SessionMeta = { key: string; name: string; updatedAt: number }

function normalizeMarkdown(md: string) {
  // Fix common LLM formatting issues that break markdown rendering.
  // 1) "1.\nTitle" -> "1. Title"
  // 2) "-\nItem" -> "- Item"
  // 3) collapse excessive blank lines
  return md
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/(\n|^)(\d+)\.\s*\n+\s*/g, '$1$2. ')
    .replace(/(\n|^)([-*])\s*\n+\s*/g, '$1$2 ')
}

const CACHE_PREFIX = 'chat_cache_v1:'
const SESSIONS_KEY = 'chat_sessions_v1'
const CURRENT_SESSION_KEY = 'chat_current_session_v1'

function defaultWelcome(): Msg[] {
  return [
    {
      role: 'agent',
      content:
        '你好，我是学院智能助手。你提问后，我会在后台调用多个专家智能体（检索/事务办理/学业成长/校验）协同完成，并附上引用来源。',
    },
  ]
}

function loadSessions(): SessionMeta[] {
  const raw = localStorage.getItem(SESSIONS_KEY)
  if (!raw) return []
  try {
    const v = JSON.parse(raw) as SessionMeta[]
    if (Array.isArray(v)) return v
  } catch {}
  return []
}

function saveSessions(sessions: SessionMeta[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

function ensureDefaultSession(): { sessions: SessionMeta[]; current: string } {
  const sessions = loadSessions()
  let current = localStorage.getItem(CURRENT_SESSION_KEY) || ''
  if (sessions.length === 0) {
    const key = crypto.randomUUID()
    const meta: SessionMeta = { key, name: '会话 1', updatedAt: Date.now() }
    const next = [meta]
    saveSessions(next)
    localStorage.setItem(CURRENT_SESSION_KEY, key)
    return { sessions: next, current: key }
  }
  if (!current || !sessions.some((s) => s.key === current)) {
    current = sessions[0].key
    localStorage.setItem(CURRENT_SESSION_KEY, current)
  }
  return { sessions, current }
}

export function AgentsPage() {
  const boot = useMemo(() => ensureDefaultSession(), [])
  const [sessions, setSessions] = useState<SessionMeta[]>(boot.sessions)
  const [sessionKey, setSessionKey] = useState<string>(boot.current)
  const [msgs, setMsgs] = useState<Msg[]>(() => {
    const cached = localStorage.getItem(CACHE_PREFIX + boot.current)
    if (cached) {
      try {
        const parsed = JSON.parse(cached) as Msg[]
        if (Array.isArray(parsed) && parsed.length) return parsed
      } catch {}
    }
    return defaultWelcome()
  })
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState<ChatResponse | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, busy])

  // Persist to local cache (fast restore on navigation)
  useEffect(() => {
    try {
      localStorage.setItem(CACHE_PREFIX + sessionKey, JSON.stringify(msgs.slice(-120)))
    } catch {}
  }, [msgs, sessionKey])

  // Save current session selection
  useEffect(() => {
    localStorage.setItem(CURRENT_SESSION_KEY, sessionKey)
  }, [sessionKey])

  // Best-effort server history sync (DB persisted) on session change
  useEffect(() => {
    // restore from local cache first
    const cached = localStorage.getItem(CACHE_PREFIX + sessionKey)
    if (cached) {
      try {
        const parsed = JSON.parse(cached) as Msg[]
        if (Array.isArray(parsed) && parsed.length) setMsgs(parsed)
      } catch {}
    } else {
      setMsgs(defaultWelcome())
    }
    setLast(null)

    api.chatHistory(sessionKey, 120)
      .then((hist) => {
        if (!hist.length) return
        const mapped: Msg[] = hist.map((h) => ({ role: h.role, content: h.content }))
        setMsgs((cur) => {
          // If we already have user-generated messages, keep them.
          // Otherwise replace with server history (better continuity).
          if (cur.length > 1) return cur
          return mapped.length ? mapped : cur
        })
      })
      .catch(() => {})
  }, [sessionKey])

  const agentName = useMemo(() => '学院智能助手', [])

  async function send() {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setLast(null)
    setMsgs((m) => [...m, { role: 'user', content: text }])
    setBusy(true)
    try {
      const res = await api.chat({ agent_id: 'assistant', message: text, session_key: sessionKey } as any)
      setLast(res)
      setMsgs((m) => [...m, { role: 'agent', content: res.reply }])
    } catch (e: any) {
      setMsgs((m) => [...m, { role: 'agent', content: `请求失败：${String(e?.message ?? e)}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <div className="lg:col-span-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="text-sm font-semibold text-slate-900">会话</div>
          <div className="mt-3 flex gap-2">
            <select
              value={sessionKey}
              onChange={(e) => setSessionKey(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            >
              {sessions
                .slice()
                .sort((a, b) => b.updatedAt - a.updatedAt)
                .map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.name}
                  </option>
                ))}
            </select>
            <button
              type="button"
              className="shrink-0 rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              onClick={() => {
                const key = crypto.randomUUID()
                const name = `会话 ${sessions.length + 1}`
                const meta: SessionMeta = { key, name, updatedAt: Date.now() }
                const next = [meta, ...sessions]
                setSessions(next)
                saveSessions(next)
                setSessionKey(key)
                localStorage.removeItem(CACHE_PREFIX + key)
                setMsgs(defaultWelcome())
              }}
            >
              新建
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              onClick={async () => {
                if (!window.confirm('确认清空当前会话记录？')) return
                await api.clearChat(sessionKey, false).catch(() => {})
                localStorage.removeItem(CACHE_PREFIX + sessionKey)
                setMsgs(defaultWelcome())
                setLast(null)
              }}
            >
              清空当前
            </button>
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              onClick={async () => {
                if (!window.confirm('确认清空全部会话与历史记录？此操作不可恢复。')) return
                await api.purgeAllChats()
                // clear local caches
                for (const s of sessions) localStorage.removeItem(CACHE_PREFIX + s.key)
                localStorage.removeItem(SESSIONS_KEY)
                localStorage.removeItem(CURRENT_SESSION_KEY)
                const boot2 = ensureDefaultSession()
                setSessions(boot2.sessions)
                setSessionKey(boot2.current)
                setMsgs(defaultWelcome())
                setLast(null)
              }}
            >
              清空全部
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="text-lg font-semibold text-slate-900">学院智能助手</div>
          <div className="mt-1 text-sm leading-6 text-slate-600">
            面向学院师生的智能体服务入口，可用于通知检索、办事咨询与信息归纳。系统会在后台进行多智能体协作。
          </div>

          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-700">
            <div className="font-semibold">提示</div>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>想要更准：请补充年级、事项类型、截止日期、你的卡点。</li>
              <li>默认离线检索模式；配置大模型后会变成“检索增强生成”。</li>
              <li>
                你也可以先去{' '}
                <Link to="/articles/notices" className="font-semibold text-brand-700 hover:text-brand-800">
                  通知公告
                </Link>{' '}
                里查看相关内容再问我。
              </li>
            </ul>
          </div>
        </div>

        {last?.trace?.length ? (
          <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="text-sm font-semibold text-slate-900">协作过程</div>
            <div className="mt-3 space-y-2 text-xs text-slate-700">
              {last.trace.map((t, idx) => (
                <details key={idx} className="rounded-xl border border-slate-200 bg-white p-3">
                  <summary className="cursor-pointer select-none font-semibold text-slate-900">
                    {t.name || t.agent}
                  </summary>
                  <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-5 text-slate-700">
                    {JSON.stringify(t.output ?? {}, null, 2)}
                  </pre>
                </details>
              ))}
            </div>
          </div>
        ) : null}

        {last?.citations?.length ? (
          <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="text-sm font-semibold text-slate-900">引用来源</div>
            <div className="mt-3 space-y-2">
              {last.citations.map((c) => (
                <Link
                  key={c.article_id}
                  to={`/article/${c.article_id}`}
                  className="block rounded-xl border border-slate-200 p-3 text-xs transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <div className="font-semibold text-slate-900">{c.title}</div>
                  <div className="mt-1 text-slate-600">相似度：{c.score.toFixed(3)}</div>
                </Link>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="lg:col-span-8">
        <div className="rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <div className="text-sm font-semibold text-slate-900">{agentName}</div>
          </div>

          <div className="h-[62vh] overflow-y-auto px-5 py-4">
            <div className="space-y-3">
              {msgs.map((m, idx) => (
                <div
                  key={idx}
                  className={[
                    'max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6',
                    m.role === 'user'
                      ? 'ml-auto bg-brand-600 text-white'
                      : 'mr-auto bg-slate-100 text-slate-900',
                  ].join(' ')}
                >
                  {m.role === 'agent' ? (
                    <div className="prose prose-sm prose-slate max-w-none leading-6 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalizeMarkdown(m.content)}</ReactMarkdown>
                    </div>
                  ) : (
                    m.content
                  )}
                </div>
              ))}
              {busy ? <div className="text-xs text-slate-500">对方正在思考…</div> : null}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t border-slate-200 px-5 py-4">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') send()
                }}
                placeholder="输入问题，例如：考研奖学金怎么申请？公示在哪里看？"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <button
                type="button"
                onClick={send}
                disabled={busy}
                className="shrink-0 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                发送
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

