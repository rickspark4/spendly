# Spec: Login and Logout

## Overview
Step 2 (Registration) lets a new user create an account and starts a session for them, but returning users have no way back in — `templates/login.html` renders a static form that posts to `/login` with no backend handling, and `/logout` is a stub string. This step wires both up: authenticating existing users against the `users` table and clearing the session on logout. Together with registration, this completes Spendly's authentication foundation and unblocks Step 4 (Profile), which needs a reliable "who is logged in" signal.

## Depends on
- Step 1 — Database Setup (`users` table, `get_db()`).
- Step 2 — Registration (`users` rows with hashed passwords exist to log into; establishes the `session["user_id"]` convention this step reuses).

## Routes
- `GET /login` — renders the login form (already implemented, unchanged) — public
- `POST /login` — validates credentials, starts a session, redirects to `/profile` — public
- `GET /logout` — clears the session, redirects to `/login` — logged-in (no-op/safe if already logged out)

## Database changes
No database changes. Reuses `users.email` and `users.password_hash` via the existing `get_db()` — no new tables, columns, or constraints.

## Templates
- **Create:** none
- **Modify:** `templates/login.html`
  - Change the form's `action="/login"` to `action="{{ url_for('login') }}"` (existing hardcoded path violates the `url_for`-only convention in CLAUDE.md).
  - Repopulate the `email` field value on validation failure (e.g. `value="{{ email or '' }}"`), matching the sticky-field pattern already used in `register.html`.
  - `{% if error %}` block already exists and is reused for "invalid credentials" — no new markup needed.

## Files to change
- `app.py` — implement `POST` handling on `/login` (accept `["GET", "POST"]`) and replace the `/logout` stub with real session-clearing logic. Move `/logout` out of the "Placeholder routes" section into "Routes" once implemented.
- `templates/login.html` — form action fix + sticky email value (see above).

## Files to create
- None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only — reuse `get_db()` from `database/db.py`, never string-format SQL.
- Passwords verified with `werkzeug.security.check_password_hash` against the stored `password_hash`; never compare plaintext passwords directly.
- Look up the user by email (`SELECT * FROM users WHERE email = ?`); if no row matches, or the password doesn't check out, re-render `login.html` with a single generic `error="Invalid email or password."` (do not reveal whether the email exists — same message for both cases).
- On success: `session["user_id"] = user["id"]`, redirect (302) to `/profile`.
- `/logout` clears the session (`session.pop("user_id", None)` or `session.clear()`) and redirects (302) to `/login`, regardless of whether a session existed.
- Use CSS variables — never hardcode hex values (no new CSS should be needed; reuse existing `auth-*`/`form-*` classes).
- All templates extend `base.html` (already true for `login.html`, unchanged).

## Definition of done
- [ ] Visiting `/login` still shows the existing form, unchanged visually.
- [ ] Submitting the seeded demo user's credentials (`demo@spendly.com` / `demo123`) redirects to `/profile` and sets a session cookie.
- [ ] Submitting a registered user's correct email/password (e.g. one created via Step 2's `/register`) logs them in the same way.
- [ ] Submitting a wrong password, or an email that doesn't exist, re-renders the form with the same generic "Invalid email or password." error, and no session is set.
- [ ] Visiting `/logout` after logging in clears the session and redirects to `/login`.
- [ ] Visiting `/logout` while not logged in does not error — it redirects to `/login` cleanly.
- [ ] Re-running `python app.py` and logging in repeatedly does not modify any rows in `users`.
