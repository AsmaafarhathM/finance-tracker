from tests.fakes import FakeConnection, FakeCursor


def test_create_user_success(client, monkeypatch):
    import routes.users as users_module

    fake_cursor = FakeCursor(lastrowid=42)
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(users_module, "get_connection", lambda: fake_conn)

    resp = client.post(
        "/users",
        headers={"role": "admin"},
        json={"name": "Alice", "email": "alice@example.com", "role": "admin"},
    )

    data = resp.get_json()
    assert resp.status_code == 201
    assert data["id"] == 42
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert data["role"] == "admin"
    assert data["status"] is True


def test_create_user_duplicate_email_returns_400(client, monkeypatch):
    import routes.users as users_module

    fake_cursor = FakeCursor(raise_on_execute=Exception("Duplicate entry"))
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(users_module, "get_connection", lambda: fake_conn)

    resp = client.post(
        "/users",
        headers={"role": "admin"},
        json={"name": "Alice", "email": "alice@example.com", "role": "admin"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Email already exists"


def test_create_user_validation_errors(client):
    resp = client.post("/users", headers={"role": "admin"}, json={"email": "x@y.com", "role": "admin"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Missing required field: name"

    resp = client.post("/users", headers={"role": "admin"}, json={"name": "A", "email": "x@y.com", "role": "owner"})
    assert resp.status_code == 400
    assert "Invalid role" in resp.get_json()["error"]


def test_list_users_returns_bool_status(client, monkeypatch):
    import routes.users as users_module

    fake_cursor = FakeCursor(
        fetchall_results=[
            [
                {"id": 1, "name": "A", "email": "a@x.com", "role": "admin", "status": 1},
                {"id": 2, "name": "B", "email": "b@x.com", "role": "viewer", "status": 0},
            ]
        ]
    )
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(users_module, "get_connection", lambda: fake_conn)

    resp = client.get("/users", headers={"role": "viewer"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["users"][0]["status"] is True
    assert data["users"][1]["status"] is False
