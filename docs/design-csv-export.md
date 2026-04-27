# Design: CSV Export Feature

**Work package:** #41
**Status:** Draft
**Depends on:** WP #1 (Investigate permissions for CSV export button)

## Problem

Finance customers need to pull the invoices list into external BI tools.
Today they screen-scrape the invoices page. We need a first-class CSV export
that respects the current page filters and the user's permissions.

## User story

> As an accountant, I want to export the invoices list to CSV so that I can
> import it into my BI tool without screen-scraping.

## Endpoint

```
GET /api/invoices.csv
```

### Why a dedicated path (not `Accept: text/csv`)?

Content negotiation on the existing `/api/invoices` endpoint would work, but
a separate `.csv` path is simpler to link from a button in the UI, easier to
test in a browser, and avoids surprising existing JSON consumers if the
`Accept` header handling has bugs.

## Request

| Parameter    | Type       | Required | Default        | Description                                         |
|--------------|------------|----------|----------------|-----------------------------------------------------|
| `from`       | `date`     | no       | none           | Start of the date range filter (inclusive, ISO 8601) |
| `to`         | `date`     | no       | none           | End of the date range filter (inclusive, ISO 8601)   |
| `status`     | `string`   | no       | none           | Filter by invoice status (e.g. `paid`, `overdue`)   |
| `customer`   | `string`   | no       | none           | Filter by customer name or ID                       |
| `limit`      | `integer`  | no       | 10 000         | Max rows returned (cap to prevent OOM)              |

All filter parameters mirror the filters available on the invoices list page
so the export button can forward the active query string as-is.

### Example

```
GET /api/invoices.csv?from=2025-01-01&to=2025-12-31&status=paid&limit=5000
```

## Response

### Success — `200 OK`

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="invoices-2025-01-01-to-2025-12-31.csv"
```

Body is RFC 4180 CSV with a header row:

```csv
invoice_id,date,customer_name,customer_id,amount,currency,status,due_date,paid_date
INV-1042,2025-03-15,Acme Corp,CUST-007,12500.00,USD,paid,2025-04-15,2025-04-10
INV-1043,2025-03-16,Globex Inc,CUST-012,8750.50,EUR,overdue,2025-04-16,
```

#### Column selection

The first version exports a fixed set of columns (listed above). A follow-up
could accept a `columns` query parameter, but that adds complexity around
validation and documentation — defer until there is demonstrated demand.

### Errors

| Status | Condition                                  | Body (JSON)                                         |
|--------|--------------------------------------------|-----------------------------------------------------|
| `400`  | Invalid date format or `limit` out of range | `{"error": "bad_request", "detail": "..."}`        |
| `401`  | Missing or invalid auth token              | `{"error": "unauthorized"}`                         |
| `403`  | User lacks export / read-invoices permission | `{"error": "forbidden", "detail": "..."}`          |
| `404`  | Project or resource not found              | `{"error": "not_found"}`                            |
| `500`  | Unexpected server error                    | `{"error": "internal_error"}`                       |

Error responses remain JSON even though the happy path is CSV — callers
already handle JSON errors from the existing API.

## Permissions

> Depends on findings from WP #1 (Investigate permissions for CSV export button).

The export endpoint must enforce the same authorization rules as the invoices
list page:

1. **Authentication** — standard session/token auth; reject with `401` if
   absent.
2. **Read invoices** — the user must have the existing read-invoices
   permission. If they can see the list page, they can export it.
3. **Export permission** (TBD from WP #1) — if the permissions investigation
   reveals a separate "export" permission is needed (e.g. for compliance or
   data-loss-prevention reasons), gate the endpoint behind it. Otherwise,
   reuse the read permission.

<!-- TODO(ai-dlc): Update this section once WP #1 findings are available. -->

## Validation

| Rule                                | Action                                      |
|-------------------------------------|---------------------------------------------|
| `from` / `to` not valid ISO 8601   | Return `400` with detail                   |
| `from` > `to`                       | Return `400` — "from must be before to"    |
| `limit` < 1 or > 50 000            | Return `400` — clamp or reject             |
| Unknown query parameters            | Ignore (forward-compatibility)              |
| Resulting row count exceeds `limit` | Truncate at `limit`, add a trailing comment row or `X-Truncated: true` header |

## Architecture

```
┌──────────────┐     GET /api/invoices.csv       ┌──────────────────┐
│  Browser /   │ ──────────────────────────────▶  │  CSV Export      │
│  BI Tool     │                                  │  Route Handler   │
└──────────────┘                                  └──────┬───────────┘
                                                         │
                                              ┌──────────┴──────────┐
                                              │                     │
                                              ▼                     ▼
                                     ┌──────────────┐     ┌──────────────┐
                                     │ Auth / Perms │     │ Query        │
                                     │ Middleware   │     │ Validation   │
                                     └──────────────┘     └──────┬───────┘
                                                                 │
                                                                 ▼
                                                        ┌──────────────┐
                                                        │ Invoice      │
                                                        │ Repository   │
                                                        │ (existing)   │
                                                        └──────┬───────┘
                                                                │
                                                                ▼
                                                        ┌──────────────┐
                                                        │ CSV          │
                                                        │ Serializer   │
                                                        └──────────────┘
```

### Key components

1. **Route handler** (`GET /api/invoices.csv`) — thin controller that
   validates query params, calls the repository, and streams the CSV
   response.

2. **Auth / permissions middleware** — reuses existing auth stack. Adds an
   export-permission check if WP #1 requires it.

3. **Query validation** — a pydantic model (or framework equivalent) that
   parses and validates the filter parameters. Rejects bad input before
   touching the database.

4. **Invoice repository** — the existing data-access layer that the invoices
   list page already uses. The export calls it with the same filter
   interface; no new queries needed.

5. **CSV serializer** — a small function that takes an iterable of invoice
   rows and yields RFC 4180 CSV text. Uses Python's `csv` module (stdlib)
   with streaming to avoid loading the full result set into memory.

### Streaming

For large exports (tens of thousands of rows), the response should be
streamed rather than buffered. Most Python web frameworks support
`StreamingResponse` / generator-based responses. The serializer yields
chunks (e.g. 100 rows at a time) so memory usage stays flat regardless of
export size.

## Acceptance criteria

1. `GET /api/invoices.csv` returns `200` with valid RFC 4180 CSV including a
   header row.
2. The export respects `from`, `to`, `status`, and `customer` filters.
3. Results are limited to `limit` rows (default 10 000, max 50 000).
4. The endpoint enforces the same permissions as the invoices list page.
5. Invalid filter values return `400` with a descriptive error.
6. Unauthenticated requests return `401`; unauthorized users get `403`.
7. The response includes `Content-Disposition` so browsers trigger a
   download.
8. Exports of 10 000+ rows do not cause OOM on a standard web worker
   (streaming).

## Out of scope

- **PDF export** — separate feature, different serialization concerns.
- **Async / background export** — only needed if exports routinely exceed
  50 000 rows. Revisit if usage data warrants it.
- **Column customization** — defer until there is demand.
- **Scheduled / recurring exports** — a future feature; this design covers
  on-demand only.

## Risks

| Risk                                | Mitigation                                        |
|-------------------------------------|---------------------------------------------------|
| Large exports OOM the web worker    | Stream the response; enforce `limit` cap at 50 000 |
| Slow queries block the worker pool  | Add a query timeout (e.g. 30 s); consider read replica |
| CSV injection (formulas in fields)  | Prefix cell values starting with `=`, `+`, `-`, `@` with a single quote |
| Permission model unclear            | Blocked on WP #1; design accommodates either outcome |

## Open questions

1. **WP #1 outcome** — does the export need its own permission, or is
   read-invoices sufficient?
2. **Filename convention** — should the filename include the project or
   entity name, or just the date range?
3. **Encoding** — UTF-8 is the right default, but some BI tools (older
   Excel) expect UTF-8 BOM. Should we add a `?encoding=utf-8-bom` option?
