import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

const CATEGORY_OPTIONS = [
  { id: 'notices', label: '通知公告' },
  { id: 'news', label: '学院新闻' },
  { id: 'teacher_notices', label: '教师通知' },
  { id: 'student_notices', label: '学生通知' },
]

function getAdminToken() {
  return localStorage.getItem('admin_token') || ''
}

function askAdminToken(): string | null {
  const cur = getAdminToken()
  const next = window.prompt('请输入管理员口令（ADMIN_TOKEN）', cur)
  if (!next) return null
  localStorage.setItem('admin_token', next)
  return next
}

export function AdminContentPage() {
  const [token, setToken] = useState(getAdminToken())
  const [authed, setAuthed] = useState(false)
  const [checking, setChecking] = useState(false)
  const [items, setItems] = useState<
    Array<{
      id: number
      category: string
      title: string
      summary: string | null
      published_at: string | null
      source_url: string
      is_manual: boolean
    }>
  >([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const [form, setForm] = useState({
    category: 'notices',
    title: '',
    summary: '',
    content_text: '',
    published_at: '',
  })

  async function refresh(t: string) {
    setLoading(true)
    setErr('')
    try {
      const list = await api.adminListArticles(t)
      setItems(list)
    } catch (e: any) {
      setErr(String(e?.message ?? e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!token) return
    setChecking(true)
    api.adminPing(token)
      .then(() => setAuthed(true))
      .then(() => refresh(token))
      .catch(() => setAuthed(false))
      .finally(() => setChecking(false))
  }, [token])

  const manualItems = useMemo(() => items.filter((x) => x.is_manual), [items])

  async function ensureToken() {
    if (token) return token
    const t = askAdminToken()
    if (!t) return null
    setToken(t)
    return t
  }

  async function create() {
    const t = await ensureToken()
    if (!t) return
    if (!form.title.trim()) {
      window.alert('请填写标题')
      return
    }
    setLoading(true)
    setErr('')
    try {
      await api.adminCreateArticle(t, {
        category: form.category,
        title: form.title.trim(),
        summary: form.summary.trim() || null,
        content_text: form.content_text.trim() || null,
        published_at: form.published_at ? new Date(form.published_at).toISOString() : null,
      })
      setForm((f) => ({ ...f, title: '', summary: '', content_text: '' }))
      await refresh(t)
      window.alert('发布成功')
    } catch (e: any) {
      setErr(String(e?.message ?? e))
      window.alert(`发布失败：${String(e?.message ?? e)}`)
    } finally {
      setLoading(false)
    }
  }

  async function remove(id: number) {
    const t = await ensureToken()
    if (!t) return
    if (!window.confirm('确认删除该条内容？')) return
    setLoading(true)
    setErr('')
    try {
      await api.adminDeleteArticle(t, id)
      await refresh(t)
    } catch (e: any) {
      setErr(String(e?.message ?? e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xl font-semibold text-slate-900">内容管理</div>
          <div className="mt-1 text-sm text-slate-600">管理员可在此发布与维护本站内容。</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {checking ? (
            <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
              验证中…
            </span>
          ) : authed ? (
            <span className="rounded-full bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
              已验证
            </span>
          ) : (
            <span className="rounded-full bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
              未验证
            </span>
          )}
          <button
            type="button"
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            onClick={() => {
              const t = askAdminToken()
              if (t) setToken(t)
            }}
          >
            设置口令
          </button>
          <button
            type="button"
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            onClick={() => {
              localStorage.removeItem('admin_token')
              setToken('')
              setAuthed(false)
              setItems([])
            }}
          >
            退出
          </button>
          <Link
            to="/"
            className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            返回首页
          </Link>
        </div>
      </div>

      {!authed ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <div className="text-sm font-semibold text-slate-900">管理员登录</div>
          <div className="mt-2 text-sm text-slate-600">请输入管理员口令后才能进行发布/删除操作。</div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              onClick={() => {
                const t = askAdminToken()
                if (t) setToken(t)
              }}
            >
              输入口令
            </button>
            <Link
              to="/"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              返回首页
            </Link>
          </div>
          {token ? (
            <div className="mt-3 text-xs text-slate-600">
              当前已保存口令，但验证失败。请检查是否输入正确。
            </div>
          ) : null}
        </div>
      ) : null}

      {authed ? (
        <>
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="text-sm font-semibold text-slate-900">发布新内容</div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="block">
            <div className="text-xs font-semibold text-slate-700">栏目</div>
            <select
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <div className="text-xs font-semibold text-slate-700">发布日期（可选）</div>
            <input
              type="datetime-local"
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
              value={form.published_at}
              onChange={(e) => setForm((f) => ({ ...f, published_at: e.target.value }))}
            />
          </label>
        </div>

        <label className="mt-3 block">
          <div className="text-xs font-semibold text-slate-700">标题</div>
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="例如：关于XX事项的通知"
          />
        </label>

        <label className="mt-3 block">
          <div className="text-xs font-semibold text-slate-700">摘要（可选）</div>
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            value={form.summary}
            onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
            placeholder="用于列表页快速预览"
          />
        </label>

        <label className="mt-3 block">
          <div className="text-xs font-semibold text-slate-700">正文（文本）</div>
          <textarea
            className="mt-2 h-44 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            value={form.content_text}
            onChange={(e) => setForm((f) => ({ ...f, content_text: e.target.value }))}
            placeholder="建议直接粘贴纯文本；需要排版可后续扩展为富文本编辑器。"
          />
        </label>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={create}
            disabled={loading || !authed}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            发布
          </button>
          <button
            type="button"
            onClick={async () => {
              const t = await ensureToken()
              if (t) refresh(t)
            }}
            disabled={loading || !token}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            刷新列表
          </button>
        </div>
        {err ? <div className="mt-3 text-sm text-red-700">错误：{err}</div> : null}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-slate-900">本站手动发布的内容</div>
            <div className="mt-1 text-xs text-slate-600">仅展示 `manual:*` 的文章（可删除）。</div>
          </div>
          <div className="text-xs text-slate-600">共 {manualItems.length} 条</div>
        </div>

        <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
          {loading ? (
            <div className="p-4 text-sm text-slate-600">加载中…</div>
          ) : manualItems.length === 0 ? (
            <div className="p-4 text-sm text-slate-600">暂无手动发布内容。</div>
          ) : (
            <ul className="divide-y divide-slate-200">
              {manualItems.map((x) => (
                <li key={x.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-900">{x.title}</div>
                    <div className="mt-1 text-xs text-slate-600">
                      栏目：{x.category} · ID：{x.id}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      to={`/article/${x.id}`}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      预览
                    </Link>
                    <button
                      type="button"
                      onClick={() => remove(x.id)}
                      disabled={!authed}
                      className="rounded-xl border border-red-200 bg-white px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
                    >
                      删除
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
        </>
      ) : null}
    </div>
  )
}

