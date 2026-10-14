/**
 * Prop AI - API client.
 *
 * The only place that knows URLs, query formats and error shapes of the
 * backend. Types mirror backend/app/schemas/property.py; keep them in sync.
 */

// Public by design: VITE_* values are bundled into the JavaScript every
// visitor downloads. Never put secrets in them.
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export type ListingType = "sale" | "rent";
export type PropertyType = "apartment" | "villa" | "independent_house" | "studio" | "penthouse";
export type Furnishing = "unfurnished" | "semi_furnished" | "fully_furnished";

/** Mirrors PropertyRead. price_inr is whole rupees: total for sale, monthly for rent. */
export interface Property {
  listing_code: string;
  title: string;
  description: string;
  listing_type: ListingType;
  property_type: PropertyType;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  price_inr: number;
  city: string;
  locality: string;
  furnishing: Furnishing;
  amenities: string[];
  status: string;
  available_from: string | null;
  is_demo_data: boolean;
}

/** Mirrors PropertySearchFilters. listing_type is required, as in the API. */
export interface SearchFilters {
  listing_type: ListingType;
  city?: string;
  locality?: string;
  property_type?: PropertyType;
  bedrooms?: number;
  min_price?: number;
  max_price?: number;
  furnishing?: Furnishing;
  amenities?: string[];
  limit?: number;
}

export interface SearchResponse {
  count: number;
  results: Property[];
}

/** Any failure talking to the API. status 0 = the API could not be reached. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Turn filters into a query string, leaving out anything not set. */
export function buildSearchQuery(filters: SearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      // FastAPI reads lists as repeated keys: ?amenities=a&amenities=b
      for (const item of value) params.append(key, String(item));
    } else {
      params.set(key, String(value));
    }
  }
  return params;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    detail = ((await response.json()) as { detail?: unknown }).detail;
  } catch {
    // Body was not JSON; fall through to a generic message.
  }
  if (typeof detail === "string") return new ApiError(response.status, detail);
  if (response.status === 422) return new ApiError(422, "Some search filters are invalid.");
  return new ApiError(response.status, `Request failed (${response.status}).`);
}

type RequestOptions = { signal?: AbortSignal };

/** Shared GET logic: one place for network errors, status checks and JSON. */
async function getJson<T>(path: string, options: RequestOptions): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal: options.signal });
  } catch (error) {
    // A cancelled request is expected (inputs changed); let the caller ignore it.
    if (options.signal?.aborted) throw error;
    throw new ApiError(0, "Can't reach the Prop AI API. Is the backend running?");
  }

  // fetch does NOT throw on 404/422/500, so check the status ourselves.
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as T;
}

export function searchProperties(
  filters: SearchFilters,
  options: RequestOptions = {}
): Promise<SearchResponse> {
  return getJson(`/properties/search?${buildSearchQuery(filters)}`, options);
}

/** One listing by code, any status. Rejects with ApiError status 404 if unknown. */
export function getProperty(listingCode: string, options: RequestOptions = {}): Promise<Property> {
  // Encode: the code becomes part of the URL path, so "../health" must stay text.
  return getJson(`/properties/${encodeURIComponent(listingCode)}`, options);
}
