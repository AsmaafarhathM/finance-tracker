from flask import Blueprint, jsonify

from db import get_connection
from middleware.auth import ROLES, authorize


bp = Blueprint("summary", __name__)


def _to_number(value):
    # MySQL DECIMAL often comes back as Decimal; Flask can jsonify floats/ints.
    if value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


@bp.get("/summary/income")
@authorize(["admin", "analyst"])
def summary_income():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total_income FROM Records WHERE type='income'")
        row = cur.fetchone() or {"total_income": 0}
        return jsonify({"total_income": _to_number(row.get("total_income"))}), 200
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.get("/summary/expense")
@authorize(["admin", "analyst"])
def summary_expense():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total_expense FROM Records WHERE type='expense'")
        row = cur.fetchone() or {"total_expense": 0}
        return jsonify({"total_expense": _to_number(row.get("total_expense"))}), 200
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.get("/summary/balance")
@authorize(list(ROLES))
def summary_balance():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                COALESCE(
                    SUM(CASE WHEN type='income' THEN amount ELSE 0 END)
                    - SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),
                0) AS balance
            FROM Records
            """
        )
        row = cur.fetchone() or {"balance": 0}
        return jsonify({"balance": _to_number(row.get("balance"))}), 200
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.get("/summary/category")
@authorize(list(ROLES))
def summary_category():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM Records
            WHERE type='income'
            GROUP BY category
            ORDER BY total DESC
            """
        )
        income_rows = cur.fetchall() or []
        income_by_category = [
            {"category": r.get("category"), "total": _to_number(r.get("total"))} for r in income_rows
        ]

        cur.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM Records
            WHERE type='expense'
            GROUP BY category
            ORDER BY total DESC
            """
        )
        expense_rows = cur.fetchall() or []
        expense_by_category = [
            {"category": r.get("category"), "total": _to_number(r.get("total"))} for r in expense_rows
        ]

        return jsonify({"income_by_category": income_by_category, "expense_by_category": expense_by_category}), 200
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

