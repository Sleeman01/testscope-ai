import pytest


@pytest.mark.parametrize("password", ["wrong", ""])
def test_login_rejects_invalid_password(client, password):
    """Login must reject invalid passwords with 401."""
    response = client.post("/api/login", json={"password": password})
    assert response.status_code == 401
