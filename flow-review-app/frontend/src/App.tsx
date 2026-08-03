import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/ReviewTask/HomePage'
import NewTaskPage from './pages/ReviewTask/NewTaskPage'
import ReportPage from './pages/ReportView/ReportPage'
import ExpertReviewPage from './pages/ExpertReview/ExpertReviewPage'
import StandardsPage from './pages/ReviewStandards/StandardsPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="tasks/new" element={<NewTaskPage />} />
          <Route path="tasks/:id/report" element={<ReportPage />} />
          <Route path="tasks/:id/review" element={<ExpertReviewPage />} />
          <Route path="standards" element={<StandardsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
