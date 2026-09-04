import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  api,
  ApiError,
  type Article,
  type CustomerProfileResponse,
  type HistoryResponse,
  type RecommendationResponse,
} from '../lib/api'
import { compactNumber, fullDate } from '../lib/format'
import { formatPrice } from '../components/ProductCard'
import ProductCard from '../components/ProductCard'
import ProductImage from '../components/ProductImage'
import RecommendationCard from '../components/RecommendationCard'
import { SkeletonGrid, SkeletonRows, StatePanel } from '../components/Skeletons'

export default function CustomerView() {
  const { id = '' } = useParams()
  const [profile, setProfile] = useState<CustomerProfileResponse | null>(null)
  const [history, setHistory] = useState<HistoryResponse | null>(null)
  const [recs, setRecs] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const carouselRef = useRef<HTMLDivElement>(null)

  const scrollPurchases = (direction: -1 | 1) => {
    if (carouselRef.current) {
      const scrollAmount = 480 * direction
      carouselRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' })
    }
  }

  useEffect(() => {
    setLoading(true)
    setError(null)
    setProfile(null)
    setHistory(null)
    setRecs(null)
    let alive = true
    Promise.all([api.customerProfile(id), api.customerHistory(id, 24)])
      .then(([p, h]) => {
        if (!alive) return
        setProfile(p)
        setHistory(h)
        setError(null)
      })
      .catch((e: ApiError) => alive && setError(e))
      .finally(() => alive && setLoading(false))

    api.customerRecommendations(id, 10)
      .then((r) => alive && setRecs(r))
      .catch(() => alive && setRecs(null))

    return () => {
      alive = false
    }
  }, [id])

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl space-y-10 px-5 pb-24 pt-14 sm:px-8">
        <div className="skeleton h-48 w-full rounded-3xl" />
        <SkeletonRows count={2} />
        <SkeletonGrid count={10} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-5 pb-24 pt-20 sm:px-8">
        <StatePanel
          title={error.status === 404 ? 'Member not found' : 'Session Interrupted'}
          body={
            error.status === 404
              ? 'No profile exists for this customer id. Double-check the id or pick another member from discovery.'
              : error.message
          }
          hint={error.status === 0 ? 'uvicorn backend.app.main:app' : undefined}
        />
        <div className="mt-8 text-center">
          <Link to="/discover" className="font-grotesk text-xs uppercase tracking-[0.2em] text-[#8b9e7a] hover:underline">
            ← Back to Customer Discovery
          </Link>
        </div>
      </div>
    )
  }

  const c = profile!.customer
  const hasHistory = (history?.returned ?? 0) > 0

  const handleCopy = () => {
    navigator.clipboard?.writeText(c.customer_id)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="mx-auto max-w-7xl px-5 pb-24 pt-10 sm:px-8 space-y-16">
      {/* ---------- PROFILE BANNER ---------- */}
      <section className="panel relative overflow-hidden p-8 sm:p-10 rounded-3xl bg-white/90 dark:bg-white/[0.04] border border-neutral-200 dark:border-white/[0.08] shadow-sm">
        <div className="relative grid gap-10 lg:grid-cols-[1.3fr_1fr] items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-[#8b9e7a]/20 border border-[#8b9e7a]/30 px-3 py-1 font-grotesk text-[10px] uppercase tracking-[0.25em] text-[#6d805c] dark:text-[#a4b893] font-bold">
              <span>✦</span>
              <span>Member Styling Session</span>
            </div>

            <h1 className="mt-4 break-all font-display text-2xl sm:text-3xl font-medium text-neutral-950 dark:text-white">
              {c.customer_id.slice(0, 24)}…
            </h1>

            <div className="mt-4 flex flex-wrap items-center gap-2.5">
              {c.club_member_status && (
                <span className="rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-3 py-1 font-grotesk text-[10px] uppercase tracking-wider text-neutral-700 dark:text-neutral-300 font-medium">
                  {c.club_member_status.toLowerCase()} status
                </span>
              )}
              {c.age && (
                <span className="rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-3 py-1 font-grotesk text-[10px] uppercase tracking-wider text-neutral-700 dark:text-neutral-300 font-medium">
                  Age {c.age} yrs
                </span>
              )}
              <button
                onClick={handleCopy}
                className="rounded-full border border-[#8b9e7a] bg-[#8b9e7a]/10 px-3.5 py-1 font-grotesk text-[10px] uppercase tracking-wider text-[#6d805c] dark:text-[#a4b893] font-bold hover:bg-[#8b9e7a] hover:text-white transition-all cursor-pointer"
              >
                {copied ? '✓ Copied ID' : 'Copy Full ID'}
              </button>
            </div>

            {profile!.top_categories.length > 0 && (
              <div className="mt-6 pt-6 border-t border-neutral-100 dark:border-neutral-800">
                <p className="font-grotesk text-[10px] uppercase tracking-wider text-neutral-400 font-semibold">
                  Personal Taste Affinities
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {profile!.top_categories.map((t) => (
                    <span
                      key={t.label}
                      className="rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200/80 dark:border-neutral-700 px-3 py-1 text-xs text-neutral-700 dark:text-neutral-300 font-grotesk"
                    >
                      {t.feature} <strong className="text-[#8b9e7a]">· {t.code}</strong>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <dl className="grid grid-cols-2 gap-6 bg-neutral-50 dark:bg-white/[0.02] p-6 rounded-2xl border border-neutral-200/70 dark:border-white/[0.05]">
            <Metric label="Total Purchases" value={compactNumber(c.purchase_count)} />
            <Metric label="Unique Garments" value={compactNumber(c.unique_articles_count)} />
            <Metric label="Average Price" value={formatPrice(c.average_price)} />
            <Metric label="Last Active Date" value={fullDate(profile!.last_purchase_date)} />
          </dl>
        </div>
      </section>

      {/* ---------- PURCHASE STORY / HISTORY ---------- */}
      <section>
        <div className="flex flex-wrap items-end justify-between gap-4 pb-4 border-b border-neutral-200 dark:border-neutral-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-grotesk text-[10px] uppercase tracking-[0.25em] text-[#8b9e7a] font-bold">
                Transaction Story
              </span>
              <span className="text-[10px] font-grotesk text-neutral-400 dark:text-neutral-500 font-medium">
                • Scrollable Carousel
              </span>
            </div>
            <h2 className="mt-1 font-display text-2xl sm:text-3xl font-medium text-neutral-950 dark:text-white">
              Recent Customer Purchases
            </h2>
          </div>

          <div className="flex items-center gap-4">
            <p className="font-grotesk text-xs text-neutral-500 dark:text-neutral-400">
              {hasHistory
                ? `${history!.returned} of ${history!.total_transactions.toLocaleString()} items recorded`
                : ''}
            </p>

            {/* Carousel navigation controls */}
            {hasHistory && history!.items.length > 3 && (
              <div className="flex items-center gap-1.5 bg-neutral-100 dark:bg-white/[0.04] p-1 rounded-full border border-neutral-200/80 dark:border-white/[0.08]">
                <button
                  onClick={() => scrollPurchases(-1)}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-[#8b9e7a] hover:text-white transition-all shadow-xs cursor-pointer text-sm font-bold"
                  aria-label="Scroll previous purchases"
                >
                  ←
                </button>
                <button
                  onClick={() => scrollPurchases(1)}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-[#8b9e7a] hover:text-white transition-all shadow-xs cursor-pointer text-sm font-bold"
                  aria-label="Scroll next purchases"
                >
                  →
                </button>
              </div>
            )}
          </div>
        </div>

        {hasHistory ? (
          <div className="relative mt-6 group">
            <div
              ref={carouselRef}
              className="flex gap-4 overflow-x-auto pb-4 pt-1 scroll-smooth snap-x snap-mandatory scrollbar-thin"
              style={{ scrollbarGutter: 'stable' }}
            >
              {history!.items.map((item, i) => (
                <ProductCard
                  key={`${item.article_id}-${item.t_dat}-${i}`}
                  item={item}
                  index={i}
                  onSelect={(art) => art && setSelectedArticle(art)}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="mt-6">
            <StatePanel
              title="Cold-Start Customer"
              body="This club member has zero purchases in the transaction window. Our recommendation engine provides an explainable popularity and seasonal demand fallback."
            />
          </div>
        )}
      </section>

      {/* ---------- RECOMMENDATIONS GALLERY ---------- */}
      <section>
        <div className="flex flex-wrap items-end justify-between gap-4 pb-4 border-b border-neutral-200 dark:border-neutral-800">
          <div>
            <p className="font-grotesk text-[10px] uppercase tracking-[0.25em] text-[#8b9e7a] font-bold">
              Aura Hybrid Model
            </p>
            <h2 className="mt-1 font-display text-3xl sm:text-4xl font-medium text-neutral-950 dark:text-white">
              Personalized Top-10 Selection
            </h2>
          </div>
          {recs && (
            <div className="inline-flex items-center gap-2 rounded-full bg-[#8b9e7a]/15 text-[#6d805c] dark:text-[#a4b893] px-3.5 py-1 font-grotesk text-xs font-semibold">
              <span>{recs.source === 'precomputed' ? 'Hybrid Multi-Signal Pool' : 'Popularity Baseline'}</span>
              {recs.filtered_out > 0 && <span>· ({recs.filtered_out} owned filtered)</span>}
            </div>
          )}
        </div>

        <div className="mt-8 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-5">
          {recs && recs.items.length > 0 ? (
            recs.items.map((item, i) => (
              <RecommendationCard key={item.article_id} item={item} index={i} />
            ))
          ) : (
            <div className="col-span-full">
              <StatePanel
                title="Recommendation pool is loading"
                body="Precomputing recommendations for this member..."
              />
            </div>
          )}
        </div>

        {recs && recs.items.length > 0 && (
          <div className="mt-10 p-6 rounded-2xl bg-neutral-100/80 dark:bg-white/[0.02] border border-neutral-200/80 dark:border-neutral-800 text-xs leading-relaxed text-neutral-600 dark:text-neutral-400 font-sans">
            <strong className="text-neutral-900 dark:text-neutral-200 font-semibold">Explainable Hybrid AI: </strong>
            Each recommendation above is composed of four weighted behavior signals (45% Collaborative Filtering from similar customer baskets, 25% Content feature vector match, 20% Popularity demand, and 10% Repeat repurchase affinity). Reranked for product diversity at request time.
          </div>
        )}
      </section>

      {/* ---------- ARTICLE QUICK-VIEW MODAL ---------- */}
      <AnimatePresence>
        {selectedArticle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-white dark:bg-[#121318] p-6 sm:p-8 border border-neutral-200 dark:border-white/[0.08] shadow-2xl"
            >
              <button
                onClick={() => setSelectedArticle(null)}
                className="absolute top-5 right-5 w-8 h-8 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-[#8b9e7a] hover:text-white transition-colors flex items-center justify-center font-bold text-sm cursor-pointer"
                aria-label="Close details"
              >
                ✕
              </button>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-start">
                <div className="overflow-hidden rounded-2xl">
                  <ProductImage article={selectedArticle} className="aspect-[3/4] w-full" />
                </div>

                <div className="space-y-4">
                  <span className="inline-block rounded-full bg-[#8b9e7a]/20 text-[#6d805c] dark:text-[#a4b893] px-3 py-1 font-grotesk text-[10px] uppercase tracking-wider font-bold">
                    {selectedArticle.index_group || 'Aura Collection'}
                  </span>

                  <h2 className="font-display text-2xl font-medium text-neutral-950 dark:text-white">
                    {selectedArticle.product_type ?? `Product ${selectedArticle.article_id}`}
                  </h2>

                  <p className="font-grotesk text-2xl font-bold text-neutral-950 dark:text-white">
                    {formatPrice(selectedArticle.stats.avg_price)}
                  </p>

                  <div className="space-y-2 border-t border-b border-neutral-100 dark:border-neutral-800 py-3 text-xs font-sans">
                    <div className="flex justify-between text-neutral-600 dark:text-neutral-400">
                      <span>Department:</span>
                      <strong className="text-neutral-900 dark:text-neutral-100">{selectedArticle.department || 'General'}</strong>
                    </div>
                    <div className="flex justify-between text-neutral-600 dark:text-neutral-400">
                      <span>Product Group:</span>
                      <strong className="text-neutral-900 dark:text-neutral-100">{selectedArticle.product_group || 'Apparel'}</strong>
                    </div>
                    <div className="flex justify-between text-neutral-600 dark:text-neutral-400">
                      <span>Colour Group:</span>
                      <strong className="text-neutral-900 dark:text-neutral-100">{selectedArticle.colour || 'Standard'}</strong>
                    </div>
                    <div className="flex justify-between text-neutral-600 dark:text-neutral-400">
                      <span>Article ID:</span>
                      <code className="font-grotesk text-[11px] text-[#8b9e7a]">{selectedArticle.article_id}</code>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <p className="font-grotesk text-[10px] uppercase tracking-wider text-neutral-400">Demand Analytics</p>
                    <p className="text-xs text-neutral-600 dark:text-neutral-300">
                      Purchased by <strong>{selectedArticle.stats.unique_customers.toLocaleString()}</strong> unique club members ({selectedArticle.stats.purchase_count.toLocaleString()} total units).
                    </p>
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => setSelectedArticle(null)}
                      className="w-full rounded-full bg-[#111111] dark:bg-white text-white dark:text-neutral-900 py-3 font-grotesk text-xs uppercase tracking-wider font-bold hover:bg-[#8b9e7a] dark:hover:bg-[#8b9e7a] dark:hover:text-white transition-colors cursor-pointer"
                    >
                      Close Details
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dd className="font-display text-2xl font-medium text-neutral-950 dark:text-white">{value}</dd>
      <dt className="mt-0.5 font-grotesk text-[10px] uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
        {label}
      </dt>
    </div>
  )
}
