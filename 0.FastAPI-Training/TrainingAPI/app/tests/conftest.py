import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
async def auth_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "testpass123"},
        )
        login_resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
        )
        token = login_resp.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
