import os

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

with app.app_context():
    init_db()
    seed_db()


# Hardcoded profile data — Step 4 placeholder, real queries in Step 5
PROFILE_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "initials": "DU",
    "member_since": "March 2025",
}

PROFILE_STATS = {
    "total_spent": "₹18,240",
    "transaction_count": 34,
    "top_category": "Food",
}

PROFILE_TRANSACTIONS = [
    {"date": "11 Aug 2026", "description": "Grocery run at BigBasket", "category": "Food", "amount": "₹1,240.00"},
    {"date": "09 Aug 2026", "description": "Uber to airport", "category": "Transport", "amount": "₹650.00"},
    {"date": "07 Aug 2026", "description": "Electricity bill — August", "category": "Bills", "amount": "₹2,180.00"},
    {"date": "05 Aug 2026", "description": "Pharmacy — cold medicine", "category": "Health", "amount": "₹340.00"},
    {"date": "03 Aug 2026", "description": "Movie night with friends", "category": "Entertainment", "amount": "₹980.00"},
    {"date": "01 Aug 2026", "description": "New running shoes", "category": "Shopping", "amount": "₹3,499.00"},
]

PROFILE_CATEGORY_BREAKDOWN = [
    {"category": "Food", "total": "₹5,420", "percent": 30},
    {"category": "Bills", "total": "₹4,360", "percent": 25},
    {"category": "Shopping", "total": "₹3,499", "percent": 20},
    {"category": "Entertainment", "total": "₹2,180", "percent": 10},
    {"category": "Transport", "total": "₹1,650", "percent": 10},
    {"category": "Health", "total": "₹1,131", "percent": 5},
]


@app.context_processor
def inject_current_user():
    if session.get("user_id"):
        return {"current_user": PROFILE_USER}
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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        user=PROFILE_USER,
        stats=PROFILE_STATS,
        transactions=PROFILE_TRANSACTIONS,
        categories=PROFILE_CATEGORY_BREAKDOWN,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
