"""
Tests for Spec 07: Add Expense.

Spec: .claude/specs/07-add-expense.md

Covers:
- GET/POST /expenses/add auth guard (redirect to /login when not authenticated)
- GET /expenses/add renders a form with amount, category (from CATEGORIES),
  date, and description fields
- Submitting valid data inserts a row scoped to the logged-in user and
  redirects to /profile
- The new expense is reflected on the profile page's transactions/stats
  without a server restart
- Validation errors (negative/non-numeric amount, invalid category,
  malformed/future date) re-render the form with an error, preserve
  submitted values, and do not insert a row
- The insert is always scoped to session["user_id"], never a client-supplied id
"""
from datetime import date, timedelta

import pytest

from database.db import CATEGORIES, get_db


def html(response):
    return response.data.decode("utf-8")


def count_expenses(user_id):
    db = get_db()
    n = db.execute(
        "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()["n"]
    db.close()
    return n


def latest_expense(user_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    db.close()
    return row


VALID_PAYLOAD = {
    "amount": "42.50",
    "category": "Food",
    "date": "2024-01-15",
    "description": "Test lunch",
}


class TestAuthGuard:
    def test_get_add_expense_redirects_to_login_when_not_authenticated(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302, "Unauthenticated GET should redirect, not render the form"
        assert "/login" in response.headers.get("Location", ""), (
            "Unauthenticated GET /expenses/add should redirect to /login"
        )

    def test_post_add_expense_redirects_to_login_when_not_authenticated(self, client):
        response = client.post("/expenses/add", data=VALID_PAYLOAD)
        assert response.status_code == 302, "Unauthenticated POST should redirect, not process the form"
        assert "/login" in response.headers.get("Location", ""), (
            "Unauthenticated POST /expenses/add should redirect to /login"
        )

    def test_post_add_expense_while_logged_out_does_not_insert_a_row(self, client, demo_user_id):
        before = count_expenses(demo_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        after = count_expenses(demo_user_id)
        assert after == before, "An unauthenticated POST must never create an expense row"


class TestFormRendering:
    def test_get_add_expense_returns_200_when_authenticated(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200

    def test_form_contains_amount_field(self, auth_client):
        page = html(auth_client.get("/expenses/add"))
        assert 'name="amount"' in page, "Form should include an amount field"

    def test_form_contains_category_field(self, auth_client):
        page = html(auth_client.get("/expenses/add"))
        assert 'name="category"' in page, "Form should include a category field"

    def test_form_contains_date_field(self, auth_client):
        page = html(auth_client.get("/expenses/add"))
        assert 'name="date"' in page, "Form should include a date field"

    def test_form_contains_description_field(self, auth_client):
        page = html(auth_client.get("/expenses/add"))
        assert 'name="description"' in page, "Form should include a description field"

    def test_category_options_populated_from_categories_list(self, auth_client):
        page = html(auth_client.get("/expenses/add"))
        for category in CATEGORIES:
            assert category in page, (
                f"Category select should be populated from CATEGORIES and include {category!r}"
            )

    def test_date_field_defaults_to_today(self, auth_client):
        page = html(auth_client.get("/expenses/add"))
        today = date.today().isoformat()
        assert today in page, "Date field should default to today's date"


class TestHappyPath:
    def test_valid_submission_redirects_to_profile(self, auth_client, clean_expenses):
        response = auth_client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("Location", "").endswith("/profile"), (
            "A valid submission should redirect to /profile"
        )

    def test_valid_submission_creates_exactly_one_row(self, auth_client, clean_expenses):
        user_id = clean_expenses
        before = count_expenses(user_id)
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        after = count_expenses(user_id)
        assert after == before + 1, "A valid submission should insert exactly one expense row"

    def test_valid_submission_persists_submitted_fields(self, auth_client, clean_expenses):
        user_id = clean_expenses
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        row = latest_expense(user_id)
        assert row is not None
        assert row["amount"] == pytest.approx(42.50)
        assert row["category"] == "Food"
        assert row["date"] == "2024-01-15"
        assert row["description"] == "Test lunch"

    def test_valid_submission_appears_on_profile_page(self, auth_client, clean_expenses):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        page = html(auth_client.get("/profile"))
        assert "Test lunch" in page, (
            "Newly added expense should appear in the profile page's transaction list"
        )

    def test_valid_submission_updates_profile_total(self, auth_client, clean_expenses):
        auth_client.post("/expenses/add", data=VALID_PAYLOAD)
        page = html(auth_client.get("/profile"))
        assert "42.50" in page, "Profile total/transaction amount should reflect the new expense"

    def test_valid_submission_without_description_is_allowed(self, auth_client, clean_expenses):
        user_id = clean_expenses
        payload = {**VALID_PAYLOAD, "description": ""}
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302, "Description is optional; omitting it should still succeed"
        assert count_expenses(user_id) == 1


class TestUserScoping:
    def test_inserted_expense_uses_session_user_id_not_client_supplied_id(
        self, auth_client, clean_expenses, demo_user_id
    ):
        """Even if a malicious client supplies a user_id field, the row must be
        scoped to session["user_id"], never a client-supplied value."""
        other_user_id = demo_user_id + 999
        payload = {**VALID_PAYLOAD, "user_id": other_user_id}
        auth_client.post("/expenses/add", data=payload)

        row = latest_expense(demo_user_id)
        assert row is not None, "Expense should be inserted for the logged-in session user"
        assert row["user_id"] == demo_user_id, (
            "Expense must be scoped to session user_id, ignoring any client-supplied user_id"
        )

        db = get_db()
        foreign_count = db.execute(
            "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (other_user_id,)
        ).fetchone()["n"]
        db.close()
        assert foreign_count == 0, "No row should ever be created for a client-supplied user_id"


class TestAmountValidation:
    @pytest.mark.parametrize("bad_amount", ["-10", "0", "-0.01", "abc", "", "12abc", "NaN"])
    def test_invalid_amount_rerenders_form_with_error(self, auth_client, clean_expenses, bad_amount):
        user_id = clean_expenses
        payload = {**VALID_PAYLOAD, "amount": bad_amount}
        response = auth_client.post("/expenses/add", data=payload)

        assert response.status_code == 200, "Validation failure should re-render the form, not redirect"
        page = html(response)
        assert "error" in page.lower(), f"Expected an inline error for invalid amount {bad_amount!r}"
        assert count_expenses(user_id) == 0, "Invalid amount must not insert a row"

    def test_invalid_amount_preserves_other_submitted_values(self, auth_client, clean_expenses):
        payload = {**VALID_PAYLOAD, "amount": "-5", "description": "Keep me around"}
        response = auth_client.post("/expenses/add", data=payload)
        page = html(response)
        assert "Keep me around" in page, "Submitted description should be preserved on validation failure"
        assert "2024-01-15" in page, "Submitted date should be preserved on validation failure"


class TestCategoryValidation:
    def test_invalid_category_rerenders_form_with_error(self, auth_client, clean_expenses):
        user_id = clean_expenses
        payload = {**VALID_PAYLOAD, "category": "NotARealCategory"}
        response = auth_client.post("/expenses/add", data=payload)

        assert response.status_code == 200, "Invalid category should re-render the form, not redirect"
        page = html(response)
        assert "error" in page.lower(), "Expected an inline error for an invalid category"
        assert count_expenses(user_id) == 0, "Invalid category must not insert a row"

    def test_empty_category_rerenders_form_with_error(self, auth_client, clean_expenses):
        user_id = clean_expenses
        payload = {**VALID_PAYLOAD, "category": ""}
        response = auth_client.post("/expenses/add", data=payload)
        assert response.status_code == 200
        assert count_expenses(user_id) == 0, "Empty category must not insert a row"


class TestDateValidation:
    def test_future_date_rerenders_form_with_error(self, auth_client, clean_expenses):
        user_id = clean_expenses
        future_date = (date.today() + timedelta(days=1)).isoformat()
        payload = {**VALID_PAYLOAD, "date": future_date}
        response = auth_client.post("/expenses/add", data=payload)

        assert response.status_code == 200, "Future date should re-render the form, not redirect"
        page = html(response)
        assert "error" in page.lower(), "Expected an inline error for a future date"
        assert count_expenses(user_id) == 0, "Future date must not insert a row"

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "2024-13-40",
        "2024/01/15",
        "15-01-2024",
        "",
    ])
    def test_malformed_date_rerenders_form_with_error(self, auth_client, clean_expenses, bad_date):
        user_id = clean_expenses
        payload = {**VALID_PAYLOAD, "date": bad_date}
        response = auth_client.post("/expenses/add", data=payload)

        assert response.status_code == 200, "Malformed date should re-render the form, not redirect"
        page = html(response)
        assert "error" in page.lower(), f"Expected an inline error for malformed date {bad_date!r}"
        assert count_expenses(user_id) == 0, "Malformed date must not insert a row"

    def test_todays_date_is_accepted(self, auth_client, clean_expenses):
        user_id = clean_expenses
        payload = {**VALID_PAYLOAD, "date": date.today().isoformat()}
        response = auth_client.post("/expenses/add", data=payload, follow_redirects=False)
        assert response.status_code == 302, "Today's date is not in the future and should be accepted"
        assert count_expenses(user_id) == 1
