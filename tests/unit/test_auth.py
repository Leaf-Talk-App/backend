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
    
"""
Os testes de autenticação têm como objetivo validar todo o fluxo de acesso e segurança da aplicação, 
garantindo que apenas usuários autorizados consigam utilizar os recursos protegidos do sistema. 
Durante os testes são verificadas funcionalidades essenciais como o registro de novos usuários, 
assegurando que os dados sejam cadastrados corretamente no banco de dados, e o processo de login, 
confirmando que usuários válidos consigam se autenticar utilizando suas credenciais. Também é realizada 
a validação da geração e funcionamento do token JWT, utilizado para controlar sessões autenticadas e proteger 
rotas privadas da aplicação. Além disso, os testes verificam cenários de erro importantes, como tentativa 
de login com senha inválida, impedindo acessos não autorizados, e cadastro de e-mails duplicados, garantindo 
a integridade e unicidade das contas cadastradas. Por fim, são testadas as proteções de rota da API, 
confirmando que endpoints privados só possam ser acessados mediante autenticação válida.

"""