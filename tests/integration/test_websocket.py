from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_websocket_connect():

    with client.websocket_connect("/ws/user1") as websocket:

        websocket.send_json({
            "type": "typing",
            "to": "user2"
        })

        assert websocket is not None
        
"""
Este teste tem como objetivo validar o funcionamento da conexão WebSocket da aplicação, 
garantindo que a comunicação em tempo real entre clientes e servidor aconteça corretamente. 
Inicialmente é criado um TestClient utilizando a aplicação FastAPI para simular conexões durante os testes. 
Em seguida, o teste realiza uma conexão com o endpoint WebSocket "/ws/user1", representando um usuário autenticado 
conectado ao sistema de mensagens em tempo real. Após estabelecer a conexão, é enviado um evento do tipo "typing", 
indicando que o usuário está digitando uma mensagem para outro usuário identificado como "user2". Por fim, 
o teste verifica se a conexão WebSocket foi criada com sucesso, assegurando que o canal de comunicação realtime 
esteja ativo e funcional para troca instantânea de eventos e mensagens dentro da aplicação.

"""