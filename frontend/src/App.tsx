import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ArticlesPage } from './pages/ArticlesPage'
import { ArticleDetailPage } from './pages/ArticleDetailPage'
import { AgentsPage } from './pages/AgentsPage'
import { AdminContentPage } from './pages/AdminContentPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/articles/:category" element={<ArticlesPage />} />
        <Route path="/article/:id" element={<ArticleDetailPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/admin/content" element={<AdminContentPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
