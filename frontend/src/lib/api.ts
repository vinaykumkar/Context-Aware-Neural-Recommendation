// Typed API client — all data access flows through here.

export interface ArticleFeature {
  feature: string
  code: number
}

export interface ArticleStats {
  purchase_count: number
  unique_customers: number
  avg_price: number | null
  first_sale_date: string | null
  last_sale_date: string | null
  sales_last_28d: number
  sales_last_84d: number
  popularity_rank: number | null
}

export interface Article {
  // canonical 10-digit zero-padded form, e.g. "0800691008" — never a number
  article_id: string
  features: ArticleFeature[]
  stats: ArticleStats
  image_url: string | null
  label: string | null
  product_type: string | null
  product_group: string | null
  colour: string | null
  department: string | null
  section: string | null
  garment_group: string | null
  graphical_appearance: string | null
  index_group: string | null
  index_name: string | null
}

export interface HistoryItem {
  article_id: string
  t_dat: string
  price: number
  sales_channel_id: number
  article: Article | null
}

export interface HistoryResponse {
  customer_id: string
  items: HistoryItem[]
  total_transactions: number
  returned: number
  range_start: string | null
  range_end: string | null
}

export type ReasonCode =
  | 'COLLABORATIVE'
  | 'CONTENT_SIMILARITY'
  | 'POPULARITY'
  | 'REPEAT_PURCHASE'
  | 'HYBRID'

export interface ComponentScores {
  collaborative: number
  content: number
  popularity: number
  repurchase: number
}

export interface RecommendationItem {
  rank: number
  article_id: string
  score: number
  components: ComponentScores
  reason: ReasonCode
  reason_text: string
  article: Article | null
}

export interface RecommendationResponse {
  customer_id: string
  items: RecommendationItem[]
  source: 'precomputed' | 'popularity_fallback'
  filtered_out: number
  count: number
}

export interface CustomerSummary {
  customer_id: string
  short_id: string
  age: number | null
  club_member_status: string | null
  fashion_news_frequency: string | null
  active: number | null
  purchase_count: number
  unique_articles_count: number
  average_price: number | null
  total_spent: number | null
  recency_days: number | null
  purchase_frequency: number | null
  customer_lifetime_days: number | null
  has_purchases: boolean
}

export interface CustomerListResponse {
  items: CustomerSummary[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ArticleListResponse {
  items: Article[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface CategoryAffinity {
  feature: string
  code: number
  label: string
}

export interface CustomerProfileResponse {
  customer: CustomerSummary
  first_purchase_date: string | null
  last_purchase_date: string | null
  top_categories: CategoryAffinity[]
}

export interface SimilarArticle {
  article_id: string
  score: number
  article: Article | null
}

export interface ArticleResponse {
  article: Article
  similar: SimilarArticle[]
}

export interface AppConfig {
  image_mode: string
  image_url_template: boolean
  history_per_customer: number
  max_recommendation_count: number
  diversity_rerank: boolean
  exclude_purchased: boolean
}

export interface DatasetStats {
  n_transactions: number
  min_date: string
  max_date: string
  n_active_customers: number
  n_purchased_articles: number
  n_articles: number
  n_customers: number
  min_age: number | null
  max_age: number | null
  avg_age: number | null
}

export interface StatsResponse {
  status: string
  dataset: DatasetStats
  serving: Record<string, unknown>
  model: Record<string, unknown>
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      if (data && data.detail) detail = data.detail
    } catch {}
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string; serving: Record<string, unknown> }>('/api/health'),
  config: () => request<AppConfig>('/api/config'),
  stats: () => request<StatsResponse>('/api/stats'),
  popularArticles: (limit = 12) => request<Article[]>(`/api/articles/popular?limit=${limit}`),
  articles: (params: {
    q?: string
    gender?: string
    product_group?: string
    age_group?: string
    min_price?: number
    max_price?: number
    sort?: string
    page?: number
    page_size?: number
  }) => {
    const usp = new URLSearchParams()
    if (params.q) usp.set('q', params.q)
    if (params.gender) usp.set('gender', params.gender)
    if (params.product_group) usp.set('product_group', params.product_group)
    if (params.age_group) usp.set('age_group', params.age_group)
    if (params.min_price !== undefined) usp.set('min_price', String(params.min_price))
    if (params.max_price !== undefined) usp.set('max_price', String(params.max_price))
    if (params.sort) usp.set('sort', params.sort)
    if (params.page) usp.set('page', String(params.page))
    if (params.page_size) usp.set('page_size', String(params.page_size))
    return request<ArticleListResponse>(`/api/articles?${usp.toString()}`)
  },
  customers: (params: {
    q?: string
    page?: number
    page_size?: number
    sort?: string
    has_purchases?: boolean
    age_min?: number
    age_max?: number
  }) => {
    const usp = new URLSearchParams()
    if (params.q) usp.set('q', params.q)
    if (params.page) usp.set('page', String(params.page))
    if (params.page_size) usp.set('page_size', String(params.page_size))
    if (params.sort) usp.set('sort', params.sort)
    if (params.has_purchases !== undefined) usp.set('has_purchases', String(params.has_purchases))
    if (params.age_min !== undefined) usp.set('age_min', String(params.age_min))
    if (params.age_max !== undefined) usp.set('age_max', String(params.age_max))
    return request<CustomerListResponse>(`/api/customers?${usp.toString()}`)
  },
  customerProfile: (id: string) => request<CustomerProfileResponse>(`/api/customers/${id}`),
  customerHistory: (id: string, limit = 60) => request<HistoryResponse>(`/api/customers/${id}/history?limit=${limit}`),
  customerRecommendations: (id: string, count = 10) =>
    request<RecommendationResponse>(`/api/customers/${id}/recommendations?count=${count}`),
  article: (id: number | string) => request<ArticleResponse>(`/api/articles/${id}`),
}

export function articleLabel(a: Article | null): string {
  if (!a) return 'Article'
  if (a.label) return a.label
  return `Product ${a.article_id}`
}

/** Human-readable chips for a card: only fields that actually exist. */
export function articleChips(a: Article | null, n = 3): string[] {
  if (!a) return []
  const candidates = [a.colour, a.product_type, a.garment_group].filter(
    (v): v is string => !!v,
  )
  return candidates.slice(0, n)
}

// Kept only as an internal fallback when no display names exist.
// The UI prefers articleChips() (human-readable labels) — see requirement:
// never show numeric codes when text exists.
export function featureChips(a: Article | null, n = 3): string[] {
  if (!a) return []
  return a.features.slice(0, n).map((f) => `${f.feature} ·${f.code}`)
}
