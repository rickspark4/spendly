import math
import os
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import CATEGORIES, get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Profile data helpers                                                #
# ------------------------------------------------------------------ #

def get_profile_user(db, user_id):
    row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if row is None:
        return None

    initials = "".join(part[0].upper() for part in row["name"].split()[:2])
    created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")

    return {
        "name": row["name"],
        "email": row["email"],
        "initials": initials,
        "member_since": created_at.strftime("%B %Y"),
    }


def build_date_range_filter(user_id, date_range):
    """Return (range_clause, params) for scoping an expenses query to user_id,
    optionally narrowed to an inclusive (start, end) date_range. range_clause
    is always one of two hardcoded literals — never built from user input —
    so splicing it into query text carries no injection risk; the actual
    start/end values are still passed as bound `?` params."""
    params = [user_id]
    range_clause = ""
    if date_range:
        range_clause = "AND date BETWEEN ? AND ?"
        params.extend(date_range)
    return range_clause, params


def get_profile_stats(db, user_id, date_range=None):
    totals_query = "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?"
    top_query = """
        SELECT category, COUNT(*) AS n
        FROM expenses
        WHERE user_id = ?
        {range_clause}
        GROUP BY category
        ORDER BY n DESC
        LIMIT 1
    """
    range_clause, params = build_date_range_filter(user_id, date_range)

    totals = db.execute(f"{totals_query} {range_clause}", params).fetchone()
    top = db.execute(top_query.format(range_clause=range_clause), params).fetchone()

    return {
        "total_spent": f"₹{totals['total']:,.2f}",
        "transaction_count": totals["count"],
        "top_category": top["category"] if top else "—",
    }


def get_profile_transactions(db, user_id, limit=10, date_range=None):
    range_clause, params = build_date_range_filter(user_id, date_range)
    params.append(limit)

    rows = db.execute(
        f"""
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        {range_clause}
        ORDER BY date DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    transactions = []
    for row in rows:
        exp_date = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append({
            "date": exp_date.strftime("%d %b %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        })
    return transactions


def get_profile_category_breakdown(db, user_id, date_range=None):
    range_clause, params = build_date_range_filter(user_id, date_range)

    rows = db.execute(
        f"""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        {range_clause}
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    ).fetchall()

    grand_total = sum(row["total"] for row in rows)
    if grand_total <= 0:
        return []

    breakdown = []
    for row in rows:
        raw_pct = (row["total"] / grand_total) * 100
        pct = int(round(raw_pct / 5) * 5)
        pct = max(5, min(100, pct))
        breakdown.append({
            "category": row["category"],
            "total": f"₹{row['total']:,.2f}",
            "percent": pct,
        })
    return breakdown


def parse_date_range(args):
    start = args.get("start")
    end = args.get("end")

    if not start or not end:
        return None, None

    try:
        # Normalize to zero-padded YYYY-MM-DD so string comparison (both here
        # and in the SQL BETWEEN clause) matches chronological order — strptime
        # itself accepts unpadded input like "2024-9-5", which would otherwise
        # sort incorrectly against "2024-10-01".
        start = datetime.strptime(start, "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None, None

    if start > end:
        return None, None

    return start, end


DESCRIPTION_MAX_LENGTH = 255


def parse_expense_form(form):
    """Validate a submitted add-expense form. Returns (data, error) where
    data holds the cleaned fields on success and error is None; on failure
    data holds the raw submitted values (for re-rendering the form) and
    error is a user-facing message for the first invalid field."""
    amount_raw = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    date_raw = form.get("date", "").strip()
    description = form.get("description", "").strip()

    data = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description,
    }

    try:
        amount = float(amount_raw)
        if not math.isfinite(amount):
            amount = None
    except ValueError:
        amount = None

    if amount is None or amount <= 0:
        return data, "Enter a valid amount greater than 0."

    if category not in CATEGORIES:
        return data, "Select a valid category."

    try:
        expense_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        return data, "Enter a valid date (not in the future)."

    if expense_date > date.today():
        return data, "Enter a valid date (not in the future)."

    if len(description) > DESCRIPTION_MAX_LENGTH:
        return data, f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer."

    data["amount"] = amount
    data["date"] = expense_date.isoformat()
    return data, None


@app.context_processor
def inject_current_user():
    if session.get("user_id"):
        return {"current_user": get_profile_user(get_db(), session["user_id"])}
    return {"current_user": None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email:
        return render_template("register.html", error="Name and email are required.",
                                name=name, email=email)

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.",
                                name=name, email=email)

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return render_template("register.html", error="An account with this email already exists.",
                                name=name, email=email)

    password_hash = generate_password_hash(password)
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    db.commit()
    session["user_id"] = cursor.lastrowid

    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"] = user["id"]

    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    return render_template("analytics.html")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]

    user = get_profile_user(db, user_id)
    if user is None:
        # Stale session referencing a user that no longer exists in the DB
        session.pop("user_id", None)
        return redirect(url_for("login"))

    start, end = parse_date_range(request.args)
    date_range = (start, end) if start else None

    return render_template(
        "profile.html",
        user=user,
        stats=get_profile_stats(db, user_id, date_range),
        transactions=get_profile_transactions(db, user_id, date_range=date_range),
        categories=get_profile_category_breakdown(db, user_id, date_range),
        filter_start=request.args.get("start", ""),
        filter_end=request.args.get("end", ""),
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "expenses/add.html",
            categories=CATEGORIES,
            date=date.today().isoformat(),
        )

    data, error = parse_expense_form(request.form)
    if error:
        return render_template("expenses/add.html", error=error, categories=CATEGORIES, **data)

    # data holds cleaned/typed values here (float amount, ISO date string) —
    # distinct from the raw strings returned alongside a validation error above.
    db = get_db()
    try:
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                session["user_id"],
                data["amount"],
                data["category"],
                data["date"],
                data["description"] or None,
            ),
        )
        db.commit()
    finally:
        db.close()

    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
