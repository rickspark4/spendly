"""
Tests for Spec 06: Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile-page.md

Covers:
- GET /profile auth guard (redirect to /login when not authenticated)
- No filter => all-time data (unchanged Step 5 behavior)
- Valid start/end range narrows stats, transactions, and category breakdown
- Date inputs are re-populated with submitted start/end values
- "Clear" link points back to /profile with no query params
- Graceful fallback to all-time data for: missing start or end, malformed
  date strings, and start > end (never a 500)
- Zero-match date range renders without error and shows an empty/zero state
- Category breakdown percentages still sum to ~100% within a filtered range
"""
import re

import pytest

from conftest import insert_expense

# A small, fully controlled dataset independent of "today" so date-range
# math is deterministic regardless of when the suite runs.
JAN_EXPENSE_1 = dict(amount=10.00, category="Food", date="2024-01-05", description="Jan Groceries A")
JAN_EXPENSE_2 = dict(amount=15.00, category="Food", date="2024-01-10", description="Jan Groceries B")
JAN_EXPENSE_3 = dict(amount=20.00, category="Transport", date="2024-01-20", description="Jan Bus Pass")
FEB_EXPENSE_1 = dict(amount=30.00, category="Bills", date="2024-02-05", description="Feb Electricity")
FEB_EXPENSE_2 = dict(amount=40.00, category="Shopping", date="2024-02-15", description="Feb Shoes")

ALL_EXPENSES = [JAN_EXPENSE_1, JAN_EXPENSE_2, JAN_EXPENSE_3, FEB_EXPENSE_1, FEB_EXPENSE_2]


@pytest.fixture
def controlled_expenses(clean_expenses):
    """Seeds the demo user with ALL_EXPENSES only (seeded random expenses removed)."""
    user_id = clean_expenses
    for exp in ALL_EXPENSES:
        insert_expense(user_id, exp["amount"], exp["category"], exp["date"], exp["description"])
    return user_id


def html(response):
    return response.data.decode("utf-8")


def bar_percentages(page_html):
    """Extract the rendered category-bar percentages (bar-pct-N CSS class) from the page."""
    return [int(p) for p in re.findall(r"bar-pct-(\d+)", page_html)]


class TestAuthGuard:
    def test_profile_redirects_to_login_when_not_authenticated(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "Unauthenticated /profile should redirect, not render"
        assert "/login" in response.headers.get("Location", ""), (
            "Unauthenticated /profile should redirect to /login"
        )

    def test_profile_with_date_filter_still_redirects_when_not_authenticated(self, client):
        response = client.get("/profile?start=2024-01-01&end=2024-01-31")
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")


class TestNoFilterAllTimeData:
    def test_profile_no_params_returns_200(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile")
        assert response.status_code == 200

    def test_profile_no_params_shows_all_expenses(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile")
        page = html(response)
        for exp in ALL_EXPENSES:
            assert exp["description"] in page, (
                f"All-time view should include {exp['description']!r} when no date filter is applied"
            )

    def test_profile_no_params_shows_all_time_total(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile")
        page = html(response)
        total = sum(exp["amount"] for exp in ALL_EXPENSES)
        assert f"{total:,.2f}" in page, "All-time total spent should equal the sum of every expense"

    def test_profile_date_inputs_empty_when_no_filter_applied(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile")
        page = html(response)
        assert 'name="start" value=""' in page
        assert 'name="end" value=""' in page


class TestValidDateRangeFiltering:
    def test_filter_narrows_transactions_to_range(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01&end=2024-01-31")
        page = html(response)

        for exp in (JAN_EXPENSE_1, JAN_EXPENSE_2, JAN_EXPENSE_3):
            assert exp["description"] in page, f"{exp['description']} falls within the January range"

        for exp in (FEB_EXPENSE_1, FEB_EXPENSE_2):
            assert exp["description"] not in page, (
                f"{exp['description']} falls outside the January range and should be excluded"
            )

    def test_filter_narrows_total_spent_stat(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01&end=2024-01-31")
        page = html(response)
        jan_total = JAN_EXPENSE_1["amount"] + JAN_EXPENSE_2["amount"] + JAN_EXPENSE_3["amount"]
        assert f"{jan_total:,.2f}" in page, "Total spent should reflect only in-range expenses"

    def test_filter_range_is_inclusive_of_boundary_dates(self, auth_client, controlled_expenses):
        # Range exactly matches JAN_EXPENSE_1's date on both ends.
        response = auth_client.get("/profile?start=2024-01-05&end=2024-01-05")
        page = html(response)
        assert JAN_EXPENSE_1["description"] in page, "Boundary start/end date should be included (inclusive range)"
        assert JAN_EXPENSE_2["description"] not in page
        assert JAN_EXPENSE_3["description"] not in page

    def test_filter_narrows_category_breakdown(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01&end=2024-01-31")
        page = html(response)
        assert "Food" in page
        assert "Transport" in page
        # Categories only present in February should not appear in the breakdown.
        assert "Bills" not in page
        assert "Shopping" not in page

    def test_filter_category_breakdown_percentages_sum_to_about_100(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01&end=2024-01-31")
        page = html(response)
        percentages = bar_percentages(page)
        assert percentages, "Expected at least one category bar in the filtered breakdown"
        assert abs(sum(percentages) - 100) <= 10, (
            f"Filtered category percentages should sum to ~100%, got {sum(percentages)} from {percentages}"
        )

    def test_clear_link_points_back_to_profile_with_no_query_params(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01&end=2024-01-31")
        page = html(response)
        assert 'href="/profile"' in page, "Clear link should point back to /profile with no query string"
        assert "Clear" in page


class TestDateInputRepopulation:
    def test_inputs_prepopulated_with_submitted_values(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01&end=2024-01-31")
        page = html(response)
        assert 'name="start" value="2024-01-01"' in page
        assert 'name="end" value="2024-01-31"' in page

    def test_inputs_reflect_partial_submission(self, auth_client, controlled_expenses):
        # Even though the filter falls back to all-time, the raw submitted
        # value(s) should still populate the form per the spec.
        response = auth_client.get("/profile?start=2024-01-01")
        page = html(response)
        assert 'name="start" value="2024-01-01"' in page


class TestGracefulFallbackToAllTime:
    def test_missing_end_falls_back_to_all_time(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-01-01")
        assert response.status_code == 200
        page = html(response)
        for exp in ALL_EXPENSES:
            assert exp["description"] in page, "Missing 'end' should ignore the filter, showing all-time data"

    def test_missing_start_falls_back_to_all_time(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?end=2024-01-31")
        assert response.status_code == 200
        page = html(response)
        for exp in ALL_EXPENSES:
            assert exp["description"] in page, "Missing 'start' should ignore the filter, showing all-time data"

    @pytest.mark.parametrize("start,end", [
        ("2024-13-40", "2024-01-31"),   # non-existent month/day
        ("not-a-date", "2024-01-31"),   # not a date at all
        ("2024-01-01", "banana"),       # malformed end
        ("2024/01/01", "2024/01/31"),   # wrong separator
    ])
    def test_malformed_date_falls_back_to_all_time_without_error(self, auth_client, controlled_expenses, start, end):
        response = auth_client.get(f"/profile?start={start}&end={end}")
        assert response.status_code == 200, "Malformed dates must never produce a 500 error"
        page = html(response)
        for exp in ALL_EXPENSES:
            assert exp["description"] in page, "Malformed date filter should degrade to all-time data"

    def test_start_after_end_falls_back_to_all_time(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2024-02-01&end=2024-01-01")
        assert response.status_code == 200
        page = html(response)
        for exp in ALL_EXPENSES:
            assert exp["description"] in page, "start > end should be ignored in favor of all-time data"


class TestZeroMatchRange:
    def test_zero_match_range_renders_without_error(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2025-01-01&end=2025-01-31")
        assert response.status_code == 200, "A date range with no matching expenses must not crash the page"

    def test_zero_match_range_excludes_all_known_expenses(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2025-01-01&end=2025-01-31")
        page = html(response)
        for exp in ALL_EXPENSES:
            assert exp["description"] not in page, (
                f"{exp['description']} is outside the requested range and should not be shown"
            )

    def test_zero_match_range_shows_zero_total(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2025-01-01&end=2025-01-31")
        page = html(response)
        assert "0.00" in page, "Zero-match range should render a zero total, not omit the stat"

    def test_zero_match_range_has_no_category_bars(self, auth_client, controlled_expenses):
        response = auth_client.get("/profile?start=2025-01-01&end=2025-01-31")
        page = html(response)
        assert bar_percentages(page) == [], "Zero-match range should render an empty category breakdown"


class TestNoDatabaseChanges:
    def test_filtering_does_not_mutate_expense_rows(self, auth_client, controlled_expenses):
        """The filter is a read-only query narrowing; it must not delete/alter expense rows."""
        from database.db import get_db

        auth_client.get("/profile?start=2024-01-01&end=2024-01-31")

        db = get_db()
        count = db.execute(
            "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?",
            (controlled_expenses,),
        ).fetchone()["n"]
        db.close()

        assert count == len(ALL_EXPENSES), "Applying a date filter must not delete or alter expense rows"
