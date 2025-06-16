import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Callback from './pages/Callback.jsx'
import AnalyzeOptions from './pages/AnalyzeOptions.jsx'
import AnalyzeLiked from './pages/AnalyzeLiked.jsx'
import ResultPage from './pages/ResultPage.jsx'
import AnalyzePage from './pages/AnalyzePage.jsx'
import { UserProvider } from './UserContext.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <UserProvider>
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
    </UserProvider>
function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<App />} />
        <Route path="/callback" element={<Callback />} />
        <Route path="/analyze" element={<AnalyzeOptions />} />
        <Route path="/analyze/liked" element={<AnalyzeLiked />} />
        <Route path="/result/:analysisId" element={<ResultPage />} />
        <Route path="/analyze/result/:analysisId" element={<AnalyzePage />} />
      </Routes>
    </AnimatePresence>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AnimatedRoutes />
    </BrowserRouter>
  </React.StrictMode>,
)
