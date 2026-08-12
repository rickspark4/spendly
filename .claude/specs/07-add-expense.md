# Spec: Add Expense

## Overview
This feature replaces the `/expenses/add` placeholder with a real, logged-in
expense creation flow. It gives users a form to log a new expense (amount,
category, date, description), validates and persists it to the `expenses`
table, and returns them to their profile with the new entry reflected in
stats, transactions, and category breakdown. This is the first of three
expense CRUD steps (add → edit → delete) and unblocks the profile page from
being a read-only view.

## Depends on
- `01-database-setup` — `expenses` table must exist
- `02-registration` / `03-login-logout` — user must be authenticated
- `05-profile-backend-routes` — profile helpers (`get_profile_stats`,
  `get_profile_transactions`, `get_profile_category_breakdown`) that the new
  expense should feed into once saved

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in
- `POST /expenses/add` — validate and insert a new expense row for the
  current user, then redirect to `/profile` — logged-in

If not logged in, both should redirect to `/login`, consistent with
`/profile` and `/analytics`.

## Database changes
No database changes. The `expenses` table (`database/db.py`) already has all
required columns: `user_id`, `amount`, `category`, `date`, `description`,
`created_at`. The existing `CATEGORIES` list in `database/db.py` should be
reused as the source of truth for the category `<select>` options instead of
hardcoding them in the template.

## Templates
- **Create:** `templates/expenses/add.html` — form with amount, category
  (`<select>` populated from `CATEGORIES`), date (defaulting to today), and
  optional description fields; extends `base.html`; shows validation errors
  inline the same way `register.html`/`login.html` do.
- **Modify:** none required. (`profile.html` already renders whatever the
  DB returns, so a newly added expense shows up automatically on next load.)

## Files to change
- `app.py` — implement `add_expense()` under `# Routes`, moving it out of
  the `# Placeholder routes` section; add form validation helper(s) following
  the pattern of existing validation in `register()`.
- `database/db.py` — export `CATEGORIES` is already public; no changes
  needed, just import it in `app.py`.

## Files to create
- `templates/expenses/add.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this feature, but keep existing
  auth checks intact)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate on the server: amount must be a positive number, category must
  be one of `CATEGORIES`, date must be a valid `YYYY-MM-DD` and not in the
  future; re-render the form with an `error` message and the submitted
  values on failure, matching the `register()`/`login()` pattern.
- Scope the insert to `session["user_id"]` — never trust a client-supplied
  user id.

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount,
      category (populated from `CATEGORIES`), date, and description fields
- [ ] Submitting valid data creates a row in `expenses` for the current
      user and redirects to `/profile`
- [ ] The new expense appears in the profile page's transaction list,
      totals, and category breakdown without a server restart
- [ ] Submitting a negative or non-numeric amount re-renders the form with
      an error and preserves entered values
- [ ] Submitting an invalid category re-renders the form with an error
- [ ] Submitting a malformed or future date re-renders the form with an
      error
- [ ] No hardcoded hex colors introduced in any new CSS/template markup
