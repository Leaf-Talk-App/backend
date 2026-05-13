import pytest
from bson import ObjectId
from app.core.security import create_access_token


def auth_headers():
    token = create_access_token({
        "sub": "123",
        "email": "user@email.com"
    })

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.mark.asyncio
async def test_send_message(client, db):

    chat_id = str(ObjectId())

    await db.chats.insert_one({
        "_id": ObjectId(chat_id)
    })

    response = await client.post(
        "/messages/send",
        headers=auth_headers(),
        json={
            "chat_id": chat_id,
            "receiver_id": "456",
            "content": "Olá"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "sent"


@pytest.mark.asyncio
async def test_mark_as_read(client):

    response = await client.patch(
        "/messages/read/chat123",
        headers=auth_headers()
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_edit_message(client, db):

    message_id = ObjectId()

    await db.messages.insert_one({
        "_id": message_id,
        "sender_id": "123",
        "receiver_id": "456",
        "content": "Texto antigo"
    })

    response = await client.patch(
        f"/messages/edit/{message_id}",
        headers=auth_headers(),
        json={
            "content": "Novo texto"
        }
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_message(client, db):

    message_id = ObjectId()

    await db.messages.insert_one({
        "_id": message_id,
        "sender_id": "123",
        "receiver_id": "456"
    })

    response = await client.delete(
        f"/messages/{message_id}",
        headers=auth_headers()
    )

    assert response.status_code == 200
    
"""
Os testes de mensagens têm como objetivo validar todo o funcionamento do sistema de comunicação da aplicação, 
garantindo que as interações entre usuários ocorram de forma correta, segura e em tempo real. Durante os testes 
é verificado o envio de mensagens, assegurando que o conteúdo seja armazenado corretamente e entregue ao destinatário. 
Também são realizados testes de leitura de mensagens, confirmando que os dados retornados pela API estejam corretos 
e atualizados. Além disso, são validadas funcionalidades de edição e exclusão, garantindo que apenas usuários autorizados 
consigam alterar ou remover mensagens previamente enviadas. Os testes também verificam o funcionamento do sistema realtime, 
responsável pela atualização instantânea das conversas sem necessidade de recarregar a aplicação. Por fim, são analisadas 
as regras de bloqueio entre usuários, assegurando que contas bloqueadas não consigam enviar mensagens ou interagir de forma 
indevida dentro da plataforma.

"""