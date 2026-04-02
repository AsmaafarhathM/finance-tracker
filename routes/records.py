from datetime import datetime

from flask import Blueprint, jsonify, request

from db import get_connection
from middleware.auth import authorize, require_jwt_payload


bp = Blueprint("records", __name__)


def _parse_date(date_str: str | None):
    if not date_str:
        return None
    try:
        # Strict YYYY-MM-DD parsing.
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_type(t: str | None) -> str | None:
    if not t:
        return None
    t = t.strip().lower()
    if t in {"income", "expense"}:
        return t
    return None


def _parse_positive_amount(value):
    if value is None:
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return amount


def _validate_record_payload(payload: dict):
    amount = _parse_positive_amount(payload.get("amount"))
    rec_type = _normalize_type(payload.get("type"))
    category = (payload.get("category") or "").strip()
    date = _parse_date(payload.get("date"))
    note = (payload.get("note") or "").strip() if payload.get("note") is not None else None

    if amount is None:
        return None, jsonify({"error": "Invalid amount. Must be a positive number."}), 400
    if rec_type is None:
        return None, jsonify({"error": "Invalid type. Must be 'income' or 'expense'."}), 400
    if not category:
        return None, jsonify({"error": "Missing required field: category"}), 400
    if not date:
        return None, jsonify({"error": "Invalid date. Must be YYYY-MM-DD."}), 400

    return {"amount": amount, "type": rec_type, "category": category, "date": str(date), "note": note}, None, None


@bp.post("/records")
@authorize(["admin"])
def create_record():
    jwt_payload, err = require_jwt_payload()
    if err is not None:
        return err

    payload = request.get_json(silent=True) or {}
    validated, response, status = _validate_record_payload(payload)
    if response is not None:
        return response, status

    user_id = jwt_payload.get("sub")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid token payload: sub"}), 401

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO Records (user_id, amount, type, category, date, note)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, validated["amount"], validated["type"], validated["category"], validated["date"], validated["note"]),
        )
        conn.commit()
        record_id = cur.lastrowid
        return (
            jsonify(
                {
                    "id": record_id,
                    "user_id": user_id,
                    "amount": validated["amount"],
                    "type": validated["type"],
                    "category": validated["category"],
                    "date": validated["date"],
                    "note": validated["note"],
                }
            ),
            201,
        )
    except Exception:
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to create record"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.get("/records")
@authorize(["admin", "analyst", "viewer"])
def list_records():
    user_id_raw = request.args.get("user_id")
    type_raw = request.args.get("type")
    category = (request.args.get("category") or "").strip() or None
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    user_id = None
    if user_id_raw is not None and user_id_raw.strip() != "":
        try:
            user_id = int(user_id_raw)
        except ValueError:
            return jsonify({"error": "Invalid query param: user_id must be an integer"}), 400

    rec_type = _normalize_type(type_raw)
    if type_raw is not None and rec_type is None:
        return jsonify({"error": "Invalid query param: type must be income or expense"}), 400

    start_date = _parse_date(start_date_str)
    if start_date_str and not start_date:
        return jsonify({"error": "Invalid query param: start_date must be YYYY-MM-DD"}), 400
    end_date = _parse_date(end_date_str)
    if end_date_str and not end_date:
        return jsonify({"error": "Invalid query param: end_date must be YYYY-MM-DD"}), 400

    where = []
    params = []
    if user_id is not None:
        where.append("user_id=%s")
        params.append(user_id)
    if rec_type is not None:
        where.append("type=%s")
        params.append(rec_type)
    if category is not None:
        where.append("category=%s")
        params.append(category)
    if start_date is not None:
        where.append("date >= %s")
        params.append(str(start_date))
    if end_date is not None:
        where.append("date <= %s")
        params.append(str(end_date))

    sql = """
        SELECT id, user_id, amount, type, category, date, note
        FROM Records
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC"

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(params))
        records = cur.fetchall() or []
        return jsonify({"records": records}), 200
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.put("/records/<int:record_id>")
@authorize(["admin"])
def update_record(record_id: int):
    payload = request.get_json(silent=True) or {}
    validated, response, status = _validate_record_payload(payload)
    if response is not None:
        return response, status

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            UPDATE Records
            SET amount=%s, type=%s, category=%s, date=%s, note=%s
            WHERE id=%s
            """,
            (validated["amount"], validated["type"], validated["category"], validated["date"], validated["note"], record_id),
        )
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "Record not found"}), 404

        cur.execute("SELECT id, user_id, amount, type, category, date, note FROM Records WHERE id=%s LIMIT 1", (record_id,))
        updated = cur.fetchone()
        return jsonify({"record": updated}), 200
    except Exception:
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to update record"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.delete("/records/<int:record_id>")
@authorize(["admin"])
def delete_record(record_id: int):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM Records WHERE id=%s", (record_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Record not found"}), 404
        return jsonify({"deleted": True}), 200
    except Exception:
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to delete record"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

