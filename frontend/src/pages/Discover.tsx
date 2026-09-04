import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  api,
  ApiError,
  type Article,
  type ArticleListResponse,
  type CustomerListResponse,
} from '../lib/api'
import { compactNumber } from '../lib/format'
import { CatalogProductCard, formatPrice } from '../components/ProductCard'
import ProductImage from '../components/ProductImage'
import { SkeletonCard, SkeletonRows, StatePanel } from '../components/Skeletons'
import FilterSidebar, {
  type FilterState,
  PRICE_PRESETS,
  SORT_OPTIONS_ARTICLES,
  SORT_OPTIONS_CUSTOMERS,
} from '../components/FilterSidebar'

export default function Discover() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialMode = searchParams.get('tab') === 'customers' ? 'customers' : 'articles'
  const [viewMode, setViewMode] = useState<'articles' | 'customers'>(initialMode)

  // Filters state
  const [filters, setFilters] = useState<FilterState>(() => {
    const pRange = searchParams.get('priceRange') || ''
    const preset = PRICE_PRESETS.find((p) => p.value === pRange)
    return {
      gender: searchParams.get('gender') || '',
      ageGroup: searchParams.get('age') || '',
      productGroup: searchParams.get('productGroup') || '',
      priceRange: pRange,
      minPrice: preset ? preset.min : undefined,
      maxPrice: preset ? preset.max : undefined,
      sort: searchParams.get('sort') || (initialMode === 'customers' ? 'purchase_count' : 'popularity'),
    }
  })

  const [q, setQ] = useState(searchParams.get('q') || '')
  const [page, setPage] = useState(1)

  // Article Catalog State
  const [articlesData, setArticlesData] = useState<ArticleListResponse | null>(null)
  const [articlesLoading, setArticlesLoading] = useState(true)

  // Customer Profiles State
  const [customersData, setCustomersData] = useState<CustomerListResponse | null>(null)
  const [customersLoading, setCustomersLoading] = useState(true)

  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)

  const debounce = useRef<ReturnType<typeof setTimeout>>()

  // Parse age range
  const getAgeRange = (group?: string) => {
    if (!group) return { min: undefined, max: undefined }
    if (group === '18-25') return { min: 18, max: 25 }
    if (group === '26-35') return { min: 26, max: 35 }
    if (group === '36-50') return { min: 36, max: 50 }
    if (group === '51-100') return { min: 51, max: 100 }
    return { min: undefined, max: undefined }
  }

  // Helper to parse price range presets
  const getPriceRange = (range?: string) => {
    const preset = PRICE_PRESETS.find((p) => p.value === range)
    if (preset) return { min: preset.min, max: preset.max }
    return { min: undefined, max: undefined }
  }

  // Load Articles
  const loadArticles = useCallback(() => {
    setArticlesLoading(true)
    const price = getPriceRange(filters.priceRange)
    const minP = filters.minPrice !== undefined ? filters.minPrice : price.min
    const maxP = filters.maxPrice !== undefined ? filters.maxPrice : price.max

    api
      .articles({
        q: q || undefined,
        gender: filters.gender || undefined,
        product_group: filters.productGroup || undefined,
        age_group: filters.ageGroup || undefined,
        min_price: minP,
        max_price: maxP,
        sort: filters.sort,
        page,
        page_size: 18,
      })
      .then((d) => {
        setArticlesData(d)
        setError(null)
      })
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setArticlesLoading(false))
  }, [q, filters, page])

  // Load Customers
  const loadCustomers = useCallback(() => {
    setCustomersLoading(true)
    const age = getAgeRange(filters.ageGroup)
    api
      .customers({
        q: q || undefined,
        page,
        page_size: 12,
        sort: filters.sort || 'purchase_count',
        age_min: age.min,
        age_max: age.max,
      })
      .then((d) => {
        setCustomersData(d)
        setError(null)
      })
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setCustomersLoading(false))
  }, [q, filters, page])

  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current)
    debounce.current = setTimeout(() => {
      if (viewMode === 'articles') {
        loadArticles()
      } else {
        loadCustomers()
      }
    }, q ? 250 : 0)
    return () => {
      if (debounce.current) clearTimeout(debounce.current)
    }
  }, [viewMode, loadArticles, loadCustomers, q])

  // Sync with URL
  useEffect(() => {
    const p = new URLSearchParams()
    if (viewMode === 'customers') p.set('tab', 'customers')
    if (q) p.set('q', q)
    if (filters.gender) p.set('gender', filters.gender)
    if (filters.ageGroup) p.set('age', filters.ageGroup)
    if (filters.productGroup) p.set('productGroup', filters.productGroup)
    if (filters.sort) p.set('sort', filters.sort)
    setSearchParams(p, { replace: true })
  }, [viewMode, q, filters, setSearchParams])

  const copyId = (id: string) => {
    navigator.clipboard?.writeText(id).then(() => {
      setCopied(id)
      setTimeout(() => setCopied(null), 1400)
    })
  }

  const handleResetFilters = () => {
    setFilters({
      gender: '',
      ageGroup: '',
      productGroup: '',
      priceRange: '',
      minPrice: undefined,
      maxPrice: undefined,
      sort: viewMode === 'articles' ? 'popularity' : 'purchase_count',
    })
    setQ('')
    setPage(1)
  }

  const activeTotal = viewMode === 'articles' ? articlesData?.total : customersData?.total

  return (
    <div className="mx-auto max-w-7xl px-5 pb-24 pt-10 sm:px-8">
      {/* ---------------- HEADER & MODE SWITCH ---------------- */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-8 border-b border-neutral-200 dark:border-neutral-800">
        <div>
          <p className="font-grotesk text-[10px] uppercase tracking-[0.3em] text-[#8b9e7a] font-bold">
            Curated Discovery & Filters
          </p>
          <h1 className="font-display text-4xl sm:text-5xl font-medium text-neutral-950 dark:text-white mt-1">
            {viewMode === 'articles' ? 'Garment & Product Catalog' : 'Club Member Profiles'}
          </h1>
          <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400 max-w-2xl font-sans">
            {viewMode === 'articles'
              ? 'Filter and sort real H&M apparel by Department, Age Demographic, Category and Price.'
              : 'Select any club member to inspect their taste profile, purchase history, and personalized Top-10 recommendations.'}
          </p>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="inline-flex rounded-full bg-neutral-200/80 dark:bg-neutral-800/80 p-1 border border-neutral-300 dark:border-neutral-700 shrink-0">
          <button
            onClick={() => {
              setViewMode('articles')
              setPage(1)
              setFilters((prev) => ({ ...prev, sort: 'popularity' }))
            }}
            className={`rounded-full px-5 py-2 font-grotesk text-xs uppercase tracking-wider font-semibold transition-all cursor-pointer ${
              viewMode === 'articles'
                ? 'bg-white dark:bg-[#111111] text-neutral-950 dark:text-white shadow-xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-950 dark:hover:text-white'
            }`}
          >
            Product Catalog
          </button>
          <button
            onClick={() => {
              setViewMode('customers')
              setPage(1)
              setFilters((prev) => ({ ...prev, sort: 'purchase_count' }))
            }}
            className={`rounded-full px-5 py-2 font-grotesk text-xs uppercase tracking-wider font-semibold transition-all cursor-pointer ${
              viewMode === 'customers'
                ? 'bg-white dark:bg-[#111111] text-neutral-950 dark:text-white shadow-xs'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-950 dark:hover:text-white'
            }`}
          >
            Customer Profiles
          </button>
        </div>
      </div>

      {/* ---------------- MAIN LAYOUT WITH AMAZON-STYLE FILTER SIDEBAR ---------------- */}
      <div className="mt-8 flex flex-col lg:flex-row gap-8 items-start">
        {/* Filter Sidebar */}
        <FilterSidebar
          filters={filters}
          onChange={(newFilters) => {
            setFilters(newFilters)
            setPage(1)
          }}
          onReset={handleResetFilters}
          totalCount={activeTotal}
          mode={viewMode}
        />

        {/* Main Content Area */}
        <div className="flex-1 w-full min-w-0">
          {/* Top Search & Sorting Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pb-6 border-b border-neutral-200/80 dark:border-neutral-800/80">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <input
                value={q}
                onChange={(e) => {
                  setQ(e.target.value)
                  setPage(1)
                }}
                placeholder={
                  viewMode === 'articles'
                    ? 'Search type, color, department (e.g. shirt, black, ladies)...'
                    : 'Search customer id by hex prefix...'
                }
                spellCheck={false}
                className="w-full rounded-full border border-neutral-300 dark:border-neutral-700 bg-white/80 dark:bg-white/[0.04] px-5 py-2.5 pr-10 font-grotesk text-xs text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 outline-none focus:border-[#8b9e7a] focus:ring-1 focus:ring-[#8b9e7a] transition-all"
              />
              <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">
                ⌕
              </span>
            </div>

            {/* Amazon-style Sort Select Dropdown */}
            <div className="flex items-center gap-2 shrink-0">
              <label htmlFor="sort-select" className="font-grotesk text-xs text-neutral-500 dark:text-neutral-400 font-medium">
                Sort by:
              </label>
              <select
                id="sort-select"
                value={filters.sort}
                onChange={(e) => {
                  setFilters({ ...filters, sort: e.target.value })
                  setPage(1)
                }}
                className="rounded-full border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-[#13151f] px-4 py-2 font-grotesk text-xs text-neutral-900 dark:text-neutral-100 outline-none focus:border-[#8b9e7a] cursor-pointer"
              >
                {(viewMode === 'articles' ? SORT_OPTIONS_ARTICLES : SORT_OPTIONS_CUSTOMERS).map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="mt-6">
              <StatePanel title="Connection Error" body={error} hint="Ensure FastAPI server is running on port 8000" />
            </div>
          )}

          {/* ---------------- MODE 1: ARTICLES CATALOG GRID ---------------- */}
          {viewMode === 'articles' && !error && (
            <div className="mt-6">
              {articlesLoading && !articlesData ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-3 gap-5">
                  {Array.from({ length: 9 }).map((_, i) => (
                    <SkeletonCard key={i} className="aspect-[3/4] w-full" />
                  ))}
                </div>
              ) : articlesData && articlesData.items.length === 0 ? (
                <div className="py-12">
                  <StatePanel
                    title="No garments match your filters"
                    body="Try resetting the Department, Age Demographic or Price Range filters, or using broader search terms."
                  />
                </div>
              ) : articlesData ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-3 gap-5">
                    {articlesData.items.map((art, i) => (
                      <CatalogProductCard
                        key={art.article_id}
                        article={art}
                        index={i}
                        onSelect={(article) => setSelectedArticle(article)}
                      />
                    ))}
                  </div>

                  {/* Pagination */}
                  <div className="mt-12 flex items-center justify-center gap-3">
                    <button
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className="rounded-full border border-neutral-300 dark:border-neutral-700 px-5 py-2 font-grotesk text-xs uppercase tracking-wider text-neutral-700 dark:text-neutral-300 hover:border-[#8b9e7a] disabled:opacity-30 cursor-pointer"
                    >
                      ← Previous
                    </button>
                    <span className="font-grotesk text-xs text-neutral-500 font-medium">
                      Page {articlesData.page} of {articlesData.pages.toLocaleString()}
                    </span>
                    <button
                      disabled={page >= articlesData.pages}
                      onClick={() => setPage((p) => p + 1)}
                      className="rounded-full border border-neutral-300 dark:border-neutral-700 px-5 py-2 font-grotesk text-xs uppercase tracking-wider text-neutral-700 dark:text-neutral-300 hover:border-[#8b9e7a] disabled:opacity-30 cursor-pointer"
                    >
                      Next →
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          )}

          {/* ---------------- MODE 2: CUSTOMERS LIST ---------------- */}
          {viewMode === 'customers' && !error && (
            <div className="mt-6">
              {customersLoading && !customersData ? (
                <SkeletonRows count={6} />
              ) : customersData && customersData.items.length === 0 ? (
                <div className="py-12">
                  <StatePanel
                    title="No customer profiles match"
                    body="Try broadening your age filters or clearing your customer ID search query."
                  />
                </div>
              ) : customersData ? (
                <>
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-2">
                    {customersData.items.map((c, i) => (
                      <motion.div
                        key={c.customer_id}
                        initial={{ opacity: 0, y: 14 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.35, delay: Math.min(i * 0.04, 0.3) }}
                        className="panel panel-hover p-5 rounded-2xl bg-white/80 dark:bg-white/[0.03] border border-neutral-200/80 dark:border-white/[0.08]"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <Link to={`/customer/${c.customer_id}`} className="group/min min-w-0 flex-1">
                            <p className="truncate font-grotesk text-sm font-semibold text-neutral-900 dark:text-neutral-100 group-hover/min:text-[#8b9e7a] transition-colors">
                              {c.customer_id.slice(0, 16)}…
                            </p>
                            <p className="mt-0.5 text-[11px] text-neutral-500 font-sans">
                              Click to view Top-10 recommendation pool
                            </p>
                          </Link>
                          <button
                            onClick={() => copyId(c.customer_id)}
                            title="Copy full ID"
                            className="shrink-0 rounded-full border border-neutral-300 dark:border-neutral-700 px-3 py-1 font-grotesk text-[10px] uppercase tracking-wider text-neutral-600 dark:text-neutral-400 hover:border-[#8b9e7a] hover:text-[#8b9e7a] transition-colors cursor-pointer"
                          >
                            {copied === c.customer_id ? '✓ Copied' : 'Copy'}
                          </button>
                        </div>

                        <div className="mt-4 grid grid-cols-3 gap-2 border-t border-neutral-100 dark:border-neutral-800/80 pt-3 text-center">
                          <div>
                            <p className="font-display text-lg text-neutral-900 dark:text-white">
                              {compactNumber(c.purchase_count)}
                            </p>
                            <p className="font-grotesk text-[9px] uppercase tracking-wider text-neutral-400">Purchases</p>
                          </div>
                          <div>
                            <p className="font-display text-lg text-neutral-900 dark:text-white">
                              {c.age ? `${c.age} yrs` : '—'}
                            </p>
                            <p className="font-grotesk text-[9px] uppercase tracking-wider text-neutral-400">Age</p>
                          </div>
                          <div>
                            <p className="font-display text-lg text-[#8b9e7a]">
                              {formatPrice(c.average_price)}
                            </p>
                            <p className="font-grotesk text-[9px] uppercase tracking-wider text-neutral-400">Avg Spend</p>
                          </div>
                        </div>

                        <div className="mt-4 flex items-center justify-between pt-2">
                          <span className="rounded-full bg-neutral-100 dark:bg-neutral-800 px-3 py-1 font-grotesk text-[10px] uppercase tracking-wider text-neutral-600 dark:text-neutral-400 font-medium">
                            {c.club_member_status?.toLowerCase() ?? 'Active Member'}
                          </span>
                          <Link
                            to={`/customer/${c.customer_id}`}
                            className="inline-flex items-center gap-1.5 rounded-full bg-[#111111] dark:bg-white text-white dark:text-neutral-900 px-4 py-1.5 font-grotesk text-[10px] uppercase tracking-wider font-bold hover:bg-[#8b9e7a] dark:hover:bg-[#8b9e7a] dark:hover:text-white transition-colors"
                          >
                            Personalize →
                          </Link>
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  {/* Pagination */}
                  <div className="mt-12 flex items-center justify-center gap-3">
                    <button
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className="rounded-full border border-neutral-300 dark:border-neutral-700 px-5 py-2 font-grotesk text-xs uppercase tracking-wider text-neutral-700 dark:text-neutral-300 hover:border-[#8b9e7a] disabled:opacity-30 cursor-pointer"
                    >
                      ← Previous
                    </button>
                    <span className="font-grotesk text-xs text-neutral-500 font-medium">
                      Page {customersData.page} of {customersData.pages.toLocaleString()}
                    </span>
                    <button
                      disabled={page >= customersData.pages}
                      onClick={() => setPage((p) => p + 1)}
                      className="rounded-full border border-neutral-300 dark:border-neutral-700 px-5 py-2 font-grotesk text-xs uppercase tracking-wider text-neutral-700 dark:text-neutral-300 hover:border-[#8b9e7a] disabled:opacity-30 cursor-pointer"
                    >
                      Next →
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* ---------------- ARTICLE DETAIL MODAL ---------------- */}
      <AnimatePresence>
        {selectedArticle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-white dark:bg-[#12141d] border border-neutral-200 dark:border-neutral-800 shadow-2xl p-6 sm:p-8"
            >
              {/* Close button */}
              <button
                onClick={() => setSelectedArticle(null)}
                className="absolute top-5 right-5 w-8 h-8 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-[#8b9e7a] hover:text-white transition-colors flex items-center justify-center font-bold text-sm"
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
                      className="w-full rounded-full bg-[#111111] dark:bg-white text-white dark:text-neutral-900 py-3 font-grotesk text-xs uppercase tracking-wider font-bold hover:bg-[#8b9e7a] dark:hover:bg-[#8b9e7a] dark:hover:text-white transition-colors"
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
