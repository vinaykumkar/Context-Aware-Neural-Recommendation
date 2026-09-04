import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, ApiError, type CustomerListResponse } from '../lib/api'
import { compactNumber } from '../lib/format'
import { SkeletonRows, StatePanel } from '../components/Skeletons'

const SORTS = [
  { key: 'purchase_count', label: 'Most active' },
  { key: 'recency', label: 'Recently active' },
  { key: 'total_spent', label: 'Top spenders' },
  { key: 'customer_id', label: 'A–Z' },
]

export default function Discover() {
  const [q, setQ] = useState('')
  const [sort, setSort] = useState('purchase_count')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<CustomerListResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string | null>(null)
  const debounce = useRef<ReturnType<typeof setTimeout>>()

  const load = useCallback(() => {
    setLoading(true)
    api
      .customers({ q: q || undefined, page, page_size: 12, sort })
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setLoading(false))
  }, [q, page, sort])

  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current)
    debounce.current = setTimeout(load, q ? 280 : 0)
    return () => {
      if (debounce.current) clearTimeout(debounce.current)
    }
  }, [load, q])

  const copyId = (id: string) => {
    navigator.clipboard?.writeText(id).then(() => {
      setCopied(id)
      setTimeout(() => setCopied(null), 1400)
    })
  }

  return (
    <div className="mx-auto max-w-7xl px-5 pb-24 pt-14 sm:px-8">
      <p className="micro-label">customer discovery</p>
      <h1 className="display-xl mt-3 text-4xl sm:text-5xl">
        Who are we <em className="text-gradient not-italic font-light">dressing</em> today?
      </h1>
      <p className="mt-4 max-w-2xl text-[14px] leading-relaxed text-mist">
        Search any club member by ID, or browse the most interesting shoppers. Every profile
        below carries real purchase history and a precomputed recommendation pool.
      </p>

      {/* search + sort */}
      <div className="mt-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full max-w-xl">
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setPage(1)
            }}
            placeholder="Search customer id — try pasting a 64-char hex id…"
            spellCheck={false}
            className="panel w-full bg-transparent px-5 py-3.5 pr-12 font-grotesk text-[13px] text-ivory outline-none placeholder:text-faint focus:border-iris-500/50"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 font-grotesk text-[11px] text-faint">
            ⌕
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {SORTS.map((s) => (
            <button
              key={s.key}
              onClick={() => {
                setSort(s.key)
                setPage(1)
              }}
              className={`rounded-full border px-4 py-2 font-grotesk text-[10px] uppercase tracking-[0.16em] transition-colors ${
                sort === s.key
                  ? 'border-iris-500/50 bg-iris-500/15 text-ivory'
                  : 'border-white/[0.09] text-mist hover:text-ivory'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* results */}
      <div className="mt-10">
        {error ? (
          <StatePanel title="Can't reach the data" body={error} hint="start the backend: uvicorn backend.app.main:app" />
        ) : loading && !data ? (
          <SkeletonRows count={6} />
        ) : data && data.items.length === 0 ? (
          <StatePanel
            title="No members match"
            body="Customer IDs are 64-character hexadecimal strings. Try a shorter prefix, or clear the search to browse."
          />
        ) : data ? (
          <>
            <p className="mb-4 font-grotesk text-[10px] uppercase tracking-[0.2em] text-faint">
              {data.total.toLocaleString()} members · page {data.page} / {data.pages.toLocaleString()}
            </p>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {data.items.map((c, i) => (
                <motion.div
                  key={c.customer_id}
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: Math.min(i * 0.05, 0.4), ease: [0.22, 1, 0.36, 1] }}
                  className="panel panel-hover p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <Link to={`/customer/${c.customer_id}`} className="group/min min-w-0 flex-1">
                      <p className="truncate font-grotesk text-[13px] text-ivory group-hover/min:text-iris-300">
                        {c.customer_id.slice(0, 14)}…
                      </p>
                      <p className="mt-0.5 text-[11px] text-faint">click to open the styling session</p>
                    </Link>
                    <button
                      onClick={() => copyId(c.customer_id)}
                      title="Copy full ID"
                      className="shrink-0 rounded-full border border-white/[0.1] px-2.5 py-1 font-grotesk text-[9px] uppercase tracking-[0.14em] text-mist transition-colors hover:border-iris-500/50 hover:text-ivory"
                    >
                      {copied === c.customer_id ? '✓' : 'copy'}
                    </button>
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-3 border-t border-white/[0.06] pt-4">
                    <Stat label="purchases" value={compactNumber(c.purchase_count)} />
                    <Stat label="unique items" value={compactNumber(c.unique_articles_count)} />
                    <Stat label="age" value={c.age ? String(c.age) : '—'} />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="rounded-full border border-white/[0.08] px-2.5 py-0.5 font-grotesk text-[9px] uppercase tracking-[0.14em] text-mist">
                      {c.club_member_status?.toLowerCase() ?? 'member'}
                    </span>
                    <Link
                      to={`/customer/${c.customer_id}`}
                      className="font-grotesk text-[10px] uppercase tracking-[0.18em] text-iris-300 hover:text-iris-400"
                    >
                      view →
                    </Link>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* pagination */}
            <div className="mt-10 flex items-center justify-center gap-3">
              <PageBtn disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                ← prev
              </PageBtn>
              <span className="font-grotesk text-[11px] text-faint">
                {data.page} / {data.pages.toLocaleString()}
              </span>
              <PageBtn disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
                next →
              </PageBtn>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-display text-xl text-ivory">{value}</p>
      <p className="font-grotesk text-[9px] uppercase tracking-[0.16em] text-faint">{label}</p>
    </div>
  )
}

function PageBtn({ children, disabled, onClick }: { children: React.ReactNode; disabled: boolean; onClick: () => void }) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className="rounded-full border border-white/[0.1] px-5 py-2 font-grotesk text-[10px] uppercase tracking-[0.18em] text-mist transition-colors enabled:hover:border-iris-500/50 enabled:hover:text-ivory disabled:opacity-30"
    >
      {children}
    </button>
  )
}
