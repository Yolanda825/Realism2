import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import UploadPage from './pages/UploadPage.jsx'
import ResultPage from './pages/ResultPage.jsx'
import ParallaxBackground from './components/effects/ParallaxBackground.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <ParallaxBackground />
      <div className="min-h-screen flex flex-col font-sans relative">
        <header className="bg-white/5 backdrop-blur-xl border-b border-white/20 text-white shadow">
          <div className="container mx-auto px-6 py-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">🎯</div>
              <div className="text-xl font-semibold tracking-wide">Realism Studio</div>
            </div>
            <div className="text-sm opacity-90">高端企业级图像真实感增强引擎</div>
          </div>
        </header>
        <main className="flex-1 container mx-auto px-6 py-8">
          <Routes>
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/result" element={<ResultPage />} />
            <Route path="*" element={<Navigate to="/upload" replace />} />
          </Routes>
        </main>
        <footer className="text-center py-6 text-xs text-slate-300">© Realism Studio</footer>
      </div>
    </BrowserRouter>
  )
}
