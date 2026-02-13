import React, { useEffect, useState, useMemo } from 'react'
import { motion, useReducedMotion as fmUseReducedMotion } from 'framer-motion'
import ResultPanel from '../components/ResultPanel.jsx'
import { useNavigate } from 'react-router-dom'
import SkeletonShimmer from '../components/effects/SkeletonShimmer.jsx'
import SpotlightCard from '../components/effects/SpotlightCard.jsx'
import ProgressTimeline from '../components/ProgressTimeline.jsx'

export default function ResultPage() {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    try {
      const raw = sessionStorage.getItem('latest_result')
      if (!raw) {
        setError('无可展示结果，请先上传并生成')
        return
      }
      const parsed = JSON.parse(raw)
      setResult(parsed)
    } catch (e) {
      setError('结果解析失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const prefersReduced = fmUseReducedMotion()
  const success = !!result?.enhancement_result?.enhanced_image_base64 && result?.enhancement_result?.success !== false
  const generating = !error && (loading || (!result || (!result?.enhancement_result && !result?.analysis)))
  const currentStep = useMemo(() => {
    if (error) return 2
    if (generating) return 2
    if (success) return 3
    return 1
  }, [error, generating, success])

  const handleDownload = () => {
    if (!result?.enhancement_result?.enhanced_image_base64) return
    const b64 = result.enhancement_result.enhanced_image_base64
    const link = document.createElement('a')
    link.href = b64.startsWith('data:') ? b64 : `data:image/jpeg;base64,${b64}`
    link.download = 'enhanced.jpg'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <section className="text-slate-50">
      <SpotlightCard className="p-6" intensity={0.18}>
        <div className="mb-4 flex items-center justify-between">
          <div className="text-lg font-semibold">增强结果</div>
          <button className="text-xs px-3 py-1 bg-slate-600 rounded text-white hover:bg-slate-500" onClick={() => navigate('/upload')}>返回上传</button>
        </div>
        <div className="mb-4">
          <ProgressTimeline currentStep={currentStep} failed={result && result.enhancement_result && result.enhancement_result.success === false} />
        </div>
        {generating ? (
          <SkeletonShimmer lines={3} height="h-80" />
        ) : (
          <motion.div
            initial={prefersReduced ? false : { opacity: 0, scale: 0.98 }}
            animate={prefersReduced ? {} : { opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          >
            <ResultPanel result={result} onDownload={handleDownload} imagePreview={null} error={error} loading={loading} />
          </motion.div>
        )}
      </SpotlightCard>
    </section>
  )
}
