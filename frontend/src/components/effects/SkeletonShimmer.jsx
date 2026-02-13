import React from 'react'
import useReducedMotion from '../../hooks/useReducedMotion.js'

export default function SkeletonShimmer({ lines = 3, height = 'h-64', className = '' }) {
  const reduce = useReducedMotion()

  const rows = Array.from({ length: lines })
  return (
    <div className={`bg-white/5 border border-white/10 rounded-xl p-4 ${className}`}>
      <div className={`rounded-md bg-black/20 ${height} overflow-hidden`}>
        <div className="p-4 space-y-3">
          {rows.map((_, i) => (
            <div
              key={i}
              className={`h-4 rounded bg-white/[0.08] ${reduce ? '' : 'shimmer'}`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
