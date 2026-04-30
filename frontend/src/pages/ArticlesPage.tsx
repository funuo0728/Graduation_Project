import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, type Article } from '../lib/api'

const CATEGORY_LABELS: Record<string, string> = {
  notices: '通知公告（公示公告）',
  teacher_notices: '教师通知',
  student_notices: '学生通知',
  news: '学院新闻',
}

function formatDate(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 10)
}

export function ArticlesPage() {
  const { category = 'notices' } = useParams()
  const [sp, setSp] = useSearchParams()
  const [items, setItems] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string>('')

  const q = sp.get('q') ?? ''
  const title = CATEGORY_LABELS[category] ?? category

  useEffect(() => {
    setLoading(true)
    setErr('')
    api.listArticles({ category, q: q || undefined, limit: 60 })
      .then(setItems)
      .catch((e) => setErr(String(e?.message ?? e)))
      .finally(() => setLoading(false))
  }, [category, q])

  const tabs = useMemo(
    () => [
      { id: 'notices', label: '通知公告' },
      { id: 'teacher_notices', label: '教师通知' },
      { id: 'student_notices', label: '学生通知' },
      { id: 'news', label: '学院新闻' },
    ],
    [],
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-col items-start justify-between gap-3 md:flex-row md:items-end">
        <div>
          <div className="text-xl font-semibold text-slate-900">{title}</div>
          <div className="mt-1 text-sm text-slate-600">支持关键词搜索（标题/摘要/正文）。</div>
        </div>
        <form
          className="flex w-full max-w-md items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            const form = new FormData(e.currentTarget)
            const nextQ = String(form.get('q') ?? '').trim()
            setSp(nextQ ? { q: nextQ } : {})
          }}
        >
          <input
            name="q"
            defaultValue={q}
            placeholder="搜索：如 奖学金 / 复试 / 公示"
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
          <button
            type="submit"
            className="shrink-0 rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            搜索
          </button>
        </form>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Link
            key={t.id}
            to={`/articles/${t.id}`}
            className={[
              'rounded-full border px-3 py-1 text-xs font-semibold transition',
              t.id === category
                ? 'border-brand-600 bg-brand-600 text-white'
                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300',
            ].join(' ')}
          >
            {t.label}
          </Link>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white">
        {loading ? (
          <div className="p-6 text-sm text-slate-600">加载中…</div>
        ) : err ? (
          <div className="p-6 text-sm text-red-700">加载失败：{err}</div>
        ) : items.length === 0 ? (
          <div className="p-6 text-sm text-slate-600">暂无数据。</div>
        ) : (
          <ul className="divide-y divide-slate-200">
            {items.map((a) => (
              <li key={a.id} className="p-4 hover:bg-slate-50">
                <Link to={`/article/${a.id}`} className="block">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-900">{a.title}</div>
                      {a.summary ? (
                        <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-600">
                          {a.summary}
                        </div>
                      ) : null}
                    </div>
                    <div className="shrink-0 text-xs tabular-nums text-slate-500">
                      {formatDate(a.published_at)}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

