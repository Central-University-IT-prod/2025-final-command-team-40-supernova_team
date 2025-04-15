import pytest
from fastapi.testclient import TestClient
from starlette import status

from app.main import app

client = TestClient(app)


def test_ping() -> None:
    response = client.get("/ping")
    assert response.status_code == status.HTTP_200_OK


def test_auth_register() -> None:
    response = client.post(
        "/auth/register", data={"username": "user_1", "password": "qwerty123"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.content) > 0


def test_auth_login(request: pytest.FixtureRequest) -> None:
    response = client.post(
        "/auth/login", data={"username": "user_1", "password": "qwerty123"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.content) > 0
    json = response.json()
    token = json.token

    request.config.cache.set("token", token)


def test_auth_ping(request: pytest.FixtureRequest) -> None:
    token = request.config.cache.get("token", "")

    response = client.get(
        "/auth/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK


def test_get_watchlist(request: pytest.FixtureRequest) -> None:
    token = request.config.cache.get("token", "")

    response = client.get(
        "/watchlist/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
