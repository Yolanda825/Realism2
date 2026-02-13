import React from 'react'
import { trackEvent } from '../api.js'

export default function ResultPanel({ result, onDownload, imagePreview, error, loading }) {
  const enhanced = result?.enhancement_result?.enhanced_image_base64
  const success = result?.enhancement_result?.success
  const show = !!result
  return (
    <div className="space-y-4">
      <div className="p-4 rounded-xl bg-white/5 border border-white/20 shadow-md" aria-label="result-header">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold">分析结果</h3>
          {loading ? <span className="text-sm text-sky-300">处理中...</span> : null}
        </div>
        {error && <div className="text-sm text-red-200 bg-red-900/20 p-2 rounded">{error}</div>}
      </div>
      {show && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-2">
          <div className="bg-white/5 rounded-xl p-4 border border-white/20">
            <div className="text-sm font-semibold mb-2">原始图像</div>
            <div className="h-64 bg-black/20 rounded-md flex items-center justify-center">
              {imagePreview ? <img src={imagePreview} alt="原始" className="h-full max-w-full object-contain"/> : <span>暂无预览</span>}
            </div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 border border-white/20">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-semibold">增强后图像</div>
              <button 
                className="text-xs px-3 py-1 bg-sky-600 rounded text-white hover:bg-sky-500 transition" 
                onClick={() => { trackEvent('download_click'); onDownload() }} 
                disabled={!enhanced || success === false}
              >
                下载
              </button>
            </div>
            <div className="h-64 bg-black/20 rounded-md flex items-center justify-center" aria-label="enhanced">
              {success === false ? (
                <span className="text-red-200">调用失败</span>
              ) : enhanced ? (
                <img src={enhanced.startsWith('data:') ? enhanced : `data:image/jpeg;base64,${enhanced}`} alt="增强后" className="h-full max-w-full object-contain"/>
              ) : (
                <span>暂无增强图像</span>
              )}
            </div>
          </div>
        </div>
      )}
      <div className="bg-white/5 rounded-xl p-4 border border-white/20">
        <div className="text-sm font-semibold mb-2">结果细节</div>
        <pre className="text-xs bg-black/60 text-white p-2 rounded-md overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
      </div>
    </div>
  )
}
