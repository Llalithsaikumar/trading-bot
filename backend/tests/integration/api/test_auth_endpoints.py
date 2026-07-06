import pytest


@pytest.mark.anyio
async def test_auth_register_and_login(client):
    # 1. Register a new user
    register_payload = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "strong-password-123",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    user_data = response.json()
    assert user_data["email"] == "testuser@example.com"
    assert user_data["username"] == "testuser"

    # 2. Login with registered user
    login_payload = {
        "email": "testuser@example.com",
        "password": "strong-password-123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    login_data = response.json()
    assert "tokens" in login_data
    assert "access_token" in login_data["tokens"]
    assert "refresh_token" in login_data["tokens"]
    assert login_data["user"]["email"] == "testuser@example.com"

    # 3. Try login with incorrect password
    bad_login_payload = {
        "email": "testuser@example.com",
        "password": "wrong-password",
    }
    response = await client.post("/api/v1/auth/login", json=bad_login_payload)
    assert response.status_code == 401
