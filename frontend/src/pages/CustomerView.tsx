import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  api,
  ApiError,
  type CustomerProfileResponse,
  type HistoryResponse,
  type RecommendationResponse,
} from '../lib/api'
import { compactNumber, fullDate } from '../lib/format'
import ProductCard from '../components/ProductCard'
import RecommendationCard from '../components/RecommendationCard'
import { SkeletonGrid, SkeletonRows, StatePanel } from '../components/Skeletons'

export default function CustomerView() {
  const { id = '' } = useParams()
  const [profile, setProfile] = useState<CustomerProfileResponse | null>(null)
  const [history, setHistory] = useState<HistoryResponse | null>(null)
  const [recs, setRecs] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setProfile(null)
    setHistory(null)
    setRecs(null)
    let alive = true
    // profile + history are the core view; recommendations load independently
    // so a missing pool can never blank the customer page
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
        <div className="skeleton h-40 w-full rounded-2xl" />
        <SkeletonRows count={2} />
        <SkeletonGrid count={10} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-5 pb-24 pt-20 sm:px-8">
        <StatePanel
          title={error.status === 404 ? 'Member not found' : 'Something interrupted the session'}
          body={
            error.status === 404
              ? 'No profile exists for this customer id. Double-check the id or pick another member from discovery.'
              : error.message
          }
          hint={error.status === 0 ? 'uvicorn backend.app.main:app' : undefined}
        />
        <div className="mt-8 text-center">
          <Link to="/discover" className="font-grotesk text-[11px] uppercase tracking-[0.2em] text-iris-300 hover:text-iris-400">
            ← back to discovery
          </Link>
        </div>
      </div>
    )
  }

  const c = profile!.customer
  const hasHistory = (history?.returned ?? 0) > 0

  return (
    <div className="mx-auto max-w-7xl px-5 pb-24 pt-12 sm:px-8">
      {/* ---------- PROFILE ---------- */}
      <section className="panel relative overflow-hidden p-7 sm:p-10">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-iris-500/15 blur-[90px]"
        />
        <div className="relative grid gap-10 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="micro-label">styling session for</p>
            <h1 className="mt-3 break-all font-display text-2xl font-light text-ivory sm:text-3xl">
              {c.customer_id.slice(0, 22)}…
            </h1>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {c.club_member_status && (
                <span className="rounded-full border border-white/[0.1] px-3 py-1 font-grotesk text-[9px] uppercase tracking-[0.16em] text-mist">
                  {c.club_member_status.toLowerCase()}
                </span>
              )}
              {c.age && (
                <span className="rounded-full border border-white/[0.1] px-3 py-1 font-grotesk text-[9px] uppercase tracking-[0.16em] text-mist">
                  age {c.age}
                </span>
              )}
              <button
                onClick={() => navigator.clipboard?.writeText(c.customer_id)}
                className="rounded-full border border-iris-500/40 px-3 py-1 font-grotesk text-[9px] uppercase tracking-[0.16em] text-iris-300 hover:bg-iris-500/10"
              >
                copy id
              </button>
            </div>
            {profile!.top_categories.length > 0 && (
              <div className="mt-6">
                <p className="micro-label">affinity profile</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {profile!.top_categories.map((t) => (
                    <span key={t.label} className="rounded-full bg-white/[0.05] px-3 py-1.5 text-[12px] text-mist">
                      {t.feature} <span className="font-grotesk text-iris-300">·{t.code}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-6 self-center">
            <Metric label="Purchases" value={compactNumber(c.purchase_count)} />
            <Metric label="Unique items" value={compactNumber(c.unique_articles_count)} />
            <Metric label="Last purchase" value={fullDate(profile!.last_purchase_date)} className="col-span-2" />
          </dl>
        </div>
      </section>

      {/* ---------- HISTORY ---------- */}
      <section className="mt-16">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="micro-label">purchase history</p>
            <h2 className="mt-2 font-display text-3xl font-light text-ivory">Recently purchased</h2>
          </div>
          <p className="hidden font-grotesk text-[10px] uppercase tracking-[0.18em] text-faint sm:block">
            {hasHistory
              ? `${history!.returned} of ${history!.total_transactions.toLocaleString()} transactions`
              : ''}
          </p>
        </div>
        {hasHistory ? (
          <div className="mt-8 flex gap-4 overflow-x-auto pb-4">
            {history!.items.map((item, i) => (
              <ProductCard key={`${item.article_id}-${item.t_dat}-${i}`} item={item} index={i} />
            ))}
          </div>
        ) : (
          <div className="mt-8">
            <StatePanel
              title="No purchases on record"
              body="This member has never transacted in the dataset window, so there is no purchase story — recommendations fall back to what the wider H&M crowd loves."
            />
          </div>
        )}
      </section>

      {/* ---------- RECOMMENDATIONS ---------- */}
      <section className="mt-20">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="micro-label">the feature presentation</p>
            <h2 className="mt-2 font-display text-3xl font-light text-ivory sm:text-4xl">
              Recommended for <em className="text-gradient not-italic font-light">this customer</em>
            </h2>
          </div>
          {recs && (
            <p className="font-grotesk text-[10px] uppercase tracking-[0.18em] text-faint">
              {recs.source === 'precomputed' ? 'hybrid pool · top 10 of 50' : 'popularity fallback'}
              {recs.filtered_out > 0 && ` · ${recs.filtered_out} already-owned filtered`}
            </p>
          )}
        </div>

        <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {recs && recs.items.length > 0 ? (
            recs.items.map((item, i) => (
              <RecommendationCard key={item.article_id} item={item} index={i} />
            ))
          ) : (
            <div className="col-span-full">
              <StatePanel
                title="No recommendation pool"
                body="Recommendations haven't been generated for this member yet. Run `python scripts/build_recommendations.py` to populate the pool."
              />
            </div>
          )}
        </div>

        {recs && recs.items.length > 0 && (
          <p className="mt-8 max-w-3xl text-[12px] leading-relaxed text-faint">
            Every item above comes from a precomputed top-50 hybrid pool: collaborative
            co-purchase similarity, content similarity to this customer's style profile,
            catalog popularity and repeat-purchase affinity — ranked by weighted score and
            reranked for product-group diversity at request time.
          </p>
        )}
      </section>
    </div>
  )
}

function Metric({ label, value, sub, className = '' }: { label: string; value: string; sub?: string; className?: string }) {
  return (
    <div className={className}>
      <dd className="font-display text-3xl font-light text-ivory">{value}</dd>
      <dt className="mt-1 font-grotesk text-[9px] uppercase tracking-[0.18em] text-faint">
        {label}
        {sub && <span className="ml-1 normal-case tracking-normal text-faint/70">({sub})</span>}
      </dt>
    </div>
  )
}
