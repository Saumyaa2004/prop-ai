import { useRef, useState } from "react";
import { listingFromUrl, withListing } from "@/lib/url";

/**
 * Which listing's details dialog is open, shared by every section that shows
 * listing cards (lifted state: one dialog, even for a shared ?listing= link).
 */
export function useListingDialog() {
  // Starts from the URL so shared links open the dialog on page load.
  const [code, setCode] = useState<string | null>(() => listingFromUrl(window.location.href));

  // The card button that opened the dialog, so focus can return to it on close
  // (Safari doesn't focus buttons on click, so we can't rely on the browser).
  // A ref, not state: it never affects what is rendered.
  const returnFocusRef = useRef<HTMLElement | null>(null);

  const select = (next: string | null) => {
    setCode(next);
    // Update the address bar without a reload or a new Back-button entry.
    window.history.replaceState(null, "", withListing(window.location.href, next));
  };

  const open = (listingCode: string, button: HTMLElement) => {
    returnFocusRef.current = button;
    select(listingCode);
  };

  return { code, open, close: () => select(null), returnFocusRef };
}
