from tests.fakes import FakeConnection, FakeCursor


def test_summary_income_success(client, monkeypatch):
    import routes.summary as summary_module

    fake_cursor = FakeCursor(fetchone_results=[{"total_income": 1200.5}])
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(summary_module, "get_connection", lambda: fake_conn)

    resp = client.get("/summary/income", headers={"role": "analyst"})
    assert resp.status_code == 200
    assert resp.get_json()["total_income"] == 1200.5


def test_summary_balance_viewer_access(client, monkeypatch):
    import routes.summary as summary_module

    fake_cursor = FakeCursor(fetchone_results=[{"balance": 800.0}])
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(summary_module, "get_connection", lambda: fake_conn)

    resp = client.get("/summary/balance", headers={"role": "viewer"})
    assert resp.status_code == 200
    assert resp.get_json()["balance"] == 800.0


def test_summary_category_shape(client, monkeypatch):
    import routes.summary as summary_module

    fake_cursor = FakeCursor(
        fetchall_results=[
            [{"category": "Salary", "total": 2000}],
            [{"category": "Food", "total": 400}],
        ]
    )
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(summary_module, "get_connection", lambda: fake_conn)

    resp = client.get("/summary/category", headers={"role": "viewer"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["income_by_category"][0]["category"] == "Salary"
    assert data["expense_by_category"][0]["category"] == "Food"
