import { useApi } from "@/hooks/useApi";
import { getProperty } from "@/lib/api";

const loadProperty = (code: string, signal: AbortSignal) => getProperty(code, { signal });

/** One listing by code; pass null when nothing is selected. */
export function useProperty(listingCode: string | null) {
  return useApi(listingCode, loadProperty);
}
