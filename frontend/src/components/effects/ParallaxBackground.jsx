import React from 'react'
import { motion, useScroll, useTransform, useReducedMotion as fmUseReducedMotion } from 'framer-motion'
export default function ParallaxBackground() {
  const prefersReduced = fmUseReducedMotion()
  const { scrollYProgress } = useScroll()

  const ySlow = useTransform(scrollYProgress, [0, 1], [0, -120])
  const yMedium = useTransform(scrollYProgress, [0, 1], [0, -220])
  const yFast = useTransform(scrollYProgress, [0, 1], [0, -360])

  const common = 'absolute rounded-full blur-3xl opacity-60'

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900" />

      <motion.div
        aria-hidden
        className={`${common}`}
        style={{
          width: 800,
          height: 800,
          top: -200,
          left: -200,
          background: 'radial-gradient(closest-side, rgba(56,189,248,0.20), transparent 65%)',
          y: prefersReduced ? 0 : ySlow,
        }}
      />

      <motion.div
        aria-hidden
        className={`${common}`}
        style={{
          width: 900,
          height: 900,
          top: 200,
          right: -250,
          background: 'radial-gradient(closest-side, rgba(99,102,241,0.18), transparent 70%)',
          y: prefersReduced ? 0 : yMedium,
        }}
      />

      <motion.div
        aria-hidden
        className={`${common}`}
        style={{
          width: 900,
          height: 900,
          bottom: -300,
          left: -200,
          background: 'radial-gradient(closest-side, rgba(244,114,182,0.14), transparent 70%)',
          y: prefersReduced ? 0 : yFast,
        }}
      />
    </div>
  )
}
