import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

# Render'da doimiy disk ulanganda, DB_PATH muhit o'zgaruvchisi orqali
# masalan /data/bot_data.db qilib beriladi. Lokal ishlatishda shu yerda qoladi.
DB_PATH = os.environ.get("DB_PATH", "bot_data.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            salary_usd REAL NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS salary_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_usd REAL NOT NULL,
            note TEXT,
            paid_at TEXT,
            month_key TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS expense_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            note TEXT,
            spent_at TEXT,
            month_key TEXT,
            FOREIGN KEY (category_id) REFERENCES expense_categories(id)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS exchanges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            given_amount REAL NOT NULL,
            given_currency TEXT NOT NULL,
            received_amount REAL NOT NULL,
            received_currency TEXT NOT NULL,
            rate REAL NOT NULL,
            note TEXT,
            exchanged_at TEXT,
            month_key TEXT
        )
        """)

        # Default kategoriyalar
        default_categories = ["Arenda", "Do'kon", "Komunal", "Transport", "Boshqa"]
        for cat in default_categories:
            c.execute(
                "INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (cat,)
            )


def current_month_key():
    return datetime.now().strftime("%Y-%m")


# ---------- EMPLOYEES ----------

def add_employee(name, salary_usd):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO employees (name, salary_usd, created_at) VALUES (?, ?, ?)",
            (name, salary_usd, datetime.now().isoformat()),
        )
        return c.lastrowid


def get_employees(active_only=True):
    with get_conn() as conn:
        c = conn.cursor()
        if active_only:
            c.execute("SELECT * FROM employees WHERE active = 1 ORDER BY name")
        else:
            c.execute("SELECT * FROM employees ORDER BY name")
        return c.fetchall()


def get_employee(employee_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
        return c.fetchone()


def deactivate_employee(employee_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE employees SET active = 0 WHERE id = ?", (employee_id,))


def update_employee_salary(employee_id, salary_usd):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE employees SET salary_usd = ? WHERE id = ?",
            (salary_usd, employee_id),
        )


# ---------- SALARY PAYMENTS ----------

def add_salary_payment(employee_id, amount, currency, amount_usd, note=""):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO salary_payments
               (employee_id, amount, currency, amount_usd, note, paid_at, month_key)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                employee_id,
                amount,
                currency,
                amount_usd,
                note,
                datetime.now().isoformat(),
                current_month_key(),
            ),
        )
        return c.lastrowid


def get_paid_total_usd(employee_id, month_key=None):
    with get_conn() as conn:
        c = conn.cursor()
        if month_key:
            c.execute(
                """SELECT COALESCE(SUM(amount_usd), 0) as total
                   FROM salary_payments WHERE employee_id = ? AND month_key = ?""",
                (employee_id, month_key),
            )
        else:
            c.execute(
                """SELECT COALESCE(SUM(amount_usd), 0) as total
                   FROM salary_payments WHERE employee_id = ?""",
                (employee_id,),
            )
        return c.fetchone()["total"]


def get_salary_payments(employee_id, month_key=None):
    with get_conn() as conn:
        c = conn.cursor()
        if month_key:
            c.execute(
                """SELECT * FROM salary_payments
                   WHERE employee_id = ? AND month_key = ? ORDER BY paid_at""",
                (employee_id, month_key),
            )
        else:
            c.execute(
                "SELECT * FROM salary_payments WHERE employee_id = ? ORDER BY paid_at",
                (employee_id,),
            )
        return c.fetchall()


def get_all_payments_month(month_key):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT sp.*, e.name as employee_name FROM salary_payments sp
               JOIN employees e ON e.id = sp.employee_id
               WHERE sp.month_key = ? ORDER BY sp.paid_at""",
            (month_key,),
        )
        return c.fetchall()


# ---------- EXPENSE CATEGORIES ----------

def get_categories():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM expense_categories ORDER BY name")
        return c.fetchall()


def add_category(name):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (name,)
        )
        return c.lastrowid


def get_category(category_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM expense_categories WHERE id = ?", (category_id,))
        return c.fetchone()


# ---------- EXPENSES ----------

def add_expense(category_id, amount, currency, note=""):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO expenses (category_id, amount, currency, note, spent_at, month_key)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                category_id,
                amount,
                currency,
                note,
                datetime.now().isoformat(),
                current_month_key(),
            ),
        )
        return c.lastrowid


def get_expenses_month(month_key, currency=None):
    with get_conn() as conn:
        c = conn.cursor()
        if currency:
            c.execute(
                """SELECT ex.*, ec.name as category_name FROM expenses ex
                   JOIN expense_categories ec ON ec.id = ex.category_id
                   WHERE ex.month_key = ? AND ex.currency = ? ORDER BY ex.spent_at""",
                (month_key, currency),
            )
        else:
            c.execute(
                """SELECT ex.*, ec.name as category_name FROM expenses ex
                   JOIN expense_categories ec ON ec.id = ex.category_id
                   WHERE ex.month_key = ? ORDER BY ex.spent_at""",
                (month_key,),
            )
        return c.fetchall()


def get_expense_totals_by_category(month_key):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT ec.name as category_name, ex.currency,
                      COALESCE(SUM(ex.amount), 0) as total
               FROM expenses ex
               JOIN expense_categories ec ON ec.id = ex.category_id
               WHERE ex.month_key = ?
               GROUP BY ec.name, ex.currency
               ORDER BY ec.name""",
            (month_key,),
        )
        return c.fetchall()


# ---------- EXCHANGES ----------

def add_exchange(given_amount, given_currency, received_amount, received_currency, note=""):
    rate = received_amount / given_amount if given_amount else 0
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO exchanges
               (given_amount, given_currency, received_amount, received_currency, rate, note, exchanged_at, month_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                given_amount,
                given_currency,
                received_amount,
                received_currency,
                rate,
                note,
                datetime.now().isoformat(),
                current_month_key(),
            ),
        )
        return c.lastrowid


def get_exchanges_month(month_key):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM exchanges WHERE month_key = ? ORDER BY exchanged_at",
            (month_key,),
        )
        return c.fetchall()
