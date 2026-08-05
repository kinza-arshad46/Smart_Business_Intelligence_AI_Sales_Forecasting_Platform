def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_admin_login(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@salesbi.local", "password": "Admin@123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@salesbi.local", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_register_and_login_new_user(client):
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "testuser1@example.com",
        "password": "TestPass123",
    })
    assert resp.status_code == 201

    login = client.post("/api/v1/auth/login", data={
        "username": "testuser1@example.com", "password": "TestPass123",
    })
    assert login.status_code == 200


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, admin_token):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@salesbi.local"
