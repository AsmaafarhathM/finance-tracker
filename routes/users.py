from flask import Blueprint, jsonify, request

from db import get_connection
from middleware.auth import ROLES, authorize


bp = Blueprint("users", __name__)


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    email = email.strip().lower()
    return email if email else None


def _normalize_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return None


@bp.post("/users")
@authorize(["admin"])
def create_user():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    email = _normalize_email(payload.get("email"))
    role = (payload.get("role") or "").strip().lower()
    status_raw = payload.get("status", True)
    status = _normalize_bool(status_raw)
    if status is None:
        status = True

    if not name:
        return jsonify({"error": "Missing required field: name"}), 400
    if not email:
        return jsonify({"error": "Missing required field: email"}), 400
    if role not in ROLES:
        return jsonify({"error": "Invalid role. Must be one of admin/analyst/viewer"}), 400

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO Users (name, email, role, status)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, role, int(status)),
        )
        conn.commit()
        user_id = cur.lastrowid
        return jsonify({"id": user_id, "name": name, "email": email, "role": role, "status": bool(status)}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        if "Duplicate" in str(e) or "duplicate" in str(e):
            return jsonify({"error": "Email already exists"}), 400
        return jsonify({"error": "Failed to create user"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@bp.get("/users")
@authorize(["admin", "analyst", "viewer"])
def list_users():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, role, status FROM Users ORDER BY id DESC")
        users = cur.fetchall() or []
        # mysql returns 0/1 for BOOLEAN; normalize to bool for JSON.
        for u in users:
            u["status"] = bool(u.get("status"))
        return jsonify({"users": users}), 200
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

