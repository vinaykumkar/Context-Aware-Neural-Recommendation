import { motion } from 'framer-motion'
import type { Article, HistoryItem } from '../lib/api'
import { channelName, fullDate } from '../lib/format'
import ProductImage from './ProductImage'

/** Compact editorial product tile used in the purchase-history rail. */
export default function ProductCard({ item, index = 0 }: { item: HistoryItem; index?: number }) {
  const a = item.article
  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.45, delay: Math.min(index * 0.04, 0.3), ease: [0.22, 1, 0.36, 1] }}
      className="panel panel-hover group w-[190px] shrink-0 p-3"
    >
      <ProductImage article={a} className="aspect-[3/4] w-full" />
      <div className="mt-3 space-y-1">
        <p className="font-display text-[15px] leading-snug text-ivory">
          {a?.product_type ?? `Product ${item.article_id}`}
        </p>
        {a?.colour && (
          <p className="font-grotesk text-[10px] uppercase tracking-[0.16em] text-mist">{a.colour}</p>
        )}
        <p className="text-[12px] text-mist">
          {fullDate(item.t_dat)} · {channelName(item.sales_channel_id)}
        </p>
      </div>
    </motion.article>
  )
}

export function PopularCard({ article, index = 0 }: { article: Article; index?: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.45, delay: Math.min(index * 0.05, 0.35), ease: [0.22, 1, 0.36, 1] }}
      className="panel panel-hover group w-[170px] shrink-0 p-3"
    >
      <ProductImage article={article} className="aspect-[3/4] w-full" />
      <div className="mt-3 space-y-1">
        <p className="font-display text-[15px] leading-snug text-ivory">
          {article.product_type ?? `Product ${article.article_id}`}
        </p>
        <div className="flex items-baseline justify-between gap-2">
          {article.colour && (
            <p className="font-grotesk text-[10px] uppercase tracking-[0.16em] text-mist">{article.colour}</p>
          )}
          <p className="font-grotesk text-[10px] text-iris-300">
            {article.stats.unique_customers.toLocaleString()} buyers
          </p>
        </div>
      </div>
    </motion.article>
  )
}
