# Interview prep notes

Short talking points per major feature. Only describe what is implemented and tested.

## Property search (`GET /properties/search`)
- **Why it exists:** buyers ask things like "2BHK in Powai under 1.5 crore with parking";
  the API must return only real, available listings that match, and the AI agent will reuse it.
- **How it works:** query params → Pydantic `PropertySearchFilters` (validation, rejects
  unknown params) → `search_properties(db, filters)` service builds a SQLAlchemy `select()`
  with only the filters provided → PostgreSQL → `PropertyRead` response schema.
- **Design choice:** structured SQL filters, not RAG/vector search — price, bedrooms and
  locality are exact facts, and SQL gives exact, explainable answers.
  *Alternative:* embed listings and do semantic search; useful later for fuzzy text like
  "quiet area near a park", but wrong for hard numeric constraints.
- **Failure mode prevented:** mixing sale prices (totals) with rent prices (monthly).
  `listing_type` is required and always filtered; a test proves a ₹50k budget on a sale
  search returns nothing.
- **Bug I found:** `int(1.38 * 10_000_000)` = 13,799,999 because of floating-point
  truncation. Fixed by using integer math for money and correcting the seeded row.
- **How it was tested:** 22 pytest cases with FastAPI `TestClient` — happy path,
  case-insensitivity, amenities "has all" (`@>`), limit, sale/rent separation, empty
  results, nine invalid inputs returning 422, and the service called without HTTP.
