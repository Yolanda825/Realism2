import React, { useRef } from 'react'
import useReducedMotion from '../../hooks/useReducedMotion.js'

export default function Tilt({ children, maxTilt = 4, disabled = false, className = '' }) {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const active = !disabled && !reduce
  let rafId = null

  const onMove = (e) => {
    if (!active) return
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = e.clientX - cx
    const dy = e.clientY - cy
    const rx = Math.max(Math.min((-dy / rect.height) * maxTilt, maxTilt), -maxTilt)
    const ry = Math.max(Math.min((dx / rect.width) * maxTilt, maxTilt), -maxTilt)
    if (rafId) cancelAnimationFrame(rafId)
    rafId = requestAnimationFrame(() => {
      el.style.transform = `perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(0)`
    })
  }

  const onLeave = () => {
    const el = ref.current
    if (!el) return
    if (rafId) cancelAnimationFrame(rafId)
    el.style.transform = 'perspective(800px) translateZ(0)'
  }

  return (
    <div ref={ref} onMouseMove={onMove} onMouseLeave={onLeave} className={className}>
      {children}
    </div>
  )
}
