import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api, type StatsResponse } from '../lib/api'
import { compactNumber, shortDate } from '../lib/format'
import { StatePanel } from '../components/Skeletons'

const WEIGHT_LABELS: Record<string, string> = {
  collab: 'Collaborative',
  content: 'Content',
  popularity: 'Popularity',
  repurchase: 'Repeat-buy',
}

export default function Insights() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e: { message: string }) => setError(e.message))
  }, [])

  const weights = stats?.model.weights
    ? Object.entries(stats.model.weights).sort((a, b) => b[1] - a[1])
    : []

  return (
    <div className="mx-auto max-w-7xl px-5 pb-24 pt-14 sm:px-8">
      <p className="micro-label">inside the model</p>
      <h1 className="display-xl mt-3 max-w-3xl text-4xl sm:text-5xl">
        Built offline. <em className="text-gradient not-italic font-light">Served instantly.</em>
      </h1>
      <p className="mt-5 max-w-2xl text-[14px] leading-relaxed text-mist">
        The recommender never scans the source dataset at request time. Three offline stages
        distill 31.8M transactions into compact serving artifacts; the API only reads those.
      </p>

      {error ? (
        <div className="mt-12">
          <StatePanel title="Pipeline metadata unavailable" body={error} hint="python scripts/build_all.py" />
        </div>
      ) : !stats ? (
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-44 rounded-2xl" />
          ))}
        </div>
      ) : (
        <>
          {/* pipeline stages */}
          <div className="mt-14 grid gap-5 lg:grid-cols-3">
            {[
              {
                stage: 'Stage 01 — Serving data',
                body: 'Per-article demand statistics, per-customer behavior profiles and the last 60 purchases of every member are written into hash-bucketed Parquet files the API can open directly.',
                meta: `${compactNumber(stats.dataset.n_articles)} articles · ${compactNumber(1371980)} profiles`,
              },
              {
                stage: 'Stage 02 — Similarity models',
                body: `A recency-decayed co-purchase matrix (half-life ${stats.model.half_life_days ?? 90} days) is cosine-normalized into item-item collaborative neighbors; the 9 encoded article attributes produce content neighbors. Top-${'150'} per item.`,
                meta: 'sparse blockwise computation · no full matrix in memory',
              },
              {
                stage: 'Stage 03 — Recommendation pools',
                body: `Every member's top-${stats.model.candidate_limit ?? 50} candidates are scored with the hybrid blend, given reason codes and stored with per-component scores for explainability.`,
                meta: stats.model.built_at ? `built ${stats.model.built_at}` : '',
              },
            ].map((s, i) => (
              <motion.div
                key={s.stage}
                initial={{ opacity: 0, y: 22 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="panel p-7"
              >
                <p className="font-grotesk text-[10px] uppercase tracking-[0.2em] text-iris-300">{s.stage}</p>
                <p className="mt-4 text-[13px] leading-relaxed text-mist">{s.body}</p>
                <p className="mt-4 border-t border-white/[0.06] pt-3 font-grotesk text-[10px] uppercase tracking-[0.14em] text-faint">
                  {s.meta}
                </p>
              </motion.div>
            ))}
          </div>

          {/* weights + dataset */}
          <div className="mt-14 grid gap-5 lg:grid-cols-[1.1fr_1fr]">
            <div className="panel p-8">
              <p className="micro-label">hybrid score composition</p>
              <h2 className="mt-3 font-display text-2xl font-light text-ivory">What drives a ranking</h2>
              <div className="mt-7 space-y-5">
                {weights.map(([k, v], i) => (
                  <div key={k}>
                    <div className="mb-1.5 flex items-baseline justify-between">
                      <span className="text-[13px] text-mist">{WEIGHT_LABELS[k] ?? k}</span>
                      <span className="font-grotesk text-[11px] text-ivory">{Math.round(v * 100)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                      <motion.div
                        className="h-full rounded-full"
                        style={{
                          background: ['#7c6cff', '#e44fcb', '#4ea8ff', '#d9b98a'][i % 4],
                        }}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${v * 100 * 2}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-6 text-[12px] leading-relaxed text-faint">
                Weights were chosen for a explainable, robust blend: collaborative behavior
                dominates, content keeps taste coherent, popularity covers cold-start, and
                repeat-purchase captures H&M's real re-buying habits.
              </p>
            </div>

            <div className="panel p-8">
              <p className="micro-label">the numbers</p>
              <h2 className="mt-3 font-display text-2xl font-light text-ivory">Scale of the evidence</h2>
              <dl className="mt-7 space-y-4">
                <Row label="Transactions" value={compactNumber(stats.dataset.n_transactions)} />
                <Row label="Purchasing members" value={compactNumber(stats.dataset.n_active_customers)} />
                <Row label="Catalog articles" value={compactNumber(stats.dataset.n_articles)} />
                <Row
                  label="Behavior window"
                  value={`${shortDate(stats.dataset.min_date)} → ${shortDate(stats.dataset.max_date)}`}
                />
                <Row label="Serving data on disk" value={`${stats.serving.serving_data_mb ?? '—'} MB`} />
                <Row label="Recommendation pool on disk" value={`${stats.serving.recommendations_mb ?? '—'} MB`} />
              </dl>
            </div>
          </div>

          {/* honesty section */}
          <div className="panel mt-14 p-8">
            <p className="micro-label">honest engineering</p>
            <h2 className="mt-3 font-display text-2xl font-light text-ivory">What this system does and doesn't claim</h2>
            <div className="mt-6 grid gap-8 md:grid-cols-2">
              <ul className="space-y-3 text-[13px] leading-relaxed text-mist">
                <li>✓ Scores are normalized component strengths — never presented as probabilities.</li>
                <li>✓ Reason codes map 1:1 to the dominant scoring component, not invented stories.</li>
                <li>✓ Article attributes are label-encoded in the source data; the UI shows codes as-is.</li>
              </ul>
              <ul className="space-y-3 text-[13px] leading-relaxed text-mist">
                <li>✓ Images render only from configured providers; otherwise a designed placeholder.</li>
                <li>✓ No request ever opens the ~800 MB source transaction dataset.</li>
                <li>✓ Cold-start members get an explicit popularity fallback, labelled as such.</li>
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-white/[0.06] pb-3 last:border-0">
      <dt className="text-[13px] text-mist">{label}</dt>
      <dd className="font-grotesk text-[13px] text-ivory">{value}</dd>
    </div>
  )
}
