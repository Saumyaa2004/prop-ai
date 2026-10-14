# Prop AI — Progress

Last updated: 2026-10-14

## Phase 1 — Backend foundation
- [x] FastAPI app with `/health` and `/health/db` (tested)
- [x] Settings (pydantic-settings) and DB session (`SessionLocal`, `get_db`)
- [x] `Property` model + first Alembic migration (DB at head `029858787222`)
- [x] Idempotent seed: 17 fictional `PAI-DEMO-*` listings
- [x] `GET /properties/search` — service + router + 22 passing pytest tests
- [x] `GET /properties/{listing_code}` — any status, 404 if unknown (31 tests total passing)
- [x] Pushed to GitHub: https://github.com/Saumyaa2004/prop-ai

**Phase 1 complete.**

## Phase 2 — Frontend (in progress)
- [x] `frontend/`: Vite 8 + React 19 + TypeScript 6, Tailwind v4, shadcn (base-nova)
- [x] Landing page: hero, roadmap orbit (`radial-orbital-timeline`), search showcase, features
      — static content; `npm run build` + lint pass; checked at 1440px and 390px
- [x] CORS in FastAPI (exact origins from settings, GET only; 5 tests → 36 backend tests)
- [x] API client (`lib/api.ts`), price formatting, `usePropertySearch` hook — 14 Vitest tests
- [x] Live listings section: Buy/Rent, locality, bedrooms, budget (resets on Buy↔Rent);
      loading / error / empty / results checked against the running API
- [x] Listing details dialog (`GET /properties/{code}`): shareable `?listing=` links, honest
      status (Sold/Rented), 404 "not found", focus returns to the opening card — 23 Vitest tests
- [ ] CRM views (after Phase 4 backend exists)

## Phases 3–7
Not started: text AI agent, CRM actions, voice, reliability, deploy.

## Known issues / limitations
- Tests read the dev database and expect the seed data; a separate test DB comes in Phase 6.
- Starlette warns that `TestClient` will move from `httpx` to `httpx2`; harmless today.
- City/locality matching uses `lower(...)`, which bypasses `ix_properties_search`; fine at demo scale.
- Fixed 2026-10-14: PAI-DEMO-002 was seeded at ₹1,37,99,999 due to float math; seed now uses integer lakh values and the row was corrected.

- Frontend unit tests cover the API client and formatting only; no component tests yet.
  The orbit's click/keyboard expansion was not verified in a real browser by Claude.
- Locality options in the listings filter are hard-coded to the seed data (no API for them).
- CORS allows only `http://localhost:5173`; `vite preview` (port 4173) is blocked by design.
- Keep `frontend/src/data/roadmap.ts` and the landing-page stats in sync with this file.

## Run tests
From `backend\`: `.\.venv\Scripts\python.exe -m pytest -v`
From `frontend\`: `npm test`, `npm run build` (type-check + bundle) and `npm run lint`
