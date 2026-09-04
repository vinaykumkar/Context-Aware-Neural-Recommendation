import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, type Article, type DatasetStats, type ApiError } from '../lib/api'
import { compactNumber } from '../lib/format'
import { PopularCard } from '../components/ProductCard'
import { SkeletonCard } from '../components/Skeletons'

const AURA_CATEGORIES = [
  {
    name: 'Outerwear',
    subtitle: 'Sage Quilted Parkas & Overcoats',
    price: 'From $89',
    gender: 'Ladieswear',
    productGroup: 'Garment Upper body',
    gradient: 'from-black/80 via-black/40 to-black/80',
    tag: 'Trending',
    image: 'https://images.unsplash.com/photo-1539533018447-63fcce667883?auto=format&fit=crop&w=700&q=80',
  },
  {
    name: 'Knitwear',
    subtitle: 'Blush Ribbed Turtlenecks & Sweaters',
    price: 'From $49',
    gender: 'Ladieswear',
    productGroup: 'Garment Upper body',
    gradient: 'from-black/80 via-black/40 to-black/80',
    tag: 'Essential',
    image: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=700&q=80',
  },
  {
    name: 'Trousers',
    subtitle: 'Tailored Wide-Leg Silhouettes',
    price: 'From $79',
    gender: 'Ladieswear',
    productGroup: 'Garment Lower body',
    gradient: 'from-black/80 via-black/40 to-black/80',
    tag: 'Classic',
    image: 'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=700&q=80',
  },
  {
    name: 'Layering & Shirts',
    subtitle: 'Oversized Poplin & Linen Tops',
    price: 'From $75',
    gender: 'Divided',
    productGroup: 'Garment Upper body',
    gradient: 'from-black/80 via-black/40 to-black/80',
    tag: 'New',
    image: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=700&q=80',
  },
  {
    name: 'Accessories',
    subtitle: 'Tonal Leather Bags & Cashmere Sets',
    price: 'From $59',
    gender: 'Ladieswear',
    productGroup: 'Accessories',
    gradient: 'from-black/80 via-black/40 to-black/80',
    tag: 'Curated',
    image: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=700&q=80',
  },
]

export default function Landing() {
  const [stats, setStats] = useState<DatasetStats | null>(null)
  const [popular, setPopular] = useState<Article[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.stats().then((s) => setStats(s.dataset)).catch((e: ApiError) => setError(e.message))
    api.popularArticles(12).then(setPopular).catch(() => setPopular([]))
  }, [])

  return (
    <div className="space-y-24 pb-20">
      {/* ---------------- AURA HERO ---------------- */}
      <section className="relative overflow-hidden pt-12 md:pt-16">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            
            {/* Left Hero Column */}
            <div className="lg:col-span-7 space-y-6">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="inline-flex items-center gap-2 rounded-full bg-[#8b9e7a]/15 border border-[#8b9e7a]/30 px-3.5 py-1.5 font-grotesk text-[10px] uppercase tracking-[0.25em] text-[#6d805c] dark:text-[#a4b893] font-bold"
              >
                <span>✦</span>
                <span>Aura Editorial Lookbook · Autumn / Winter 2026</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
                className="font-display text-5xl sm:text-6xl lg:text-[76px] font-normal tracking-tight leading-[1.04] text-neutral-950 dark:text-white"
              >
                Pieces worth <br />
                <span className="italic font-light text-[#8b9e7a] dark:text-[#a4b893]">
                  living in.
                </span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.16 }}
                className="max-w-xl text-base sm:text-lg leading-relaxed text-neutral-600 dark:text-neutral-300 font-sans"
              >
                Carefully considered silhouettes for the individual who moves through the world with quiet confidence. Powered by real transaction behavior across 1.37 million club members.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.24 }}
                className="flex flex-wrap items-center gap-4 pt-4"
              >
                <Link
                  to="/discover"
                  className="rounded-full bg-[#111111] dark:bg-white text-white dark:text-neutral-900 px-8 py-4 font-grotesk text-xs uppercase tracking-[0.2em] font-bold transition-all hover:bg-[#8b9e7a] dark:hover:bg-[#8b9e7a] dark:hover:text-white shadow-sm hover:shadow-md"
                >
                  Explore Collection & Filters
                </Link>
                <Link
                  to="/insights"
                  className="rounded-full border border-neutral-300 dark:border-neutral-700 bg-white/60 dark:bg-white/[0.04] text-neutral-800 dark:text-neutral-200 px-8 py-4 font-grotesk text-xs uppercase tracking-[0.2em] font-semibold hover:border-[#8b9e7a] hover:text-[#8b9e7a] transition-all"
                >
                  Inside the Neural Model
                </Link>
              </motion.div>

              {error && (
                <p className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-500">
                  {error}
                </p>
              )}
            </div>

            {/* Right Hero Column: Dataset Stat Card */}
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="lg:col-span-5 panel p-8 rounded-3xl bg-white/90 dark:bg-white/[0.04] border border-neutral-200/90 dark:border-white/[0.08] shadow-md"
            >
              <div className="flex items-center justify-between pb-6 border-b border-neutral-200 dark:border-neutral-800">
                <span className="font-grotesk text-[10px] uppercase tracking-[0.25em] text-[#8b9e7a] font-bold">
                  Intelligence Engine
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] font-grotesk font-semibold text-neutral-500">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Live Precomputed
                </span>
              </div>

              <dl className="mt-6 space-y-5">
                {[
                  ['Transactions Mined', stats ? compactNumber(stats.n_transactions) : '31.8M', 'Recorded purchase patterns 2018–2020'],
                  ['Club Members', stats ? compactNumber(1371980) : '1.37M', 'Active taste profiles with age & history'],
                  ['Article Catalog', stats ? compactNumber(stats.n_articles) : '105K', 'One-hot attribute encoded garments'],
                  ['Candidate Pool', 'Top-50', 'Hybrid-scored ranking per customer'],
                ].map(([label, value, sub]) => (
                  <div key={label as string} className="flex items-end justify-between gap-4 border-b border-neutral-100 dark:border-neutral-800/80 pb-4 last:border-0 last:pb-0">
                    <div>
                      <dt className="text-xs text-neutral-500 dark:text-neutral-400 font-medium font-sans">{label}</dt>
                      <dd className="mt-0.5 font-grotesk text-[10px] text-neutral-400 dark:text-neutral-500">{sub}</dd>
                    </div>
                    <span className="font-display text-2xl sm:text-3xl font-medium text-neutral-950 dark:text-white shrink-0">
                      {value}
                    </span>
                  </div>
                ))}
              </dl>
            </motion.div>

          </div>
        </div>
      </section>

      {/* ---------------- AURA FEATURED CATEGORIES ---------------- */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-8 border-b border-neutral-200 dark:border-neutral-800">
          <div>
            <p className="font-grotesk text-[10px] uppercase tracking-[0.3em] text-[#8b9e7a] font-bold">
              Featured This Season
            </p>
            <h2 className="font-display text-3xl sm:text-4xl text-neutral-950 dark:text-white mt-1">
              Curated Wardrobe Silhouettes
            </h2>
          </div>
          <Link
            to="/discover"
            className="font-grotesk text-xs uppercase tracking-[0.2em] font-semibold text-neutral-800 dark:text-neutral-200 hover:text-[#8b9e7a] transition-colors inline-flex items-center gap-2"
          >
            View Full Catalog & Filters <span>→</span>
          </Link>
        </div>

        {/* Categories Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mt-8">
          {AURA_CATEGORIES.map((cat, i) => (
            <motion.div
              key={cat.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.08 }}
            >
              <Link
                to={`/discover?gender=${encodeURIComponent(cat.gender)}&productGroup=${encodeURIComponent(cat.productGroup)}`}
                className="group relative flex flex-col justify-between overflow-hidden rounded-2xl p-6 min-h-[240px] border border-neutral-200/80 dark:border-white/[0.08] shadow-xs hover:shadow-2xl transition-all duration-500"
              >
                {/* Background lookbook photo */}
                <img
                  src={cat.image}
                  alt={cat.name}
                  className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/30 group-hover:via-black/40 transition-colors" />

                <div className="relative z-10">
                  <span className="inline-block rounded-full bg-white/20 backdrop-blur-md text-white px-2.5 py-0.5 font-grotesk text-[9px] uppercase tracking-wider font-bold">
                    {cat.tag}
                  </span>
                  <h3 className="font-display text-2xl font-medium text-white mt-3 group-hover:text-[#c4d7b5] transition-colors">
                    {cat.name}
                  </h3>
                  <p className="text-xs text-white/80 mt-1 font-sans">
                    {cat.subtitle}
                  </p>
                </div>

                <div className="relative z-10 flex items-center justify-between pt-6 border-t border-white/20">
                  <span className="font-grotesk text-xs font-semibold text-white">
                    {cat.price}
                  </span>
                  <span className="font-grotesk text-xs font-bold text-[#c4d7b5] transition-transform group-hover:translate-x-1.5">
                    →
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ---------------- POPULAR / RUNWAY RAIL ---------------- */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="flex items-end justify-between pb-6">
          <div>
            <p className="font-grotesk text-[10px] uppercase tracking-[0.3em] text-[#8b9e7a] font-bold">
              Currently in Demand
            </p>
            <h2 className="font-display text-3xl sm:text-4xl text-neutral-950 dark:text-white mt-1">
              Top Trending Silhouettes
            </h2>
          </div>
          <Link
            to="/discover"
            className="font-grotesk text-xs uppercase tracking-[0.2em] font-semibold text-neutral-800 dark:text-neutral-200 hover:text-[#8b9e7a] transition-colors"
          >
            Explore All <span>→</span>
          </Link>
        </div>

        {/* Horizontal scroll container with fade masks */}
        <div className="relative -mx-5 px-5 sm:-mx-8 sm:px-8">
          <div className="no-scrollbar flex gap-4 overflow-x-auto pb-4 pt-1">
            {!popular
              ? Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} className="w-[200px] shrink-0" />
                ))
              : popular.map((article, i) => (
                  <PopularCard key={article.article_id} article={article} index={i} />
                ))}
          </div>
        </div>
      </section>

      {/* ---------------- AURA 4-PILLAR ARCHITECTURE ---------------- */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <p className="font-grotesk text-[10px] uppercase tracking-[0.3em] text-[#8b9e7a] font-bold">
            Algorithmic Breakdown
          </p>
          <h2 className="font-display text-3xl sm:text-4xl text-neutral-950 dark:text-white">
            How Aura Curates Your Taste
          </h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 font-sans">
            Every candidate is scored through a multi-layer hybrid pipeline designed for high accuracy and instant latency.
          </p>
        </div>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { weight: '45%', title: 'Collaborative Affinity', desc: 'Recency-decayed co-purchase cosine matrix exploring top 100 neighbors from past customer baskets.' },
            { weight: '25%', title: 'Content Taste Vectors', desc: 'Exact cosine similarity across one-hot feature embeddings, matching preferred departments, colors & cuts.' },
            { weight: '20%', title: 'Popularity Demand', desc: 'Log-scaled global transaction frequency blended with 12-week seasonal velocity.' },
            { weight: '10%', title: 'Repeat Purchase', desc: 'Personal repurchase affinity prioritizing verified staple replenishments.' },
          ].map((col, idx) => (
            <motion.div
              key={col.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.08 }}
              className="p-6 rounded-2xl bg-white/70 dark:bg-white/[0.03] border border-neutral-200/80 dark:border-white/[0.08] shadow-xs"
            >
              <div className="font-display text-4xl text-[#8b9e7a] font-light">
                {col.weight}
              </div>
              <h3 className="font-display text-lg font-medium text-neutral-900 dark:text-neutral-100 mt-3">
                {col.title}
              </h3>
              <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-400 mt-2 font-sans">
                {col.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}
