from tests.fakes import FakeConnection, FakeCursor


def test_create_record_success(client, monkeypatch):
    import routes.records as records_module

    fake_cursor = FakeCursor(lastrowid=7)
    fake_conn = FakeConnection(fake_cursor)

    monkeypatch.setattr(records_module, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(records_module, "require_jwt_payload", lambda: ({"sub": "1"}, None))

    payload = {"amount": 1250.5, "type": "income", "category": "Salary", "date": "2026-04-02", "note": "April"}
    resp = client.post("/records", headers={"role": "admin"}, json=payload)
    data = resp.get_json()

    assert resp.status_code == 201
    assert data["id"] == 7
    assert data["user_id"] == 1
    assert data["type"] == "income"
    assert data["category"] == "Salary"


def test_create_record_validation_errors(client, monkeypatch):
    import routes.records as records_module

    monkeypatch.setattr(records_module, "require_jwt_payload", lambda: ({"sub": "1"}, None))

    payload = {"amount": -1, "type": "income", "category": "Salary", "date": "2026-04-02"}
    resp = client.post("/records", headers={"role": "admin", "Authorization": "Bearer token"}, json=payload)
    assert resp.status_code == 400
    assert "Invalid amount" in resp.get_json()["error"]

    payload = {"amount": 10, "type": "bonus", "category": "Salary", "date": "2026-04-02"}
    resp = client.post("/records", headers={"role": "admin", "Authorization": "Bearer token"}, json=payload)
    assert resp.status_code == 400
    assert "Invalid type" in resp.get_json()["error"]


def test_list_records_invalid_filters(client):
    resp = client.get("/records?user_id=abc", headers={"role": "admin"})
    assert resp.status_code == 400
    assert "user_id" in resp.get_json()["error"]

    resp = client.get("/records?type=bonus", headers={"role": "admin"})
    assert resp.status_code == 400
    assert "type" in resp.get_json()["error"]


def test_list_records_success(client, monkeypatch):
    import routes.records as records_module

    fake_cursor = FakeCursor(
        fetchall_results=[
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "amount": 50.0,
                    "type": "expense",
                    "category": "Food",
                    "date": "2026-04-01",
                    "note": "Lunch",
                }
            ]
        ]
    )
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(records_module, "get_connection", lambda: fake_conn)

    resp = client.get("/records?category=Food", headers={"role": "viewer"})
    assert resp.status_code == 200
    assert len(resp.get_json()["records"]) == 1


def test_update_record_not_found(client, monkeypatch):
    import routes.records as records_module

    fake_cursor = FakeCursor(rowcount=0)
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(records_module, "get_connection", lambda: fake_conn)

    payload = {"amount": 10, "type": "expense", "category": "Food", "date": "2026-04-02"}
    resp = client.put("/records/999", headers={"role": "admin"}, json=payload)
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Record not found"


def test_delete_record_not_found(client, monkeypatch):
    import routes.records as records_module

    fake_cursor = FakeCursor(rowcount=0)
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(records_module, "get_connection", lambda: fake_conn)

    resp = client.delete("/records/999", headers={"role": "admin"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Record not found"
