# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a Flask-based expense tracker built as a step-by-step learning project. `app.py` and `database/db.py` contain scaffolding comments (`# Students will write this file in Step N — ...`, `"... — coming in Step N"`) marking work that is intentionally not yet implemented. When asked to build a feature, check the relevant file for its step marker first — it tells you what's expected and where it fits in the overall build sequence, and you should replace the placeholder rather than working around it.

## Commands

```bash
# Run the dev server (http://localhost:5001, debug mode on)
python app.py

# Run tests
pytest
```

There is no build step, linter, or frontend bundler configured. Dependencies: `flask`, `werkzeug`, `pytest`, `pytest-flask` (see `requirements.txt`).

## Architecture

- **`app.py`** — single Flask app with all routes. Implemented routes (`/`, `/register`, `/login`, `/terms`, `/privacy`) render Jinja templates directly with no view logic yet. Routes under `/expenses/...`, `/logout`, and `/profile` are stubs returning plain strings, pending auth and DB work.
- **`database/db.py`** — intended to hold `get_db()` (SQLite connection, `row_factory` + foreign keys on), `init_db()` (`CREATE TABLE IF NOT EXISTS` statements), and `seed_db()` (sample data). Not yet implemented; the SQLite file (`expense_tracker.db`, gitignored) will live at the project root once created.
- **`templates/`** — Jinja2 templates. `base.html` is the shared layout (nav + footer) that every page extends via `{% block title %}`, `{% block head %}`, `{% block content %}`, `{% block scripts %}`.
- **`static/css/style.css`** — single stylesheet for the whole app (no preprocessor/build step); `static/js/main.js` is currently empty scaffolding.

## Conventions observed in existing code

- Routes in `app.py` are grouped under banner comments (`# Routes`, `# Placeholder routes`) — keep new routes under the appropriate section, moving a route out of "Placeholder" once implemented.
- Templates use `{{ url_for('endpoint') }}` for all internal links, never hardcoded paths.
- Design language: serif display font (DM Serif Display) for headings/brand, DM Sans for body, diamond glyph `◈` as the brand icon — keep new UI consistent with `landing.html` / `style.css` rather than introducing new fonts or components.
