import React, { useCallback, useEffect, useState } from 'react'
import { trackEvent } from '../api.js'

export default function UploadPanel({ onFile, imagePreview }) {
  const [dragOver, setDragOver] = useState(false)

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    trackEvent('upload_click')
    if (e.dataTransfer?.files?.length) {
      const f = e.dataTransfer.files[0]
      if (!f.type.startsWith('image/')) return
      const reader = new FileReader()
      reader.onload = (ev) => {
        onFile(f, ev.target.result)
      }
      reader.readAsDataURL(f)
    }
  }, [onFile])

  const onChange = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    trackEvent('upload_click')
    if (!f.type.startsWith('image/')) return
    const reader = new FileReader()
    reader.onload = (ev) => onFile(f, ev.target.result)
    reader.readAsDataURL(f)
  }

  return (
    <div className="space-y-4">
      <div
        className={`h-64 rounded-xl border-2 border-dashed ${dragOver ? 'border-sky-300' : 'border-white/20'} bg-white/5 flex items-center justify-center cursor-pointer hover:bg-white/10`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => { trackEvent('upload_click'); document.getElementById('hiddenFileInput')?.click() }}
      >
        <div className="text-center">
          <div className="text-6xl mb-2">📷</div>
          <div className="text-lg">点击上传图片或拖放到此区域</div>
          <div className="text-sm text-slate-400 mt-1">支持 JPG/PNG/WebP</div>
        </div>
      </div>
      <input id="hiddenFileInput" type="file" accept="image/*" className="hidden" onChange={onChange} />
      {imagePreview && (
        <div className="flex items-center gap-4" aria-label="image-preview">
          <img src={imagePreview} alt="预览" className="h-40 object-contain rounded-md shadow" />
        </div>
      )}
    </div>
  )
}
