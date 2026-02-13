import React, { useState } from 'react'
import SpotlightCard from '../components/effects/SpotlightCard.jsx'
import UploadPanel from '../components/UploadPanel.jsx'
import { postEnhance, trackEvent } from '../api.js'
import { useNavigate } from 'react-router-dom'

export default function UploadPage() {
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleFile = (file, preview) => {
    setImageFile(file)
    setImagePreview(preview)
    trackEvent('upload_success', { name: file.name, size: file.size, type: file.type })
  }

  const handleGenerate = async () => {
    if (!imageFile) {
      setError('请先上传图片')
      return
    }
    setError(null)
    setLoading(true)
    trackEvent('generate_click')
    try {
      const res = await postEnhance(imageFile)
      trackEvent('generate_success', { hasResult: !!res })
      // 将结果存入 sessionStorage，用于 /result 页面展示
      sessionStorage.setItem('latest_result', JSON.stringify(res))
      navigate('/result')
    } catch (e) {
      setError(e?.message || '生成失败')
      trackEvent('generate_error', { error: e?.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="text-slate-50">
      <SpotlightCard className="p-6" intensity={0.18}>
        <UploadPanel onFile={handleFile} imagePreview={imagePreview} />
      </SpotlightCard>
      <div className="mt-6 flex justify-center">
          <button
            onClick={handleGenerate}
            disabled={!imageFile || loading}
            className={`px-10 py-4 rounded-xl text-lg font-bold shadow-2xl transition-all transform hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/50 ${
              !imageFile || loading
                ? 'bg-slate-500/50 text-slate-300 cursor-not-allowed'
                : 'bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-600 hover:from-sky-400 hover:via-blue-500 hover:to-indigo-500 text-white shadow-sky-500/30'
            }`}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                处理中...
              </span>
            ) : (
              '✨ 生成增强图像'
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-200 text-sm text-center">
            {error}
          </div>
        )}
    </section>
  )
}
