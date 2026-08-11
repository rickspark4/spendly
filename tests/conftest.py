"""
Shared pytest fixtures for the Spendly test suite.

The app's DB helpers (database/db.py) use a hardcoded module-level DB_PATH
rather than reading from Flask config, so to isolate tests from the real
`expense_tracker.db` we redirect DB_PATH to a temp file *before* `app.py`
is imported (app.py calls init_db()/seed_db() at import time).
"""
import os
import tempfile

import pytest

# --- Redirect the SQLite file to an isolated temp path before app import ---
_fd, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.remove(_TEST_DB_PATH)  # let sqlite create it fresh

import database.db as db_module  # noqa: E402
db_module.DB_PATH = _TEST_DB_PATH

from app import app as flask_app  # noqa: E402
from database.db import get_db, init_db, seed_db  # noqa: E402


@pytest.fixture
def app():
    """The Flask app, configured for testing with a clean, freshly-seeded DB."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
    })

    init_db()

    # Reset to a clean slate, then reseed the standard demo user/expenses.
    db = get_db()
    db.execute("DELETE FROM expenses")
    db.execute("DELETE FROM users")
    db.commit()
    db.close()

    seed_db()

    yield flask_app


@pytest.fixture
def client(app):
    """An unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def demo_user_id(app):
    """The id of the seeded demo user (demo@spendly.com)."""
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
    db.close()
    assert row is not None, "Expected seed_db() to create the demo user"
    return row["id"]


@pytest.fixture
def auth_client(client):
    """A test client logged in as the seeded demo user."""
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )
    assert response.status_code == 302, "Expected login with seeded demo credentials to succeed"
    return client


@pytest.fixture
def clean_expenses(demo_user_id):
    """Removes all expenses for the demo user so a test can insert a known, controlled dataset."""
    db = get_db()
    db.execute("DELETE FROM expenses WHERE user_id = ?", (demo_user_id,))
    db.commit()
    db.close()
    return demo_user_id


def insert_expense(user_id, amount, category, date_str, description):
    """Test helper: insert a single expense row directly via parameterised SQL."""
    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    db.commit()
    db.close()
