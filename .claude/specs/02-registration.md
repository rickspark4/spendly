# Spec: Registration

## Overview
Spendly's `/register` route currently only renders a static form with no backend logic — the form posts to `/register` but nothing handles the `POST`. This step wires that up: validating input, hashing the password, inserting a new row into `users`, and starting a logged-in session so the user lands on their profile/dashboard immediately after signing up. This is the first authentication step in the roadmap and unblocks login (Step 3) and any route that needs to know "who is the current user."

## Depends on
- Step 1 — Database Setup (`users` table, `get_db()`, `init_db()` must exist and work — they do).

## Routes
- `GET /register` — renders the registration form (already implemented, unchanged) — public
- `POST /register` — validates form input, creates the user, logs them in, redirects to `/profile` — public

No other routes change. `/login`, `/logout`, `/profile` remain placeholders/out of scope for this step (login is Step 3).

## Database changes
No database changes. The `users` table (from `database/db.py`) already has every column registration needs: `name`, `email`, `password_hash`, `created_at`. Reuse `get_db()` as-is — no new tables, columns, or constraints.

## Templates
- **Create:** none
- **Modify:** `templates/register.html`
  - Change the form's `action="/register"` to `action="{{ url_for('register') }}"` (existing hardcoded path violates the `url_for`-only convention in CLAUDE.md).
  - Repopulate `name`/`email` field values on validation failure (e.g. `value="{{ name or '' }}"`) so the user doesn't retype everything.
  - `{% if error %}` block already exists and is reused for validation/duplicate-email errors — no new markup needed there.

## Files to change
- `app.py` — implement `POST` handling on the `/register` route (accept `["GET", "POST"]`), add `session` import from Flask, set `app.secret_key`.
- `templates/register.html` — form action fix + sticky field values (see above).

## Files to create
- None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only — reuse `get_db()` from `database/db.py`, never string-format SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash` before insert; never store or log plaintext passwords.
- Validate server-side even though HTML5 `required`/`type=email` exist client-side: name and email non-empty, password minimum 8 characters (matches the placeholder text "Min. 8 characters" already in the template).
- Check for an existing user with the same email (case-insensitive is fine to skip — match spec's plain `UNIQUE` column) before inserting; on collision, re-render `register.html` with `error="An account with this email already exists."` and HTTP 200 (not a redirect).
- On success: insert user, store `session["user_id"] = <new id>`, redirect (302) to `/profile`.
- Use CSS variables — never hardcode hex values (no new CSS should be needed; reuse existing `auth-*`/`form-*` classes).
- All templates extend `base.html` (already true for `register.html`, unchanged).

## Definition of done
- [ ] Visiting `/register` still shows the existing form, unchanged visually.
- [ ] Submitting valid name/email/password creates a row in `users` with a hashed (not plaintext) password.
- [ ] After successful registration, the browser is redirected to `/profile` and a session cookie is set.
- [ ] Submitting an email that already exists re-renders the form with an error message and does not create a duplicate row.
- [ ] Submitting with a missing name/email or a password under 8 characters re-renders the form with an error message and does not insert a row.
- [ ] Re-running `python app.py` and registering a new user does not affect the existing seeded demo user or previously registered users.
