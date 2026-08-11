
# Spec: Profile Page Backend Routes

## Overview
This feature replaces the hardcoded `PROFILE_USER`, `PROFILE_STATS`, `PROFILE_TRANSACTIONS`, and `PROFILE_CATEGORY_BREAKDOWN` dictionaries in `app.py` with real queries against the `users` and `expenses` tables. The profile page (built in Step 4) already has its full layout; this step wires that layout to the logged-in user's actual data — real name/email/member-since, real totals, a real recent-transactions list, and a real per-category breakdown — so `/profile` reflects the database instead of static fixtures.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be a protected route)
- Step 4: Profile page design (template and layout already built against hardcoded data)

## Routes
- `GET /profile` — render the profile page with the logged-in user's real data — logged-in only (redirect to `/login` if not authenticated)

No new routes are added; the existing `/profile` view function is rewritten to query the database instead of returning hardcoded context.

## Database changes
No database changes. The existing `users` and `expenses` tables (see `database/db.py`) are sufficient:
- `users(id, name, email, password_hash, created_at)` — supplies name, email, member-since (`created_at`)
- `expenses(id, user_id, amount, category, date, description, created_at)` — supplies stats, transaction history, and category breakdown, scoped by `user_id`

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — no structural changes expected; verify the fields it reads (`user.name`, `user.email`, `user.member_since`, `user.initials`, `stats.*`, each transaction's `date`/`description`/`category`/`amount`, each category's `category`/`total`/`percent`) line up with the shapes produced by the new query-backed context. Adjust only if a field name needs to change to match real data (e.g. formatting `created_at` into `member_since`).

## Files to change
- `app.py`:
  - Remove `PROFILE_USER`, `PROFILE_STATS`, `PROFILE_TRANSACTIONS`, `PROFILE_CATEGORY_BREAKDOWN` module-level constants
  - Rewrite `inject_current_user()` to look up the real user by `session["user_id"]` via `get_db()` instead of returning the hardcoded `PROFILE_USER`
  - Rewrite the `profile()` view to:
    - Fetch the current user row from `users` by `session["user_id"]`
    - Compute summary stats (total spent, transaction count, top category) from `expenses` for that user
    - Fetch the user's recent transactions from `expenses`, most recent first
    - Compute the per-category breakdown (total and percent of overall spend) from `expenses`
    - Build initials and a formatted "member since" string from the user's `name` and `created_at`
    - Pass all of the above to `profile.html` in the same shapes the template already expects

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only — never string-format SQL, always use `?` placeholders
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Every query touching `expenses` or `users` must be scoped to `session["user_id"]` — never return another user's data
- Handle the zero-expenses case (new user with no transactions yet) without raising an error — stats should show zero/empty rather than crashing
- Category percentages must be computed from actual totals, not hardcoded, and should round sensibly (e.g. no negative or >100% values)
- Close/release DB connections consistently with the existing pattern in `app.py`/`database/db.py`

## Definition of done
- [ ] Visiting `/profile` without being logged in still redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The user info card shows the actual logged-in user's name and email (not "Demo User")
- [ ] The "member since" date reflects the user's real `created_at` value
- [ ] Summary stats (total spent, transaction count, top category) match what's actually in the `expenses` table for that user
- [ ] The transaction history table lists the user's real expenses, most recent first
- [ ] The category breakdown percentages sum to ~100% and match the user's real category totals
- [ ] Logging in as a different user shows that user's own data, not another user's
- [ ] A user with zero expenses sees the profile page render without error (empty/zero state, no crash)
- [ ] No hex colour values appear in `profile.html` — only CSS variables
