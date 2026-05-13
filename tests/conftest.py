import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.main import app
import app.core.database as database_module

mock_client = AsyncMongoMockClient()
mock_db = mock_client["leaf_talk_test"]

database_module.db = mock_db

@pytest_asyncio.fixture
async def client():

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:

        yield client


@pytest_asyncio.fixture(autouse=True)
async def clear_database():

    collections = await mock_db.list_collection_names()

    for collection in collections:
        await mock_db[collection].delete_many({})


@pytest_asyncio.fixture
async def db():
    return mock_db
        
"""
O arquivo conftest.py é utilizado para centralizar configurações e recursos compartilhados entre os testes da aplicação, 
evitando repetição de código e facilitando a manutenção do projeto. Nele é criado automaticamente um client de teste, 
responsável por simular requisições para a API sem a necessidade de executar o sistema manualmente. Também é configurado 
um banco de dados fake ou temporário, permitindo que os testes sejam executados de forma segura sem alterar dados reais 
da aplicação. Além disso, o arquivo realiza a limpeza automática das informações utilizadas durante os testes, garantindo 
que cada execução aconteça em um ambiente isolado e consistente. Por fim, o conftest.py pode armazenar métodos reutilizáveis 
de autenticação, como geração de tokens e criação de usuários de teste, tornando o processo de validação mais organizado, 
padronizado e reutilizável em diferentes cenários de teste.

"""