import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_register_user(client):
    email = f"{uuid.uuid4()}@email.com"

    response = await client.post(
        "/auth/register",
        json={
            "name": "Gustavo",
            "email": email,
            "password": "123456"
        }
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    email = f"{uuid.uuid4()}@email.com"

    await client.post(
        "/auth/register",
        json={
            "name": "Teste",
            "email": email,
            "password": "123456"
        }
    )

    response = await client.post(
        "/auth/register",
        json={
            "name": "Teste",
            "email": email,
            "password": "123456"
        }
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    email = f"{uuid.uuid4()}@email.com"

    await client.post(
        "/auth/register",
        json={
            "name": "Login",
            "email": email,
            "password": "123456"
        }
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "123456"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    email = f"{uuid.uuid4()}@email.com"

    await client.post(
        "/auth/register",
        json={
            "name": "Login",
            "email": email,
            "password": "123456"
        }
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "senhaerrada"
        }
    )

    assert response.status_code == 401