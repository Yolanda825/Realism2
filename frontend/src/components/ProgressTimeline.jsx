import React from 'react'

const steps = ['上传', '分析', '生成', '完成']

export default function ProgressTimeline({ currentStep = 0, failed = false }) {
  return (
    <div className="grid grid-cols-4 gap-3">
      {steps.map((label, idx) => {
        const isCurrent = idx === currentStep
        const base = 'text-sm rounded-md px-3 py-2 border'
        const okStyles = isCurrent ? 'text-sky-300 border-sky-400/30' : 'text-slate-300 border-white/10'
        const failStyles = failed && isCurrent ? 'text-rose-300 border-rose-400/30' : ''
        return (
          <div key={label} className={`${base} ${okStyles} ${failStyles}`}>{label}</div>
        )
      })}
    </div>
  )
}
