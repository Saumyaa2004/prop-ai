import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";

type Result<T> =
  | { key: string; data: T; error: null }
  | { key: string; data: null; error: ApiError };

/**
 * Load data for `key`, re-running only when the key's value changes.
 * A null key means "nothing to load" (idle).
 *
 * `load` must be stable (defined at module level), or the effect would
 * re-run on every render.
 */
export function useApi<T>(
  key: string | null,
  load: (key: string, signal: AbortSignal) => Promise<T>
) {
  const [result, setResult] = useState<Result<T> | null>(null);

  useEffect(() => {
    if (key === null) return;
    const controller = new AbortController();

    load(key, controller.signal)
      .then((data) => setResult({ key, data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return; // superseded by a newer key
        const apiError =
          error instanceof ApiError ? error : new ApiError(0, "Unexpected error.");
        setResult({ key, data: null, error: apiError });
      });

    // Runs when the key changes or the component unmounts: cancel the old
    // request so a slow response can't overwrite newer results.
    return () => controller.abort();
  }, [key, load]);

  // Only trust a result that belongs to the current key.
  const current = key !== null && result?.key === key ? result : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: key !== null && current === null,
  };
}
