import React from 'react'
import { motion, useReducedMotion as fmUseReducedMotion } from 'framer-motion'
import GlowLayer from './effects/GlowLayer.jsx'

export default function HeroLampHeader({ title = 'Realism Studio', subtitle = '高端企业级图像真实感增强引擎', ctaLabel = '开始体验', onCTAClick }) {
  const prefersReduced = fmUseReducedMotion()

  return (
    <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-2xl border border-white/20">
      <GlowLayer className="-z-0" />
      <div className="relative z-10 p-10">
        <motion.h1
          initial={prefersReduced ? false : { opacity: 0, y: 8 }}
          animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="text-2xl md:text-3xl font-semibold text-white"
        >
          {title}
        </motion.h1>
        <motion.p
          initial={prefersReduced ? false : { opacity: 0, y: 8 }}
          animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="mt-2 text-slate-300"
        >
          {subtitle}
        </motion.p>
        {ctaLabel && (
          <motion.button
            type="button"
            onClick={onCTAClick}
            initial={prefersReduced ? false : { opacity: 0, y: 8 }}
            animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="mt-6 inline-flex items-center px-6 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 ring-offset-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/50"
          >
            {ctaLabel}
          </motion.button>
        )}
      </div>
    </div>
  )
}
