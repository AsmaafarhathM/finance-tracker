from tests.fakes import FakeConnection, FakeCursor


def test_mint_token_missing_role_header(client):
    resp = client.post("/auth/token", json={"email": "alice@example.com"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Missing role header"


def test_mint_token_invalid_role(client):
    resp = client.post("/auth/token", headers={"role": "owner"}, json={"email": "alice@example.com"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "Invalid role"


def test_mint_token_missing_email(client):
    resp = client.post("/auth/token", headers={"role": "admin"}, json={})
    assert resp.status_code == 400
    assert "email" in resp.get_json()["error"]


def test_mint_token_user_not_found(client, monkeypatch):
    import app as app_module

    fake_cursor = FakeCursor(fetchone_results=[None])
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(app_module, "get_connection", lambda: fake_conn)

    resp = client.post("/auth/token", headers={"role": "admin"}, json={"email": "alice@example.com"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "User not found"


def test_mint_token_role_mismatch(client, monkeypatch):
    import app as app_module

    fake_cursor = FakeCursor(fetchone_results=[{"id": 1, "email": "alice@example.com", "role": "viewer", "status": 1}])
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(app_module, "get_connection", lambda: fake_conn)

    resp = client.post("/auth/token", headers={"role": "admin"}, json={"email": "alice@example.com"})
    assert resp.status_code == 403
    assert "does not match" in resp.get_json()["error"]


def test_mint_token_success(client, monkeypatch):
    import app as app_module

    fake_cursor = FakeCursor(fetchone_results=[{"id": 1, "email": "alice@example.com", "role": "admin", "status": 1}])
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(app_module, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(app_module, "mint_access_token", lambda user_id, role, email: "mocked.jwt.token")

    resp = client.post("/auth/token", headers={"role": "admin"}, json={"email": "alice@example.com"})
    assert resp.status_code == 200
    assert resp.get_json()["access_token"] == "mocked.jwt.token"
