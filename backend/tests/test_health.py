def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "BalanceIQ"


def test_register_and_login(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@balanceiq.com",
            "password": "TestPassword123",
            "full_name": "Test User",
        },
    )
    assert register_response.status_code == 200
    tokens = register_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@balanceiq.com", "password": "TestPassword123"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_get_current_user(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "me@balanceiq.com", "password": "Pass123", "full_name": "Me"},
    )
    token = reg.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "me@balanceiq.com"
