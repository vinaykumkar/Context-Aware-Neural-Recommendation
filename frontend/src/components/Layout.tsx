import { Link, NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { useTheme } from '../context/ThemeContext'

const LINKS = [
  { to: '/', label: 'Home' },
  { to: '/discover', label: 'Discover & Shop' },
  { to: '/insights', label: 'Inside the Model' },
]

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="min-h-screen flex flex-col grain bg-[#fbfaf7] dark:bg-[#0c0d12] text-neutral-900 dark:text-neutral-100 transition-colors duration-300">
      {/* ---------------- AURA HEADER ---------------- */}
      <header className="sticky top-0 z-40 border-b border-neutral-200/80 dark:border-white/[0.08] bg-[#fbfaf7]/90 dark:bg-[#0c0d12]/90 backdrop-blur-md transition-colors duration-300">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          {/* Brand Logo */}
          <Link to="/" className="group flex flex-col justify-center">
            <span className="font-display text-[28px] font-semibold tracking-tight text-neutral-950 dark:text-white leading-none">
              AURA
            </span>
            <span className="font-grotesk text-[9px] uppercase tracking-[0.35em] text-[#8b9e7a] font-semibold mt-1">
              Fashion Intelligence
            </span>
          </Link>

          {/* Nav Links */}
          <nav className="hidden md:flex items-center gap-1 sm:gap-2">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `relative px-4 py-2 font-grotesk text-[11px] uppercase tracking-[0.2em] font-medium transition-colors ${
                    isActive
                      ? 'text-neutral-950 dark:text-white font-bold'
                      : 'text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-white'
                  }`
                }
              >
                {location.pathname === l.to && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-x-2 bottom-0 h-0.5 bg-[#8b9e7a]"
                    transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                  />
                )}
                <span className="relative">{l.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Right Actions: Theme Toggle & Quick CTA */}
          <div className="flex items-center gap-3">
            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              aria-label="Toggle Theme"
              className="relative p-2.5 rounded-full border border-neutral-300/80 dark:border-neutral-700/80 bg-white/70 dark:bg-neutral-800/80 text-neutral-800 dark:text-neutral-200 hover:border-[#8b9e7a] hover:text-[#8b9e7a] dark:hover:text-[#8b9e7a] transition-all cursor-pointer shadow-xs"
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {theme === 'dark' ? (
                /* Sun Icon */
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4 text-amber-400 transition-transform duration-300 hover:rotate-45"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
              ) : (
                /* Moon Icon */
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4 text-neutral-700 transition-transform duration-300 hover:-rotate-12"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                  />
                </svg>
              )}
            </button>

            <Link
              to="/discover"
              className="hidden sm:inline-flex items-center justify-center rounded-full bg-[#111111] dark:bg-white px-5 py-2.5 font-grotesk text-[11px] uppercase tracking-[0.2em] font-semibold text-white dark:text-neutral-900 transition-all hover:bg-[#8b9e7a] dark:hover:bg-[#8b9e7a] dark:hover:text-white"
            >
              Browse Catalog
            </Link>
          </div>
        </div>

        {/* Mobile Submenu Bar */}
        <div className="flex md:hidden items-center justify-around border-t border-neutral-200/60 dark:border-neutral-800/80 py-2.5 px-4 bg-white/50 dark:bg-black/40">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `font-grotesk text-[10px] uppercase tracking-[0.16em] py-1 ${
                  isActive ? 'text-[#8b9e7a] font-bold' : 'text-neutral-600 dark:text-neutral-400'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      </header>

      {/* ---------------- MAIN CONTENT ---------------- */}
      <motion.main
        key={location.pathname}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className="flex-1"
      >
        {children}
      </motion.main>

      {/* ---------------- AURA FOOTER ---------------- */}
      <footer className="mt-28 border-t border-neutral-200 dark:border-neutral-800/80 bg-[#f5f4ec] dark:bg-[#08090d] text-neutral-800 dark:text-neutral-200 py-16 transition-colors">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="grid grid-cols-1 gap-10 md:grid-cols-4 pb-12 border-b border-neutral-300/70 dark:border-neutral-800">
            {/* Column 1: Brand */}
            <div className="space-y-4">
              <h3 className="font-display text-2xl font-medium tracking-tight text-neutral-950 dark:text-white">
                AURA
              </h3>
              <p className="font-grotesk text-[10px] uppercase tracking-[0.25em] text-[#8b9e7a] font-semibold">
                Haute Recommender System
              </p>
              <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-400 max-w-xs">
                Precision neural item-to-item matching, co-purchase affinity graph modeling, and attribute-informed collaborative filters built on 31.8 million transactions.
              </p>
            </div>

            {/* Column 2: Navigation */}
            <div className="space-y-3">
              <h4 className="font-grotesk text-xs uppercase tracking-[0.2em] font-bold text-neutral-950 dark:text-white">
                Navigation
              </h4>
              <ul className="space-y-2 text-xs text-neutral-600 dark:text-neutral-400 font-medium">
                <li><Link to="/" className="hover:text-[#8b9e7a] transition-colors">Home & Lookbook</Link></li>
                <li><Link to="/discover" className="hover:text-[#8b9e7a] transition-colors">Customer Discovery</Link></li>
                <li><Link to="/discover" className="hover:text-[#8b9e7a] transition-colors">Product Catalog & Filters</Link></li>
                <li><Link to="/insights" className="hover:text-[#8b9e7a] transition-colors">Inside the Model & Weights</Link></li>
              </ul>
            </div>

            {/* Column 3: Algorithms */}
            <div className="space-y-3">
              <h4 className="font-grotesk text-xs uppercase tracking-[0.2em] font-bold text-neutral-950 dark:text-white">
                Architecture
              </h4>
              <ul className="space-y-2 text-xs text-neutral-600 dark:text-neutral-400">
                <li>Collaborative Filtering (45%)</li>
                <li>Content Taste Vectors (25%)</li>
                <li>Popularity Demand (20%)</li>
                <li>Repeat Purchase Affinity (10%)</li>
              </ul>
            </div>

            {/* Column 4: Technology */}
            <div className="space-y-3">
              <h4 className="font-grotesk text-xs uppercase tracking-[0.2em] font-bold text-neutral-950 dark:text-white">
                Engine & Data
              </h4>
              <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-400">
                Precomputed partitioned Parquet datasets + DuckDB memory engine with lazy bucket retrieval for sub-10ms response times.
              </p>
              <div className="pt-2">
                <span className="inline-block rounded-full bg-[#8b9e7a]/20 border border-[#8b9e7a]/40 px-3 py-1 font-grotesk text-[10px] uppercase tracking-wider text-[#6d805c] dark:text-[#a4b893] font-semibold">
                  Aura Edition 2026
                </span>
              </div>
            </div>
          </div>

          <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-neutral-500 dark:text-neutral-400">
            <p className="font-grotesk uppercase tracking-wider">
              © 2026 AURA · Context-Aware Neural Recommendation System
            </p>
            <p className="font-sans">
              Designed for luxury fashion personalization · Major College Internship Project
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
