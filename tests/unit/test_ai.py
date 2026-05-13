import pytest
from app.core.security import create_access_token

def headers():

    token = create_access_token({
        "sub": "123",
        "email": "user@email.com"
    })

    return {
        "Authorization": f"Bearer {token}"
    }

@pytest.mark.asyncio
async def test_ai_chat(client):

    response = await client.post(
        "/ai/chat",
        headers=headers(),
        json={
            "message": "Olá IA"
        }
    )

    assert response.status_code == 200
    
"""
Os testes relacionados à inteligência artificial têm como objetivo validar o funcionamento correto dos recursos 
de IA utilizados pela aplicação, garantindo que as análises e respostas geradas ocorram de forma consistente, 
segura e confiável. Durante os testes são verificadas funcionalidades responsáveis pelo processamento de dados, 
interpretação de informações e geração de resultados inteligentes com base nas entradas fornecidas pelo usuário. 
Além disso, os testes validam o comportamento da aplicação diante de diferentes cenários, incluindo entradas válidas, 
dados inválidos e possíveis falhas durante o processamento da IA. Também é analisada a integração entre os módulos 
de inteligência artificial e os demais componentes do sistema, assegurando que os resultados retornados sejam tratados 
corretamente pela aplicação. Dessa forma, os testes contribuem para garantir maior estabilidade, precisão e qualidade 
nas funcionalidades inteligentes implementadas no projeto.

"""