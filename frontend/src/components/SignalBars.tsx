import { motion } from 'framer-motion'
import type { ComponentScores } from '../lib/api'

const SIGNALS: { key: keyof ComponentScores; label: string; color: string }[] = [
  { key: 'collaborative', label: 'Collaborative', color: '#7c6cff' },
  { key: 'content', label: 'Content match', color: '#e44fcb' },
  { key: 'popularity', label: 'Popularity', color: '#4ea8ff' },
  { key: 'repurchase', label: 'Repeat-buy', color: '#d9b98a' },
]

/** Honest signal-strength bars (normalized 0–1 component scores). */
export default function SignalBars({ components, compact = false }: { components: ComponentScores; compact?: boolean }) {
  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
      {SIGNALS.map(({ key, label, color }) => (
        <div key={key} className="flex items-center gap-2">
          <span className={`${compact ? 'w-[86px] text-[9px]' : 'w-[96px] text-[10px]'} shrink-0 font-grotesk uppercase tracking-[0.14em] text-faint`}>
            {label}
          </span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
            <motion.div
              className="h-full rounded-full"
              style={{ background: color }}
              initial={{ width: 0 }}
              whileInView={{ width: `${Math.round(components[key] * 100)}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
          <span className="w-7 shrink-0 text-right font-grotesk text-[9px] text-mist/80">
            {Math.round(components[key] * 100)}
          </span>
        </div>
      ))}
    </div>
  )
}
