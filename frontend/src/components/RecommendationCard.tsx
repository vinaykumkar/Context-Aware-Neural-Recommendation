import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { RecommendationItem } from '../lib/api'
import { articleChips, articleLabel } from '../lib/api'
import { compactNumber } from '../lib/format'
import { formatPrice } from './ProductCard'
import ProductImage from './ProductImage'
import SignalBars from './SignalBars'

const REASON_ACCENT: Record<string, { bg: string; text: string; border: string }> = {
  COLLABORATIVE: { bg: 'rgba(139, 158, 122, 0.15)', text: '#6d805c', border: '#8b9e7a' },
  CONTENT_SIMILARITY: { bg: 'rgba(196, 142, 100, 0.15)', text: '#a36d42', border: '#c48e64' },
  POPULARITY: { bg: 'rgba(59, 130, 246, 0.15)', text: '#2563eb', border: '#3b82f6' },
  REPEAT_PURCHASE: { bg: 'rgba(217, 119, 6, 0.15)', text: '#b45309', border: '#d97706' },
  HYBRID: { bg: 'rgba(139, 158, 122, 0.2)', text: '#556b2f', border: '#8b9e7a' },
}

/** Hero recommendation tile: rank numeral, product, reason, expandable "why". */
export default function RecommendationCard({ item, index }: { item: RecommendationItem; index: number }) {
  const [open, setOpen] = useState(false)
  const reasonStyle = REASON_ACCENT[item.reason] || REASON_ACCENT.HYBRID

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 24, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.45, delay: Math.min(index * 0.05, 0.4), ease: [0.22, 1, 0.36, 1] }}
      className="panel panel-hover group relative flex flex-col overflow-hidden p-4 rounded-2xl bg-white/80 dark:bg-white/[0.035] border border-neutral-200/80 dark:border-white/[0.08] shadow-xs hover:shadow-lg transition-all"
    >
      {/* rank numeral watermark */}
      <span
        className="pointer-events-none absolute -right-2 -top-4 select-none font-display text-[72px] font-light leading-none text-neutral-900/[0.05] dark:text-white/[0.05]"
        aria-hidden
      >
        {item.rank}
      </span>

      <div className="relative overflow-hidden rounded-xl">
        <ProductImage article={item.article} index={index} className="aspect-[3/4] w-full transition-transform duration-500 group-hover:scale-105" />
        
        {/* Reason badge */}
        <span
          className="absolute left-2 top-2 rounded-full px-2.5 py-0.5 font-grotesk text-[9px] uppercase tracking-wider font-semibold border backdrop-blur-md"
          style={{
            backgroundColor: reasonStyle.bg,
            color: reasonStyle.text,
            borderColor: reasonStyle.border,
          }}
        >
          {item.reason.replace(/_/g, ' ')}
        </span>

        {/* Score indicator badge */}
        <span className="absolute top-2 right-2 rounded-full bg-black/60 dark:bg-black/80 backdrop-blur-md px-2 py-0.5 font-grotesk text-[9px] text-white font-medium">
          {(item.score * 100).toFixed(0)}% match
        </span>
      </div>

      <div className="mt-4 flex-1 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display text-[16px] font-medium leading-snug text-neutral-900 dark:text-neutral-100 line-clamp-1 group-hover:text-[#8b9e7a] transition-colors">
            {item.article?.product_type ?? articleLabel(item.article)}
          </h3>
          <span className="font-grotesk text-sm font-bold text-neutral-950 dark:text-white shrink-0">
            {formatPrice(item.article?.stats.avg_price)}
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {articleChips(item.article, 2).map((chip) => (
            <span
              key={chip}
              className="rounded-full bg-neutral-100 dark:bg-white/[0.05] border border-neutral-200/70 dark:border-white/[0.08] px-2.5 py-0.5 text-[10px] text-neutral-600 dark:text-neutral-400 font-grotesk font-medium"
            >
              {chip}
            </span>
          ))}
          {item.article?.index_group && (
            <span className="rounded-full bg-[#8b9e7a]/15 text-[#6d805c] dark:text-[#a4b893] border border-[#8b9e7a]/30 px-2.5 py-0.5 text-[10px] font-grotesk font-semibold">
              {item.article.index_group}
            </span>
          )}
        </div>

        <p className="text-[12px] leading-relaxed text-neutral-600 dark:text-neutral-400 pt-1">
          {item.reason_text}
        </p>

        {item.article && (
          <p className="font-grotesk text-[10px] text-neutral-400 dark:text-neutral-500">
            {compactNumber(item.article.stats.purchase_count)} purchases recorded in catalog
          </p>
        )}
      </div>

      <button
        onClick={() => setOpen((v) => !v)}
        className="mt-4 flex w-full items-center justify-between border-t border-neutral-200/80 dark:border-white/[0.08] pt-3 font-grotesk text-[10px] uppercase tracking-[0.2em] text-[#6d805c] dark:text-[#8b9e7a] font-semibold hover:text-neutral-950 dark:hover:text-white transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <span>Why this item?</span>
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
            <div className="mt-4 space-y-3 pt-2 border-t border-neutral-100 dark:border-neutral-800">
              <SignalBars components={item.components} />
              <p className="text-[10px] leading-relaxed text-neutral-500 dark:text-neutral-400 font-sans">
                Normalized 0–100 signal decomposition across collaborative filtering, content taste similarity, popularity demand, and repeat affinity.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  )
}
