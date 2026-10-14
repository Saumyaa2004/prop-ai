# Book a Site Visit — Design (CRM sub-project A)

Date: 2026-10-14 · Status: approved by owner ("do what feels right") · Roadmap: Phase 4

## Goal

A buyer books a site visit for a listing, from the AI chat (typed or spoken) or from the
listing details dialog. Two buyers can never hold the same slot. The AI can propose a
visit but can never save one: a person confirms with a click, and their name and phone
go only to our backend, never to the LLM.

## Decisions (owner)

- First CRM sub-project = A (book a visit). B (agent dashboard, needs login) and
  C (lead qualification) get their own specs later.
- Fixed hourly slots, 10:00–18:00 IST: start hours 10–17 (8 per day), bookable today
  through today + 13 days (14 days), never in the past.
- "AI proposes, human confirms": the agent's tools are read-only; a confirmation card
  collects name + phone and calls `POST /visits`.

## Assumptions (made by Claude, owner delegated)

- Only `status='available'` listings are bookable (sale or rent).
- A lead is identified by phone. Indian mobile only: 10 digits starting 6–9, optional
  `+91`/`91`/`0` prefix, spaces or dashes allowed; stored normalised as `+91XXXXXXXXXX`.
  Booking again with the same phone reuses the lead and updates its name.
- Name: 2–100 characters after trimming.
- Out of scope: buyer cancellation, notifications, agent assignment, login, audit log,
  rate limiting. The card says "Demo project: use a made-up name and number."
- IST has no daylight saving, so a fixed `+05:30` offset is exact; no `tzdata` package.

## Data (Alembic migration, reviewed before `upgrade head`)

`leads`: `id`, `name` varchar(100), `phone` varchar(13) UNIQUE, timestamps.

`site_visits`: `id`, `property_id` FK→properties, `lead_id` FK→leads, `starts_at`
timestamptz, `status` ('booked' | 'cancelled' | 'completed', default 'booked'), timestamps.

- Partial unique index `uq_site_visits_booked_slot` on `(property_id, starts_at)
  WHERE status = 'booked'` — the conflict guard. Cancelled rows free the slot.
- CHECK `status` in the list; CHECK `starts_at` is on the hour with IST hour 10–17.

Why the index and not "check then insert": two requests can both see a slot free and
both insert (race condition). The database refuses the second insert; we map that
error to 409.

## Backend

`app/services/visits.py` — single implementation for API and agent:

- `normalise_phone(raw) -> str | None`
- `parse_slot(value: str | datetime) -> datetime` — naive values are IST.
- `available_slots(db, listing_code, day=None, now=None) -> list[datetime]` —
  free, future, in-window slots (one day, or all 14 days).
- `check_slot(db, listing_code, starts_at, now=None) -> Property` — raises
  `ListingNotFound`, `ListingNotBookable`, `InvalidSlot`, `SlotTaken`.
- `book_visit(db, listing_code, starts_at, name, phone, now=None) -> BookedVisit` —
  `check_slot`, upsert lead (`INSERT … ON CONFLICT (phone) DO UPDATE`), insert visit,
  commit; unique-index violation → `SlotTaken`. Then re-reads the row (post-write
  verification) and returns it.

API (`app/routers/visits.py`):

- `GET /properties/{code}/slots?date=YYYY-MM-DD` → `{listing_code, slots: [iso…]}`;
  404 unknown, 409 not bookable, 422 date outside window.
- `POST /visits` `{listing_code, starts_at, name, phone}` → 201
  `{id, listing_code, title, starts_at, status}` (phone never echoed); 404, 409
  (taken / not bookable), 422 (phone, name, slot).

Agent (`app/services/agent.py`):

- Tools `check_visit_slots(listing_code, date?)` and `propose_visit(listing_code,
  starts_at)`. Both read-only. Without a date, `check_visit_slots` returns the next 8
  free slots. Slot labels are pre-formatted ("Sun 18 Oct, 11:00") so the model quotes,
  not computes.
- A successful `propose_visit` sets `visit_proposal` on the result; `ChatResponse`
  gains `visit_proposal: {listing_code, title, starts_at, label} | null`, taken from
  tool results only (like `listings`).
- System prompt gets today's IST date per request; rule 6 becomes "propose, the user
  confirms on a card; never ask for name or phone".
- Before any LLM call, Indian mobile numbers in user messages become
  `[phone removed]`.

## Frontend

- `lib/api.ts`: `VisitProposal`, `ChatResponse.visit_proposal`, `getSlots`, `bookVisit`.
- `lib/visits.ts` (pure, tested): `isValidIndianMobile`, `formatSlot` (IST via Intl),
  `groupSlotsByDay`.
- `components/BookVisitCard.tsx`: day chips + hour buttons (from `getSlots`), proposal
  preselected; name + phone fields; Confirm. States: loading, picking, submitting,
  booked (summary), error. 409 → "That slot was just taken" + reload slots.
- Chat: card under the assistant message that carries a proposal.
- Details dialog: "Book a visit" button on available listings opens the same card.
- Site claims: features gain "Book a site visit" (Live); hero endpoint and test counts
  re-measured.

## Testing

- Backend, with a rollback fixture (each test in a transaction, nothing persists):
  phone normalisation; slot generation (hours, window, past, booked excluded);
  `book_visit` happy path, lead reuse, taken, not bookable, unknown, invalid slot;
  API status codes and that the phone is not echoed; a two-thread race where exactly
  one booking wins (cleans up its committed rows); agent: proposal from tool results
  only, no write tool exists, phone redaction, date in prompt.
- Frontend (Vitest): `lib/visits.ts`, `getSlots`/`bookVisit` request shape and errors.
- Build, lint, both suites green before every commit; headless check of the card.
