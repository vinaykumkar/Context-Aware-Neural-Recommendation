import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export interface FilterState {
  gender?: string
  ageGroup?: string
  productGroup?: string
  priceRange?: string
  minPrice?: number
  maxPrice?: number
  sort: string
  reason?: string
}

interface FilterSidebarProps {
  filters: FilterState
  onChange: (filters: FilterState) => void
  onReset: () => void
  totalCount?: number
  mode?: 'articles' | 'customers'
}

export const GENDER_OPTIONS = [
  { label: 'Ladieswear', value: 'Ladieswear' },
  { label: 'Menswear', value: 'Menswear' },
  { label: 'Divided / Young Fashion', value: 'Divided' },
  { label: 'Baby & Children', value: 'Baby/Children' },
  { label: 'Sportswear & Active', value: 'Sport' },
]

export const AGE_OPTIONS = [
  { label: 'Gen Z / Young (18–25 yrs)', value: '18-25', min: 18, max: 25 },
  { label: 'Young Adults (26–35 yrs)', value: '26-35', min: 26, max: 35 },
  { label: 'Mature Adults (36–50 yrs)', value: '36-50', min: 36, max: 50 },
  { label: 'Seniors (51+ yrs)', value: '51-100', min: 51, max: 100 },
]

export const PRODUCT_GROUPS = [
  { label: 'Upper Body (Shirts, Knitwear)', value: 'Garment Upper body' },
  { label: 'Lower Body (Trousers, Skirts)', value: 'Garment Lower body' },
  { label: 'Full Body (Dresses, Jumpsuits)', value: 'Garment Full body' },
  { label: 'Shoes & Footwear', value: 'Shoes' },
  { label: 'Accessories & Bags', value: 'Accessories' },
  { label: 'Underwear & Loungewear', value: 'Underwear' },
  { label: 'Swimwear', value: 'Swimwear' },
  { label: 'Nightwear', value: 'Nightwear' },
]

export const PRICE_PRESETS = [
  { label: 'Under $15', value: 'under-15', min: 0, max: 0.015 },
  { label: '$15 to $35', value: '15-35', min: 0.015, max: 0.035 },
  { label: '$35 to $60', value: '35-60', min: 0.035, max: 0.06 },
  { label: '$60 & Above', value: 'above-60', min: 0.06, max: undefined },
]

export const SORT_OPTIONS_ARTICLES = [
  { label: 'Featured / Recommended', value: 'popularity' },
  { label: 'Price: Low to High', value: 'price_asc' },
  { label: 'Price: High to Low', value: 'price_desc' },
  { label: 'Most Popular (Sales Count)', value: 'purchase_count' },
  { label: 'Trending (Recent 28d)', value: 'recency' },
]

export const SORT_OPTIONS_CUSTOMERS = [
  { label: 'Most Active (Purchase Count)', value: 'purchase_count' },
  { label: 'Recently Active (Recency)', value: 'recency' },
  { label: 'Top Spenders (Total Spent)', value: 'total_spent' },
  { label: 'Customer ID (A–Z)', value: 'customer_id' },
]

export default function FilterSidebar({
  filters,
  onChange,
  onReset,
  totalCount,
  mode = 'articles',
}: FilterSidebarProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    gender: true,
    age: true,
    category: true,
    price: true,
  })

  const toggleSection = (s: string) => {
    setOpenSections((prev) => ({ ...prev, [s]: !prev[s] }))
  }

  const activeFilterCount = [
    filters.gender,
    filters.ageGroup,
    filters.productGroup,
    filters.priceRange,
    filters.reason,
  ].filter(Boolean).length

  // Toggle helpers
  const handleGenderToggle = (val: string) => {
    onChange({
      ...filters,
      gender: filters.gender === val ? '' : val,
    })
  }

  const handleAgeToggle = (val: string) => {
    onChange({
      ...filters,
      ageGroup: filters.ageGroup === val ? '' : val,
    })
  }

  const handleCategoryToggle = (val: string) => {
    onChange({
      ...filters,
      productGroup: filters.productGroup === val ? '' : val,
    })
  }

  const handlePriceToggle = (preset: typeof PRICE_PRESETS[0]) => {
    if (filters.priceRange === preset.value) {
      onChange({
        ...filters,
        priceRange: '',
        minPrice: undefined,
        maxPrice: undefined,
      })
    } else {
      onChange({
        ...filters,
        priceRange: preset.value,
        minPrice: preset.min,
        maxPrice: preset.max,
      })
    }
  }

  return (
    <aside className="w-full lg:w-72 shrink-0 space-y-6">
      {/* Header with active filters count and Clear All */}
      <div className="flex items-center justify-between pb-3 border-b border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center gap-2">
          <span className="font-display text-lg font-medium text-neutral-950 dark:text-neutral-100">
            Filters
          </span>
          {activeFilterCount > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[#8b9e7a] text-white text-[11px] font-bold">
              {activeFilterCount}
            </span>
          )}
        </div>
        {activeFilterCount > 0 && (
          <button
            onClick={onReset}
            className="font-grotesk text-xs text-[#6d805c] dark:text-[#a4b893] hover:underline uppercase tracking-wider font-semibold transition-colors cursor-pointer"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Active Filter Chips */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {filters.gender && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#8b9e7a]/15 text-[#6d805c] dark:text-[#a4b893] border border-[#8b9e7a]/30 px-3 py-1 text-xs font-grotesk font-semibold">
              {filters.gender}
              <button
                onClick={() => onChange({ ...filters, gender: '' })}
                className="hover:text-red-500 font-bold ml-0.5 cursor-pointer"
                title="Remove filter"
              >
                ×
              </button>
            </span>
          )}
          {filters.ageGroup && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#8b9e7a]/15 text-[#6d805c] dark:text-[#a4b893] border border-[#8b9e7a]/30 px-3 py-1 text-xs font-grotesk font-semibold">
              Age: {filters.ageGroup}
              <button
                onClick={() => onChange({ ...filters, ageGroup: '' })}
                className="hover:text-red-500 font-bold ml-0.5 cursor-pointer"
                title="Remove filter"
              >
                ×
              </button>
            </span>
          )}
          {filters.productGroup && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#8b9e7a]/15 text-[#6d805c] dark:text-[#a4b893] border border-[#8b9e7a]/30 px-3 py-1 text-xs font-grotesk font-semibold">
              {filters.productGroup}
              <button
                onClick={() => onChange({ ...filters, productGroup: '' })}
                className="hover:text-red-500 font-bold ml-0.5 cursor-pointer"
                title="Remove filter"
              >
                ×
              </button>
            </span>
          )}
          {filters.priceRange && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#8b9e7a]/15 text-[#6d805c] dark:text-[#a4b893] border border-[#8b9e7a]/30 px-3 py-1 text-xs font-grotesk font-semibold">
              {PRICE_PRESETS.find((p) => p.value === filters.priceRange)?.label || 'Custom Price'}
              <button
                onClick={() =>
                  onChange({ ...filters, priceRange: '', minPrice: undefined, maxPrice: undefined })
                }
                className="hover:text-red-500 font-bold ml-0.5 cursor-pointer"
                title="Remove filter"
              >
                ×
              </button>
            </span>
          )}
        </div>
      )}

      {/* 1. Department / Gender Filter */}
      <div className="border-b border-neutral-200/70 dark:border-neutral-800/80 pb-5">
        <button
          onClick={() => toggleSection('gender')}
          className="flex w-full items-center justify-between py-2 text-left font-grotesk text-xs uppercase tracking-[0.16em] font-semibold text-neutral-900 dark:text-neutral-200 cursor-pointer"
        >
          <span>Department / Gender</span>
          <span className="text-neutral-400 font-light">{openSections.gender ? '−' : '+'}</span>
        </button>
        <AnimatePresence>
          {openSections.gender && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 space-y-1.5"
            >
              {GENDER_OPTIONS.map((opt) => {
                const active = (filters.gender || '') === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleGenderToggle(opt.value)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] font-sans transition-all cursor-pointer ${
                      active
                        ? 'bg-[#8b9e7a]/20 text-[#556b2f] dark:text-[#a4b893] font-semibold border border-[#8b9e7a]/40 shadow-2xs'
                        : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60'
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <span className={`w-4 h-4 rounded-md border flex items-center justify-center text-[10px] transition-colors ${
                        active ? 'bg-[#8b9e7a] border-[#8b9e7a] text-white font-bold' : 'border-neutral-300 dark:border-neutral-600'
                      }`}>
                        {active && '✓'}
                      </span>
                      <span>{opt.label}</span>
                    </span>
                  </button>
                )
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* 2. Age Demographic Filter (Amazon Style) */}
      <div className="border-b border-neutral-200/70 dark:border-neutral-800/80 pb-5">
        <button
          onClick={() => toggleSection('age')}
          className="flex w-full items-center justify-between py-2 text-left font-grotesk text-xs uppercase tracking-[0.16em] font-semibold text-neutral-900 dark:text-neutral-200 cursor-pointer"
        >
          <span>Age Demographic</span>
          <span className="text-neutral-400 font-light">{openSections.age ? '−' : '+'}</span>
        </button>
        <AnimatePresence>
          {openSections.age && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 space-y-1.5"
            >
              {AGE_OPTIONS.map((opt) => {
                const active = (filters.ageGroup || '') === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleAgeToggle(opt.value)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] font-sans transition-all cursor-pointer ${
                      active
                        ? 'bg-[#8b9e7a]/20 text-[#556b2f] dark:text-[#a4b893] font-semibold border border-[#8b9e7a]/40 shadow-2xs'
                        : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60'
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <span className={`w-4 h-4 rounded-md border flex items-center justify-center text-[10px] transition-colors ${
                        active ? 'bg-[#8b9e7a] border-[#8b9e7a] text-white font-bold' : 'border-neutral-300 dark:border-neutral-600'
                      }`}>
                        {active && '✓'}
                      </span>
                      <span>{opt.label}</span>
                    </span>
                  </button>
                )
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* 3. Product Group / Category Filter (Articles Mode) */}
      {mode === 'articles' && (
        <div className="border-b border-neutral-200/70 dark:border-neutral-800/80 pb-5">
          <button
            onClick={() => toggleSection('category')}
            className="flex w-full items-center justify-between py-2 text-left font-grotesk text-xs uppercase tracking-[0.16em] font-semibold text-neutral-900 dark:text-neutral-200 cursor-pointer"
          >
            <span>Product Category</span>
            <span className="text-neutral-400 font-light">{openSections.category ? '−' : '+'}</span>
          </button>
          <AnimatePresence>
            {openSections.category && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-3 space-y-1.5 max-h-60 overflow-y-auto pr-1"
              >
                {PRODUCT_GROUPS.map((opt) => {
                  const active = (filters.productGroup || '') === opt.value
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => handleCategoryToggle(opt.value)}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] font-sans transition-all cursor-pointer ${
                        active
                          ? 'bg-[#8b9e7a]/20 text-[#556b2f] dark:text-[#a4b893] font-semibold border border-[#8b9e7a]/40 shadow-2xs'
                          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60'
                      }`}
                    >
                      <span className="flex items-center gap-2.5">
                        <span className={`w-4 h-4 rounded-md border flex items-center justify-center text-[10px] transition-colors ${
                          active ? 'bg-[#8b9e7a] border-[#8b9e7a] text-white font-bold' : 'border-neutral-300 dark:border-neutral-600'
                        }`}>
                          {active && '✓'}
                        </span>
                        <span className="truncate">{opt.label}</span>
                      </span>
                    </button>
                  )
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* 4. Price Filter (Articles Mode) */}
      {mode === 'articles' && (
        <div className="border-b border-neutral-200/70 dark:border-neutral-800/80 pb-5">
          <button
            onClick={() => toggleSection('price')}
            className="flex w-full items-center justify-between py-2 text-left font-grotesk text-xs uppercase tracking-[0.16em] font-semibold text-neutral-900 dark:text-neutral-200 cursor-pointer"
          >
            <span>Price Range</span>
            <span className="text-neutral-400 font-light">{openSections.price ? '−' : '+'}</span>
          </button>
          <AnimatePresence>
            {openSections.price && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-3 space-y-1.5"
              >
                {PRICE_PRESETS.map((opt) => {
                  const active = (filters.priceRange || '') === opt.value
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => handlePriceToggle(opt)}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] font-sans transition-all cursor-pointer ${
                        active
                          ? 'bg-[#8b9e7a]/20 text-[#556b2f] dark:text-[#a4b893] font-semibold border border-[#8b9e7a]/40 shadow-2xs'
                          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800/60'
                      }`}
                    >
                      <span className="flex items-center gap-2.5">
                        <span className={`w-4 h-4 rounded-md border flex items-center justify-center text-[10px] transition-colors ${
                          active ? 'bg-[#8b9e7a] border-[#8b9e7a] text-white font-bold' : 'border-neutral-300 dark:border-neutral-600'
                        }`}>
                          {active && '✓'}
                        </span>
                        <span>{opt.label}</span>
                      </span>
                    </button>
                  )
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* 5. Summary Info */}
      {totalCount !== undefined && (
        <div className="pt-2">
          <p className="text-xs text-neutral-500 dark:text-neutral-400 font-grotesk">
            Showing <strong className="text-neutral-900 dark:text-neutral-100 font-semibold">{totalCount.toLocaleString()}</strong> results
          </p>
        </div>
      )}
    </aside>
  )
}
