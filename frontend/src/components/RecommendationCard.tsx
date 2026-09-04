import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { RecommendationItem } from '../lib/api'
import { articleChips, articleLabel } from '../lib/api'
import { compactNumber } from '../lib/format'
import ProductImage from './ProductImage'
import SignalBars from './SignalBars'

const REASON_ACCENT: Record<string, string> = {
  COLLABORATIVE: '#7c6cff',
  CONTENT_SIMILARITY: '#e44fcb',
  POPULARITY: '#4ea8ff',
  REPEAT_PURCHASE: '#d9b98a',
  HYBRID: '#b3a7ff',
}

/** Hero recommendation tile: rank numeral, product, reason, expandable "why". */
export default function RecommendationCard({ item, index }: { item: RecommendationItem; index: number }) {
  const [open, setOpen] = useState(false)
  const accent = REASON_ACCENT[item.reason] ?? '#b3a7ff'

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 26, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.5, delay: Math.min(index * 0.06, 0.5), ease: [0.22, 1, 0.36, 1] }}
      className="panel panel-hover group relative flex flex-col overflow-hidden p-4"
    >
      {/* rank numeral */}
      <span
        className="pointer-events-none absolute -right-2 -top-5 select-none font-display text-[86px] font-light leading-none text-white/[0.05]"
        aria-hidden
      >
        {item.rank}
      </span>

      <div className="relative">
        <ProductImage article={item.article} className="aspect-[3/4] w-full" />
        <span
          className="absolute left-2 top-2 rounded-full border px-2 py-0.5 font-grotesk text-[9px] uppercase tracking-[0.16em]"
          style={{ borderColor: `${accent}55`, color: accent, background: `${accent}14` }}
        >
          {item.reason.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="mt-4 flex-1 space-y-2">
        <h3 className="font-display text-[17px] leading-snug text-ivory">
          {item.article?.product_type ?? articleLabel(item.article)}
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {articleChips(item.article, 2).map((chip) => (
            <span key={chip} className="rounded-full border border-white/[0.08] px-2 py-0.5 text-[10px] text-mist">
              {chip}
            </span>
          ))}
        </div>
        <p className="font-grotesk text-[10px] uppercase tracking-[0.18em] text-faint">
          ART-{item.article_id}
        </p>
        <p className="text-[12px] leading-relaxed text-mist">{item.reason_text}</p>
        {item.article && (
          <p className="font-grotesk text-[10px] text-faint">
            {compactNumber(item.article.stats.purchase_count)} sold · {compactNumber(item.article.stats.unique_customers)} buyers
          </p>
        )}
      </div>

      <button
        onClick={() => setOpen((v) => !v)}
        className="mt-4 flex w-full items-center justify-between border-t border-white/[0.07] pt-3 font-grotesk text-[10px] uppercase tracking-[0.2em] text-iris-300 transition-colors hover:text-iris-400"
        aria-expanded={open}
      >
        Why this item?
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25 }}>
          ▾
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-4 space-y-3">
              <SignalBars components={item.components} />
              <p className="text-[10px] leading-relaxed text-faint">
                Signals are normalized 0–100 strengths of each recommendation component —
                collaborative filtering, content similarity, popularity and repeat-purchase
                affinity. Ranks come from the weighted hybrid score.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  )
}
