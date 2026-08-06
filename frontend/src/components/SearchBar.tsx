import { useEffect, useRef, useState } from 'react'

import { searchCompanies, type SearchResult } from '../api/client'

interface SearchBarProps {
  onSelect: (ticker: string) => void
  disabled?: boolean
}

export default function SearchBar({ onSelect, disabled }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([])
      setOpen(false)
      return
    }

    const timer = window.setTimeout(async () => {
      try {
        const data = await searchCompanies(query)
        setResults(data.results)
        setOpen(data.results.length > 0)
      } catch {
        setResults([])
        setOpen(false)
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
    <div className="search-bar" ref={wrapperRef}>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Search ticker or company (e.g. AMZN, Amazon)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={disabled}
          autoComplete="off"
        />
        <button type="submit" disabled={disabled || !query.trim()}>
          Analyze
        </button>
      </form>
      {open && (
        <ul className="search-dropdown">
          {results.map((result) => (
            <li key={result.cik}>
              <button type="button" onClick={() => handleSelect(result)}>
                <strong>{result.ticker}</strong>
                <span>{result.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
