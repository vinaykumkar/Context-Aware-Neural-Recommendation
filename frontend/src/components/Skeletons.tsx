export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`panel overflow-hidden p-3 ${className}`}>
      <div className="skeleton aspect-[3/4] w-full" />
      <div className="mt-3 space-y-2">
        <div className="skeleton h-3 w-3/4" />
        <div className="skeleton h-3 w-1/2" />
      </div>
    </div>
  )
}

export function SkeletonGrid({ count = 10, cols = 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5' }: { count?: number; cols?: string }) {
  return (
    <div className={`grid gap-4 ${cols}`}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function SkeletonRows({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="panel flex items-center gap-4 p-4">
          <div className="skeleton h-14 w-14 rounded-xl" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-3 w-1/3" />
            <div className="skeleton h-3 w-1/4" />
          </div>
          <div className="skeleton h-3 w-16" />
        </div>
      ))}
    </div>
  )
}

export function StatePanel({ title, body, hint }: { title: string; body: string; hint?: string }) {
  return (
    <div className="panel mx-auto max-w-lg p-10 text-center">
      <div className="mx-auto mb-5 h-10 w-10 rounded-full border border-iris-500/40 bg-iris-500/10" />
      <h3 className="font-display text-xl text-ivory">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-mist">{body}</p>
      {hint && <p className="mt-4 font-grotesk text-[10px] uppercase tracking-[0.2em] text-faint">{hint}</p>}
    </div>
  )
}
