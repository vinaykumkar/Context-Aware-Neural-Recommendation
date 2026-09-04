import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { api, type Article, type DatasetStats, type ApiError } from '../lib/api'
import { compactNumber } from '../lib/format'
import { PopularCard } from '../components/ProductCard'
import { SkeletonCard, StatePanel } from '../components/Skeletons'

export default function Landing() {
  const reduced = useReducedMotion()
  const [stats, setStats] = useState<DatasetStats | null>(null)
  const [popular, setPopular] = useState<Article[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.stats().then((s) => setStats(s.dataset)).catch((e: ApiError) => setError(e.message))
    api.popularArticles(12).then(setPopular).catch(() => setPopular([]))
  }, [])

  return (
    <div>
      {/* ---------------- HERO ---------------- */}
      <section className="relative overflow-hidden">
        {/* ambient glow shapes */}
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <motion.div
            className="absolute -top-32 right-[8%] h-[420px] w-[420px] rounded-full bg-iris-500/20 blur-[130px]"
            animate={reduced ? undefined : { y: [0, 30, 0], scale: [1, 1.08, 1] }}
            transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="absolute left-[4%] top-[38%] h-[300px] w-[300px] rounded-full bg-magenta-500/10 blur-[110px]"
            animate={reduced ? undefined : { y: [0, -24, 0] }}
            transition={{ duration: 13, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>

        <div className="relative mx-auto grid max-w-7xl gap-12 px-5 pb-20 pt-16 sm:px-8 lg:grid-cols-[1.35fr_1fr] lg:gap-6 lg:pb-28 lg:pt-24">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="micro-label"
            >
              H&M dataset · 31.8M purchases · hybrid recommender
            </motion.p>
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
              className="display-xl mt-6 text-[13vw] sm:text-6xl lg:text-[76px]"
            >
              A wardrobe that
              <br />
              <em className="text-gradient font-light not-italic">
                understands you.
              </em>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.18 }}
              className="mt-7 max-w-xl text-[15px] leading-relaxed text-mist"
            >
              AURA reads two years of real H&M purchase behavior — co-purchase patterns,
              style attributes, recency and popularity — and turns them into a personal
              Top-10 selection for any of 1.37 million club members. Pick a customer,
              see their story, get honest recommendations.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.28 }}
              className="mt-10 flex flex-wrap items-center gap-4"
            >
              <Link
                to="/discover"
                className="group relative overflow-hidden rounded-full bg-ivory px-7 py-3.5 font-grotesk text-[12px] font-medium uppercase tracking-[0.22em] text-ink-950 transition-transform hover:scale-[1.02]"
              >
                <span className="relative z-10">Explore recommendations</span>
                <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-iris-300/60 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
              </Link>
              <Link
                to="/insights"
                className="rounded-full border border-white/[0.12] px-7 py-3.5 font-grotesk text-[12px] uppercase tracking-[0.22em] text-mist transition-colors hover:border-iris-500/50 hover:text-ivory"
              >
                Inside the model
              </Link>
            </motion.div>

            {error && (
              <p className="mt-8 rounded-xl border border-magenta-500/30 bg-magenta-500/10 px-4 py-3 text-[12px] text-magenta-400">
                {error}
              </p>
            )}
          </div>

          {/* stat panel */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="panel relative self-center p-8 lg:mt-4"
          >
            <p className="micro-label">the dataset behind the taste</p>
            <dl className="mt-6 space-y-5">
              {[
                ['Purchases analyzed', stats ? compactNumber(stats.n_transactions) : null, 'transactions, Sep 2018 – Sep 2020 window'],
                ['Club members', stats ? compactNumber(1371980) : null, 'profiles with behavior features'],
                ['Articles in catalog', stats ? compactNumber(stats.n_articles) : null, 'attribute-encoded products'],
                ['Recommendation pool', 'Top-50', 'candidates precomputed per customer'],
              ].map(([label, value, sub]) => (
                <div key={label as string} className="flex items-end justify-between gap-4 border-b border-white/[0.06] pb-4 last:border-0 last:pb-0">
                  <div>
                    <dt className="text-[13px] text-mist">{label}</dt>
                    <dd className="mt-1 font-grotesk text-[10px] uppercase tracking-[0.16em] text-faint">{sub}</dd>
                  </div>
                  <span className="font-display text-3xl text-ivory">{value ?? '—'}</span>
                </div>
              ))}
            </dl>
          </motion.div>
        </div>
      </section>

      {/* ---------------- POPULAR RAIL ---------------- */}
      <section className="mx-auto max-w-7xl px-5 pb-24 sm:px-8">
        <div className="flex items-end justify-between">
          <div>
            <p className="micro-label">currently in demand</p>
            <h2 className="mt-2 font-display text-3xl font-light text-ivory">What everyone is wearing</h2>
          </div>
        </div>
        <div className="mt-8 flex gap-4 overflow-x-auto pb-4">
          {popular === null
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} className="w-[170px] shrink-0" />)
            : popular.length > 0
              ? popular.map((a, i) => <PopularCard key={a.article_id} article={a} index={i} />)
              : (
                <div className="w-full">
                  <StatePanel
                    title="Catalog is warming up"
                    body="Article serving data hasn't been built yet. Run the offline pipeline scripts to populate popular products."
                  />
                </div>
              )}
        </div>
      </section>

      {/* ---------------- HOW IT WORKS ---------------- */}
      <section className="mx-auto max-w-7xl px-5 pb-24 sm:px-8">
        <p className="micro-label">the approach</p>
        <h2 className="mt-2 max-w-2xl font-display text-3xl font-light leading-tight text-ivory sm:text-4xl">
          Heavy thinking happens offline. Answering you is instant.
        </h2>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {[
            ['01', 'Learn from behavior', 'A recency-decayed co-purchase matrix and article-feature profiles are mined from 31.8M transactions — collaborative and content signals side by side.'],
            ['02', 'Precompute the pool', 'For every customer, the top-50 candidate garments are scored, explained and stored in compact serving buckets. No 800 MB scan ever happens live.'],
            ['03', 'Answer instantly', 'Selecting a customer reads one small bucket file, applies diversity reranking and returns a personal Top-10 in milliseconds.'],
          ].map(([n, title, body]) => (
            <motion.div
              key={n}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.55, delay: Number(n) * 0.06, ease: [0.22, 1, 0.36, 1] }}
              className="panel p-7"
            >
              <span className="font-display text-4xl font-light text-iris-400/80">{n}</span>
              <h3 className="mt-4 font-display text-xl text-ivory">{title}</h3>
              <p className="mt-3 text-[13px] leading-relaxed text-mist">{body}</p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}
