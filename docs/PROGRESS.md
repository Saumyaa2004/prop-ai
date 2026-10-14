# Prop AI — Progress

Last updated: 2026-10-14

## Phase 1 — Backend foundation
- [x] FastAPI app with `/health` and `/health/db` (tested)
- [x] Settings (pydantic-settings) and DB session (`SessionLocal`, `get_db`)
- [x] `Property` model + first Alembic migration (DB at head `029858787222`)
- [x] Idempotent seed: 17 fictional `PAI-DEMO-*` listings
- [x] `GET /properties/search` — service + router + 22 passing pytest tests
- [x] `GET /properties/{listing_code}` — any status, 404 if unknown (31 tests total passing)
- [ ] Push to GitHub (next — needs owner's GitHub account)

## Phases 2–7
Not started: frontend, text AI agent, CRM actions, voice, reliability, deploy.

## Known issues / limitations
- Tests read the dev database and expect the seed data; a separate test DB comes in Phase 6.
- Starlette warns that `TestClient` will move from `httpx` to `httpx2`; harmless today.
- City/locality matching uses `lower(...)`, which bypasses `ix_properties_search`; fine at demo scale.
- Fixed 2026-10-14: PAI-DEMO-002 was seeded at ₹1,37,99,999 due to float math; seed now uses integer lakh values and the row was corrected.

## Run tests
From `backend\`: `.\.venv\Scripts\python.exe -m pytest -v`
