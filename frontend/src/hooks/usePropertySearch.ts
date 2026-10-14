import { useEffect, useState } from "react";
import { ApiError, searchProperties } from "@/lib/api";
import type { SearchFilters, SearchResponse } from "@/lib/api";

type Result =
  | { key: string; data: SearchResponse; error: null }
  | { key: string; data: null; error: ApiError };

/** Fetch search results whenever the filters' contents change. */
export function usePropertySearch(filters: SearchFilters) {
  // Compare filters by content: a new object is created on every render, and
  // depending on the object itself would refetch forever.
  const key = JSON.stringify(filters);
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    searchProperties(JSON.parse(key) as SearchFilters, { signal: controller.signal })
      .then((data) => setResult({ key, data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return; // superseded by newer filters
        const apiError =
          error instanceof ApiError ? error : new ApiError(0, "Unexpected error.");
        setResult({ key, data: null, error: apiError });
      });

    // Runs when the filters change or the component unmounts: cancel the old
    // request so a slow response can't overwrite newer results.
    return () => controller.abort();
  }, [key]);

  // Only trust a result that belongs to the current filters.
  const current = result?.key === key ? result : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: current === null,
  };
}
