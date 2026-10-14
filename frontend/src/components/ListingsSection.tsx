import { useState } from "react";
import type { ReactNode } from "react";
import { ServerCrash, SearchX } from "lucide-react";
import ListingCard from "@/components/ListingCard";
import { usePropertySearch } from "@/hooks/usePropertySearch";
import type { ListingType, SearchFilters } from "@/lib/api";
import { cn } from "@/lib/utils";

// Localities present in the demo seed data. (No API endpoint lists them yet.)
const LOCALITIES = [
  "Powai",
  "Andheri West",
  "Andheri East",
  "Bandra West",
  "Thane West",
  "Goregaon East",
  "Chembur",
];

const BEDROOM_OPTIONS = [
  { value: 0, label: "Studio" },
  { value: 1, label: "1 BHK" },
  { value: 2, label: "2 BHK" },
  { value: 3, label: "3 BHK" },
  { value: 4, label: "4 BHK" },
];

// Separate budget lists per listing type: sale prices are totals, rent is monthly.
const BUDGETS: Record<ListingType, { value: number; label: string }[]> = {
  sale: [
    { value: 10_000_000, label: "Under ₹1 Cr" },
    { value: 15_000_000, label: "Under ₹1.5 Cr" },
    { value: 20_000_000, label: "Under ₹2 Cr" },
    { value: 50_000_000, label: "Under ₹5 Cr" },
  ],
  rent: [
    { value: 35_000, label: "Under ₹35k/mo" },
    { value: 50_000, label: "Under ₹50k/mo" },
    { value: 75_000, label: "Under ₹75k/mo" },
  ],
};

const selectClass =
  "h-10 w-full rounded-lg border border-white/15 bg-black/60 px-3 text-sm text-white outline-none transition-colors focus-visible:border-white/40 focus-visible:ring-2 focus-visible:ring-white/20";

function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-white/50">
      {label}
      {children}
    </label>
  );
}

function SkeletonCard() {
  return (
    <div className="h-56 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
  );
}

function Message({ icon, title, body }: { icon: ReactNode; title: string; body: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-white/15 px-6 py-14 text-center">
      <div className="mb-3 text-white/50">{icon}</div>
      <p className="font-medium text-white">{title}</p>
      <div className="mt-1 max-w-md text-sm text-white/50">{body}</div>
    </div>
  );
}

export default function ListingsSection({
  onOpenListing,
}: {
  onOpenListing: (code: string, button: HTMLButtonElement) => void;
}) {
  const [listingType, setListingType] = useState<ListingType>("sale");
  const [locality, setLocality] = useState("");
  const [bedrooms, setBedrooms] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  const filters: SearchFilters = {
    listing_type: listingType,
    locality: locality || undefined,
    bedrooms: bedrooms === "" ? undefined : Number(bedrooms),
    max_price: maxPrice === "" ? undefined : Number(maxPrice),
  };
  const { data, error, loading } = usePropertySearch(filters);

  const changeListingType = (next: ListingType) => {
    setListingType(next);
    // A sale budget means nothing for monthly rent (and vice versa).
    setMaxPrice("");
  };

  return (
    <section id="listings" className="mx-auto max-w-6xl scroll-mt-20 px-4 pb-24 sm:px-6">
      <div className="mb-8 max-w-2xl">
        <p className="mb-3 text-sm font-medium tracking-wider text-blue-300 uppercase">
          Live listings
        </p>
        <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Try the search yourself
        </h2>
        <p className="mt-4 text-white/60">
          Every result comes straight from the API.
        </p>
      </div>

      <div className="mb-8 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.02] p-4 sm:grid-cols-2 lg:grid-cols-4">
        <FilterField label="Looking to">
          <div className="grid h-10 grid-cols-2 rounded-lg border border-white/15 bg-black/60 p-1">
            {(["sale", "rent"] as const).map((type) => (
              <button
                key={type}
                type="button"
                aria-pressed={listingType === type}
                onClick={() => changeListingType(type)}
                className={cn(
                  "rounded-md text-sm transition-colors focus-visible:ring-2 focus-visible:ring-white/30 focus-visible:outline-none",
                  listingType === type
                    ? "bg-white text-black"
                    : "text-white/60 hover:text-white"
                )}
              >
                {type === "sale" ? "Buy" : "Rent"}
              </button>
            ))}
          </div>
        </FilterField>
        <FilterField label="Locality">
          <select
            className={selectClass}
            value={locality}
            onChange={(e) => setLocality(e.target.value)}
          >
            <option value="">Any locality</option>
            {LOCALITIES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Bedrooms">
          <select
            className={selectClass}
            value={bedrooms}
            onChange={(e) => setBedrooms(e.target.value)}
          >
            <option value="">Any</option>
            {BEDROOM_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Budget">
          <select
            className={selectClass}
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
          >
            <option value="">Any budget</option>
            {BUDGETS[listingType].map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FilterField>
      </div>

      <p className="mb-4 text-sm text-white/50" aria-live="polite">
        {loading
          ? "Searching…"
          : data && data.count > 0
            ? `${data.count} available ${data.count === 1 ? "listing" : "listings"}, cheapest first`
            : ""}
      </p>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error ? (
        <Message
          icon={<ServerCrash className="size-8" aria-hidden="true" />}
          title={error.status === 0 ? "The API isn't reachable" : "Search failed"}
          body={
            error.status === 0 ? (
              <>
                Start the backend from <code className="text-white/70">backend\</code>:
                <code className="mt-2 block rounded bg-white/5 px-2 py-1 text-xs text-white/70">
                  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
                </code>
              </>
            ) : (
              error.message
            )
          }
        />
      ) : data && data.count === 0 ? (
        <Message
          icon={<SearchX className="size-8" aria-hidden="true" />}
          title="No available listings match"
          body="Try a higher budget, another locality or any number of bedrooms."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.results.map((listing) => (
            <ListingCard
              key={listing.listing_code}
              listing={listing}
              onOpen={(button) => onOpenListing(listing.listing_code, button)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
