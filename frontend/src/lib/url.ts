/**
 * Shareable listing links: ?listing=PAI-DEMO-002
 * Pure functions (URL string in, value out) so they are easy to test.
 */

const PARAM = "listing";

/** The listing code in a URL, or null if there is none. */
export function listingFromUrl(href: string): string | null {
  const code = new URL(href).searchParams.get(PARAM)?.trim();
  return code ? code : null;
}

/** The same URL with ?listing set to `code`, or removed when `code` is null. */
export function withListing(href: string, code: string | null): string {
  const url = new URL(href);
  if (code === null) url.searchParams.delete(PARAM);
  else url.searchParams.set(PARAM, code);
  url.hash = "";
  return url.toString();
}
