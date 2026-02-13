import React, { useRef } from 'react'
import useReducedMotion from '../../hooks/useReducedMotion.js'

export default function SpotlightCard({ children, intensity = 0.15, disabled = false, className = '' }) {
  const ref = useRef(null)
  const reduce = useReducedMotion()

  const active = !disabled && !reduce
  let rafId = null

  const onMove = (e) => {
    if (!active) return
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    if (rafId) cancelAnimationFrame(rafId)
    rafId = requestAnimationFrame(() => {
      el.style.backgroundImage = `radial-gradient(300px circle at ${x}px ${y}px, rgba(56,189,248,${intensity}), transparent 60%)`
    })
  }

  const onLeave = () => {
    const el = ref.current
    if (!el) return
    if (rafId) cancelAnimationFrame(rafId)
    el.style.backgroundImage = ''
  }

  const base = 'bg-white/5 backdrop-blur-xl border border-white/20 rounded-xl shadow-lg'

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={`${base} ${className}`}
      style={active ? undefined : undefined}
    >
      {children}
    </div>
  )
}
