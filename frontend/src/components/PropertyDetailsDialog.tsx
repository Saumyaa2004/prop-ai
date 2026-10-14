import { useState } from "react";
import type { ReactNode, RefObject } from "react";
import { CalendarCheck, Check, Link2, SearchX, ServerCrash } from "lucide-react";
import BookVisitCard from "@/components/BookVisitCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useProperty } from "@/hooks/useProperty";
import type { Property } from "@/lib/api";
import { formatDate, formatPrice, humanize } from "@/lib/format";
import { withListing } from "@/lib/url";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  available: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  under_offer: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  sold: "border-red-400/30 bg-red-400/10 text-red-300",
  rented: "border-red-400/30 bg-red-400/10 text-red-300",
};

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
      <dt className="text-[11px] text-white/45">{label}</dt>
      <dd className="text-sm text-white">{value}</dd>
    </div>
  );
}

function CopyLinkButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(withListing(window.location.href, code));
      setCopied(true); // only after the browser confirms the copy
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false); // clipboard blocked (e.g. insecure context); stay silent
    }
  };

  return (
    <Button variant="outline" size="sm" onClick={copy} className="gap-1.5">
      {copied ? <Check aria-hidden="true" /> : <Link2 aria-hidden="true" />}
      {copied ? "Link copied" : "Copy link"}
    </Button>
  );
}

function Details({ listing }: { listing: Property }) {
  const [booking, setBooking] = useState(false);
  const bookable = listing.status === "available";
  const perSqft =
    listing.listing_type === "sale"
      ? `₹${Math.round(listing.price_inr / listing.area_sqft).toLocaleString("en-IN")}/sq ft`
      : null;

  return (
    <>
      <DialogHeader className="gap-3 pr-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-white/40">{listing.listing_code}</span>
          <Badge className={cn("border", STATUS_STYLES[listing.status])}>
            {humanize(listing.status)}
          </Badge>
          <Badge className="border border-white/15 bg-white/5 text-white/50">Demo</Badge>
        </div>
        <DialogTitle className="text-xl text-white">{listing.title}</DialogTitle>
        <div className="flex items-baseline gap-3">
          <p className="text-2xl font-semibold text-white">
            {formatPrice(listing.price_inr, listing.listing_type)}
          </p>
          {perSqft && <p className="text-sm text-white/50">{perSqft}</p>}
        </div>
        <DialogDescription className="text-white/65">
          {listing.description}
        </DialogDescription>
      </DialogHeader>

      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Fact label="Location" value={`${listing.locality}, ${listing.city}`} />
        <Fact label="Type" value={humanize(listing.property_type)} />
        <Fact
          label="Bedrooms"
          value={listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms} BHK`}
        />
        <Fact label="Bathrooms" value={listing.bathrooms} />
        <Fact label="Area" value={`${listing.area_sqft} sq ft`} />
        <Fact label="Furnishing" value={humanize(listing.furnishing)} />
        <Fact
          label="Available from"
          value={listing.available_from ? formatDate(listing.available_from) : "Not specified"}
        />
        <Fact label="For" value={listing.listing_type === "sale" ? "Sale" : "Rent"} />
      </dl>

      <div>
        <h3 className="mb-2 text-xs font-medium tracking-wider text-white/50 uppercase">
          Amenities
        </h3>
        <ul className="flex flex-wrap gap-1.5">
          {listing.amenities.map((amenity) => (
            <li
              key={amenity}
              className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/75"
            >
              {humanize(amenity)}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
        <p className="text-xs text-white/40">Fictional demo listing for Prop AI.</p>
        <div className="flex gap-2">
          <CopyLinkButton code={listing.listing_code} />
          {bookable && !booking && (
            <Button size="sm" onClick={() => setBooking(true)} className="gap-1.5">
              <CalendarCheck aria-hidden="true" />
              Book a visit
            </Button>
          )}
        </div>
      </div>

      {booking && <BookVisitCard listingCode={listing.listing_code} title={listing.title} />}
    </>
  );
}

function StateMessage({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="flex flex-col items-center py-8 text-center">
      <div className="mb-3 text-white/50">{icon}</div>
      <DialogTitle className="text-white">{title}</DialogTitle>
      <DialogDescription className="mt-1 max-w-sm text-white/55">{body}</DialogDescription>
    </div>
  );
}

export default function PropertyDetailsDialog({
  code,
  onClose,
  returnFocusRef,
}: {
  code: string | null;
  onClose: () => void;
  /** Element to focus after closing (the card that opened it). */
  returnFocusRef?: RefObject<HTMLElement | null>;
}) {
  const { data, error, loading } = useProperty(code);

  return (
    <Dialog open={code !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        // Back to the card that opened it; `true` = Base UI's default (e.g. after a deep link).
        finalFocus={() => returnFocusRef?.current ?? true}
        className="max-h-[90vh] gap-5 overflow-y-auto border border-white/10 bg-zinc-950 p-6 text-white sm:max-w-xl">
        {loading ? (
          <div aria-busy="true" className="space-y-3">
            <DialogTitle className="sr-only">Loading listing…</DialogTitle>
            <div className="h-4 w-32 animate-pulse rounded bg-white/10" />
            <div className="h-6 w-64 animate-pulse rounded bg-white/10" />
            <div className="h-24 animate-pulse rounded bg-white/5" />
          </div>
        ) : error?.status === 404 ? (
          <StateMessage
            icon={<SearchX className="size-8" aria-hidden="true" />}
            title="Listing not found"
            body={`There is no listing with the code ${code}. The link may be mistyped or out of date.`}
          />
        ) : error ? (
          <StateMessage
            icon={<ServerCrash className="size-8" aria-hidden="true" />}
            title={error.status === 0 ? "The API isn't reachable" : "Couldn't load this listing"}
            body={error.status === 0 ? "Start the backend and try again." : error.message}
          />
        ) : data ? (
          // key: a different listing starts with a fresh booking form
          <Details key={data.listing_code} listing={data} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
