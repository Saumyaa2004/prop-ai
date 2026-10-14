import { BedDouble, CalendarDays, MapPin, Ruler } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Property } from "@/lib/api";
import { formatDate, formatPrice, humanize } from "@/lib/format";

/** A listing summary card. Used by the listings grid and the AI chat. */
export default function ListingCard({
  listing,
  onOpen,
}: {
  listing: Property;
  onOpen: (button: HTMLButtonElement) => void;
}) {
  return (
    <Card className="relative border border-white/10 bg-white/[0.03] transition-colors hover:border-white/25 has-[button:focus-visible]:border-white/50">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <p className="font-mono text-xs text-white/40">{listing.listing_code}</p>
          <Badge className="border border-white/15 bg-white/5 text-[10px] text-white/50">
            Demo
          </Badge>
        </div>
        <CardTitle className="text-base text-white">
          {/* "Stretched button": the ::after layer makes the whole card clickable
              while screen readers still announce just the title as the button. */}
          <button
            type="button"
            onClick={(e) => onOpen(e.currentTarget)}
            className="text-left outline-none after:absolute after:inset-0 after:rounded-xl after:content-['']"
          >
            {listing.title}
          </button>
        </CardTitle>
        <p className="text-xl font-semibold text-white">
          {formatPrice(listing.price_inr, listing.listing_type)}
        </p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-white/60">
        <div className="flex flex-wrap gap-x-4 gap-y-1.5">
          <span className="flex items-center gap-1.5">
            <MapPin className="size-4" aria-hidden="true" />
            {listing.locality}
          </span>
          <span className="flex items-center gap-1.5">
            <BedDouble className="size-4" aria-hidden="true" />
            {listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms} BHK`}
          </span>
          <span className="flex items-center gap-1.5">
            <Ruler className="size-4" aria-hidden="true" />
            {listing.area_sqft} sq ft
          </span>
          {listing.available_from && (
            <span className="flex items-center gap-1.5">
              <CalendarDays className="size-4" aria-hidden="true" />
              From {formatDate(listing.available_from, { year: false })}
            </span>
          )}
        </div>
        <p className="text-xs text-white/45">{humanize(listing.furnishing)}</p>
        <ul className="flex flex-wrap gap-1.5" aria-label="Amenities">
          {listing.amenities.map((amenity) => (
            <li
              key={amenity}
              className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70"
            >
              {humanize(amenity)}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
