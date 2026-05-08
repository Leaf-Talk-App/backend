import pytest
import mongomock
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_database

mock_client = mongomock.MongoClient()
mock_db = mock_client["leaf_talk_test"]

def override_get_database():
    return mock_db

app.dependency_overrides[get_database] = override_get_database

@pytest.fixture

def client():
    return TestClient(app)

@pytest.fixture

def db():
    return mock_db

@pytest.fixture(autouse=True)

def clear_database():
    collections = mock_db.list_collection_names()

    for collection in collections:
        mock_db[collection].delete_many({})
        
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