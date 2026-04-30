import { Link, NavLink, Outlet } from 'react-router-dom'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded-md px-3 py-2 text-sm font-medium transition',
    isActive ? 'bg-brand-600 text-white' : 'text-slate-700 hover:bg-white hover:text-slate-900',
  ].join(' ')

export function Layout() {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-sm font-bold text-white">
              信电
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-slate-900">浙江工商大学</div>
              <div className="text-xs text-slate-600">信息与电子工程学院</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-2 md:flex">
            <NavLink to="/" className={navLinkClass} end>
              首页
            </NavLink>
            <NavLink to="/articles/notices" className={navLinkClass}>
              通知公告
            </NavLink>
            <NavLink to="/articles/news" className={navLinkClass}>
              学院新闻
            </NavLink>
            <NavLink to="/agents" className={navLinkClass}>
              智能体中心
            </NavLink>
            <NavLink to="/admin/content" className={navLinkClass}>
              内容管理
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="container-page py-8">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="container-page py-8 text-xs text-slate-600">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              © {new Date().getFullYear()} 浙江工商大学信息与电子工程学院
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

