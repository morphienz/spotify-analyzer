import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Callback from './pages/Callback.jsx'
import AnalyzeOptions from './pages/AnalyzeOptions.jsx'
import AnalyzeLiked from './pages/AnalyzeLiked.jsx'
import ResultPage from './pages/ResultPage.jsx'
import AnalyzePage from './pages/AnalyzePage.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/callback" element={<Callback />} />
        <Route path="/analyze" element={<AnalyzeOptions />} />
        <Route path="/analyze/liked" element={<AnalyzeLiked />} />
        <Route path="/result/:analysisId" element={<ResultPage />} />
        <Route path="/analyze/result/:analysisId" element={<AnalyzePage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
