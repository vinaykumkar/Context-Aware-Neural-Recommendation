// Display helpers. Prices in this dataset are normalized (H&M source units),
// so they are shown as relative values, never as invented currency amounts.

export function normPrice(p: number | null | undefined): string {
  if (p === null || p === undefined) return '—'
  return p.toFixed(3)
}

export function compactNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`
  return String(n)
}

export function shortDate(d: string | null | undefined): string {
  if (!d) return '—'
  const dt = new Date(d)
  if (isNaN(dt.getTime())) return d
  return dt.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

export function fullDate(d: string | null | undefined): string {
  if (!d) return '—'
  const dt = new Date(d)
  if (isNaN(dt.getTime())) return d
  return dt.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function channelName(id: number): string {
  return id === 1 ? 'In-store' : 'Online'
}

/** Deterministic accent pair derived from an id — used by editorial placeholders. */
export function accentPair(seed: number | string): [string, string] {
  const n = typeof seed === 'string' ? hashString(seed) : seed
  const palettes: [string, string][] = [
    ['#7c6cff', '#4ea8ff'],
    ['#e44fcb', '#7c6cff'],
    ['#4ea8ff', '#e44fcb'],
    ['#d9b98a', '#7c6cff'],
    ['#74b9ff', '#e8d3ac'],
    ['#9884ff', '#ef7fdd'],
  ]
  return palettes[n % palettes.length]
}

function hashString(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}
