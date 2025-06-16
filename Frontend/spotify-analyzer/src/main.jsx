import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Callback from './pages/Callback.jsx';
import AnalyzeOptions from './pages/AnalyzeOptions.jsx';
import AnalyzeLiked from './pages/AnalyzeLiked.jsx';
import AnalyzePlaylist from './pages/AnalyzePlaylist.jsx';
import ResultPage from './pages/ResultPage.jsx';
import AnalyzePage from './pages/AnalyzePage.jsx';
import History from './pages/History.jsx';
import Layout from './components/Layout.jsx';
import { UserProvider } from './UserContext.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<App />} />
            <Route path="/callback" element={<Callback />} />
          <Route path="/analyze" element={<AnalyzeOptions />} />
          <Route path="/analyze/playlist" element={<AnalyzePlaylist />} />
          <Route path="/analyze/liked" element={<AnalyzeLiked />} />
            <Route path="/result/:analysisId" element={<ResultPage />} />
            <Route path="/analyze/result/:analysisId" element={<AnalyzePage />} />
            <Route path="/history" element={<History />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  </React.StrictMode>,
);
