# Spec: Date Filter for Profile Page

## Overview
This feature adds a date range filter to the `/profile` page so a user can narrow their summary stats, transaction history, and category breakdown to a specific time window (e.g. "this month" or a custom start/end date) instead of always seeing all-time data. It builds directly on Step 5, which wired `/profile` to real database queries — this step adds an optional date range on top of those same queries, submitted via a simple GET form so the filter is shareable/bookmarkable via the URL.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 3: Login + Logout (session-protected `/profile` route)
- Step 5: Profile page backend routes (`/profile` already queries `users`/`expenses` for stats, transactions, and category breakdown — this step adds date-range scoping to those same queries)

## Routes
- `GET /profile` — modified, not new. Accepts optional `start` and `end` query string parameters (`YYYY-MM-DD`). When present and valid, stats/transactions/category breakdown are scoped to that inclusive date range; otherwise behavior is unchanged (all-time data) — logged-in only (redirect to `/login` if not authenticated)

No new routes.

## Database changes
No database changes. `expenses.date` (`TEXT`, `YYYY-MM-DD`) already supports lexicographic range filtering with `BETWEEN ? AND ?` / `>= ? AND <= ?`.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — add a date filter form (two `<input type="date">` fields for `start`/`end`, a submit button, and a "Clear" link back to `/profile` with no query params) above the "Recent Transactions" block. Form uses `method="GET"` so the range lives in the URL. Preserve submitted `start`/`end` values in the input fields after filtering (`value="{{ request.args.get('start', '') }}"` etc.).

## Files to change
- `app.py`:
  - Read `start` and `end` from `request.args`
  - Validate both are well-formed `YYYY-MM-DD` dates (via `datetime.strptime`); if either is missing or invalid, ignore the filter and fall back to all-time (do not error/500)
  - If `start` > `end`, ignore the filter and fall back to all-time
  - Thread the validated `(start, end)` range through `get_profile_stats`, `get_profile_transactions`, and `get_profile_category_breakdown` so all three add `AND date BETWEEN ? AND ?` (parameterised) when a range is present
  - Pass the raw `start`/`end` strings (or empty strings) to the template so the form can re-populate itself
- `templates/profile.html`: add the filter form described above

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only — never string-format SQL, always use `?` placeholders
- Passwords hashed with werkzeug (unrelated to this step, no changes)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Every query touching `expenses` must stay scoped to `session["user_id"]` — the date filter narrows further, it never replaces the user scope
- Invalid, missing, or reversed (`start` > `end`) date input must degrade gracefully to the unfiltered all-time view, never a 500 error
- Category percentages must still be computed from the filtered totals, not hardcoded, and still sum to ~100% within the filtered set
- Handle the zero-results case (a range with no matching expenses) without raising an error — stats should show zero/empty rather than crashing
- Close/release DB connections consistently with the existing pattern in `app.py`/`database/db.py`

## Definition of done
- [ ] Visiting `/profile` without being logged in still redirects to `/login`
- [ ] Visiting `/profile` with no `start`/`end` params shows all-time data, unchanged from Step 5 behavior
- [ ] Submitting a valid `start`/`end` range filters stats, transaction history, and category breakdown to only expenses within that inclusive range
- [ ] The date inputs remain populated with the submitted `start`/`end` values after filtering
- [ ] The "Clear" link returns to `/profile` with no query params and shows all-time data again
- [ ] Submitting only `start` or only `end` (not both) falls back to all-time data without error
- [ ] Submitting an invalid date string (e.g. malformed or non-existent date) falls back to all-time data without error
- [ ] Submitting `start` later than `end` falls back to all-time data without error
- [ ] A range with zero matching expenses renders the page with empty/zero stats, not a crash
- [ ] Category breakdown percentages still sum to ~100% within the filtered range
- [ ] No hex colour values appear in `profile.html` — only CSS variables
