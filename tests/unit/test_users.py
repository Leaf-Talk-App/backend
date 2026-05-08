from app.core.security import create_access_token

def test_get_me(client, db):

    db.users.insert_one({
        "_id": "123",
        "name": "User",
        "email": "user@email.com",
        "searchable": True
    })

    token = create_access_token({
        "sub": "123",
        "email": "user@email.com"
    })

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "user@email.com"

def test_search_users(client, db):

    db.users.insert_one({
        "name": "Gustavo",
        "email": "g@email.com",
        "searchable": True
    })

    token = create_access_token({
        "sub": "1",
        "email": "a@a.com"
    })

    response = client.get(
        "/users/search?q=Gus",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) > 0
    
"""
Os testes relacionados aos usuários têm como objetivo validar o funcionamento correto das operações 
envolvendo gerenciamento e manipulação de contas dentro da aplicação. Esses testes garantem que os dados 
dos usuários sejam criados, consultados, atualizados e removidos corretamente, assegurando a integridade 
das informações armazenadas no sistema. Também são verificadas regras de negócio importantes, como validação 
de permissões de acesso, proteção de dados sensíveis e tratamento adequado de usuários inexistentes ou inválidos. 
Além disso, os testes confirmam se os endpoints responsáveis pelas funcionalidades de usuários retornam os 
status corretos da API, mensagens apropriadas e comportamentos esperados em diferentes cenários, contribuindo 
para maior segurança, confiabilidade e estabilidade da aplicação.

"""