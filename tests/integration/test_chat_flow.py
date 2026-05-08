from bson import ObjectId

def test_complete_chat_flow(client):

    client.post(
        "/auth/register",
        json={
            "name": "Gustavo",
            "email": "g@email.com",
            "password": "123456"
        }
    )

    login = client.post(
        "/auth/login",
        json={
            "email": "g@email.com",
            "password": "123456"
        }
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    chat_id = str(ObjectId())

    response = client.post(
        "/messages/send",
        headers=headers,
        json={
            "chat_id": chat_id,
            "receiver_id": "456",
            "content": "Olá"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "sent"
    
"""
Os testes de fluxo completo têm como objetivo validar o funcionamento integrado de todas as principais funcionalidades 
da aplicação, simulando cenários reais de utilização do sistema do início ao fim. Nesse tipo de teste são verificadas 
as interações entre autenticação, gerenciamento de usuários, envio de mensagens, comunicação em tempo real, banco de dados 
e demais recursos envolvidos no fluxo principal da aplicação de chat. Durante a execução, o sistema é testado de forma 
mais próxima do ambiente real, garantindo que diferentes módulos funcionem corretamente em conjunto e que os dados sejam 
processados de maneira consistente ao longo de toda a operação. Além disso, os testes ajudam a identificar falhas de 
integração, problemas de comunicação entre componentes e comportamentos inesperados que poderiam não ser percebidos em 
testes unitários isolados. Dessa forma, os testes de integração contribuem significativamente para a estabilidade, 
confiabilidade e qualidade geral da aplicação.

"""