import {
  ArrowRight,
  BedDouble,
  Bot,
  Building2,
  CalendarCheck,
  Car,
  CodeXml,
  Database,
  MapPin,
  LockKeyhole,
  Mic,
  Ruler,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import RadialOrbitalTimeline from "@/components/ui/radial-orbital-timeline";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ChatSection from "@/components/ChatSection";
import ListingsSection from "@/components/ListingsSection";
import PropertyDetailsDialog from "@/components/PropertyDetailsDialog";
import { useListingDialog } from "@/hooks/useListingDialog";
import { sections } from "@/data/sections";
import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

const GITHUB_URL = "https://github.com/Saumyaa2004/prop-ai";

// Verified Unsplash photos (illustrative only, not the demo listings).
const PHOTO_INTERIOR =
  "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200&q=80&auto=format&fit=crop";
const PHOTO_BUILDING =
  "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=900&q=80&auto=format&fit=crop";

// Real response from GET /properties/search for the query shown on the page
// (fictional seed data; prices in whole rupees, as the API returns them).
const SAMPLE_RESULTS = [
  {
    code: "PAI-DEMO-002",
    title: "Hiranandani Gardens 2BHK",
    locality: "Powai",
    priceInr: 13_800_000,
    areaSqft: 850,
    bedrooms: 2,
  },
  {
    code: "PAI-DEMO-001",
    title: "Lakeview Residency 2BHK",
    locality: "Powai",
    priceInr: 14_500_000,
    areaSqft: 780,
    bedrooms: 2,
  },
];

type Feature = {
  icon: LucideIcon;
  title: string;
  body: string;
  live: boolean;
};

const FEATURES: Feature[] = [
  {
    icon: Search,
    title: "Exact search, not guesses",
    body: "Budget, bedrooms, locality and amenities are filtered in SQL. Sale prices and monthly rents never mix.",
    live: true,
  },
  {
    icon: ShieldCheck,
    title: "Honest answers",
    body: "Ask about a sold flat and you hear it's sold. Unknown listing codes get a clear 'not found', never made-up details.",
    live: true,
  },
  {
    icon: Bot,
    title: "AI agent with real tools",
    body: "The assistant answers by calling the same tested backend functions. It never writes SQL or invents listings.",
    live: true,
  },
  {
    icon: Mic,
    title: "Voice first",
    body: "Speak your search and hear replies read aloud. Typing always works as a fallback.",
    live: true,
  },
  {
    icon: CalendarCheck,
    title: "Book a site visit",
    body: "Ask the assistant for a time; you confirm on a card. The database guarantees a slot is never booked twice.",
    live: true,
  },
  {
    icon: LockKeyhole,
    title: "Private by design",
    body: "The AI can propose a visit but never book one, and phone numbers are removed before anything reaches the AI.",
    live: true,
  },
];

function StatusBadge({ live }: { live: boolean }) {
  return live ? (
    <Badge className="border border-emerald-400/30 bg-emerald-400/10 text-emerald-300">
      Live
    </Badge>
  ) : (
    <Badge className="border border-white/15 bg-white/5 text-white/60">Coming</Badge>
  );
}

function NavBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-black/60 backdrop-blur-lg">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2 font-semibold text-white">
          <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 via-blue-500 to-teal-500">
            <Building2 className="size-4" aria-hidden="true" />
          </span>
          Prop AI
        </a>
        <div className="hidden items-center gap-8 text-sm text-white/70 md:flex">
          <a href="#search" className="transition-colors hover:text-white">
            How it works
          </a>
          <a href="#chat" className="transition-colors hover:text-white">
            Ask AI
          </a>
          <a href="#listings" className="transition-colors hover:text-white">
            Listings
          </a>
          <a href="#features" className="transition-colors hover:text-white">
            Features
          </a>
        </div>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1.5")}
        >
          <CodeXml aria-hidden="true" />
          GitHub
        </a>
      </nav>
    </header>
  );
}

function Hero() {
  return (
    <section
      id="top"
      className="relative mx-auto grid max-w-6xl items-center gap-4 px-4 pt-12 sm:px-6 lg:grid-cols-2 lg:pt-4"
    >
      <div className="relative z-10 max-w-xl">
        <Badge className="mb-6 gap-1.5 border border-white/15 bg-white/5 px-3 py-1 text-white/80">
          <Sparkles className="size-3.5 text-teal-300" aria-hidden="true" />
          Portfolio project · in development
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
          Find your next home by{" "}
          <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-teal-300 bg-clip-text text-transparent">
            just asking.
          </span>
        </h1>
        <p className="mt-6 text-lg leading-relaxed text-white/65">
          Prop AI is a voice-first real estate assistant. Describe what you want in
          plain words: it searches real listings and helps you book a site visit.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a
            href="#search"
            className={cn(buttonVariants({ size: "lg" }), "h-11 gap-2 px-5 text-base")}
          >
            See how it works
            <ArrowRight aria-hidden="true" />
          </a>
          <a
            href="#chat"
            className={cn(
              buttonVariants({ variant: "outline", size: "lg" }),
              "h-11 px-5 text-base"
            )}
          >
            Ask the AI
          </a>
        </div>
        <dl className="mt-10 grid max-w-md grid-cols-3 gap-6 border-t border-white/10 pt-6">
          {[
            ["5", "live API endpoints"],
            ["192", "passing tests"],
            ["17", "listings"],
          ].map(([value, label]) => (
            <div key={label}>
              <dt className="sr-only">{label}</dt>
              <dd className="text-2xl font-semibold text-white">{value}</dd>
              <dd className="text-xs text-white/50">{label}</dd>
            </div>
          ))}
        </dl>
      </div>

      <nav aria-label="Explore Prop AI" className="relative">
        <RadialOrbitalTimeline
          timelineData={sections}
          className="h-[480px] sm:h-[560px] lg:h-[640px]"
        />
      </nav>
    </section>
  );
}

function SearchShowcase() {
  return (
    <section id="search" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
      <div className="mb-12 max-w-2xl">
        <p className="mb-3 text-sm font-medium tracking-wider text-teal-300 uppercase">
          How it works
        </p>
        <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          From a sentence to exact matches
        </h2>
        <p className="mt-4 text-white/60">
          The AI assistant turns what you say into structured filters, then answers
          from the search results. This is the search's real output for that sentence.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        <figure className="relative overflow-hidden rounded-2xl border border-white/10 lg:col-span-2">
          <img
            src={PHOTO_INTERIOR}
            alt="Bright, furnished apartment living room with large windows"
            width={1200}
            height={800}
            loading="lazy"
            className="h-full min-h-72 w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />
          <figcaption className="absolute inset-x-0 bottom-0 p-6">
            <div className="rounded-2xl rounded-bl-sm border border-white/15 bg-white/10 p-4 text-white backdrop-blur-md">
              <p className="mb-1 text-xs text-white/50">Buyer</p>
              <p className="text-lg">"2BHK in Powai under 1.5 crore, must have parking."</p>
            </div>
            <p className="mt-3 text-[11px] text-white/40">Illustrative photo · Unsplash</p>
          </figcaption>
        </figure>

        <div className="space-y-4 lg:col-span-3">
          <div className="overflow-x-auto rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 font-mono text-xs text-white/70">
            <span className="text-teal-300">GET</span> /properties/search?listing_type=sale
            &amp;locality=Powai&amp;bedrooms=2&amp;max_price=15000000&amp;amenities=parking
          </div>

          {SAMPLE_RESULTS.map((listing) => (
            <Card
              key={listing.code}
              className="border border-white/10 bg-white/[0.03] transition-colors hover:border-white/25"
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg text-white">{listing.title}</CardTitle>
                  </div>
                  <p className="text-xl font-semibold whitespace-nowrap text-white">
                    {formatPrice(listing.priceInr, "sale")}
                  </p>
                </div>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-white/60">
                <span className="flex items-center gap-1.5">
                  <MapPin className="size-4" aria-hidden="true" />
                  {listing.locality}, Mumbai
                </span>
                <span className="flex items-center gap-1.5">
                  <BedDouble className="size-4" aria-hidden="true" />
                  {listing.bedrooms} BHK
                </span>
                <span className="flex items-center gap-1.5">
                  <Ruler className="size-4" aria-hidden="true" />
                  {listing.areaSqft} sq ft
                </span>
                <span className="flex items-center gap-1.5 text-emerald-300">
                  <Car className="size-4" aria-hidden="true" />
                  Parking
                </span>
              </CardContent>
            </Card>
          ))}

          <p className="flex items-center gap-2 text-xs text-white/40">
            <Database className="size-3.5" aria-hidden="true" />
            Cheapest first; sold and under-offer listings are excluded.
          </p>
        </div>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-4 pb-24 sm:px-6">
      <div className="mb-12 max-w-2xl">
        <p className="mb-3 text-sm font-medium tracking-wider text-purple-300 uppercase">
          Features
        </p>
        <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Built to be trusted with real decisions
        </h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {FEATURES.map(({ icon: Icon, title, body, live }) => (
          <Card
            key={title}
            className="border border-white/10 bg-white/[0.03] transition-colors hover:border-white/25"
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="flex size-10 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                  <Icon className="size-5 text-white" aria-hidden="true" />
                </span>
                <StatusBadge live={live} />
              </div>
              <CardTitle className="mt-4 text-lg text-white">{title}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-relaxed text-white/60">{body}</CardContent>
          </Card>
        ))}
      </div>

      <div className="relative mt-16 overflow-hidden rounded-2xl border border-white/10">
        <img
          src={PHOTO_BUILDING}
          alt="Modern apartment building with balconies at dusk"
          width={900}
          height={600}
          loading="lazy"
          className="absolute inset-0 h-full w-full -scale-x-100 object-cover object-[center_70%] opacity-70"
        />
        {/* Dark on the left keeps the text readable; the photo shows on the right. */}
        <div className="absolute inset-0 bg-gradient-to-r from-black via-black/75 to-transparent" />
        <div className="relative max-w-xl p-8 sm:p-12">
          <h3 className="text-2xl font-semibold text-white">Follow the build</h3>
          <p className="mt-3 text-white/65">
            Every feature ships with tests. The code, progress log and design
            decisions are public on GitHub.
          </p>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className={cn(buttonVariants({ size: "lg" }), "mt-6 h-11 gap-2 px-5 text-base")}
          >
            <CodeXml aria-hidden="true" />
            View the repository
          </a>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/10">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-xs text-white/40 sm:flex-row sm:justify-between sm:px-6">
        <p>Prop AI · FastAPI, PostgreSQL, React. All listings are fictional, for illustration only.</p>
        <p>Photos: Unsplash (illustrative).</p>
      </div>
    </footer>
  );
}

export default function App() {
  // One details dialog for the whole page, opened from chat or listing cards.
  const dialog = useListingDialog();

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-black text-white">
      {/* Soft background glows, purely decorative. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 left-1/4 size-[36rem] rounded-full bg-purple-600/20 blur-3xl" />
        <div className="absolute top-40 right-0 size-[30rem] rounded-full bg-teal-500/10 blur-3xl" />
      </div>
      <div className="relative">
        <NavBar />
        <main>
          <Hero />
          <SearchShowcase />
          <ChatSection onOpenListing={dialog.open} />
          <ListingsSection onOpenListing={dialog.open} />
          <Features />
        </main>
        <Footer />
      </div>
      <PropertyDetailsDialog
        code={dialog.code}
        onClose={dialog.close}
        returnFocusRef={dialog.returnFocusRef}
      />
    </div>
  );
}
