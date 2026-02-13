import React from 'react'
export default function GlowLayer({
  colorFrom = 'rgba(56,189,248,0.15)',
  blur = 'blur-3xl',
  opacity = 0.7,
  className = '',
}) {
  const style = {
    backgroundImage: `radial-gradient(1200px circle at 50% -10%, ${colorFrom}, transparent 60%)`,
    opacity,
  }
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-[-20%] ${blur} ${className}`}
      style={style}
    />
  )
}
