import json
import os
import re
import secrets
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DATABASE = INSTANCE_DIR / "good_indian_textile.db"

ITEM_OPTIONS = [
    "Saree",
    "Shirt",
    "Pant",
    "Slippers",
    "Inner Wear B",
    "Inner Wear G",
    "Kids Wear",
    "T-Shirt",
    "Shorts",
    "Belt",
    "Makeup Items",
]

PAYMENT_METHODS = ["Cash", "UPI", "Card"]

BUSINESS = {
    "name": "Good Indian Textile",
    "tagline": "Fashion • Fabrics • Everyday Essentials",
    "initials": "GI",
}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            phone TEXT,
            bill_date TEXT NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'Cash',
            subtotal REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost REAL NOT NULL,
            discount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_bills_date ON bills (bill_date);
        CREATE INDEX IF NOT EXISTS idx_bills_customer ON bills (customer_name);
        CREATE INDEX IF NOT EXISTS idx_bill_items_bill ON bill_items (bill_id);
        """
    )
    db.commit()
    db.close()


init_db()


def money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pretty_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d %b %Y")
    except (TypeError, ValueError):
        return value


def inr(value):
    amount = money(value)
    sign = "-" if amount < 0 else ""
    whole, decimals = f"{abs(amount):.2f}".split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        whole = ",".join(groups) + "," + last_three
    return f"₹{sign}{whole}.{decimals}"


ONES = [
    "Zero",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def two_digit_words(number):
    if number < 20:
        return ONES[number]
    return TENS[number // 10] + (" " + ONES[number % 10] if number % 10 else "")


def three_digit_words(number):
    parts = []
    if number >= 100:
        parts.append(f"{ONES[number // 100]} Hundred")
        number %= 100
        if number:
            parts.append("and")
    if number:
        parts.append(two_digit_words(number))
    return " ".join(parts)


def amount_in_words(value):
    amount = money(value)
    rupees = int(amount)
    paise = int((amount - rupees) * 100)

    if rupees == 0 and paise == 0:
        return "Zero Rupees Only"

    parts = []
    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000

    if crore:
        parts.append(f"{three_digit_words(crore)} Crore")
    if lakh:
        parts.append(f"{three_digit_words(lakh)} Lakh")
    if thousand:
        parts.append(f"{three_digit_words(thousand)} Thousand")
    if rupees:
        parts.append(three_digit_words(rupees))

    words = " ".join(parts) + " Rupees"
    if paise:
        words += f" and {two_digit_words(paise)} Paise"
    return words + " Only"


app.jinja_env.filters["inr"] = inr
app.jinja_env.filters["words"] = amount_in_words
app.jinja_env.filters["pretty_date"] = pretty_date


@app.context_processor
def inject_globals():
    return {
        "business": BUSINESS,
        "today": date.today(),
        "item_options": ITEM_OPTIONS,
        "payment_methods": PAYMENT_METHODS,
    }


def next_bill_no(db):
    row = db.execute(
        "SELECT MAX(CAST(SUBSTR(bill_no, 5) AS INTEGER)) AS last_no FROM bills"
    ).fetchone()
    number = (row["last_no"] or 1000) + 1
    return f"GIT-{number:04d}"


def suggest_customer_id(db):
    row = db.execute(
        "SELECT customer_id FROM bills ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        match = re.search(r"(\d+)$", row["customer_id"])
        if match:
            return f"GIT-C{int(match.group(1)) + 1:03d}"
    return "GIT-C001"


def parse_items(raw_items):
    try:
        items = json.loads(raw_items or "[]")
    except (TypeError, json.JSONDecodeError):
        raise ValueError("The item list could not be read. Please try again.")

    if not isinstance(items, list) or not items:
        raise ValueError("Add at least one item to the bill.")

    parsed = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} is invalid.")

        item_name = str(item.get("item_name", "")).strip()
        if item_name not in ITEM_OPTIONS:
            raise ValueError(f"Choose a valid item for row {index}.")

        try:
            quantity = int(item.get("quantity", 1))
            cost = money(item.get("cost", 0))
            discount = money(item.get("discount", 0))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"Check the quantity, cost, and discount for row {index}.")

        if quantity < 1:
            raise ValueError(f"Quantity must be at least 1 for row {index}.")
        if cost < 0:
            raise ValueError(f"Cost cannot be negative for row {index}.")
        if discount < 0:
            raise ValueError(f"Discount cannot be negative for row {index}.")

        gross = money(cost * quantity)
        if discount > gross:
            raise ValueError(
                f"Discount for {item_name} cannot be more than its cost."
            )

        parsed.append(
            {
                "item_name": item_name,
                "quantity": quantity,
                "cost": cost,
                "discount": discount,
                "total": money(gross - discount),
            }
        )
    return parsed


def form_defaults(db):
    return {
        "customer_name": "",
        "customer_id": suggest_customer_id(db),
        "phone": "",
        "bill_date": date.today().isoformat(),
        "payment_method": "Cash",
        "notes": "",
        "bill_no": next_bill_no(db),
    }


@app.route("/")
def dashboard():
    db = get_db()
    today_iso = date.today().isoformat()
    month_prefix = date.today().strftime("%Y-%m")

    stats = {
        "today_sales": db.execute(
            "SELECT COALESCE(SUM(total), 0) FROM bills WHERE bill_date = ?",
            (today_iso,),
        ).fetchone()[0],
        "month_sales": db.execute(
            "SELECT COALESCE(SUM(total), 0) FROM bills WHERE bill_date LIKE ?",
            (f"{month_prefix}%",),
        ).fetchone()[0],
        "total_bills": db.execute("SELECT COUNT(*) FROM bills").fetchone()[0],
        "total_discount": db.execute(
            "SELECT COALESCE(SUM(discount), 0) FROM bills"
        ).fetchone()[0],
        "items_sold": db.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM bill_items"
        ).fetchone()[0],
    }

    recent_bills = db.execute(
        """
        SELECT b.*, COUNT(i.id) AS item_count
        FROM bills b
        LEFT JOIN bill_items i ON i.bill_id = b.id
        GROUP BY b.id
        ORDER BY b.bill_date DESC, b.id DESC
        LIMIT 6
        """
    ).fetchall()

    top_categories = db.execute(
        """
        SELECT item_name, SUM(quantity) AS units, SUM(total) AS revenue
        FROM bill_items
        GROUP BY item_name
        ORDER BY revenue DESC, units DESC
        LIMIT 5
        """
    ).fetchall()
    max_category = max((row["revenue"] for row in top_categories), default=0)

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        page_title="Dashboard",
        page_eyebrow="Good Indian Textile",
        stats=stats,
        recent_bills=recent_bills,
        top_categories=top_categories,
        max_category=max_category,
    )


@app.route("/bills/new", methods=["GET", "POST"])
def new_bill():
    db = get_db()

    if request.method == "POST":
        defaults = form_defaults(db)
        form_values = {
            "customer_name": request.form.get("customer_name", "").strip(),
            "customer_id": request.form.get("customer_id", "").strip().upper(),
            "phone": request.form.get("phone", "").strip(),
            "bill_date": request.form.get("bill_date", "").strip(),
            "payment_method": request.form.get("payment_method", "Cash"),
            "notes": request.form.get("notes", "").strip(),
            "bill_no": request.form.get("bill_no", "").strip() or defaults["bill_no"],
        }
        raw_items = request.form.get("items_json", "")

        try:
            if not form_values["customer_name"]:
                raise ValueError("Enter the customer's name.")
            if not form_values["customer_id"]:
                raise ValueError("Enter a customer ID.")
            try:
                datetime.strptime(form_values["bill_date"], "%Y-%m-%d")
            except ValueError:
                raise ValueError("Choose a valid bill date.")
            if form_values["payment_method"] not in PAYMENT_METHODS:
                raise ValueError("Choose a valid payment method.")

            items = parse_items(raw_items)
            subtotal = sum((item["cost"] * item["quantity"] for item in items), Decimal("0"))
            discount_total = sum((item["discount"] for item in items), Decimal("0"))
            total = money(subtotal - discount_total)

            cursor = db.execute(
                """
                INSERT INTO bills (
                    bill_no, customer_name, customer_id, phone, bill_date,
                    payment_method, subtotal, discount, total, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form_values["bill_no"],
                    form_values["customer_name"],
                    form_values["customer_id"],
                    form_values["phone"],
                    form_values["bill_date"],
                    form_values["payment_method"],
                    float(money(subtotal)),
                    float(discount_total),
                    float(total),
                    form_values["notes"],
                ),
            )
            bill_id = cursor.lastrowid

            db.executemany(
                """
                INSERT INTO bill_items (
                    bill_id, item_name, quantity, cost, discount, total
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        bill_id,
                        item["item_name"],
                        item["quantity"],
                        float(item["cost"]),
                        float(item["discount"]),
                        float(item["total"]),
                    )
                    for item in items
                ],
            )
            db.commit()
            flash(f"Bill {form_values['bill_no']} saved successfully.", "success")
            return redirect(url_for("view_bill", bill_id=bill_id))
        except (ValueError, sqlite3.IntegrityError) as error:
            db.rollback()
            message = str(error)
            if isinstance(error, sqlite3.IntegrityError):
                message = "That bill number already exists. Please refresh and try again."
            try:
                draft_items = json.loads(raw_items)
            except (json.JSONDecodeError, TypeError):
                draft_items = []
            return render_template(
                "bill_form.html",
                active_page="new_bill",
                page_title="New Bill",
                page_eyebrow="Create invoice",
                form_values=form_values,
                initial_items=draft_items,
                error=message,
            )

    form_values = form_defaults(db)
    return render_template(
        "bill_form.html",
        active_page="new_bill",
        page_title="New Bill",
        page_eyebrow="Create invoice",
        form_values=form_values,
        initial_items=[],
        error=None,
    )


@app.route("/bills")
def bills():
    db = get_db()
    search = request.args.get("search", "").strip()

    if search:
        term = f"%{search}%"
        rows = db.execute(
            """
            SELECT b.*, COUNT(i.id) AS item_count
            FROM bills b
            LEFT JOIN bill_items i ON i.bill_id = b.id
            WHERE b.bill_no LIKE ?
               OR b.customer_name LIKE ?
               OR b.customer_id LIKE ?
               OR b.phone LIKE ?
            GROUP BY b.id
            ORDER BY b.bill_date DESC, b.id DESC
            """,
            (term, term, term, term),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT b.*, COUNT(i.id) AS item_count
            FROM bills b
            LEFT JOIN bill_items i ON i.bill_id = b.id
            GROUP BY b.id
            ORDER BY b.bill_date DESC, b.id DESC
            """
        ).fetchall()

    totals = {
        "count": len(rows),
        "total": sum((row["total"] for row in rows), 0),
        "discount": sum((row["discount"] for row in rows), 0),
    }

    return render_template(
        "bills.html",
        active_page="bills",
        page_title="All Bills",
        page_eyebrow="Billing history",
        bills=rows,
        search=search,
        totals=totals,
    )


@app.route("/bills/<int:bill_id>")
def view_bill(bill_id):
    db = get_db()
    bill = db.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    if bill is None:
        flash("That bill could not be found.", "error")
        return redirect(url_for("bills"))

    items = db.execute(
        "SELECT * FROM bill_items WHERE bill_id = ? ORDER BY id", (bill_id,)
    ).fetchall()

    return render_template(
        "invoice.html",
        active_page="bills",
        page_title=bill["bill_no"],
        page_eyebrow="Invoice",
        bill=bill,
        items=items,
    )


@app.post("/bills/<int:bill_id>/delete")
def delete_bill(bill_id):
    db = get_db()
    bill = db.execute(
        "SELECT bill_no FROM bills WHERE id = ?", (bill_id,)
    ).fetchone()
    if bill is None:
        flash("That bill could not be found.", "error")
        return redirect(url_for("bills"))

    db.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
    db.commit()
    flash(f"Bill {bill['bill_no']} deleted.", "success")
    return redirect(url_for("bills"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)
