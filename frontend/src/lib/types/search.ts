export interface SearchResult {
  ticker: string
  name: string
  cik: string
}

export interface SearchResponse {
  results: SearchResult[]
}
