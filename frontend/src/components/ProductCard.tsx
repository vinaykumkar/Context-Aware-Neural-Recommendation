import { motion } from 'framer-motion'
import type { Article, HistoryItem } from '../lib/api'
import { channelName, fullDate } from '../lib/format'
import ProductImage from './ProductImage'

/** Format normalized dataset price (e.g. 0.0339 -> $33.99) */
export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined) return '$29.99'
  const val = price * 1000
  return `$${val.toFixed(2)}`
}

/** Luxury editorial product tile used in catalog and purchase-history. */
export default function ProductCard({
  item,
  index = 0,
  onSelect,
}: {
  item: HistoryItem
  index?: number
  onSelect?: (article: Article | null) => void
}) {
  const a = item.article
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-20px' }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.03, 0.25), ease: [0.22, 1, 0.36, 1] }}
      onClick={() => onSelect?.(a)}
      className="panel panel-hover group relative overflow-hidden rounded-2xl p-3.5 bg-white/80 dark:bg-white/[0.035] border border-neutral-200/80 dark:border-white/[0.08] transition-all cursor-pointer shadow-xs hover:shadow-lg w-[210px] sm:w-[230px] shrink-0 snap-start flex flex-col justify-between"
    >
      <div>
        <div className="relative overflow-hidden rounded-xl">
          <ProductImage article={a} index={index} className="aspect-[3/4] w-full transition-transform duration-500 group-hover:scale-105" />
          {a?.index_group && (
            <span className="absolute top-2 left-2 rounded-full bg-black/60 dark:bg-black/80 backdrop-blur-md px-2.5 py-0.5 font-grotesk text-[9px] uppercase tracking-wider text-white font-medium">
              {a.index_group}
            </span>
          )}
          <span className="absolute bottom-2 right-2 rounded-full bg-black/70 dark:bg-black/90 backdrop-blur-md px-2 py-0.5 font-grotesk text-[9px] font-semibold text-[#a4b893]">
            {channelName(item.sales_channel_id)}
          </span>
        </div>

        <div className="mt-3.5 space-y-1.5">
          <div className="flex items-start justify-between gap-2">
            <p className="font-display text-[14px] font-medium leading-snug text-neutral-900 dark:text-neutral-100 line-clamp-1 group-hover:text-[#8b9e7a] transition-colors">
              {a?.product_type ?? `Article #${item.article_id}`}
            </p>
            <span className="font-grotesk text-xs font-bold text-neutral-950 dark:text-white shrink-0">
              {formatPrice(item.price || a?.stats.avg_price)}
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-neutral-500 dark:text-neutral-400 font-grotesk">
            <span className="truncate max-w-[100px]">{a?.colour || 'Neutral'}</span>
            <span className="shrink-0">{fullDate(item.t_dat)}</span>
          </div>
        </div>
      </div>
    </motion.article>
  )
}

/** Standalone Catalog Card for general browsing with Amazon-style details */
export function CatalogProductCard({
  article,
  index = 0,
  onSelect,
}: {
  article: Article
  index?: number
  onSelect?: (article: Article) => void
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-20px' }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.03, 0.25), ease: [0.22, 1, 0.36, 1] }}
      onClick={() => onSelect?.(article)}
      className="panel panel-hover group relative overflow-hidden rounded-2xl p-3.5 bg-white/80 dark:bg-white/[0.035] border border-neutral-200/80 dark:border-white/[0.08] transition-all cursor-pointer shadow-xs hover:shadow-lg"
    >
      <div className="relative overflow-hidden rounded-xl">
        <ProductImage article={article} index={index} className="aspect-[3/4] w-full transition-transform duration-500 group-hover:scale-105" />
        
        {/* Department / Audience badge */}
        {article.index_group && (
          <span className="absolute top-2 left-2 rounded-full bg-black/60 dark:bg-black/80 backdrop-blur-md px-2.5 py-0.5 font-grotesk text-[9px] uppercase tracking-wider text-white font-medium">
            {article.index_group}
          </span>
        )}

        {/* Popularity Rank Badge */}
        {article.stats.popularity_rank && article.stats.popularity_rank <= 100 && (
          <span className="absolute top-2 right-2 rounded-full bg-[#8b9e7a] px-2 py-0.5 font-grotesk text-[9px] uppercase tracking-wider text-white font-bold shadow-xs">
            Top {article.stats.popularity_rank}
          </span>
        )}
      </div>

      <div className="mt-3.5 space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display text-[15px] font-medium leading-snug text-neutral-900 dark:text-neutral-100 line-clamp-1 group-hover:text-[#8b9e7a] transition-colors">
            {article.product_type ?? `Product ${article.article_id}`}
          </h3>
          <span className="font-grotesk text-sm font-bold text-neutral-950 dark:text-white shrink-0">
            {formatPrice(article.stats.avg_price)}
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px] text-neutral-500 dark:text-neutral-400 font-grotesk">
          <span className="truncate max-w-[120px]">{article.product_group || article.colour || 'Signature'}</span>
          <span>{article.colour || 'Classic'}</span>
        </div>

        {/* Amazon-style social proof */}
        <div className="pt-2 flex items-center justify-between border-t border-neutral-100 dark:border-neutral-800/80 text-[11px] font-grotesk">
          <div className="flex items-center gap-1 text-amber-500 dark:text-amber-400 text-xs">
            <span>★</span>
            <span className="font-semibold text-neutral-700 dark:text-neutral-300">4.8</span>
          </div>
          <span className="text-neutral-500 dark:text-neutral-400">
            {article.stats.unique_customers.toLocaleString()} bought
          </span>
        </div>
      </div>
    </motion.article>
  )
}

export function PopularCard({ article, index = 0 }: { article: Article; index?: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.04, 0.3), ease: [0.22, 1, 0.36, 1] }}
      className="panel panel-hover group w-[200px] shrink-0 p-3.5 bg-white/80 dark:bg-white/[0.035] border border-neutral-200/80 dark:border-white/[0.08] transition-all rounded-2xl shadow-xs"
    >
      <div className="overflow-hidden rounded-xl">
        <ProductImage article={article} index={index} className="aspect-[3/4] w-full transition-transform duration-500 group-hover:scale-105" />
      </div>
      <div className="mt-3 space-y-1">
        <div className="flex items-baseline justify-between gap-1">
          <p className="font-display text-[14px] font-medium leading-snug text-neutral-900 dark:text-neutral-100 line-clamp-1">
            {article.product_type ?? `Product ${article.article_id}`}
          </p>
          <span className="font-grotesk text-xs font-semibold text-neutral-950 dark:text-white shrink-0">
            {formatPrice(article.stats.avg_price)}
          </span>
        </div>
        <div className="flex items-baseline justify-between gap-2 text-[10px] font-grotesk text-neutral-500 dark:text-neutral-400">
          <span>{article.colour || 'Standard'}</span>
          <span className="text-[#8b9e7a] font-medium">
            {article.stats.unique_customers.toLocaleString()} buyers
          </span>
        </div>
      </div>
    </motion.article>
  )
}
