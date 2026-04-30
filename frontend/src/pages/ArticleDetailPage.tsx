import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type ArticleDetail } from '../lib/api'

function formatDate(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 10)
}

export function ArticleDetailPage() {
  const { id } = useParams()
  const articleId = Number(id)
  const [data, setData] = useState<ArticleDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string>('')

  useEffect(() => {
    if (!Number.isFinite(articleId)) return
    setLoading(true)
    setErr('')
    api.getArticle(articleId)
      .then(setData)
      .catch((e) => setErr(String(e?.message ?? e)))
      .finally(() => setLoading(false))
  }, [articleId])

  const backTo = useMemo(() => {
    const category = data?.category ?? 'notices'
    return `/articles/${category}`
  }, [data?.category])

  if (!Number.isFinite(articleId)) {
    return <div className="text-sm text-red-700">无效的文章 ID。</div>
  }

  if (loading) return <div className="text-sm text-slate-600">加载中…</div>
  if (err) return <div className="text-sm text-red-700">加载失败：{err}</div>
  if (!data) return <div className="text-sm text-slate-600">文章不存在。</div>

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to={backTo} className="text-sm font-semibold text-brand-700 hover:text-brand-800">
          ← 返回列表
        </Link>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="text-xl font-semibold text-slate-900">{data.title}</div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>栏目：{data.category}</span>
          <span>日期：{formatDate(data.published_at)}</span>
        </div>

        <div className="mt-4">
          <div
            className="prose prose-slate max-w-none"
            dangerouslySetInnerHTML={{ __html: data.content_html || '<div>（暂无正文）</div>' }}
          />
        </div>
      </div>
    </div>
  )
}

