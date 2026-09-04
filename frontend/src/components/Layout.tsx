import { Link, NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

const LINKS = [
  { to: '/', label: 'Home' },
  { to: '/discover', label: 'Discover' },
  { to: '/insights', label: 'Inside the model' },
]

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  return (
    <div className="grain min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-950/70 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="group flex items-baseline gap-2">
            <span className="font-display text-[22px] font-medium tracking-tight text-ivory">
              AURA
            </span>
            <span className="hidden font-grotesk text-[10px] uppercase tracking-[0.3em] text-faint transition-colors group-hover:text-iris-300 sm:inline">
              fashion intelligence
            </span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `relative rounded-full px-3 py-1.5 font-grotesk text-[11px] uppercase tracking-[0.18em] transition-colors sm:px-4 ${
                    isActive ? 'text-ivory' : 'text-mist hover:text-ivory'
                  }`
                }
              >
                {location.pathname === l.to && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-full border border-iris-500/30 bg-iris-500/10"
                    transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                  />
                )}
                <span className="relative">{l.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <motion.main
        key={location.pathname}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.main>
      <footer className="mt-24 border-t border-white/[0.06] py-10">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-4 px-5 sm:flex-row sm:items-center sm:px-8">
          <p className="font-grotesk text-[10px] uppercase tracking-[0.24em] text-faint">
            AURA — major project · H&M personalized recommendations
          </p>
          <p className="max-w-md text-[11px] leading-relaxed text-faint">
            Built on the public H&M Group transaction dataset. Prices are normalized source
            units; article attributes are label-encoded by the data pipeline.
          </p>
        </div>
      </footer>
    </div>
  )
}
