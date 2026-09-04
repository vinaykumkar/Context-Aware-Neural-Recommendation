import { useState } from 'react'
import type { Article } from '../lib/api'
import { accentPair } from '../lib/format'

interface Props {
  article: Article | null
  className?: string
  rounded?: string
}

/**
 * Product image with an honest, deterministic editorial fallback.
 * Real H&M images are resolved by the backend's image index and served from
 * /api/images/{id}; when no image exists we render a deterministic
 * placeholder derived from the article's encoded features — never a fake photo.
 */
export default function ProductImage({ article, className = '', rounded = 'rounded-xl' }: Props) {
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const id = article?.article_id ?? '0000000000'
  const [c1, c2] = accentPair(id)

  const placeholder = (
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
        <span className="font-grotesk text-[10px] tracking-[0.22em] text-ivory/60">
          {(() => {
            const type = article?.features.find((f) => f.feature === 'Type')?.code
            const group = article?.features.find((f) => f.feature === 'Group')?.code
            return type !== undefined && group !== undefined ? `T${type} · G${group}` : id
          })()}
        </span>
      </div>
    </div>
  )

  if (article?.image_url && !failed) {
    return (
      <div className={`relative ${className} ${rounded} overflow-hidden bg-ink-800`}>
        {!loaded && <div className="skeleton absolute inset-0" />}
        <img
          src={article.image_url}
          alt={`Article ${id}`}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-500 ${
            loaded ? 'opacity-100' : 'opacity-0'
          }`}
        />
      </div>
    )
  }

  return placeholder
}
