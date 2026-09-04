import { useState } from 'react'
import type { Article } from '../lib/api'
import { accentPair } from '../lib/format'
import { getCuratedFashionImage } from '../lib/fashionImages'

interface Props {
  article: Article | null
  className?: string
  rounded?: string
  index?: number
  indexOffset?: number
}

/**
 * Product image with authentic curated high-resolution editorial fashion lookbook photos.
 * If a local H&M image exists, it is served; otherwise it displays the high-resolution
 * category-matched lookbook photography for the garment.
 */
export default function ProductImage({
  article,
  className = '',
  rounded = 'rounded-xl',
  index = 0,
  indexOffset,
}: Props) {
  const [loaded, setLoaded] = useState(false)
  const [errorCount, setErrorCount] = useState(0)
  const id = article?.article_id ?? '0000000000'
  const [c1, c2] = accentPair(id)

  const offset = indexOffset !== undefined ? indexOffset : index

  const curatedImage = getCuratedFashionImage(
    article?.product_type,
    article?.product_group,
    article?.index_group,
    id,
    offset
  )

  // Primary source is backend image if available and not failed; secondary is curated editorial photo
  const primarySrc = article?.image_url && errorCount === 0 ? article.image_url : curatedImage

  const handleError = () => {
    setErrorCount((prev) => prev + 1)
  }

  // If even curated CDN failed multiple times, fall back to geometric placeholder
  if (errorCount >= 2) {
    return (
      <div
        className={`${rounded} relative overflow-hidden ${className}`}
        style={{
          background: `radial-gradient(130% 110% at 20% 10%, ${c1}2e 0%, transparent 55%), radial-gradient(120% 100% at 85% 90%, ${c2}24 0%, transparent 50%), linear-gradient(160deg, #14182b, #0c0e1a)`,
        }}
        aria-label={`Placeholder for article ${id}`}
      >
        <svg viewBox="0 0 100 130" className="absolute inset-0 h-full w-full opacity-70">
          <g transform={`rotate(${(parseInt(id.slice(-3), 10) % 24) - 12} 50 65)`}>
            <path
              d="M 34 44 C 34 34 42 28 50 28 C 58 28 66 34 66 44 L 62 96 C 62 102 55 106 50 106 C 45 106 38 102 38 96 Z"
              fill="none"
              stroke={`${c1}55`}
              strokeWidth="0.8"
            />
            <path d="M 38 30 L 34 44 L 42 48 M 62 30 L 66 44 L 58 48" fill="none" stroke={`${c2}44`} strokeWidth="0.7" />
            <line x1="46" y1="52" x2="54" y2="52" stroke={`${c1}66`} strokeWidth="0.6" />
            <line x1="45" y1="60" x2="55" y2="60" stroke={`${c2}50`} strokeWidth="0.6" />
          </g>
        </svg>
        <div className="absolute bottom-2 left-0 right-0 text-center">
          <span className="font-grotesk text-[10px] tracking-[0.22em] text-white/60">
            {article?.product_type ?? id}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${className} ${rounded} overflow-hidden bg-neutral-200/80 dark:bg-neutral-900`}>
      {!loaded && <div className="skeleton absolute inset-0 z-10" />}
      <img
        src={primarySrc}
        alt={article?.product_type ? `${article.product_type} - ${id}` : `Article ${id}`}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onError={handleError}
        className={`h-full w-full object-cover transition-all duration-700 ${
          loaded ? 'opacity-100 scale-100' : 'opacity-0 scale-105'
        }`}
      />
      {/* Subtle bottom shadow overlay for contrast */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-40 pointer-events-none" />
    </div>
  )
}
