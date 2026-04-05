def test_missing_role_header_returns_401(client):
    resp = client.get("/users")
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Missing role header"


def test_forbidden_role_returns_403(client):
    resp = client.post("/users", headers={"role": "viewer"}, json={"name": "A", "email": "a@x.com", "role": "admin"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "Forbidden: role not allowed"


def test_records_requires_bearer_token(client):
    payload = {"amount": 10, "type": "income", "category": "Salary", "date": "2026-04-02"}
    resp = client.post("/records", headers={"role": "admin"}, json=payload)
    assert resp.status_code == 401
    assert "Authorization Bearer token" in resp.get_json()["error"]


def test_records_invalid_bearer_token_returns_401(client):
    payload = {"amount": 10, "type": "income", "category": "Salary", "date": "2026-04-02"}
    resp = client.post(
        "/records",
        headers={"role": "admin", "Authorization": "Bearer not-a-valid-jwt"},
        json=payload,
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Invalid token"
