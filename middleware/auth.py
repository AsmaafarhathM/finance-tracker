import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import jsonify, request


ROLES = {"admin", "analyst", "viewer"}


def _normalize_role(role: str | None) -> str | None:
    if role is None:
        return None
    role = role.strip().lower()
    return role if role else None


def authorize(allowed_roles: list[str]):
    """
    Simple RBAC middleware.

    Reads role from request headers:
    - If role is missing -> 401
    - If role not allowed -> 403
    - Else -> allow the request
    """

    allowed = {_normalize_role(r) for r in allowed_roles if r is not None}
    allowed.discard(None)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = _normalize_role(request.headers.get("role"))
            if not role:
                return jsonify({"error": "Missing role header"}), 401
            if role not in allowed:
                return jsonify({"error": "Forbidden: role not allowed"}), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


def _get_bearer_token() -> str | None:
    # Expected: Authorization: Bearer <token>
    auth = request.headers.get("Authorization", "")
    parts = auth.split()
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev_secret_change_me")


def decode_access_token(token: str) -> dict:
    """
    Decode JWT and return its payload.
    Raises jwt exceptions on failures.
    """

    return jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
        options={"require": ["sub", "exp"]},
    )


def require_jwt_payload():
    """
    For routes that need JWT.

    Returns:
      (payload_dict, None) on success
      (None, (jsonify_response, status_code)) on failure
    """

    token = _get_bearer_token()
    if not token:
        return None, (jsonify({"error": "Missing or invalid Authorization Bearer token"}), 401)

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Token expired"}), 401)
    except jwt.PyJWTError:
        return None, (jsonify({"error": "Invalid token"}), 401)

    # sub is required to map to user_id
    user_id = payload.get("sub")
    if user_id is None:
        return None, (jsonify({"error": "Invalid token payload (missing sub)"}), 401)

    return payload, None


def mint_access_token(user_id: int, role: str, email: str) -> str:
    alg = os.getenv("JWT_ALGORITHM", "HS256")
    secret = get_jwt_secret()

    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(hours=1)
    payload = {
        # JWT spec expects subject to be a string.
        "sub": str(user_id),
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    # PyJWT returns a string in v2.x
    return jwt.encode(payload, secret, algorithm=alg)

