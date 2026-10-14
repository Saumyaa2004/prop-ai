import { useApi } from "@/hooks/useApi";
import { searchProperties } from "@/lib/api";
import type { SearchFilters } from "@/lib/api";

// Module level, so the function identity never changes between renders.
const loadSearch = (key: string, signal: AbortSignal) =>
  searchProperties(JSON.parse(key) as SearchFilters, { signal });

/** Search results, refetched whenever the filters' contents change. */
export function usePropertySearch(filters: SearchFilters) {
  // Compare filters by content: a new object is created on every render.
  return useApi(JSON.stringify(filters), loadSearch);
}
