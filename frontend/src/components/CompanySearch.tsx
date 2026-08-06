import { useEffect, useRef, useState } from 'react'
import { ArrowUpIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Input } from '@/components/ui/input'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group'
import { cn } from '@/lib/utils'
import { searchCompanies } from '@/lib/api'
import type { SearchResult } from '@/lib/types'

interface CompanySearchProps {
  onSelect: (ticker: string) => void
  disabled?: boolean
  variant?: 'default' | 'hero'
  className?: string
}

export default function CompanySearch({
  onSelect,
  disabled,
  variant = 'default',
  className,
}: CompanySearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const isHero = variant === 'hero'

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
    <div
      className={cn(
        'relative w-full',
        isHero ? 'max-w-2xl' : 'max-w-md',
        className,
      )}
      ref={wrapperRef}
    >
      <form onSubmit={handleSubmit}>
        {isHero ? (
          <InputGroup className="h-14 rounded-2xl shadow-sm md:h-[3.25rem]">
            <InputGroupInput
              type="text"
              className="px-4 text-base"
              placeholder="Search ticker or company (e.g. AMZN, Amazon)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => results.length > 0 && setOpen(true)}
              disabled={disabled}
              autoComplete="off"
            />
            <InputGroupAddon align="inline-end" className="pr-2">
              <InputGroupButton
                type="submit"
                size="icon-sm"
                variant="default"
                className="rounded-full"
                disabled={disabled || !query.trim()}
              >
                <ArrowUpIcon />
                <span className="sr-only">Analyze</span>
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        ) : (
          <div className="flex gap-2">
            <Input
              type="text"
              className="h-9 flex-1"
              placeholder="Search ticker or company (e.g. AMZN, Amazon)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => results.length > 0 && setOpen(true)}
              disabled={disabled}
              autoComplete="off"
            />
            <Button type="submit" size="lg" disabled={disabled || !query.trim()}>
              Analyze
            </Button>
          </div>
        )}
      </form>

      {searchError && (
        <p className="mt-2 text-left text-sm text-destructive" role="alert">
          {searchError}
        </p>
      )}

      {open && results.length > 0 && (
        <div className="absolute top-[calc(100%+4px)] right-0 left-0 z-50 overflow-hidden rounded-xl border bg-popover shadow-md">
          <Command shouldFilter={false}>
            <CommandList>
              <CommandEmpty>No companies found.</CommandEmpty>
              <CommandGroup>
                {results.map((result) => (
                  <CommandItem
                    key={result.cik}
                    value={result.ticker}
                    onSelect={() => handleSelect(result)}
                    className="flex cursor-pointer flex-col items-start gap-0.5 py-2.5"
                  >
                    <span className="font-medium">{result.ticker}</span>
                    <span className="text-xs text-muted-foreground">
                      {result.name}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </div>
      )}
    </div>
  )
}
