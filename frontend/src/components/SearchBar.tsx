import { useEffect, useRef, useState } from 'react'

import { searchCompanies } from '../lib/api'
import type { SearchResult } from '../lib/types'

interface SearchBarProps {
  onSelect: (ticker: string) => void
  disabled?: boolean
}

export default function SearchBar({ onSelect, disabled }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([])
      setOpen(false)
      setSearchError(null)
      return
    }

    const timer = window.setTimeout(async () => {
      try {
        const data = await searchCompanies(query)
        setResults(data.results)
        setOpen(data.results.length > 0)
        setSearchError(null)
      } catch (err) {
        setResults([])
        setOpen(false)
        setSearchError(
          err instanceof Error ? err.message : 'Search unavailable. Try again.',
        )
      }
    }, 300)

    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    onSelect(trimmed.toUpperCase())
    setOpen(false)
  }

  function handleSelect(result: SearchResult) {
    setQuery(result.ticker)
    onSelect(result.ticker)
    setOpen(false)
  }

  return (
    <div className="relative mx-auto w-full max-w-xl" ref={wrapperRef}>
      <form className="flex gap-2 shadow-[var(--shadow-app)]" onSubmit={handleSubmit}>
        <input
          type="text"
          className="flex-1 rounded-lg border border-border bg-bg px-4 py-3 font-[inherit] text-text-heading outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
          placeholder="Search ticker or company (e.g. AMZN, Amazon)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={disabled}
          autoComplete="off"
        />
        <button
          type="submit"
          className="cursor-pointer rounded-lg border-none bg-accent px-5 py-3 font-[inherit] font-medium text-white hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled || !query.trim()}
        >
          Analyze
        </button>
      </form>

      {searchError && (
        <p className="mt-2 text-left text-sm text-negative" role="alert">
          {searchError}
        </p>
      )}

      {open && (
        <ul className="absolute top-[calc(100%+6px)] right-0 left-0 z-10 m-0 list-none rounded-lg border border-border bg-bg p-1 shadow-[var(--shadow-app)]">
          {results.map((result) => (
            <li key={result.cik}>
              <button
                type="button"
                className="flex w-full cursor-pointer flex-col items-start gap-0.5 rounded-md border-none bg-transparent px-3 py-2.5 text-left text-text-heading hover:bg-accent-bg"
                onClick={() => handleSelect(result)}
              >
                <strong className="text-accent">{result.ticker}</strong>
                <span className="text-sm text-text">{result.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
