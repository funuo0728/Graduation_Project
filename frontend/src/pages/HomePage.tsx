import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Article } from '../lib/api'

function formatDate(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 10)
}

function SectionHeader(props: { title: string; to: string; hint?: string }) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <div className="text-lg font-semibold text-slate-900">{props.title}</div>
        {props.hint ? <div className="text-sm text-slate-600">{props.hint}</div> : null}
      </div>
      <Link to={props.to} className="text-sm font-medium text-brand-700 hover:text-brand-800">
        查看更多 →
      </Link>
    </div>
  )
}

function ArticleList(props: { items: Article[] }) {
  return (
    <div className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
      {props.items.map((a) => (
        <Link
          key={a.id}
          to={`/article/${a.id}`}
          className="block px-4 py-3 transition hover:bg-slate-50"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-slate-900">{a.title}</div>
              {a.summary ? (
                <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-600">{a.summary}</div>
              ) : null}
            </div>
            <div className="shrink-0 text-xs tabular-nums text-slate-500">{formatDate(a.published_at)}</div>
          </div>
        </Link>
      ))}
    </div>
  )
}

export function HomePage() {
  const [notices, setNotices] = useState<Article[]>([])
  const [news, setNews] = useState<Article[]>([])
  const [health, setHealth] = useState<string>('')

  useEffect(() => {
    api.health()
      .then((h) => setHealth(h.app))
      .catch(() => setHealth(''))
    api.listArticles({ category: 'notices', limit: 8 }).then(setNotices).catch(() => setNotices([]))
    api.listArticles({ category: 'news', limit: 8 }).then(setNews).catch(() => setNews([]))
  }, [])

  const shortcuts = useMemo(
    () => [
      { title: '通知公告', desc: '公示公告 / 办事提醒', to: '/articles/notices' },
      { title: '教师通知', desc: '教学科研相关通知', to: '/articles/teacher_notices' },
      { title: '学生通知', desc: '评奖评优 / 活动 / 事务', to: '/articles/student_notices' },
      { title: '智能体中心', desc: '多智能体协作问答 / 办事咨询', to: '/agents' },
    ],
    [],
  )

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-brand-700 via-brand-600 to-slate-900 px-6 py-10 text-white md:px-10">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs">
            <span className="font-semibold">学院门户</span>
            <span className="opacity-80">·</span>
            <span className="opacity-90">智能体增强服务</span>
            {health ? <span className="opacity-70">（后端：{health}）</span> : null}
          </div>
          <h1 className="mt-4 text-2xl font-semibold leading-snug md:text-4xl">
            浙江工商大学信息与电子工程学院
          </h1>
          <p className="mt-3 text-sm leading-6 text-white/85 md:text-base">
            为师生提供信息查询、办事咨询与智能问答服务。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/agents"
              className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-white/90"
            >
              进入智能体中心
            </Link>
          </div>
        </div>
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        {shortcuts.map((s) => (
          <Link
            key={s.to}
            to={s.to}
            className="group rounded-2xl border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-sm"
          >
            <div className="text-sm font-semibold text-slate-900 group-hover:text-brand-700">
              {s.title}
            </div>
            <div className="mt-1 text-xs leading-5 text-slate-600">{s.desc}</div>
          </Link>
        ))}
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="space-y-3">
          <SectionHeader title="通知公告" to="/articles/notices" />
          <ArticleList items={notices} />
        </div>
        <div className="space-y-3">
          <SectionHeader title="学院新闻" to="/articles/news" hint="活动报道 / 学科科研 / 教学动态" />
          <ArticleList items={news} />
        </div>
      </section>
    </div>
  )
}

