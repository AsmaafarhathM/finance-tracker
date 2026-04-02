import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from flask_cors import CORS

from db import init_db, get_connection
from middleware.auth import ROLES, mint_access_token


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    CORS(app)

    init_db()

    # Register blueprints
    from routes.users import bp as users_bp
    from routes.records import bp as records_bp
    from routes.summary import bp as summary_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(summary_bp)

    # Simple HTML dashboard (same-origin; uses role header via fetch).
    @app.get("/")
    @app.get("/dashboard")
    def dashboard_page():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "dashboard.html",
        )

    # JWT minting endpoint (bonus) for easy Postman testing.
    @app.post("/auth/token")
    def mint_token():
        role = (request.headers.get("role") or "").strip().lower()
        if not role:
            return jsonify({"error": "Missing role header"}), 401
        if role not in ROLES:
            return jsonify({"error": "Invalid role"}), 403

        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or "").strip().lower()
        if not email:
            return jsonify({"error": "Missing required field: email"}), 400

        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, email, role, status FROM Users WHERE email=%s LIMIT 1", (email,))
            user = cur.fetchone()

            if not user or not user.get("status"):
                return jsonify({"error": "User not found"}), 404

            if user["role"] != role:
                return jsonify({"error": "Role header does not match user role"}), 403

            token = mint_access_token(user_id=int(user["id"]), role=user["role"], email=user["email"])
            return jsonify({"access_token": token}), 200
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    # JSON error handling
    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        response = err.get_response()
        response_body = {"error": err.name}
        try:
            if response and response.content_length:
                # Sometimes Werkzeug already includes a body; we ignore to keep JSON consistent.
                pass
        except Exception:
            pass
        return jsonify(response_body), err.code or 500

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(_err):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=debug)

