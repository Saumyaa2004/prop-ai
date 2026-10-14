import type { ListingType } from "@/lib/api";

const CRORE = 10_000_000;
const LAKH = 100_000;
const indianNumber = new Intl.NumberFormat("en-IN");

/** 1.40 -> "1.4", 12.50 -> "12.5", 2.00 -> "2" */
function trimDecimals(value: number): string {
  return value.toFixed(2).replace(/\.?0+$/, "");
}

/**
 * Display a whole-rupee price. The API never sends floats; division happens
 * here only to produce a label.
 *   sale: 13_800_000 -> "₹1.38 Cr", 9_800_000 -> "₹98 L"
 *   rent: 42_000 -> "₹42,000/mo"
 */
export function formatPrice(priceInr: number, listingType: ListingType): string {
  if (listingType === "rent") return `₹${indianNumber.format(priceInr)}/mo`;
  if (priceInr >= CRORE) return `₹${trimDecimals(priceInr / CRORE)} Cr`;
  if (priceInr >= LAKH) return `₹${trimDecimals(priceInr / LAKH)} L`;
  return `₹${indianNumber.format(priceInr)}`;
}

/** "power_backup" -> "Power backup" */
export function humanize(value: string): string {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
